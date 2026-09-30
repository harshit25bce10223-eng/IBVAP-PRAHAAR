"""Performance measurement for Component 7 (ANPR + Vehicle Intelligence) — spec §50.

Measures, with the real ANPR ingest path (DemoANPRProvider — no real OCR
model compute) and real read APIs over HTTP against a live uvicorn server,
at 100 / 1,000 / 10,000 cumulative vehicle sightings:

      * ingest latency            POST /api/v1/anpr/internal/observe  (1-sighting batch)
      * list latency              GET  /api/v1/anpr/sightings
      * detail latency            GET  /api/v1/anpr/sightings/{id}
      * search latency            GET  /api/v1/anpr/search            (exact + partial text)
      * history latency           GET  /api/v1/anpr/vehicles/{id}/history
      * camera feed latency       GET  /api/v1/anpr/cameras/{cam}/vehicles/feed

plus camera vehicle-list / summary context, and reports p50 / p95 / max per
measurement.

Honesty notes (§50):
  * The registered provider is DEMO — no real ANPR/OCR model compute is
    included; ingest latency reflects the orchestration + persistence
    pipeline only (recognition is fixture pass-through).
  * Search probes are text-match probes over demo plate tokens. This
    platform computes no OCR accuracy metrics and none are implied here.
  * These are observations on this machine (SQLite via aiosqlite, single dev
    process, SEQUENTIAL requests). They are NOT production-capacity claims,
    and no numbers are extrapolated.

Usage (from C:/SIH/ibvap-backend, venv python):

    venv/Scripts/python.exe scripts/c7_performance.py
    venv/Scripts/python.exe scripts/c7_performance.py --stages 100,1000
"""

from __future__ import annotations

import argparse
import asyncio
import json
import math
import os
import statistics
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DB_REL = "tests/test_dbs/c7_perf_run.db"
DB_PATH = BACKEND_ROOT / DB_REL
REPORT_PATH = BACKEND_ROOT / "tests/test_dbs/c7_performance_report.json"
PORT = 8127
BASE = f"http://127.0.0.1:{PORT}"
INTERNAL_HEADERS = {"X-Internal-Service": "c7-perf-harness"}

LATENCY_CAMERA = "CAM-PF-ANPR-LAT"   # 1-sighting ingest-latency samples land here
BASE_TS = datetime(2026, 9, 27, 0, 0, 0, tzinfo=timezone.utc)
CHUNK_MAX = 200                      # ANPR ingest schema cap (max 200 sightings per POST)
VEHICLE_GROUP = 10                   # sightings per vehicle → history depth 10


class StepFailed(RuntimeError):
    pass


def _log(msg: str) -> None:
    print(f"[perf] {msg}", flush=True)


def _percentiles(samples_ms: list[float]) -> dict:
    ordered = sorted(samples_ms)
    n = len(ordered)

    def pick(q: float) -> float:
        idx = max(0, min(n - 1, math.ceil(q * n) - 1))
        return round(ordered[idx], 2)

    return {
        "count": n,
        "p50_ms": pick(0.50),
        "p95_ms": pick(0.95),
        "max_ms": round(ordered[-1], 2),
        "mean_ms": round(statistics.fmean(ordered), 2),
    }


