"""Performance measurement for Component 6 (Tracking) — spec §37.

Measures, with the real tracking ingest path and real read APIs over HTTP
against a live uvicorn server, at 10 / 30 / 100 cumulative tracks:

      * update latency            POST /api/v1/internal/tracking/update  (1-detection batch)
      * history query             GET  /api/v1/tracks/{id}/history
      * camera track feed         GET  /api/v1/cameras/{cam}/tracks/feed
      * camera summary            GET  /api/v1/cameras/{cam}/tracks/summary

and reports p50 / p95 / max per measurement.

Honesty notes (§37):
  * The registered provider is DEMO — no real tracker compute is included;
    update latency reflects the orchestration pipeline only.
  * History depth per track in this dataset is ≤ 2 rows (the DEMO provider
    emits no LOST/reacquire events), so the history measurement reflects
    query/response overhead, not deep-history scans.
  * These are observations on this machine (SQLite, single dev process).
    They are NOT production-capacity claims, and no numbers are extrapolated.

Usage (from C:/SIH/ibvap-backend, venv python):

    venv/Scripts/python.exe scripts/c6_performance.py
    venv/Scripts/python.exe scripts/c6_performance.py --stages 10,30
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
DB_REL = "tests/test_dbs/c6_perf_run.db"
DB_PATH = BACKEND_ROOT / DB_REL
REPORT_PATH = BACKEND_ROOT / "tests/test_dbs/c6_performance_report.json"
PORT = 8126
BASE = f"http://127.0.0.1:{PORT}"
INTERNAL_HEADERS = {"X-Internal-Service": "c6-perf-harness"}

LATENCY_CAMERA = "CAM-PF-LAT"    # single track T1; update-latency samples match it
BASE_TS = datetime(2026, 9, 27, 0, 0, 0, tzinfo=timezone.utc)


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
    """Fresh schema via the model metadata (same approach as c4_performance.py)."""
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
    log_path = BACKEND_ROOT / "tests/test_dbs/c6_perf_uvicorn.log"
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


def _det_item(det_id: str, cam_id: str, ts: datetime, seq: int) -> dict:
    return {
        "detectionId": det_id,
        "cameraId": cam_id,
        "observedAt": ts.isoformat(),
        "bboxX": 0.30 + (seq % 5) * 0.01,
        "bboxY": 0.40,
        "bboxWidth": 0.05,
        "bboxHeight": 0.10,
        "objectClass": "PERSON",
        "confidence": 0.8,
        "source": "DEMO",
    }


def _payload(cam_id: str, items: list[dict]) -> dict:
    return {"cameraId": cam_id, "source": "DEMO", "detections": items}


async def _timed_get(client, url: str, params: dict | None = None) -> tuple[float, int]:
    t0 = time.perf_counter()
    r = await client.get(url, params=params, timeout=30.0)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return elapsed_ms, r.status_code


async def measure_update_latency(client, samples: int, offset_s: int) -> dict:
    """`samples` sequential 1-detection ingest POSTs on LATENCY_CAMERA.

    First sample creates track T1; the rest match it (new detection ids), so
    the track count stays controlled while the full pipeline runs each time.
    """
    lat: list[float] = []
    for i in range(samples):
        item = _det_item(
            f"DET-PF-LAT-{offset_s + i:04d}", LATENCY_CAMERA,
            BASE_TS + timedelta(seconds=offset_s + i), i,
        )
        t0 = time.perf_counter()
        r = await client.post(
            f"{BASE}/api/v1/internal/tracking/update",
            json=_payload(LATENCY_CAMERA, [item]),
            headers=INTERNAL_HEADERS,
            timeout=60.0,
        )
        lat.append((time.perf_counter() - t0) * 1000.0)
        if r.status_code != 200:
            raise StepFailed(f"latency ingest failed: {r.status_code} {r.text[:300]}")
    return _percentiles(lat)


async def seed_track_batch(client, camera: str, count: int, offset_s: int) -> dict:
    """One POST batch of `count` detections on a fresh camera.

    All detections of the batch carry the same class; the DEMO provider's
    class queue for a fresh camera is empty for the whole batch, so each
    detection creates exactly one new TENTATIVE track.
    """
    items = [
        _det_item(f"DET-PF-{camera}-{i:04d}", camera, BASE_TS + timedelta(seconds=offset_s + i), i)
        for i in range(count)
    ]
    t0 = time.perf_counter()
    r = await client.post(
        f"{BASE}/api/v1/internal/tracking/update",
        json=_payload(camera, items),
        headers=INTERNAL_HEADERS,
        timeout=120.0,
    )
    wall_ms = (time.perf_counter() - t0) * 1000.0
    if r.status_code != 200:
        raise StepFailed(f"batch ingest failed: {r.status_code} {r.text[:300]}")
    body = r.json()
    expected_new = count
    if body["newTracks"] != expected_new or body["errors"] != 0:
        raise StepFailed(
            f"batch ingest mismatch on {camera}: expected newTracks={expected_new}, "
            f"got {body['newTracks']} (errors={body['errors']}, rejected={body['rejected']})"
        )
    return {
        "detections": count,
        "response_new_tracks": body["newTracks"],
        "response_matched": body["matched"],
        "wall_ms": round(wall_ms, 2),
        "provider_reported_latency_ms": body.get("processingLatencyMs"),
    }


async def verify_camera(client, camera: str, expected_tracks: int) -> dict:
    """Feed + summary + list must agree with the expected track count."""
    r = await client.get(f"{BASE}/api/v1/cameras/{camera}/tracks/feed", timeout=30.0)
    if r.status_code != 200:
        raise StepFailed(f"feed probe failed on {camera}: {r.status_code}")
    feed = r.json()
    feed_n = len(feed["tracks"])
    if feed_n != expected_tracks:
        raise StepFailed(f"feed track count mismatch on {camera}: {feed_n} != {expected_tracks}")

    r = await client.get(f"{BASE}/api/v1/cameras/{camera}/tracks/summary", timeout=30.0)
    if r.status_code != 200:
        raise StepFailed(f"summary probe failed on {camera}: {r.status_code}")
    summary = r.json()
    if summary["totalTracks"] != expected_tracks or summary["totalActive"] != expected_tracks:
        raise StepFailed(
            f"summary mismatch on {camera}: totalTracks={summary['totalTracks']}, "
            f"totalActive={summary['totalActive']}, expected={expected_tracks}"
        )

    r = await client.get(
        f"{BASE}/api/v1/tracks", params={"camera_id": camera, "page": 1, "pageSize": 1}, timeout=30.0
    )
    if r.status_code != 200:
        raise StepFailed(f"list probe failed on {camera}: {r.status_code}")
    total = r.json()["total"]
    if total != expected_tracks:
        raise StepFailed(f"list total mismatch on {camera}: {total} != {expected_tracks}")

    return {
        "feed_tracks": feed_n,
        "feed_state": feed["state"],
        "summary_total_tracks": summary["totalTracks"],
        "summary_total_active": summary["totalActive"],
        "summary_by_class": summary["byClass"],
        "list_total": total,
    }


async def measure_reads(client, camera: str, history_track_id: str, iterations: int) -> dict:
    reads: dict[str, dict] = {}
    for label, fn in {
        "history": lambda: _timed_get(
            client, f"{BASE}/api/v1/tracks/{history_track_id}/history", {"page": 1, "pageSize": 50}
        ),
        "camera_track_feed": lambda: _timed_get(client, f"{BASE}/api/v1/cameras/{camera}/tracks/feed"),
        "camera_summary": lambda: _timed_get(client, f"{BASE}/api/v1/cameras/{camera}/tracks/summary"),
    }.items():
        samples: list[float] = []
        for _ in range(iterations):
            ms, code = await fn()
            if code != 200:
                raise StepFailed(f"{label} returned HTTP {code}")
            samples.append(ms)
        reads[label] = _percentiles(samples)
    return reads


async def run(stages: list[int], iterations: int, latency_samples: int) -> dict:
    import httpx

    report: dict = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "base_url": BASE,
        "database": DB_REL,
        "provider": "DEMO (no real tracker compute — orchestration pipeline only)",
        "environment_note": (
            "Measured on this development machine (SQLite via aiosqlite, single "
            "uvicorn process, sequential requests). Observations only — NOT a "
            "production-capacity claim (§37). History depth per track in this "
            "dataset is ≤ 2 rows (no LOST/reacquire events from the DEMO provider)."
        ),
        "stages": [],
        "failures": [],
    }

    async with httpx.AsyncClient() as client:
        await wait_for_health(client)
        prev_target = 0
        latency_offset = 0
        stage_idx = 0
        history_track_id: str | None = None

        for target in stages:
            stage_idx += 1
            stage_add = target - prev_target
            if stage_add <= 0:
                raise StepFailed(f"stage targets must be strictly increasing: {stages}")
            camera = f"CAM-PF-{stage_idx}"
            _log(f"stage {stage_idx}: +{stage_add} tracks (cumulative {target})")

            latency = await measure_update_latency(client, latency_samples, latency_offset)
            latency_offset += latency_samples

            if history_track_id is None:
                r = await client.get(f"{BASE}/api/v1/cameras/{LATENCY_CAMERA}/tracks", timeout=30.0)
                if r.status_code != 200 or not r.json():
                    raise StepFailed("latency-camera track not found after latency phase")
                history_track_id = r.json()[0]["trackId"]

            batch = await seed_track_batch(client, camera, stage_add, prev_target)
            prev_target = target

            camera_checks = await verify_camera(client, camera, stage_add)

            r = await client.get(f"{BASE}/api/v1/tracks", params={"page": 1, "pageSize": 1}, timeout=30.0)
            if r.status_code != 200:
                raise StepFailed(f"global list probe failed: {r.status_code}")
            global_total = r.json()["total"]
            expected_global = target + 1  # + the single LATENCY_CAMERA track
            if global_total != expected_global:
                raise StepFailed(
                    f"global track total mismatch: {global_total} != {expected_global}"
                )

            reads = await measure_reads(client, camera, history_track_id, iterations)
            report["stages"].append({
                "stage": stage_idx,
                "tracks_added": stage_add,
                "cumulative_tracks": target,
                "global_tracks_in_db": global_total,
                "latency_camera_track_id": history_track_id,
                "update_latency_1det": latency,
                "batch_seed": batch,
                "camera": camera,
                "camera_checks": camera_checks,
                "reads": reads,
            })
            _log(
                f"  done: cam={camera} tracks={camera_checks['feed_tracks']} | "
                f"update p50={latency['p50_ms']}ms p95={latency['p95_ms']}ms | "
                f"feed p50={reads['camera_track_feed']['p50_ms']}ms p95={reads['camera_track_feed']['p95_ms']}ms | "
                f"summary p50={reads['camera_summary']['p50_ms']}ms | "
                f"history p50={reads['history']['p50_ms']}ms"
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
    parser.add_argument("--stages", default="10,30,100", help="comma-separated cumulative track targets")
    parser.add_argument("--iterations", type=int, default=30, help="read samples per endpoint per stage")
    parser.add_argument("--latency-samples", type=int, default=15, help="update-latency samples per stage")
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
                f"{stage['cumulative_tracks']:>4} tracks | "
                f"update {stage['update_latency_1det']['p50_ms']}/{stage['update_latency_1det']['p95_ms']} ms | "
                f"history {r['history']['p50_ms']}/{r['history']['p95_ms']} ms | "
                f"feed {r['camera_track_feed']['p50_ms']}/{r['camera_track_feed']['p95_ms']} ms | "
                f"summary {r['camera_summary']['p50_ms']}/{r['camera_summary']['p95_ms']} ms "
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
