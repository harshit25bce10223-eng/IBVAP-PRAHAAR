"""E2E traceability run for Component 7 (ANPR + Vehicle Intelligence) — spec §53.

Exercises the real chain over HTTP against a live uvicorn server and captures
the actual server-generated identifiers:

    C5 Detection -> C6 Track -> C7 Vehicle/Plate Sighting -> C4 Event/Correlation
    -> C1 Risk/Incident -> C3 Evidence

Honest limitations recorded in the report (not papered over):

1. C5 detection creation has NO working HTTP path in this repo:
   POST /api/v1/detections/internal/ingest is a 501 stub
   (app/api/routes/detection/routes.py:540-553) and no frame-ingestion HTTP
   route exists. The seeded detection is therefore created through the REAL
   C5 pipeline (DemoInferenceProvider -> DetectionNormalizer ->
   DetectionRepository.create_batch via DetectionService._process_frame_direct,
   app/domain/detection/service.py:175-319) in a pre-server child process.
   Everything after the first read-back runs over HTTP. A VEHICLE detection is
   REQUIRED for this run (the C7 chain needs a vehicle) — the seeder fails hard
   if 12 demo frames produce none.
2. plate_read_id is not exposed by any ANPR read API (VehicleSightingResponse /
   PlateReadResponse omit it — app/schemas/anpr/schemas.py:75-135). It is
   captured by a read-only DB read-back of the row persisted through the real
   HTTP ingestion path: an actual value, never fabricated (§53).
3. The plate string and its candidate are harness-supplied inputs. The E2E
   proves ingestion, persistence, traceability and the C4/C1/C3 chain — not OCR
   accuracy: no OCR model runs in this task (§54).
4. DemoANPRProvider / demo inference+tracking providers are active (repo demo
   mode). No production ANPR model selection/training; no production-capacity
   claim (§54).

Usage (from C:/SIH/ibvap-backend, venv python):

    venv/Scripts/python.exe scripts/e2e_c7_traceability.py
    venv/Scripts/python.exe scripts/e2e_c7_traceability.py --bootstrap-only
"""

from __future__ import annotations

import argparse
import asyncio
import base64
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DB_REL = "tests/test_dbs/e2e_c7_run.db"
DB_PATH = BACKEND_ROOT / DB_REL
REPORT_PATH = BACKEND_ROOT / "tests/test_dbs/e2e_c7_traceability_report.json"
PORT = 8123
BASE = f"http://127.0.0.1:{PORT}"

INTERNAL_HEADER = {"X-Internal-Service": "edge-ingest"}

CAMERA_ID = "CAM-E2E-C7-01"
SECTOR_ID = "SEC-E2E-C7-01"
ZONE_NAME = "E2E C7 ZONE"
SIGHTING_ID = "SGT-C7E2E-0001"
PLATE = "PB10C7E2001"  # harness-supplied string (recorded as such)
CANDIDATE_PLATE = "PB10C7E20O1"  # plausible OCR alternative (O<->0)
CANDIDATE_SEARCH_TOKEN = "20O1"  # matches only the candidate, not the read
IDEMPOTENCY_PROBE_PLATE = "PB10C7E2OOO"  # would overwrite raw_read if a bug existed
SEED_FRAME_ATTEMPTS = 12

# Zone polygon (normalized 0..1) — full-frame square minus an epsilon margin so
# any seeded bbox bottom-center is inside. Deterministic, not random.
ZONE_POLYGON = [
    [0.001, 0.001],
    [0.999, 0.001],
    [0.999, 0.999],
    [0.001, 0.999],
]

CLASS_TO_OBJECT_TYPE = {"PERSON": "HUMAN", "VEHICLE": "VEHICLE", "ANIMAL": "ANIMAL"}


class StepFailed(RuntimeError):
    pass


def _log(msg: str) -> None:
    print(f"[e2e] {msg}", flush=True)


def _emit_report(report: dict) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    _log(f"report written: {REPORT_PATH}")


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise StepFailed(msg)


def _show(label: str, payload) -> None:
    text = json.dumps(payload, indent=2, sort_keys=True, default=str)
    if len(text) > 4000:
        text = text[:4000] + "\n... (truncated for display)"
    print(f"--- {label} ---\n{text}", flush=True)


def _safe_json(response) -> object:
    try:
        return response.json()
    except Exception:  # noqa: BLE001
        return {"_raw": response.text[:2000]}


def _pick(d: object, *keys, default=None):
    """First present non-None value among camelCase/snake_case keys."""
    if isinstance(d, dict):
        for k in keys:
            if d.get(k) is not None:
                return d[k]
    return default


def _is_night_utc(iso_ts: str) -> bool:
    dt = datetime.fromisoformat(iso_ts.replace("Z", "+00:00"))
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    hour = dt.astimezone(timezone.utc).hour
    return hour >= 18 or hour < 6


# ─────────────────────────────────────────────────────────────────────────────
# Schema bootstrap (same pattern as the C4/C6 E2E harnesses)
# ─────────────────────────────────────────────────────────────────────────────