def bootstrap_schema() -> None:
    """Fresh schema via the model metadata (same approach as c4/c6 scripts)."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    if DB_PATH.exists():
        DB_PATH.unlink()
    code = (
        "import asyncio\n"
        "from app.db.database import Base, engine\n"
        "import app.models  # noqa: F401\n"
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
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=str(BACKEND_ROOT),
        env=env,
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0 or "SCHEMA_OK" not in proc.stdout:
        raise StepFailed(f"schema bootstrap failed\nstdout: {proc.stdout}\nstderr: {proc.stderr}")
    _log(f"schema bootstrapped: {DB_REL}")


def start_server() -> subprocess.Popen:
    log_path = BACKEND_ROOT / "tests/test_dbs/c7_perf_uvicorn.log"
    log_file = open(log_path, "w", encoding="utf-8")  # noqa: SIM115 — closed by caller
    env = dict(os.environ)
    env["DATABASE_URL"] = f"sqlite+aiosqlite:///./{DB_REL}"
    env.pop("PYTEST_CURRENT_TEST", None)
    env["ENV"] = "development"
    env["PYTHONUNBUFFERED"] = "1"
    proc = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1",
         "--port", str(PORT), "--log-level", "warning"],
        cwd=str(BACKEND_ROOT),
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
    )
    proc._perf_log_file = log_file  # type: ignore[attr-defined]
    _log(f"uvicorn starting on port {PORT} (pid {proc.pid})")
    return proc


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


# ── Payload builders (snake_case contract + plateRead key) ───────────────────

def _plate_token(stage_idx: int, group: int) -> str:
    """Deterministic demo plate for stage/vehicle-group (text-match probes only)."""
    return f"PB10PF{stage_idx}{group:04d}"


def _plate_read(plate: str, observed_at: datetime) -> dict:
    return {
        "raw_read": plate,
        "normalized_read": plate,
        "display_read": plate,
        "confidence": 0.92,
        "quality": "GOOD",
        "format_status": "VALID_FORMAT",
        "observed_at": observed_at.isoformat(),
        "candidates": [
            {
                "rank": 1,
                "raw_read": plate,
                "normalized_read": plate,
                "confidence": 0.92,
                "format_status": "VALID_FORMAT",
            }
        ],
    }


def _sighting_item(stage_idx: int, i: int, observed_at: datetime) -> dict:
    cam = f"CAM-PF-ANPR-{stage_idx}"
    plate = _plate_token(stage_idx, i // VEHICLE_GROUP)
    return {
        "camera_id": cam,
        "observed_at": observed_at.isoformat(),
        "sighting_id": f"SGT-PF{stage_idx}-{i:05d}",
        "vehicle_id": f"VEH-PF{stage_idx}-{i // VEHICLE_GROUP:04d}",
        "vehicle_class": "PERSONAL_CAR",
        "vehicle_direction": "NORTH",
        "track_id": f"TRK-PF{stage_idx}-{i:05d}",
        "detection_id": f"DET-PF{stage_idx}-{i:05d}",
        "confidence": 0.9,
        "plateRead": _plate_read(plate, observed_at),
    }


def _latency_item(n: int, observed_at: datetime) -> dict:
    plate = f"PB10PFLAT{n:04d}"
    return {
        "camera_id": LATENCY_CAMERA,
        "observed_at": observed_at.isoformat(),
        "sighting_id": f"SGT-PF-LAT-{n:04d}",
        "vehicle_id": f"VEH-PF-LAT-{n:04d}",
        "vehicle_class": "PERSONAL_CAR",
        "vehicle_direction": "NORTH",
        "track_id": f"TRK-PF-LAT-{n:04d}",
        "detection_id": f"DET-PF-LAT-{n:04d}",
        "confidence": 0.9,
        "plateRead": _plate_read(plate, observed_at),
    }


# ── Ingest ───────────────────────────────────────────────────────────────────

async def _post_batch(client, camera: str, items: list[dict], timeout: float) -> tuple[float, dict]:
    body = {"camera_id": camera, "source": "LIVE", "sightings": items}
    t0 = time.perf_counter()
    r = await client.post(
        f"{BASE}/api/v1/anpr/internal/observe",
        json=body,
        headers=INTERNAL_HEADERS,
        timeout=timeout,
    )
    wall_ms = (time.perf_counter() - t0) * 1000.0
    if r.status_code != 200:
        raise StepFailed(f"ingest failed on {camera}: {r.status_code} {r.text[:300]}")
    return wall_ms, r.json()


async def measure_ingest_latency(client, samples: int, offset: int) -> dict:
    """`samples` sequential 1-sighting ingest POSTs on LATENCY_CAMERA."""
    lat: list[float] = []
    for i in range(samples):
        n = offset + i
        item = _latency_item(n, BASE_TS + timedelta(seconds=n))
        wall_ms, body = await _post_batch(client, LATENCY_CAMERA, [item], timeout=60.0)
        if body["created"] != 1:
            raise StepFailed(f"latency ingest created={body['created']} expected 1")
        lat.append(wall_ms)
    return _percentiles(lat)


async def seed_stage(client, stage_idx: int, count: int, data_offset: int) -> dict:
    """Seed `count` sightings on a fresh camera, in chunks of CHUNK_MAX."""
    camera = f"CAM-PF-ANPR-{stage_idx}"
    wall: list[float] = []
    for start in range(0, count, CHUNK_MAX):
        chunk = min(CHUNK_MAX, count - start)
        items = [
            _sighting_item(stage_idx, start + j, BASE_TS + timedelta(seconds=data_offset + start + j))
            for j in range(chunk)
        ]
        wall_ms, body = await _post_batch(client, camera, items, timeout=300.0)
        if body["created"] != chunk or body["duplicates"] != 0 or body["errors"] != 0:
            raise StepFailed(
                f"seed mismatch on {camera} chunk@{start}: created={body['created']} "
                f"duplicates={body['duplicates']} errors={body['errors']} expected {chunk}"
            )
        wall.append(wall_ms)
    return {
        "sightings": count,
        "chunks": len(wall),
        "max_chunk_size": CHUNK_MAX,
        "per_chunk_wall_ms": _percentiles(wall),
        "total_wall_ms": round(sum(wall), 2),
    }


# ── Verification probes ──────────────────────────────────────────────────────

async def verify_camera(client, stage_idx: int, stage_count: int) -> dict:
    camera = f"CAM-PF-ANPR-{stage_idx}"

    r = await client.get(f"{BASE}/api/v1/anpr/cameras/{camera}/vehicles/feed", timeout=30.0)
    if r.status_code != 200:
        raise StepFailed(f"feed probe failed on {camera}: {r.status_code}")
    feed = r.json()
    expected_feed = min(stage_count, 50)
    if feed["state"] != "READY":
        raise StepFailed(f"feed state on {camera}: {feed['state']} != READY")
    if len(feed["sightings"]) != expected_feed:
        raise StepFailed(f"feed count on {camera}: {len(feed['sightings'])} != {expected_feed}")
    if not feed.get("lastUpdatedAt"):
        raise StepFailed(f"feed lastUpdatedAt missing on {camera}")

    r = await client.get(f"{BASE}/api/v1/anpr/cameras/{camera}/vehicles",
                         params={"limit": 100}, timeout=30.0)
    if r.status_code != 200:
        raise StepFailed(f"camera list probe failed on {camera}: {r.status_code}")
    expected_list = min(stage_count, 100)
    if len(r.json()) != expected_list:
        raise StepFailed(f"camera list count on {camera}: {len(r.json())} != {expected_list}")

    r = await client.get(f"{BASE}/api/v1/anpr/cameras/{camera}/vehicles/summary", timeout=30.0)
    if r.status_code != 200:
        raise StepFailed(f"camera summary probe failed on {camera}: {r.status_code}")
    summary = r.json()
    if summary["totalSightings"] != stage_count:
        raise StepFailed(
            f"camera summary on {camera}: totalSightings={summary['totalSightings']} != {stage_count}"
        )

    return {
        "feed_state": feed["state"],
        "feed_count": len(feed["sightings"]),
        "feed_last_updated_at": feed["lastUpdatedAt"],
        "camera_list_count": expected_list,
        "camera_summary_total": summary["totalSightings"],
        "camera_summary_by_quality": summary["byQuality"],
    }


async def verify_global_summary(client, expected_total: int, expected_cameras: int) -> dict:
    r = await client.get(f"{BASE}/api/v1/anpr/summary", timeout=30.0)
    if r.status_code != 200:
        raise StepFailed(f"global summary probe failed: {r.status_code}")
    s = r.json()
    if s["totalReads"] != expected_total:
        raise StepFailed(f"summary totalReads={s['totalReads']} != {expected_total}")
    if s["readablePlates"] != expected_total or s["partialReads"] != 0 or s["unreadablePlates"] != 0:
        raise StepFailed(
            f"summary buckets mismatch: readable={s['readablePlates']} partial={s['partialReads']} "
            f"unreadable={s['unreadablePlates']} (all data here is VALID_FORMAT/GOOD)"
        )
    if s["uniqueTrackedSightings"] != expected_total:
        raise StepFailed(
            f"summary uniqueTrackedSightings={s['uniqueTrackedSightings']} != {expected_total}"
        )
    if s["camerasReporting"] != expected_cameras:
        raise StepFailed(f"summary camerasReporting={s['camerasReporting']} != {expected_cameras}")
    if not s.get("lastUpdated"):
        raise StepFailed("summary lastUpdated missing")
    return {
        "totalReads": s["totalReads"],
        "readablePlates": s["readablePlates"],
        "partialReads": s["partialReads"],
        "unreadablePlates": s["unreadablePlates"],
        "uniqueTrackedSightings": s["uniqueTrackedSightings"],
        "camerasReporting": s["camerasReporting"],
    }


# ── Reads ────────────────────────────────────────────────────────────────────

async def measure_reads(client, stage_idx: int, stage_count: int, iterations: int) -> dict:
    camera = f"CAM-PF-ANPR-{stage_idx}"
    sgt0 = f"SGT-PF{stage_idx}-00000"
    veh0 = f"VEH-PF{stage_idx}-0000"
    plate0 = _plate_token(stage_idx, 0)
    partial_q = f"PB10PF{stage_idx}"
    expected_partial = min(stage_count, 500)

    def _v_list(r) -> None:
        b = r.json()
        if len(b["sightings"]) != 50 or not b["hasMore"]:
            raise StepFailed(f"list probe shape: {len(b['sightings'])} rows")

    def _v_detail(r) -> None:
        if r.json()["sightingId"] != sgt0:
            raise StepFailed("detail probe returned wrong sighting")

    def _v_search_exact(r) -> None:
        rows = r.json()
        if len(rows) != VEHICLE_GROUP:
            raise StepFailed(f"exact search rows={len(rows)} != {VEHICLE_GROUP}")
        if any(x["matchType"] != "EXACT_NORMALIZED_MATCH" for x in rows):
            raise StepFailed("exact search returned a non-exact label")

    def _v_search_partial(r) -> None:
        rows = r.json()
        if len(rows) != expected_partial:
            raise StepFailed(f"partial search rows={len(rows)} != {expected_partial}")
        if any(x["matchType"] != "RAW_READ_MATCH" for x in rows):
            raise StepFailed("partial-text search labels drifted")

    def _v_history(r) -> None:
        b = r.json()
        if b["totalSightings"] != VEHICLE_GROUP or len(b["sightings"]) != VEHICLE_GROUP:
            raise StepFailed(f"history probe: total={b['totalSightings']} rows={len(b['sightings'])}")
        if not b["firstSeen"] or not b["lastSeen"]:
            raise StepFailed("history probe: firstSeen/lastSeen missing")

    def _v_feed(r) -> None:
        if r.json()["state"] != "READY":
            raise StepFailed("feed probe state not READY")

    def _v_camera_list(r) -> None:
        if len(r.json()) != min(stage_count, 100):
            raise StepFailed("camera list shape")

    def _v_camera_summary(r) -> None:
        if r.json()["totalSightings"] != stage_count:
            raise StepFailed("camera summary shape")

    specs: dict[str, tuple[str, dict | None, object]] = {
        "list": (f"{BASE}/api/v1/anpr/sightings", {"limit": 50}, _v_list),
        "detail": (f"{BASE}/api/v1/anpr/sightings/{sgt0}", None, _v_detail),
        "search_exact": (f"{BASE}/api/v1/anpr/search", {"q": plate0, "limit": 50}, _v_search_exact),
        "search_partial": (f"{BASE}/api/v1/anpr/search", {"q": partial_q, "limit": 500}, _v_search_partial),
        "history": (f"{BASE}/api/v1/anpr/vehicles/{veh0}/history", None, _v_history),
        "camera_feed": (f"{BASE}/api/v1/anpr/cameras/{camera}/vehicles/feed", None, _v_feed),
        "camera_vehicles": (f"{BASE}/api/v1/anpr/cameras/{camera}/vehicles", {"limit": 100}, _v_camera_list),
        "camera_summary": (f"{BASE}/api/v1/anpr/cameras/{camera}/vehicles/summary", None, _v_camera_summary),
    }

    reads: dict[str, dict] = {}
    for label, (url, params, validator) in specs.items():
        samples: list[float] = []
        for _ in range(iterations):
            t0 = time.perf_counter()
            r = await client.get(url, params=params, timeout=60.0)
            ms = (time.perf_counter() - t0) * 1000.0
            if r.status_code != 200:
                raise StepFailed(f"{label} returned HTTP {r.status_code}")
            validator(r)  # type: ignore[operator]
            samples.append(ms)
        reads[label] = _percentiles(samples)
    return reads


# ── Main ─────────────────────────────────────────────────────────────────────

async def run(stages: list[int], iterations: int, latency_samples: int) -> dict:
    import httpx

    report: dict = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "base_url": BASE,
        "database": DB_REL,
        "provider": "ANPR-DEMO (no real OCR model compute — orchestration + persistence pipeline only)",
        "environment_note": (
            "Measured on this development machine (SQLite via aiosqlite, single "
            "uvicorn process, sequential requests). Observations only — NOT a "
            "production-capacity claim (§50). Plates are deterministic demo "
            "tokens; no OCR accuracy metric is computed or implied."
        ),
        "stages": [],
        "failures": [],
    }

    async with httpx.AsyncClient() as client:
        await wait_for_health(client)
        prev_target = 0
        data_offset = 0
        latency_offset = 0
        stage_idx = 0

        for target in stages:
            stage_idx += 1
            stage_add = target - prev_target
            if stage_add <= 0:
                raise StepFailed(f"stage targets must be strictly increasing: {stages}")
            _log(f"stage {stage_idx}: +{stage_add} sightings (cumulative {target})")

            latency = await measure_ingest_latency(client, latency_samples, latency_offset)
            latency_offset += latency_samples

            seed = await seed_stage(client, stage_idx, stage_add, data_offset)
            data_offset += stage_add
            prev_target = target

            camera_checks = await verify_camera(client, stage_idx, stage_add)

            expected_total = target + latency_samples * stage_idx
            expected_cameras = stage_idx + 1  # stage cameras + LATENCY_CAMERA
            global_summary = await verify_global_summary(client, expected_total, expected_cameras)

            reads = await measure_reads(client, stage_idx, stage_add, iterations)

            report["stages"].append({
                "stage": stage_idx,
                "sightings_added": stage_add,
                "cumulative_sightings": target,
                "camera": f"CAM-PF-ANPR-{stage_idx}",
                "ingest_latency_1sighting": latency,
                "seed_batches": seed,
                "camera_checks": camera_checks,
                "global_summary": global_summary,
                "reads": reads,
            })
            _log(
                f"  done: cam=CAM-PF-ANPR-{stage_idx} rows={stage_add} | "
                f"ingest p50={latency['p50_ms']}ms p95={latency['p95_ms']}ms | "
                f"list p50={reads['list']['p50_ms']}ms p95={reads['list']['p95_ms']}ms | "
                f"detail p50={reads['detail']['p50_ms']}ms | "
                f"search_exact p50={reads['search_exact']['p50_ms']}ms | "
                f"history p50={reads['history']['p50_ms']}ms | "
                f"feed p50={reads['camera_feed']['p50_ms']}ms"
            )

    report["finished_at"] = datetime.now(timezone.utc).isoformat()
    report["result"] = "PASS"
    return report


def _emit(report: dict) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    _log(f"report written: {REPORT_PATH}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stages", default="100,1000,10000",
                        help="comma-separated cumulative sighting targets")
    parser.add_argument("--iterations", type=int, default=30, help="read samples per endpoint per stage")
    parser.add_argument("--latency-samples", type=int, default=15, help="ingest-latency samples per stage")
    args = parser.parse_args()
    stages = [int(s) for s in args.stages.split(",")]

    report: dict = {}
    server = None
    try:
        bootstrap_schema()
        server = start_server()
        report = asyncio.run(run(stages, args.iterations, args.latency_samples))
        _emit(report)
        for stage in report["stages"]:
            r = stage["reads"]
            _log(
                f"{stage['cumulative_sightings']:>6} sightings | "
                f"ingest {stage['ingest_latency_1sighting']['p50_ms']}/{stage['ingest_latency_1sighting']['p95_ms']} ms | "
                f"list {r['list']['p50_ms']}/{r['list']['p95_ms']} ms | "
                f"detail {r['detail']['p50_ms']}/{r['detail']['p95_ms']} ms | "
                f"search {r['search_exact']['p50_ms']}/{r['search_exact']['p95_ms']} ms | "
                f"history {r['history']['p50_ms']}/{r['history']['p95_ms']} ms | "
                f"feed {r['camera_feed']['p50_ms']}/{r['camera_feed']['p95_ms']} ms "
                f"(p50/p95)"
            )
        _log("RESULT: PASS")
        return 0
    except StepFailed as exc:
        report = report or {"started_at": datetime.now(timezone.utc).isoformat(), "stages": [], "failures": []}
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        report["result"] = "FAIL"
        report.setdefault("failures", []).append(str(exc))
        _emit(report)
        _log(f"RESULT: FAIL — {exc}")
        return 1
    except Exception as exc:  # noqa: BLE001
        report = report or {"started_at": datetime.now(timezone.utc).isoformat(), "stages": [], "failures": []}
        report["finished_at"] = datetime.now(timezone.utc).isoformat()
        report["result"] = "FAIL"
        report.setdefault("failures", []).append(f"{type(exc).__name__}: {exc}")
        _emit(report)
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
            log_file = getattr(server, "_perf_log_file", None)
            if log_file is not None:
                log_file.close()


if __name__ == "__main__":
    raise SystemExit(main())
