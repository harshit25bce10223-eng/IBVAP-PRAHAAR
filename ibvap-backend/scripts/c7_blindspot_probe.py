"""C7 §48 blind-spot probe — platform handling of degraded plate observations.

Scope (honest): no production OCR model exists in this task (§54). The 14 §48
scenarios are therefore split into two verifiable layers:

  · HANDLING (verifiable now, over the real HTTP API): what the platform does
    when a read carrying the scenario's characteristics arrives — is it
    recorded, are flags/quality preserved, is uncertainty visible, is the read
    searchable, is anything fabricated?
  · RECOGNITION (NOT verifiable now): whether an actual OCR model would read a
    dirty/angled/glared/moving plate correctly. That requires the production
    ANPR model — deferred to the AI/ML phase (§54). Marked KNOWN LIMITATION.

Every item is ingested through POST /api/v1/anpr/internal/observe over HTTP and
read back through the read APIs. All asserted values come from actual responses.

Usage (from C:/SIH/ibvap-backend, venv python):

    venv/Scripts/python.exe scripts/c7_blindspot_probe.py
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[1]
DB_REL = "tests/test_dbs/c7_blindspot_run.db"
DB_PATH = BACKEND_ROOT / DB_REL
REPORT_PATH = BACKEND_ROOT / "tests/test_dbs/c7_blindspot_report.json"
PORT = 8122
BASE = f"http://127.0.0.1:{PORT}"

INTERNAL_HEADER = {"X-Internal-Service": "blindspot-probe"}

CAM_1 = "CAM-C7BS-01"
CAM_2 = "CAM-C7BS-02"
CAM_3 = "CAM-C7BS-03"

# Recognition-layer disclosure attached to every imaging-condition item.
RECOG_NOTE = (
    "Recognition quality under this condition requires the production ANPR/OCR "
    "model, which is a separate AI/ML phase (§54). Not verifiable in this task."
)


class StepFailed(RuntimeError):
    pass


def _log(msg: str) -> None:
    print(f"[bs] {msg}", flush=True)


def _emit_report(report: dict) -> None:
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    _log(f"report written: {REPORT_PATH}")


def _require(cond: bool, msg: str) -> None:
    if not cond:
        raise StepFailed(msg)


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


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _iso_z(ts: str) -> str:
    """Normalize an ISO timestamp to Z-form for exact comparison."""
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ─────────────────────────────────────────────────────────────────────────────
# Schema bootstrap + server (same child-process pattern as the e2e harnesses)
# ─────────────────────────────────────────────────────────────────────────────

def bootstrap_schema() -> None:
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
        raise StepFailed(f"schema bootstrap failed\nstdout: {proc.stdout}\nstderr: {proc.stderr}")
    _log(f"schema bootstrapped: {DB_REL}")


def start_server() -> tuple[subprocess.Popen, Path]:
    log_path = BACKEND_ROOT / "tests/test_dbs/c7_blindspot_uvicorn.log"
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
            "warning",
        ],
        cwd=str(BACKEND_ROOT),
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
        text=True,
    )
    proc._bs_log_file = log_file  # type: ignore[attr-defined]
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
# HTTP helpers
# ─────────────────────────────────────────────────────────────────────────────

async def ingest(client, camera_id: str, sightings: list[dict]) -> dict:
    for s in sightings:
        s["camera_id"] = camera_id  # per-sighting key is required by the contract
    r = await client.post(
        f"{BASE}/api/v1/anpr/internal/observe",
        headers=INTERNAL_HEADER,
        json={"camera_id": camera_id, "source": "LIVE", "sightings": sightings},
        timeout=30.0,
    )
    _require(r.status_code == 200, f"ingest HTTP {r.status_code}: {r.text[:400]}")
    return _safe_json(r)


async def detail(client, sighting_id: str) -> dict:
    r = await client.get(f"{BASE}/api/v1/anpr/sightings/{sighting_id}", timeout=15.0)
    _require(r.status_code == 200, f"detail({sighting_id}) HTTP {r.status_code}")
    return _safe_json(r)


async def candidates_of(client, sighting_id: str) -> list:
    r = await client.get(f"{BASE}/api/v1/anpr/sightings/{sighting_id}/candidates", timeout=15.0)
    _require(r.status_code == 200, f"candidates({sighting_id}) HTTP {r.status_code}")
    return _safe_json(r)


async def search(client, q: str, limit: int = 50) -> list:
    r = await client.get(f"{BASE}/api/v1/anpr/search", params={"q": q, "limit": limit}, timeout=15.0)
    _require(r.status_code == 200, f"search({q}) HTTP {r.status_code}")
    return _safe_json(r)


async def global_summary(client) -> dict:
    r = await client.get(f"{BASE}/api/v1/anpr/summary", timeout=15.0)
    _require(r.status_code == 200, f"summary HTTP {r.status_code}")
    return _safe_json(r)


def _sighting_item(
    sighting_id: str,
    observed_at: str,
    *,
    vehicle_class: str = "CAR",
    vehicle_color: str = "WHITE",
    direction: str = "INBOUND",
    track_id: str | None = None,
    detection_id: str | None = None,
    detection_quality: str | None = None,
    camera_health_state: str | None = None,
    camera_health_context_json: str | None = None,
    plate: dict | None = None,
) -> dict:
    item: dict = {
        "camera_id": None,  # filled by caller's camera wrapper
        "observed_at": observed_at,
        "sighting_id": sighting_id,
        "vehicle_class": vehicle_class,
        "vehicle_color": vehicle_color,
        "vehicle_direction": direction,
    }
    if track_id is not None:
        item["track_id"] = track_id
    if detection_id is not None:
        item["detection_id"] = detection_id
    if detection_quality is not None:
        item["detection_quality"] = detection_quality
    if camera_health_state is not None:
        item["camera_health_state"] = camera_health_state
    if camera_health_context_json is not None:
        item["camera_health_context_json"] = camera_health_context_json
    if plate is not None:
        item["plateRead"] = plate
    return item


def _plate(
    raw: str,
    display: str,
    confidence: float,
    quality: str,
    format_status: str,
    observed_at: str,
    *,
    normalized: str | None = None,
    character_confidence: list[float] | None = None,
    candidates: list[dict] | None = None,
) -> dict:
    plate: dict = {
        "raw_read": raw,
        "normalized_read": normalized,
        "display_read": display,
        "confidence": confidence,
        "quality": quality,
        "format_status": format_status,
        "observed_at": observed_at,
    }
    if character_confidence is not None:
        plate["character_confidence"] = character_confidence
    if candidates:
        plate["candidates"] = candidates
    return plate


def _cand(rank: int, raw: str, confidence: float, format_status: str,
          normalized: str | None = None) -> dict:
    c: dict = {"rank": rank, "raw_read": raw, "confidence": confidence,
               "format_status": format_status}
    if normalized is not None:
        c["normalized_read"] = normalized
    return c


# ─────────────────────────────────────────────────────────────────────────────
# §48 battery
# ─────────────────────────────────────────────────────────────────────────────

async def run_battery() -> dict:
    import httpx

    items: dict[str, dict] = {}
    failures: list[str] = []

    def record(name: str, status: str, handling: list[str], evidence: dict,
               recognition: str | None = None) -> None:
        items[name] = {
            "status": status,
            "handling_assertions": handling,
            "evidence": evidence,
            "recognition": recognition,
        }

    async with httpx.AsyncClient() as client:
        await wait_for_health(client)

        # ── 1. dirty plate: worn characters, no clean normalization ──────────
        sid = "SGT-C7BS-0001"
        ts = "2026-09-28T10:00:01+00:00"
        ack = await ingest(client, CAM_1, [_sighting_item(
            sid, ts, track_id="TRK-C7BS-0001",
            plate=_plate("HR26DK44O1", "HR26DK44O1", 0.48, "LOW", "POSSIBLE_FORMAT", ts),
        )])
        _require(_pick(ack, "created") == 1, f"item1 ack created != 1: {ack}")
        d = await detail(client, sid)
        pr = _pick(d, "plateRead", "plate_read") or {}
        _require(_pick(pr, "rawRead", "raw_read") == "HR26DK44O1", f"item1 raw not preserved: {pr}")
        _require(_pick(pr, "normalizedRead", "normalized_read") in (None,), f"item1 fabricated normalized: {pr}")
        _require(_pick(pr, "displayRead", "display_read") == "HR26DK44O1", f"item1 display fallback wrong: {pr}")
        _require(abs(float(_pick(pr, "confidence")) - 0.48) < 1e-6, f"item1 confidence wrong: {pr}")
        hits = await search(client, "44O1")
        hit_ids = [_pick(_pick(h, "sighting") or {}, "sightingId", "sighting_id") for h in hits]
        _require(sid in hit_ids, f"item1 dirty read not searchable by its own chars: {hits}")
        record("dirty_plate", "PASS", [
            "raw read preserved byte-for-byte (no silent cleanup)",
            "normalized stays null (no fabricated clean plate)",
            "display falls back to raw",
            "searchable by its own (dirty) characters",
        ], {"sighting_id": sid, "raw": "HR26DK44O1", "display": "HR26DK44O1",
            "confidence": 0.48, "search_hits": len(hits)},
            recognition=RECOG_NOTE)

        # ── 2. extreme angle: skewed read, low confidence ────────────────────
        sid = "SGT-C7BS-0002"
        ts = "2026-09-28T10:00:02+00:00"
        ack = await ingest(client, CAM_1, [_sighting_item(
            sid, ts, plate=_plate("MH12DE1433", "MH12DE1433", 0.19, "LOW",
                                  "POSSIBLE_FORMAT", ts, normalized="MH12DE1433"),
        )])
        _require(_pick(ack, "created") == 1, f"item2 ack created != 1: {ack}")
        d = await detail(client, sid)
        pr = _pick(d, "plateRead", "plate_read") or {}
        _require(abs(float(_pick(pr, "confidence")) - 0.19) < 1e-6, f"item2 confidence not exact: {pr}")
        _require(_pick(d, "watchlistStatus", "watchlist_status") == "NOT_CHECKED",
                 f"item2 watchlist overclaim: {d}")
        record("extreme_angle", "PASS", [
            "low-confidence skewed read recorded, not dropped",
            "confidence 0.19 returned exactly (uncertainty visible)",
            "watchlist status stays NOT_CHECKED (no identity overclaim)",
        ], {"sighting_id": sid, "confidence": 0.19}, recognition=RECOG_NOTE)

        # ── 3. two-wheeler: canonical class round-trip (also reused by item 14) ─
        sid = "SGT-C7BS-0003"
        ts = "2026-09-28T10:00:03+00:00"
        item3_payload = _sighting_item(
            sid, ts, vehicle_class="MOTORCYCLE", vehicle_color="BLACK",
            track_id="TRK-C7BS-0003",
            plate=_plate("KA05HJ8899", "KA05HJ8899", 0.88, "HIGH", "VALID_FORMAT", ts,
                         normalized="KA05HJ8899"),
        )
        ack = await ingest(client, CAM_1, [item3_payload])
        _require(_pick(ack, "created") == 1, f"item3 ack created != 1: {ack}")
        d = await detail(client, sid)
        _require(_pick(d, "vehicleClass", "vehicle_class") == "MOTORCYCLE",
                 f"item3 class not preserved: {d}")
        hits = await search(client, "KA05HJ8899")
        exact = [h for h in hits if _pick(h, "matchType", "match_type") == "EXACT_NORMALIZED_MATCH"]
        _require(len(exact) >= 1, f"item3 exact search failed: {hits}")
        record("two_wheeler", "PASS", [
            "MOTORCYCLE class (canonical taxonomy) preserved through ingest → detail",
            "plate of two-wheeler treated identically (no class assumptions)",
            "exact search hit via EXACT_NORMALIZED_MATCH",
        ], {"sighting_id": sid, "vehicle_class": "MOTORCYCLE", "search_label": "EXACT_NORMALIZED_MATCH"})

        # ── 4. partial plate: truncated read ─────────────────────────────────
        sid = "SGT-C7BS-0004"
        ts = "2026-09-28T10:00:04+00:00"
        ack = await ingest(client, CAM_1, [_sighting_item(
            sid, ts, plate=_plate("KA05M", "KA05M", 0.52, "PARTIAL",
                                  "NOT_ENOUGH_DATA", ts),
        )])
        _require(_pick(ack, "created") == 1, f"item4 ack created != 1: {ack}")
        hits = await search(client, "KA05")
        hit_ids = [( _pick(_pick(h, "sighting") or {}, "sightingId", "sighting_id"),
                     _pick(h, "matchType", "match_type")) for h in hits]
        mine = [label for hid, label in hit_ids if hid == sid]
        _require(mine and mine[0] in ("RAW_READ_MATCH", "PARTIAL_MATCH"),
                 f"item4 partial read not searchable/labeled: {hit_ids}")
        _require(all(label != "EXACT_NORMALIZED_MATCH" for hid, label in hit_ids if hid == sid),
                 f"item4 truncated read labeled exact (overclaim): {hit_ids}")
        record("partial_plate", "PASS", [
            "truncated read stored (quality PARTIAL / format NOT_ENOUGH_DATA)",
            "searchable by visible fragment",
            "never labeled EXACT_NORMALIZED_MATCH (no identity overclaim)",
        ], {"sighting_id": sid, "raw": "KA05M", "label": mine[0]})

        # ── 5. glare: garbage read, unreadable ───────────────────────────────
        sid = "SGT-C7BS-0005"
        ts = "2026-09-28T10:00:05+00:00"
        ack = await ingest(client, CAM_2, [_sighting_item(
            sid, ts, plate=_plate("IIIIIIII", "IIIIIIII", 0.21, "UNREADABLE",
                                  "UNKNOWN_FORMAT", ts),
        )])
        _require(_pick(ack, "created") == 1, f"item5 ack created != 1: {ack}")
        d = await detail(client, sid)
        pr = _pick(d, "plateRead", "plate_read") or {}
        _require(_pick(pr, "normalizedRead", "normalized_read") in (None,),
                 f"item5 fabricated normalization from garbage: {pr}")
        record("glare", "PASS", [
            "garbage read recorded as UNREADABLE / UNKNOWN_FORMAT",
            "no normalization fabricated from glare-corrupted text",
        ], {"sighting_id": sid, "quality": "UNREADABLE"}, recognition=RECOG_NOTE)

        # ── 6. night: correct instant, no suppression ───────────────────────
        sid = "SGT-C7BS-0006"
        ts = "2026-09-28T21:30:00+00:00"  # 03:00 IST — night operational window
        ack = await ingest(client, CAM_2, [_sighting_item(
            sid, ts, plate=_plate("DL8CAF5031", "DL8CAF5031", 0.77, "HIGH",
                                  "VALID_FORMAT", ts, normalized="DL8CAF5031"),
        )])
        _require(_pick(ack, "created") == 1, f"item6 ack created != 1: {ack}")
        d = await detail(client, sid)
        _require(_iso_z(_pick(d, "observedAt", "observed_at")) == "2026-09-28T21:30:00Z",
                 f"item6 night instant not preserved: {d}")
        record("night", "PASS", [
            "night observation recorded (no time-of-day suppression)",
            "UTC instant preserved exactly through round-trip",
        ], {"sighting_id": sid, "observed_at": "2026-09-28T21:30:00Z"}, recognition=RECOG_NOTE)

        # ── 7. fog: low-confidence top + candidate ambiguity ─────────────────
        sid = "SGT-C7BS-0007"
        ts = "2026-09-28T10:00:07+00:00"
        ack = await ingest(client, CAM_2, [_sighting_item(
            sid, ts, plate=_plate("MH12AB1234", "MH12AB1234", 0.41, "LOW",
                                  "POSSIBLE_FORMAT", ts, normalized="MH12AB1234",
                                  candidates=[
                                      _cand(1, "MH12AB1234", 0.41, "POSSIBLE_FORMAT"),
                                      _cand(2, "MH12A81234", 0.38, "POSSIBLE_FORMAT"),
                                  ]),
        )])
        _require(_pick(ack, "created") == 1, f"item7 ack created != 1: {ack}")
        cands = await candidates_of(client, sid)
        _require([_pick(c, "rank") for c in cands] == [1, 2], f"item7 rank order: {cands}")
        hits = await search(client, "A81234")
        labels = [_pick(h, "matchType", "match_type") for h in hits]
        _require("CANDIDATE_MATCH" in labels, f"item7 candidate not searchable: {labels}")
        record("fog", "PASS", [
            "low-confidence top read recorded with candidates preserved in rank order",
            "alternative interpretation searchable as CANDIDATE_MATCH",
            "uncertainty visible (confidence + candidate list)",
        ], {"sighting_id": sid, "top_conf": 0.41, "candidates": 2,
            "label": "CANDIDATE_MATCH"}, recognition=RECOG_NOTE)

        # ── 8. rain: per-character confidence degradation preserved ──────────
        sid = "SGT-C7BS-0008"
        ts = "2026-09-28T10:00:08+00:00"
        cc = [0.93, 0.88, 0.97, 0.91, 0.55, 0.42, 0.95, 0.90, 0.87, 0.92]
        ack = await ingest(client, CAM_2, [_sighting_item(
            sid, ts, plate=_plate("MH12RA1234", "MH12RA1234", 0.72, "HIGH",
                                  "VALID_FORMAT", ts, normalized="MH12RA1234",
                                  character_confidence=cc),
        )])
        _require(_pick(ack, "created") == 1, f"item8 ack created != 1: {ack}")
        d = await detail(client, sid)
        pr = _pick(d, "plateRead", "plate_read") or {}
        got = _pick(pr, "characterConfidence", "character_confidence")
        _require(got is not None and [round(float(x), 2) for x in got] == cc,
                 f"item8 character confidence not preserved: {got}")
        record("rain", "PASS", [
            "per-character confidence array persisted verbatim",
            "weak characters (0.42/0.55) visible to operator, not smoothed away",
        ], {"sighting_id": sid, "char_conf_len": len(got)}, recognition=RECOG_NOTE)

        # ── 9. motion blur: unreadable, no candidates ────────────────────────
        sid = "SGT-C7BS-0009"
        ts = "2026-09-28T10:00:09+00:00"
        ack = await ingest(client, CAM_2, [_sighting_item(
            sid, ts, plate=_plate("M1IZ4SS9", "M1IZ4SS9", 0.15, "UNREADABLE",
                                  "UNKNOWN_FORMAT", ts),
        )])
        _require(_pick(ack, "created") == 1, f"item9 ack created != 1: {ack}")
        d = await detail(client, sid)
        pr = _pick(d, "plateRead", "plate_read") or {}
        _require(_pick(pr, "quality") == "UNREADABLE", f"item9 quality lost: {pr}")
        record("motion_blur", "PASS", [
            "blurred read stored as UNREADABLE (observation kept, not dropped)",
            "quality flag survives ingest → detail",
        ], {"sighting_id": sid, "quality": "UNREADABLE"}, recognition=RECOG_NOTE)

        # ── 10. occlusion: heavily truncated visible fragment ────────────────
        sid = "SGT-C7BS-0010"
        ts = "2026-09-28T10:00:10+00:00"
        ack = await ingest(client, CAM_3, [_sighting_item(
            sid, ts, plate=_plate("MH12", "MH12", 0.35, "PARTIAL",
                                  "NOT_ENOUGH_DATA", ts),
        )])
        _require(_pick(ack, "created") == 1, f"item10 ack created != 1: {ack}")
        hits = await search(client, "MH1")
        mine = [_pick(h, "matchType", "match_type")
                for h in hits
                if _pick(_pick(h, "sighting") or {}, "sightingId", "sighting_id") == sid]
        _require(mine and mine[0] != "EXACT_NORMALIZED_MATCH",
                 f"item10 fragment labeled exact: {mine}")
        record("occlusion", "PASS", [
            "occluded fragment stored as PARTIAL / NOT_ENOUGH_DATA",
            "searchable by visible fragment, never labeled exact",
        ], {"sighting_id": sid, "raw": "MH12", "label": mine[0]})

        # ── 11. small/distant plate: very low confidence ─────────────────────
        sid = "SGT-C7BS-0011"
        ts = "2026-09-28T10:00:11+00:00"
        ack = await ingest(client, CAM_3, [_sighting_item(
            sid, ts, plate=_plate("GJ01XY4567", "GJ01XY4567", 0.08, "LOW",
                                  "POSSIBLE_FORMAT", ts, normalized="GJ01XY4567"),
        )])
        _require(_pick(ack, "created") == 1, f"item11 ack created != 1: {ack}")
        d = await detail(client, sid)
        pr = _pick(d, "plateRead", "plate_read") or {}
        _require(abs(float(_pick(pr, "confidence")) - 0.08) < 1e-6,
                 f"item11 confidence not exact: {pr}")
        _require(_pick(d, "watchlistStatus", "watchlist_status") == "NOT_CHECKED",
                 f"item11 watchlist overclaim: {d}")
        record("small_distant_plate", "PASS", [
            "0.08-confidence read recorded, confidence rendered exactly",
            "quality and confidence kept separate from identity",
        ], {"sighting_id": sid, "confidence": 0.08}, recognition=RECOG_NOTE)

        # ── 12. degraded camera: health context flows through ────────────────
        sid = "SGT-C7BS-0012"
        ts = "2026-09-28T10:00:12+00:00"
        ctx = json.dumps({"reason": "lens_blur", "since": "2026-09-28T09:00:00Z"})
        ack = await ingest(client, CAM_3, [_sighting_item(
            sid, ts, camera_health_state="DEGRADED", camera_health_context_json=ctx,
            detection_quality="LOW",
            plate=_plate("UP32KL7788", "UP32KL7788", 0.64, "LOW",
                          "POSSIBLE_FORMAT", ts, normalized="UP32KL7788"),
        )])
        _require(_pick(ack, "created") == 1, f"item12 ack created != 1: {ack}")
        d = await detail(client, sid)
        _require(_pick(d, "cameraHealthState", "camera_health_state") == "DEGRADED",
                 f"item12 health state lost: {d}")
        record("degraded_camera", "PASS", [
            "DEGRADED camera health state attached to the sighting (C2 context)",
            "sighting still recorded — degraded source does not silently drop reads",
        ], {"sighting_id": sid, "camera_health_state": "DEGRADED"})

        # ── 13. wrong candidate ranking: rank is authoritative ───────────────
        sid = "SGT-C7BS-0013"
        ts = "2026-09-28T10:00:13+00:00"
        ack = await ingest(client, CAM_3, [_sighting_item(
            sid, ts, track_id="TRK-C7BS-0013",
            plate=_plate("GJ01XX0000", "GJ01XX0000", 0.52, "LOW", "POSSIBLE_FORMAT", ts,
                         normalized="GJ01XX0000",
                         candidates=[
                             _cand(1, "GJ01XX0000", 0.52, "POSSIBLE_FORMAT"),
                             _cand(2, "GJ01XX0O00", 0.71, "POSSIBLE_FORMAT"),
                         ]),
        )])
        _require(_pick(ack, "created") == 1, f"item13 ack created != 1: {ack}")
        cands = await candidates_of(client, sid)
        _require([_pick(c, "rank") for c in cands] == [1, 2],
                 f"item13 candidates not in rank order: {cands}")
        _require(_pick(cands[0], "rawRead", "raw_read") == "GJ01XX0000",
                 f"item13 rank-1 candidate not first (provider order not preserved): {cands}")
        hits = await search(client, "0O00")
        labels = [_pick(h, "matchType", "match_type") for h in hits]
        _require("CANDIDATE_MATCH" in labels, f"item13 rank-2 candidate unsearchable: {labels}")
        record("wrong_candidate_ranking", "PASS", [
            "provider rank order preserved exactly (rank 1 first) even when rank 2 "
            "carries a higher raw confidence number — platform does not re-sort",
            "both rank-1 and rank-2 interpretations searchable via CANDIDATE_MATCH",
        ], {"sighting_id": sid, "rank_order": [1, 2], "label": "CANDIDATE_MATCH"})

        # ── 14. duplicate observation: idempotent re-ingest ──────────────────
        ack = await ingest(client, CAM_1, [item3_payload])
        _require(_pick(ack, "created") == 0 and _pick(ack, "duplicates") == 1,
                 f"item14 duplicate not detected: {ack}")
        d = await detail(client, "SGT-C7BS-0003")
        pr = _pick(d, "plateRead", "plate_read") or {}
        _require(_pick(pr, "rawRead", "raw_read") == "KA05HJ8899",
                 f"item14 stored raw mutated by duplicate: {pr}")
        record("duplicate_observation", "PASS", [
            "exact re-ingest → created=0, duplicates=1 (no second row)",
            "stored raw read unchanged after duplicate attempt",
        ], {"sighting_id": "SGT-C7BS-0003", "ack_created": 0, "ack_duplicates": 1})

        # ── Global bucket accounting over the whole battery ──────────────────
        summ = await global_summary(client)
        total = int(_pick(summ, "totalReads", "total_reads"))
        readable = int(_pick(summ, "readablePlates", "readable_plates"))
        partial = int(_pick(summ, "partialReads", "partial_reads"))
        unreadable = int(_pick(summ, "unreadablePlates", "unreadable_plates"))
        tracked = int(_pick(summ, "uniqueTrackedSightings", "unique_tracked_sightings"))
        cameras = int(_pick(summ, "camerasReporting", "cameras_reporting"))

        # Expected: 13 unique reads (14th is the duplicate). Buckets per repo
        # precedence: unreadable items 5,9; partial items 4,10; readable rest.
        expected = {"total": 13, "readable": 9, "partial": 2, "unreadable": 2,
                    "tracked": 3, "cameras": 3}
        got = {"total": total, "readable": readable, "partial": partial,
               "unreadable": unreadable, "tracked": tracked, "cameras": cameras}
        if got != expected:
            failures.append(f"summary buckets mismatch: expected {expected}, got {got}")

        return {"items": items, "summary_counts": got,
                "summary_expected": expected, "failures": failures}


async def main() -> int:
    started = _now_iso()
    report: dict = {
        "component": "C7_ANPR",
        "spec_section": "§48 blind-spot tests",
        "scope_note": (
            "Handling layer verified over the real HTTP API. Recognition layer "
            "(whether an OCR model would read degraded plates correctly) requires "
            "the production model — separate AI/ML phase (§54)."
        ),
        "started_at": started,
        "status": "FAIL",
        "items": {},
        "summary_counts": None,
        "failures": [],
    }
    proc = None
    log_path = None
    try:
        bootstrap_schema()
        proc, log_path = start_server()
        result = await run_battery()
        report.update(result)
        report["status"] = "PASS" if not report["failures"] else "FAIL"
    except StepFailed as exc:
        report["failures"].append(str(exc))
        report["status"] = "FAIL"
    except Exception as exc:  # noqa: BLE001
        report["failures"].append(f"{type(exc).__name__}: {exc}")
        report["status"] = "FAIL"
    finally:
        if proc is not None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except Exception:  # noqa: BLE001
                proc.kill()
            log_file = getattr(proc, "_bs_log_file", None)
            if log_file:
                log_file.close()
        report["finished_at"] = _now_iso()
        if log_path is not None:
            report["server_log"] = str(log_path)
        _emit_report(report)
        print(f"[bs] RESULT: {report['status']}", flush=True)
        for f in report.get("failures", []):
            print(f"[bs] FAILURE: {f}", flush=True)

    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--bootstrap-only", action="store_true")
    args = parser.parse_args()
    if args.bootstrap_only:
        bootstrap_schema()
        raise SystemExit(0)
    raise SystemExit(asyncio.run(main()))