def bootstrap_schema() -> None:
    """Create the schema with the REAL model registry (TrackV2 included).

    `alembic upgrade head` cannot build a fresh DB (pre-existing C7 migration
    inconsistency: 20260919_ed2783c7ad30 re-adds `sync_state` already created by
    20260919_e1467df5c282 -> "duplicate column name"). The E2E therefore
    bootstraps schema from the model metadata, in a child process started with a
    non-test environment so that app/models/__init__.py registers TrackV2.
    """
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()

    code = (
        "import asyncio\n"
        "from app.db.database import Base, engine\n"
        "import app.models  # noqa: F401  (registers every model)\n"
        "async def main():\n"
        "    async with engine.begin() as conn:\n"
        "        await conn.run_sync(Base.metadata.create_all)\n"
        "    await engine.dispose()\n"
        "    print('SCHEMA_OK')\n"
        "asyncio.run(main())\n"
    )
    env = dict(os.environ)
    env["DATABASE_URL"] = f"sqlite+aiosqlite:///./{DB_REL}"
    env.pop("PYTEST_CURRENT_TEST", None)
    env["ENV"] = "development"
    env["PYTHONUTF8"] = "1"
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(BACKEND_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0 or "SCHEMA_OK" not in proc.stdout:
        raise StepFailed(
            "schema bootstrap failed\n"
            f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
        )
    _log(f"schema bootstrapped: {DB_REL}")


# ─────────────────────────────────────────────────────────────────────────────
# C5 seed — real detection pipeline in a child process (pre-server)
# ─────────────────────────────────────────────────────────────────────────────

async def _seed_child_run() -> dict:
    import numpy as np  # noqa: F401  (venv dependency, detection domain)

    from app.db.database import SessionLocal, engine
    import app.models  # noqa: F401  (registers every model)
    from app.models.detection import DetectionConfig
    from app.domain.detection.service import DetectionService

    result: dict = {"camera_id": CAMERA_ID, "frames": [], "detection": None}
    chosen: dict | None = None
    try:
        async with SessionLocal() as session:
            session.add(
                DetectionConfig(
                    camera_id=CAMERA_ID,
                    provider="demo",
                    model_name="demo-detector",
                    model_version="1.0.0",
                    confidence_threshold=0.3,
                    max_detections=20,
                    active=True,
                )
            )
            await session.commit()

            service = DetectionService(session)
            try:
                for i in range(SEED_FRAME_ATTEMPTS):
                    frame = np.zeros((720, 1280, 3), dtype=np.uint8)
                    frame_id = f"FRM-C7E2E-{i:03d}"
                    created = await service._process_frame_direct(
                        frame,
                        CAMERA_ID,
                        frame_id,
                        frame_width=1280,
                        frame_height=720,
                        observed_at=datetime.now(timezone.utc).isoformat(),
                    )
                    await session.commit()
                    result["frames"].append(
                        {
                            "frame_id": frame_id,
                            "created": len(created),
                            "classes": [d.class_name for d in created],
                        }
                    )
                    # C7 chain REQUIRES a VEHICLE detection; the seeder fails
                    # hard if none appears (deterministic demo provider).
                    usable = [d for d in created if d.class_name == "VEHICLE"]
                    if usable:
                        usable.sort(key=lambda d: -(d.confidence or 0))
                        d = usable[0]
                        obs = d.observed_at
                        chosen = {
                            "detection_id": d.detection_id,
                            "camera_id": d.camera_id,
                            "frame_id": d.frame_id,
                            "class_name": d.class_name,
                            "provider_class": d.provider_class,
                            "confidence": d.confidence,
                            "observed_at": obs.isoformat() if isinstance(obs, datetime) else str(obs),
                            "bbox_x": d.bbox_x,
                            "bbox_y": d.bbox_y,
                            "bbox_width": d.bbox_width,
                            "bbox_height": d.bbox_height,
                            "source": d.source,
                            "provider": d.provider,
                        }
                        break
            finally:
                await service.shutdown_all_providers()
    finally:
        await engine.dispose()

    result["detection"] = chosen
    print("SEED_JSON:" + json.dumps(result, default=str), flush=True)
    return result


def _seed_child_main() -> int:
    result = asyncio.run(_seed_child_run())
    return 0 if result.get("detection") else 2


def seed_c5_detection() -> dict:
    """Spawn the seed child (real C5 pipeline) with the E2E database env."""
    env = dict(os.environ)
    env["DATABASE_URL"] = f"sqlite+aiosqlite:///./{DB_REL}"
    env.pop("PYTEST_CURRENT_TEST", None)
    env["ENV"] = "development"
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONUTF8"] = "1"
    # Script mode puts scripts/ on sys.path[0]; the backend root must be importable.
    env["PYTHONPATH"] = str(BACKEND_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--seed-c5-child"],
        cwd=str(BACKEND_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=300,
    )
    marker = "SEED_JSON:"
    seed_line = None
    for line in proc.stdout.splitlines():
        if line.startswith(marker):
            seed_line = line[len(marker):]
    if proc.returncode != 0 or not seed_line:
        raise StepFailed(
            "C5 seed child failed\n"
            f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
        )
    payload = json.loads(seed_line)
    frames = len(payload.get("frames", []))
    _require(
        bool(payload.get("detection")),
        f"no VEHICLE detection after {frames} demo frame(s): {payload}",
    )
    _log(
        "C5 seed: detection "
        f"{payload['detection']['detection_id']} class={payload['detection']['class_name']} "
        f"after {frames} frame(s)"
    )
    return payload


# ─────────────────────────────────────────────────────────────────────────────
# DB read-back child (read-only) — captures plate_read_id (§53)
# ─────────────────────────────────────────────────────────────────────────────

async def _db_check_child_run() -> dict:
    from sqlalchemy import select

    from app.db.database import SessionLocal, engine
    import app.models  # noqa: F401  (registers every model)
    from app.models.anpr.models import PlateCandidate, PlateRead, VehicleSighting

    out: dict = {"sighting": None, "plate_read": None, "candidates": []}
    try:
        async with SessionLocal() as session:
            vs = (
                await session.execute(
                    select(VehicleSighting).where(VehicleSighting.sighting_id == SIGHTING_ID)
                )
            ).scalar_one_or_none()
            if vs is not None:
                out["sighting"] = {
                    "sighting_id": vs.sighting_id,
                    "camera_id": vs.camera_id,
                    "detection_id": vs.detection_id,
                    "track_id": vs.track_id,
                    "vehicle_id": vs.vehicle_id,
                    "plate_read_id": vs.plate_read_id,
                    "plate_quality": vs.plate_quality,
                    "vehicle_class": vs.vehicle_class,
                    "vehicle_color": vs.vehicle_color,
                    "vehicle_direction": vs.vehicle_direction,
                    "provider": vs.provider,
                    "provider_version": vs.provider_version,
                    "source": vs.source,
                }
                if vs.plate_read_id:
                    pr = (
                        await session.execute(
                            select(PlateRead).where(PlateRead.plate_read_id == vs.plate_read_id)
                        )
                    ).scalar_one_or_none()
                    if pr is not None:
                        out["plate_read"] = {
                            "plate_read_id": pr.plate_read_id,
                            "sighting_id": pr.sighting_id,
                            "raw_read": pr.raw_read,
                            "normalized_read": pr.normalized_read,
                            "display_read": pr.display_read,
                            "confidence": pr.confidence,
                            "format_status": pr.format_status,
                            "quality": pr.quality,
                            "provider": pr.provider,
                            "provider_version": pr.provider_version,
                        }
                    cands = (
                        await session.execute(
                            select(PlateCandidate)
                            .where(PlateCandidate.plate_read_id == vs.plate_read_id)
                            .order_by(PlateCandidate.rank)
                        )
                    ).scalars().all()
                    out["candidates"] = [
                        {
                            "candidate_id": c.candidate_id,
                            "rank": c.rank,
                            "raw_read": c.raw_read,
                            "normalized_read": c.normalized_read,
                            "confidence": c.confidence,
                        }
                        for c in cands
                    ]
    finally:
        await engine.dispose()

    print("CHECK_JSON:" + json.dumps(out, default=str), flush=True)
    return out


def db_check_readback() -> dict:
    """Spawn the read-only DB check child with the E2E database env."""
    env = dict(os.environ)
    env["DATABASE_URL"] = f"sqlite+aiosqlite:///./{DB_REL}"
    env.pop("PYTEST_CURRENT_TEST", None)
    env["ENV"] = "development"
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONUTF8"] = "1"
    env["PYTHONPATH"] = str(BACKEND_ROOT) + os.pathsep + env.get("PYTHONPATH", "")
    proc = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), "--db-check-child"],
        cwd=str(BACKEND_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    marker = "CHECK_JSON:"
    check_line = None
    for line in proc.stdout.splitlines():
        if line.startswith(marker):
            check_line = line[len(marker):]
    if proc.returncode != 0 or not check_line:
        raise StepFailed(
            "DB check child failed\n"
            f"stdout: {proc.stdout}\nstderr: {proc.stderr}"
        )
    return json.loads(check_line)


# ─────────────────────────────────────────────────────────────────────────────
# Server lifecycle (same pattern as the C4/C6 E2E harnesses)
# ─────────────────────────────────────────────────────────────────────────────

def start_server() -> tuple[subprocess.Popen, Path]:
    log_path = BACKEND_ROOT / "tests/test_dbs/e2e_c7_uvicorn.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = open(log_path, "w", encoding="utf-8")  # noqa: SIM115 — closed by caller
    env = dict(os.environ)
    env["DATABASE_URL"] = f"sqlite+aiosqlite:///./{DB_REL}"
    env.pop("PYTEST_CURRENT_TEST", None)
    env["ENV"] = "development"
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONUTF8"] = "1"
    proc = subprocess.Popen(
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:app",
            "--host",
            "127.0.0.1",
            "--port",
            str(PORT),
            "--log-level",
            "info",
        ],
        cwd=str(BACKEND_ROOT),
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
    )
    proc._e2e_log_file = log_file  # type: ignore[attr-defined]
    _log(f"uvicorn starting on port {PORT} (pid {proc.pid}), log: {log_path}")
    return proc, log_path


async def wait_for_health(client, timeout_s: float = 60.0) -> None:
    deadline = time.time() + timeout_s
    last_err: str | None = None
    while time.time() < deadline:
        try:
            r = await client.get(f"{BASE}/api/v1/health", timeout=3.0)
            if r.status_code == 200:
                _log("server healthy")
                return
            last_err = f"status {r.status_code}"
        except Exception as exc:  # noqa: BLE001
            last_err = f"{type(exc).__name__}: {exc}"
        await asyncio.sleep(0.5)
    raise StepFailed(f"server did not become healthy in {timeout_s}s (last: {last_err})")


# ─────────────────────────────────────────────────────────────────────────────
# Chain
# ─────────────────────────────────────────────────────────────────────────────

async def run_chain(seed: dict) -> dict:
    import httpx

    detection = seed["detection"]
    detection_id = detection["detection_id"]

    report: dict = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "base_url": BASE,
        "database": DB_REL,
        "chain": (
            "C5 Detection -> C6 Track -> C7 Vehicle/Plate Sighting -> "
            "C4 Event/Correlation -> C1 Risk/Incident -> C3 Evidence"
        ),
        "scenario": {
            "camera_id": CAMERA_ID,
            "sector_id": SECTOR_ID,
            "zone_name": ZONE_NAME,
            "zone_polygon": ZONE_POLYGON,
            "seeded_detection": detection,
            "seed_frames": seed["frames"],
            "request_supplied_sighting_id": SIGHTING_ID,
            "harness_supplied_plate": PLATE,
            "harness_supplied_candidate": CANDIDATE_PLATE,
        },
        "limitations": {
            "c5_no_http_ingest": (
                "C5 detection creation has no working HTTP path: "
                "POST /api/v1/detections/internal/ingest is a 501 stub "
                "(app/api/routes/detection/routes.py:540-553) and no frame-ingestion "
                "route exists. The detection above was created through the REAL C5 "
                "pipeline (demo provider -> normalizer -> repository.create_batch via "
                "DetectionService._process_frame_direct, app/domain/detection/service.py:175-319) "
                "in a pre-server child process; everything after read-back runs over HTTP."
            ),
            "plate_read_id_surface": (
                "plate_read_id is not exposed by any ANPR read API "
                "(VehicleSightingResponse / PlateReadResponse omit it, "
                "app/schemas/anpr/schemas.py:75-135). It is captured by a read-only DB "
                "read-back of the row persisted through the real HTTP ingestion path — "
                "an actual value, never fabricated (§53)."
            ),
            "harness_supplied_plate": (
                "The plate string and its candidate are harness-supplied inputs. This "
                "run proves ingestion, persistence, traceability and the C4/C1/C3 "
                "chain — not OCR accuracy: no OCR model runs in this task (§54)."
            ),
            "demo_providers": (
                "DEMO ANPR/inference/tracking providers are active (repo demo mode). "
                "No production ANPR model selection or training; no production-capacity claim."
            ),
        },
        "steps": {},
        "ids": {},
        "failures": [],
    }

    async with httpx.AsyncClient(timeout=60.0) as client:
        await wait_for_health(client)

        # ── Step 1: C5 read-back over HTTP ───────────────────────────────────
        r = await client.get(f"{BASE}/api/v1/detections/{detection_id}")
        _show("GET /api/v1/detections/{id}", {"status": r.status_code, "body": _safe_json(r)})
        _require(r.status_code == 200, f"detection read-back failed: {r.status_code} {r.text}")
        det = _safe_json(r)
        det_class = _pick(det, "class_name", "className")
        det_bbox = det.get("bbox") or {}
        det_observed_at = _pick(det, "observed_at", "observedAt")
        _require(
            det_class == detection["class_name"],
            f"detection class mismatch: {det_class} != {detection['class_name']}",
        )
        _require(bool(det_observed_at), f"observed_at missing in read-back: {det}")
        for axis in ("x", "y", "width", "height"):
            rb = float(det_bbox.get(axis))
            sd = float(detection[f"bbox_{axis}"])
            _require(abs(rb - sd) < 1e-9, f"bbox.{axis} mismatch: {rb} != {sd}")
        report["steps"]["1_detection_read_back"] = {
            "status_code": 200,
            "detection_id": detection_id,
            "class_name": det_class,
            "confidence": _pick(det, "confidence"),
            "bbox": det_bbox,
            "observed_at": det_observed_at,
            "frame_id": _pick(det, "frame_id", "frameId"),
            "source": _pick(det, "source"),
            "provider": _pick(det, "provider"),
        }
        report["ids"]["detection_id"] = detection_id
        report["ids"]["detection_class"] = det_class

        object_type = CLASS_TO_OBJECT_TYPE[det_class]
        is_night = _is_night_utc(det_observed_at)

        # ── Step 2: Zone (C1) ────────────────────────────────────────────────
        zone_body = {
            "camera_id": CAMERA_ID,
            "name": ZONE_NAME,
            "polygon": [{"x": p[0], "y": p[1]} for p in ZONE_POLYGON],
            "rules": {"allowed_object_types": ["HUMAN", "VEHICLE", "ANIMAL"]},
            "active": True,
        }
        r = await client.post(f"{BASE}/api/v1/zones", json=zone_body)
        _show("POST /api/v1/zones", {"status": r.status_code, "body": _safe_json(r)})
        _require(r.status_code in (200, 201), f"zone create failed: {r.status_code} {r.text}")
        zone = _safe_json(r)
        zone_id = _pick(zone, "zone_id", "zoneId")
        _require(bool(zone_id), f"zone_id missing in response: {zone}")
        report["steps"]["2_zone"] = {"status_code": r.status_code, "zone_id": zone_id}
        report["ids"]["zone_id"] = zone_id

        # ── Step 3: Tracking ingest + C6 read surfaces ───────────────────────
        tracking_body = {
            "cameraId": CAMERA_ID,
            "source": "LIVE",
            "sectorId": SECTOR_ID,
            "detections": [
                {
                    "detectionId": detection_id,
                    "cameraId": CAMERA_ID,
                    "observedAt": det_observed_at,
                    "bboxX": detection["bbox_x"],
                    "bboxY": detection["bbox_y"],
                    "bboxWidth": detection["bbox_width"],
                    "bboxHeight": detection["bbox_height"],
                    "objectClass": det_class,
                    "confidence": detection["confidence"],
                    "source": "LIVE",
                    "frameId": detection["frame_id"],
                    "sectorId": SECTOR_ID,
                }
            ],
        }
        r = await client.post(
            f"{BASE}/api/v1/internal/tracking/update",
            json=tracking_body,
            headers=INTERNAL_HEADER,
        )
        _show("POST /api/v1/internal/tracking/update", {"status": r.status_code, "body": _safe_json(r)})
        _require(r.status_code == 200, f"tracking ingest failed: {r.status_code} {r.text}")
        ingest_ack = _safe_json(r)
        _require(
            _pick(ingest_ack, "newTracks", "new_tracks", default=0) >= 1,
            f"ingest did not create a track: {ingest_ack}",
        )

        r = await client.get(f"{BASE}/api/v1/tracks", params={"camera_id": CAMERA_ID, "pageSize": 50})
        _show("GET /api/v1/tracks", {"status": r.status_code, "body": _safe_json(r)})
        _require(r.status_code == 200, f"track list failed: {r.status_code} {r.text}")
        tracks = (_safe_json(r) or {}).get("tracks") or []
        _require(len(tracks) > 0, "no track returned after ingestion")
        track_id = _pick(tracks[0], "trackId", "track_id")
        _require(bool(track_id), f"trackId missing: {tracks[0]}")

        r = await client.get(
            f"{BASE}/api/v1/tracks/{track_id}",
            params={"includeTrajectory": "true", "maxTrajectoryPoints": 25},
        )
        _show("GET /api/v1/tracks/{id}", {"status": r.status_code, "body": _safe_json(r)})
        _require(r.status_code == 200, f"track detail failed: {r.status_code} {r.text}")
        detail = _safe_json(r)

        r = await client.get(f"{BASE}/api/v1/tracks/{track_id}/observations")
        _show("GET /api/v1/tracks/{id}/observations", {"status": r.status_code, "body": _safe_json(r)})
        _require(r.status_code == 200, f"observations failed: {r.status_code} {r.text}")
        obs_payload = _safe_json(r)
        observations = obs_payload.get("observations") or []
        provenance_match = any(
            _pick(o, "detectionId", "detection_id") == detection_id for o in observations
        )
        _require(
            provenance_match,
            f"no C6 observation carries the C5 detection id {detection_id}: {observations}",
        )

        r = await client.get(f"{BASE}/api/v1/cameras/{CAMERA_ID}/tracks/feed")
        _require(r.status_code == 200, f"track feed failed: {r.status_code} {r.text}")
        feed = _safe_json(r)
        feeds_track = any(
            _pick(t, "trackId", "track_id") == track_id for t in (feed.get("tracks") or [])
        )
        _require(feeds_track, f"feed does not contain the track: {feed}")

        report["steps"]["3_tracking"] = {
            "ingest_ack": ingest_ack,
            "track_id": track_id,
            "track_status": _pick(detail, "status"),
            "object_class": _pick(detail, "objectClass", "object_class"),
            "observation_detection_id_provenance_match": provenance_match,
            "observations_total": obs_payload.get("total"),
            "feed_state": _pick(feed, "state"),
        }
        report["ids"]["track_id"] = track_id

        # ── Step 4: C7 ANPR — ingest + full read surface ─────────────────────
        sighting_item = {
            "sighting_id": SIGHTING_ID,
            "camera_id": CAMERA_ID,
            "observed_at": det_observed_at,
            "track_id": track_id,
            "detection_id": detection_id,
            "vehicle_class": "CAR",
            "vehicle_color": "WHITE",
            "vehicle_direction": "INBOUND",
            "detection_quality": "HIGH",
            "confidence": detection["confidence"],
            "sector_id": SECTOR_ID,
            "zone_id": zone_id,
            "plateRead": {
                "raw_read": PLATE,
                "normalized_read": PLATE,
                "display_read": PLATE,
                "confidence": 0.93,
                "character_confidence": [0.99, 0.98],
                "format_status": "VALID_FORMAT",
                "quality": "HIGH",
                "observed_at": det_observed_at,
                "candidates": [
                    {
                        "rank": 1,
                        "raw_read": CANDIDATE_PLATE,
                        "normalized_read": CANDIDATE_PLATE,
                        "confidence": 0.61,
                        "format_status": "POSSIBLE_FORMAT",
                    }
                ],
            },
        }
        anpr_body = {
            "camera_id": CAMERA_ID,
            "source": "LIVE",
            "sector_id": SECTOR_ID,
            "zone_id": zone_id,
            "sightings": [sighting_item],
        }
        r = await client.post(
            f"{BASE}/api/v1/anpr/internal/observe",
            json=anpr_body,
            headers=INTERNAL_HEADER,
        )
        _show("POST /api/v1/anpr/internal/observe", {"status": r.status_code, "body": _safe_json(r)})
        _require(r.status_code == 200, f"anpr ingest failed: {r.status_code} {r.text}")
        anpr_ack = _safe_json(r)
        _require(_pick(anpr_ack, "created", default=0) == 1, f"expected 1 created: {anpr_ack}")
        _require(_pick(anpr_ack, "duplicates", default=-1) == 0, f"unexpected duplicates: {anpr_ack}")
        _require(_pick(anpr_ack, "errors", default=-1) == 0, f"ingest errors: {anpr_ack}")
        _require(
            _pick(anpr_ack, "totalSightings", "total_sightings", default=0) == 1,
            f"totalSightings != 1: {anpr_ack}",
        )

        r = await client.get(f"{BASE}/api/v1/anpr/sightings/{SIGHTING_ID}")
        _show("GET /api/v1/anpr/sightings/{id}", {"status": r.status_code, "body": _safe_json(r)})
        _require(r.status_code == 200, f"sighting read-back failed: {r.status_code} {r.text}")
        sighting = _safe_json(r)
        read_sighting_id = _pick(sighting, "sightingId", "sighting_id")
        _require(
            read_sighting_id == SIGHTING_ID,
            f"request-supplied sighting id did not survive: {read_sighting_id}",
        )
        read_plate = sighting.get("plateRead") or sighting.get("plate_read") or {}
        _require(
            _pick(read_plate, "rawRead", "raw_read") == PLATE,
            f"raw read did not survive: {read_plate}",
        )
        _require(
            _pick(read_plate, "normalizedRead", "normalized_read") == PLATE,
            f"normalized read mismatch: {read_plate}",
        )
        _require(
            _pick(sighting, "vehicleTrackId", "vehicle_track_id") == track_id,
            f"C6->C7 link broken: {_pick(sighting, 'vehicleTrackId', 'vehicle_track_id')} != {track_id}",
        )
        vehicle_id = _pick(sighting, "vehicleId", "vehicle_id")
        _require(bool(vehicle_id), f"vehicleId missing: {sighting}")
        detail_candidates = read_plate.get("candidates") or []
        _require(
            len(detail_candidates) == 1
            and _pick(detail_candidates[0], "rawRead", "raw_read") == CANDIDATE_PLATE,
            f"candidate did not survive in detail read-back: {detail_candidates}",
        )

        # Candidates endpoint
        r = await client.get(f"{BASE}/api/v1/anpr/sightings/{SIGHTING_ID}/candidates")
        _show("GET /api/v1/anpr/sightings/{id}/candidates", {"status": r.status_code, "body": _safe_json(r)})
        _require(r.status_code == 200, f"candidates read failed: {r.status_code} {r.text}")
        candidates_payload = _safe_json(r)
        _require(
            len(candidates_payload) == 1
            and _pick(candidates_payload[0], "rawRead", "raw_read") == CANDIDATE_PLATE
            and candidates_payload[0].get("rank") == 1,
            f"candidates endpoint mismatch: {candidates_payload}",
        )

        # Exact plate search
        r = await client.get(f"{BASE}/api/v1/anpr/search", params={"q": PLATE, "limit": 50})
        _show("GET /api/v1/anpr/search (exact)", {"status": r.status_code, "body": _safe_json(r)})
        _require(r.status_code == 200, f"exact search failed: {r.status_code} {r.text}")
        exact_results = _safe_json(r)
        _require(len(exact_results) == 1, f"exact search expected 1 hit: {exact_results}")
        exact_hit = exact_results[0]
        _require(
            _pick(exact_hit.get("sighting") or {}, "sightingId", "sighting_id") == SIGHTING_ID
            and _pick(exact_hit, "matchType", "match_type") == "EXACT_NORMALIZED_MATCH",
            f"exact search classification wrong: {exact_hit}",
        )

        # Candidate-only search (label check §24)
        r = await client.get(
            f"{BASE}/api/v1/anpr/search",
            params={"q": CANDIDATE_SEARCH_TOKEN, "limit": 50},
        )
        _show("GET /api/v1/anpr/search (candidate)", {"status": r.status_code, "body": _safe_json(r)})
        _require(r.status_code == 200, f"candidate search failed: {r.status_code} {r.text}")
        cand_results = _safe_json(r)
        _require(len(cand_results) == 1, f"candidate search expected 1 hit: {cand_results}")
        _require(
            _pick(cand_results[0], "matchType", "match_type") == "CANDIDATE_MATCH",
            f"candidate search classification wrong: {cand_results[0]}",
        )

        # Vehicle history
        r = await client.get(f"{BASE}/api/v1/anpr/vehicles/{vehicle_id}/history")
        _show("GET /api/v1/anpr/vehicles/{id}/history", {"status": r.status_code, "body": _safe_json(r)})
        _require(r.status_code == 200, f"history failed: {r.status_code} {r.text}")
        history = _safe_json(r)
        _require(
            _pick(history, "totalSightings", "total_sightings", default=0) == 1,
            f"history total != 1: {history}",
        )
        _require(
            all(_pick(h, "sightingId", "sighting_id") == SIGHTING_ID for h in (history.get("sightings") or [])),
            f"history rows mismatch: {history}",
        )

        # Camera feed + camera summary + global summary
        r = await client.get(f"{BASE}/api/v1/anpr/cameras/{CAMERA_ID}/vehicles/feed")
        _show("GET /api/v1/anpr/cameras/{id}/vehicles/feed", {"status": r.status_code, "body": _safe_json(r)})
        _require(r.status_code == 200, f"camera feed failed: {r.status_code} {r.text}")
        cam_feed = _safe_json(r)
        _require(_pick(cam_feed, "state") == "READY", f"camera feed state != READY: {cam_feed}")
        feed_sightings = cam_feed.get("sightings") or []
        _require(
            any(_pick(fs, "sightingId", "sighting_id") == SIGHTING_ID for fs in feed_sightings),
            f"camera feed does not contain the sighting: {cam_feed}",
        )

        r = await client.get(f"{BASE}/api/v1/anpr/cameras/{CAMERA_ID}/vehicles/summary")
        _require(r.status_code == 200, f"camera summary failed: {r.status_code} {r.text}")
        cam_summary = _safe_json(r)
        _require(
            _pick(cam_summary, "totalSightings", "total_sightings", default=0) == 1,
            f"camera summary total != 1: {cam_summary}",
        )

        r = await client.get(f"{BASE}/api/v1/anpr/summary")
        _require(r.status_code == 200, f"global summary failed: {r.status_code} {r.text}")
        summary = _safe_json(r)
        for key, expected in (
            (("totalReads", "total_reads"), 1),
            (("readablePlates", "readable_plates"), 1),
            (("partialReads", "partial_reads"), 0),
            (("unreadablePlates", "unreadable_plates"), 0),
            (("uniqueTrackedSightings", "unique_tracked_sightings"), 1),
            (("camerasReporting", "cameras_reporting"), 1),
        ):
            got = _pick(summary, key[0], key[1], default=None)
            _require(got == expected, f"summary {key[0]} expected {expected}, got {got}: {summary}")

        # Idempotent re-ingest + raw-read immutability probe (audit fix #16)
        probe_body = json.loads(json.dumps(anpr_body))
        probe_body["sightings"][0]["plateRead"]["raw_read"] = IDEMPOTENCY_PROBE_PLATE
        probe_body["sightings"][0]["plateRead"]["normalized_read"] = IDEMPOTENCY_PROBE_PLATE
        probe_body["sightings"][0]["plateRead"]["candidates"] = []
        r = await client.post(
            f"{BASE}/api/v1/anpr/internal/observe",
            json=probe_body,
            headers=INTERNAL_HEADER,
        )
        _show("POST /api/v1/anpr/internal/observe (idempotency probe)", {"status": r.status_code, "body": _safe_json(r)})
        _require(r.status_code == 200, f"idempotency probe failed: {r.status_code} {r.text}")
        probe_ack = _safe_json(r)
        _require(
            _pick(probe_ack, "created", default=-1) == 0
            and _pick(probe_ack, "duplicates", default=0) == 1
            and _pick(probe_ack, "errors", default=-1) == 0,
            f"idempotent re-ingest wrong outcome: {probe_ack}",
        )
        r = await client.get(f"{BASE}/api/v1/anpr/sightings/{SIGHTING_ID}")
        re_read = _safe_json(r)
        re_plate = re_read.get("plateRead") or re_read.get("plate_read") or {}
        _require(
            _pick(re_plate, "rawRead", "raw_read") == PLATE,
            f"raw_read was overwritten by duplicate ingest: {re_plate}",
        )

        report["steps"]["4_c7_anpr"] = {
            "ingest_ack": anpr_ack,
            "detail": {
                "sighting_id": read_sighting_id,
                "vehicle_id": vehicle_id,
                "vehicle_track_id": _pick(sighting, "vehicleTrackId", "vehicle_track_id"),
                "vehicle_class": _pick(sighting, "vehicleClass", "vehicle_class"),
                "vehicle_direction": _pick(sighting, "vehicleDirection", "vehicle_direction"),
                "observed_at": _pick(sighting, "observedAt", "observed_at"),
                "source_provider": _pick(sighting, "sourceProvider", "source_provider"),
                "plate_read": {
                    "raw_read": _pick(read_plate, "rawRead", "raw_read"),
                    "normalized_read": _pick(read_plate, "normalizedRead", "normalized_read"),
                    "display_read": _pick(read_plate, "displayRead", "display_read"),
                    "confidence": _pick(read_plate, "confidence"),
                    "format_status": _pick(read_plate, "formatStatus", "format_status"),
                    "quality": _pick(read_plate, "quality"),
                },
                "candidates": detail_candidates,
            },
            "candidates_endpoint_count": len(candidates_payload),
            "search_exact": {
                "query": PLATE,
                "hits": len(exact_results),
                "match_type": _pick(exact_hit, "matchType", "match_type"),
            },
            "search_candidate": {
                "query": CANDIDATE_SEARCH_TOKEN,
                "hits": len(cand_results),
                "match_type": _pick(cand_results[0], "matchType", "match_type"),
            },
            "history": {
                "total_sightings": _pick(history, "totalSightings", "total_sightings"),
                "first_seen": _pick(history, "firstSeen", "first_seen"),
                "last_seen": _pick(history, "lastSeen", "last_seen"),
            },
            "camera_feed_state": _pick(cam_feed, "state"),
            "camera_summary": cam_summary,
            "global_summary": summary,
            "idempotency_probe": {
                "ack": probe_ack,
                "raw_read_after_duplicate_ingest": _pick(re_plate, "rawRead", "raw_read"),
            },
        }
        report["ids"]["sighting_id"] = read_sighting_id
        report["ids"]["vehicle_id"] = vehicle_id

        # ── Step 5: Evaluation (C1 risk + incident, C4 event) ────────────────
        eval_body = {
            "track_id": track_id,
            "camera_id": CAMERA_ID,
            "object_type": object_type,
            "bbox": {
                "x": detection["bbox_x"],
                "y": detection["bbox_y"],
                "width": detection["bbox_width"],
                "height": detection["bbox_height"],
            },
            "confidence": detection["confidence"],
            "is_night": is_night,
            "multi_camera_confirmed": False,
            "reliability": "HIGH",
            "timestamp": det_observed_at,
        }
        r = await client.post(f"{BASE}/api/v1/evaluation/track_and_evaluate", json=eval_body)
        _show("POST /api/v1/evaluation/track_and_evaluate", {"status": r.status_code, "body": _safe_json(r)})
        _require(r.status_code == 200, f"evaluation failed: {r.status_code} {r.text}")
        evaluation = _safe_json(r)
        event_block = evaluation.get("event") or {}
        incident_block = evaluation.get("incident") or {}
        event_id = event_block.get("event_id")
        incident_id = incident_block.get("incident_id")
        risk_score = incident_block.get("risk_score")
        severity = incident_block.get("severity")
        _require(bool(event_id), f"no C1 event created: {evaluation}")
        _require(bool(incident_id), f"no C1 incident created: {evaluation}")
        report["steps"]["5_evaluation"] = {
            "status_code": 200,
            "object_type": object_type,
            "is_night_derived": is_night,
            "event_id": event_id,
            "incident_id": incident_id,
            "risk_score": risk_score,
            "severity": severity,
        }
        report["ids"]["event_id"] = event_id
        report["ids"]["incident_id"] = incident_id
        report["ids"]["risk_score"] = risk_score
        report["ids"]["risk_severity"] = severity

        # ── Step 6: Correlation (C4) — C1 event + C7 ANPR event ──────────────
        c1_event_ingest = {
            "event_id": event_id,
            "event_type": "ZONE_ENTRY",
            "source": "VIRTUAL_FENCE",
            "camera_id": CAMERA_ID,
            "zone_id": zone_id,
            "sector_id": SECTOR_ID,
            "track_id": track_id,
            "event_time": det_observed_at,
            "object_type": object_type,
            "confidence": detection["confidence"],
            "is_night": is_night,
            "reliability": "HIGH",
            "multi_camera_confirmed": False,
            "modality": "VIDEO",
            "payload": {
                "severity": severity,
                "reliability": "HIGH",
                "confidence": detection["confidence"],
                "detection_id": detection_id,
            },
        }
        r = await client.post(
            f"{BASE}/api/v1/correlations/events/ingest",
            params={"source": "VIRTUAL_FENCE"},
            json=c1_event_ingest,
        )
        _show("POST /api/v1/correlations/events/ingest (C1 event)", {"status": r.status_code, "body": _safe_json(r)})
        _require(r.status_code in (200, 201), f"C4 ingest (C1 event) failed: {r.status_code} {r.text}")
        first_ingest = _safe_json(r)
        correlation_id = _pick(first_ingest, "correlation_id", "correlationId")
        _require(bool(correlation_id), f"correlation_id missing: {first_ingest}")

        # event_id intentionally omitted: C4 assigns it server-side and we read
        # it back from the response (nothing fabricated).
        c7_event_ingest = {
            "event_type": "ANPR_READ",
            "source": "ANPR",
            "camera_id": CAMERA_ID,
            "zone_id": zone_id,
            "sector_id": SECTOR_ID,
            "track_id": track_id,
            "event_time": det_observed_at,
            "object_type": "VEHICLE",
            "confidence": 0.93,
            "is_night": is_night,
            "reliability": "HIGH",
            "modality": "VIDEO",
            "payload": {
                "anpr_plate": PLATE,
                "anpr_plate_confidence": 0.93,
                "anpr_quality": "HIGH",
                "anpr_sighting_id": SIGHTING_ID,
                "track_candidate": track_id,
                "detection_id": detection_id,
            },
        }
        r = await client.post(
            f"{BASE}/api/v1/correlations/events/ingest",
            params={"source": "ANPR"},
            json=c7_event_ingest,
        )
        _show("POST /api/v1/correlations/events/ingest (C7 event)", {"status": r.status_code, "body": _safe_json(r)})
        _require(r.status_code in (200, 201), f"C4 ingest (C7 event) failed: {r.status_code} {r.text}")
        second_ingest = _safe_json(r)
        correlation_id_2 = _pick(second_ingest, "correlation_id", "correlationId")
        c7_event_id = _pick(second_ingest, "event_id", "eventId")
        _require(bool(c7_event_id), f"C4 did not report the ANPR event_id: {second_ingest}")
        _require(
            correlation_id_2 == correlation_id,
            f"correlation id changed between ingests: {correlation_id} vs {correlation_id_2}",
        )

        r = await client.get(f"{BASE}/api/v1/correlations/{correlation_id}")
        _show("GET /api/v1/correlations/{id}", {"status": r.status_code, "body": _safe_json(r)})
        _require(r.status_code == 200, f"correlation detail failed: {r.status_code} {r.text}")
        group = _safe_json(r)
        members = group.get("members") or []
        member_track_ids = [_pick(m, "track_id", "trackId") for m in members]
        report["steps"]["6_correlation"] = {
            "first_ingest": first_ingest,
            "second_ingest": second_ingest,
            "group_status": group.get("status"),
            "group_confidence": group.get("confidence"),
            "group_correlation_strength": group.get("correlation_strength"),
            "member_count": len(members),
            "members": [
                {
                    "event_id": _pick(m, "event_id", "eventId"),
                    "source": _pick(m, "source"),
                    "kind": _pick(m, "kind"),
                    "track_id": _pick(m, "track_id", "trackId"),
                    "camera_id": _pick(m, "camera_id", "cameraId"),
                    "anpr_plate": _pick(m, "anpr_plate", "anprPlate"),
                }
                for m in members
            ],
            "explanation_summary": group.get("explanation_summary"),
            "risk_reference": {
                "risk_score": group.get("risk_score"),
                "risk_severity": group.get("risk_severity"),
                "risk_incident_ids": group.get("risk_incident_ids"),
            },
        }
        report["ids"]["correlation_id"] = correlation_id
        report["ids"]["correlation_member_c1_event_id"] = event_id
        report["ids"]["correlation_member_c7_event_id"] = c7_event_id

        # ── Step 7: Evidence (C3) ────────────────────────────────────────────
        evidence_content = f"PRHAAR C7 E2E evidence for incident {incident_id} / camera {CAMERA_ID}"
        evidence_body = {
            "incident_id": incident_id,
            "event_id": event_id,
            "zone_id": zone_id,
            "type": "SNAPSHOT",
            "source": "CAMERA",
            "role": "ORIGINAL_CAPTURE",
            "captured_at": det_observed_at,
            "mime_type": "text/plain",
            "file_size_bytes": len(evidence_content.encode("utf-8")),
            "width": 1920,
            "height": 1080,
            "sector": SECTOR_ID,
            "content": base64.b64encode(evidence_content.encode("utf-8")).decode("ascii"),
        }
        r = await client.post(
            f"{BASE}/api/v1/evidence/internal/cameras/{CAMERA_ID}/evidence/observations",
            json=evidence_body,
        )
        _show("POST evidence ingest", {"status": r.status_code, "body": _safe_json(r)})
        _require(r.status_code in (200, 201), f"evidence ingest failed: {r.status_code} {r.text}")
        evidence_ack = _safe_json(r)
        evidence_id = _pick(evidence_ack, "evidenceId", "evidence_id")
        _require(bool(evidence_id), f"evidenceId missing: {evidence_ack}")

        r = await client.post(f"{BASE}/api/v1/evidence/{evidence_id}/verify")
        _show("POST /api/v1/evidence/{id}/verify", {"status": r.status_code, "body": _safe_json(r)})
        _require(r.status_code == 200, f"evidence verify failed: {r.status_code} {r.text}")
        verify = _safe_json(r)

        report["steps"]["7_evidence"] = {"ingest_ack": evidence_ack, "verify": verify}
        report["ids"]["evidence_id"] = evidence_id

        # ── Step 8: DB read-back (read-only child) — plate_read_id (§53) ─────
        db_check = db_check_readback()
        db_sighting = db_check.get("sighting") or {}
        db_plate = db_check.get("plate_read") or {}
        db_candidates = db_check.get("candidates") or []
        _require(bool(db_sighting), f"DB read-back found no sighting: {db_check}")
        plate_read_id = db_sighting.get("plate_read_id")
        _require(bool(plate_read_id), f"plate_read_id not persisted: {db_check}")
        _require(
            db_sighting.get("detection_id") == detection_id,
            f"DB sighting detection_id mismatch: {db_sighting}",
        )
        _require(
            db_sighting.get("track_id") == track_id,
            f"DB sighting track_id mismatch: {db_sighting}",
        )
        _require(
            db_plate.get("raw_read") == PLATE
            and db_plate.get("normalized_read") == PLATE
            and db_plate.get("format_status") == "VALID_FORMAT"
            and db_plate.get("quality") == "HIGH",
            f"DB plate read mismatch: {db_plate}",
        )
        _require(
            len(db_candidates) == 1
            and db_candidates[0].get("raw_read") == CANDIDATE_PLATE
            and db_candidates[0].get("rank") == 1,
            f"DB candidates mismatch: {db_candidates}",
        )
        report["steps"]["8_db_cross_check"] = {
            "technique": (
                "read-only DB read-back in a child process (plate_read_id is not on any "
                "ANPR read API surface); rows were created through the HTTP ingestion path"
            ),
            "sighting": db_sighting,
            "plate_read": db_plate,
            "candidates": db_candidates,
        }
        report["ids"]["plate_read_id"] = plate_read_id

        # ── Cross-component ID consistency summary ───────────────────────────
        report["id_consistency"] = {
            "c5_detection_id": detection_id,
            "c6_track_id": track_id,
            "c6_observation_detection_id_match": provenance_match,
            "c7_sighting_id": read_sighting_id,
            "c7_sighting_id_is_request_supplied": read_sighting_id == SIGHTING_ID,
            "c7_plate_read_id": plate_read_id,
            "c7_sighting_track_matches_c6": db_sighting.get("track_id") == track_id,
            "c7_sighting_detection_matches_c5": db_sighting.get("detection_id") == detection_id,
            "c4_events_reference_c6_track": all(t == track_id for t in member_track_ids) if members else None,
            "c4_correlation_id": correlation_id,
            "c4_anpr_event_id": c7_event_id,
            "c1_event_id": event_id,
            "c1_incident_id": incident_id,
            "c3_evidence_id": evidence_id,
        }

    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    report["result"] = "PASS"
    return report


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap-only", action="store_true")
    args = parser.parse_args()

    if args.bootstrap_only:
        bootstrap_schema()
        return 0

    report: dict = {}
    server = None
    log_path: Path | None = None
    try:
        bootstrap_schema()
        seed = seed_c5_detection()
        server, log_path = start_server()

        report = await run_chain(seed)
        _emit_report(report)
        _log("RESULT: PASS — chain completed with real ids")
        return 0
    except StepFailed as exc:
        report = report or {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "base_url": BASE,
            "database": DB_REL,
            "ids": {},
            "steps": {},
            "failures": [],
        }
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        report["result"] = "FAIL"
        report.setdefault("failures", []).append(str(exc))
        _emit_report(report)
        _log(f"RESULT: FAIL — {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001
        report = report or {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "base_url": BASE,
            "database": DB_REL,
            "ids": {},
            "steps": {},
            "failures": [],
        }
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        report["result"] = "FAIL"
        report.setdefault("failures", []).append(f"{type(exc).__name__}: {exc}")
        _emit_report(report)
        _log(f"RESULT: FAIL — {type(exc).__name__}: {exc}")
        return 1
    finally:
        if server is not None:
            server.terminate()
            try:
                server.wait(timeout=15)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait(timeout=10)
        log_file = getattr(server, "_e2e_log_file", None) if server is not None else None
        if log_file is not None:
            log_file.close()
        if log_path is not None and log_path.exists():
            lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
            tail = "\n".join(lines[-60:])
            print(f"--- uvicorn tail ---\n{tail}", flush=True)


if __name__ == "__main__":
    if "--seed-c5-child" in sys.argv[1:]:
        raise SystemExit(_seed_child_main())
    if "--db-check-child" in sys.argv[1:]:
        asyncio.run(_db_check_child_run())
        raise SystemExit(0)
    raise SystemExit(asyncio.run(main()))
