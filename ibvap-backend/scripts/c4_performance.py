"""Performance measurement for Component 4 (Correlation) — spec §61.

Measures, with the real C4 ingest path and real read APIs over HTTP against a
live uvicorn server, at 100 / 1,000 / 10,000 member events:

  * event list latency        GET /api/v1/correlations/
  * correlation detail        GET /api/v1/correlations/{id}
  * history                   GET /api/v1/correlations/{id}/history
  * relationship lookup       GET /api/v1/correlations/{id}/relationships

and reports p50 / p95 / max per measurement.

These are observations on this machine (SQLite, single dev process). They are
NOT production-capacity claims (§61) and no numbers are extrapolated.

Usage (from C:/SIH/ibvap-backend, venv python):

    venv/Scripts/python.exe scripts/c4_performance.py
    venv/Scripts/python.exe scripts/c4_performance.py --stages 100,1000
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
DB_REL = "tests/test_dbs/c4_perf_run.db"
DB_PATH = BACKEND_ROOT / DB_REL
REPORT_PATH = BACKEND_ROOT / "tests/test_dbs/c4_performance_report.json"
PORT = 8125
BASE = f"http://127.0.0.1:{PORT}"

CAMERAS = ["CAM-PF-01", "CAM-PF-02", "CAM-PF-03", "CAM-PF-04"]
SECTORS = ["SECTOR-PF-01", "SECTOR-PF-02"]
BASE_TS = datetime(2026, 9, 26, 0, 0, 0, tzinfo=timezone.utc)
# One triple of members every 10 minutes; members 5 s apart. Cross-triple gap
# (600 s) is far beyond the configured 60 s temporal window, so each triple
# forms exactly one group and no false cross-triple correlation can occur.
TRIPLE_SOURCES = [
    ("ZONE_ENTRY", "VIRTUAL_FENCE"),
    ("ANPR_READ", "ANPR"),
    ("ZONE_ENTRY", "VIRTUAL_FENCE"),
]


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
    """Fresh schema via the model metadata (alembic fresh-upgrade is broken by a
    pre-existing C7 migration — see scripts/e2e_c4_traceability.py docstring)."""
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
    log_path = BACKEND_ROOT / "tests/test_dbs/c4_perf_uvicorn.log"
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
            r = await client.get(f"{BASE}/api/v1/correlations/?page=1&page_size=1", timeout=3.0)
            if r.status_code == 200:
                _log("server healthy")
                return
            last_err = f"status {r.status_code}"
        except Exception as exc:  # noqa: BLE001
            last_err = f"{type(exc).__name__}: {exc}"
        await asyncio.sleep(0.5)
    raise StepFailed(f"server did not become healthy in {timeout_s}s (last: {last_err})")


def _event_body(triple: int, slot: int, kind: str, source: str) -> dict:
    camera = CAMERAS[triple % len(CAMERAS)]
    sector = SECTORS[triple % len(SECTORS)]
    track_id = f"TRK-PF-{triple:06d}"
    ts = (BASE_TS + timedelta(seconds=triple * 600 + slot * 5)).isoformat()
    body: dict = {
        "event_type": kind,
        "source": source,
        "camera_id": camera,
        "sector_id": sector,
        "track_id": track_id,
        "event_time": ts,
        "object_type": "VEHICLE",
        "confidence": 0.9,
        "is_night": False,
        "reliability": "HIGH",
        "modality": "VIDEO",
        "payload": {},
    }
    if source == "ANPR":
        plate = f"DL8CAF{triple:04d}"
        body["payload"] = {
            "anpr_plate": plate,
            "anpr_plate_confidence": 0.9,
            "anpr_quality": "HIGH",
            "track_candidate": track_id,
        }
    return body


async def _timed_get(client, url: str, params: dict | None = None) -> tuple[float, int]:
    t0 = time.perf_counter()
    r = await client.get(url, params=params, timeout=30.0)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    return elapsed_ms, r.status_code


async def seed_stage(
    client, first_triple: int, first_slot: int, events_to_add: int
) -> dict:
    """Ingest exactly `events_to_add` events, continuing the triple sequence.

    Continues from ``(first_triple, first_slot)`` so the cumulative event
    stream stays a contiguous sequence of 5s-spaced triples: the partial
    triple at the end of a stage is completed at the start of the next stage
    instead of being abandoned. This keeps the model invariant
    ``total_groups == ceil(cumulative_events / 3)`` exact at every stage.
    """
    ingest_ms: list[float] = []
    last_correlation_id: str | None = None
    events_done = 0
    triple = first_triple
    slot = first_slot
    t_batch = time.perf_counter()
    while events_done < events_to_add:
        kind, source = TRIPLE_SOURCES[slot]
        body = _event_body(triple, slot, kind, source)
        t0 = time.perf_counter()
        r = await client.post(
            f"{BASE}/api/v1/correlations/events/ingest",
            params={"source": source},
            json=body,
            timeout=60.0,
        )
        ingest_ms.append((time.perf_counter() - t0) * 1000.0)
        if r.status_code not in (200, 201):
            raise StepFailed(f"ingest failed at triple {triple} slot {slot}: {r.status_code} {r.text[:300]}")
        payload = r.json()
        cid = payload.get("correlation_id") or payload.get("correlationId")
        if cid:
            last_correlation_id = cid
        events_done += 1
        slot += 1
        if slot == 3:
            slot = 0
            triple += 1
        if events_done % 1000 == 0:
            _log(f"  ingested {events_done}/{events_to_add} events...")
    last_triple = triple - 1 if slot == 0 else triple
    batch_s = time.perf_counter() - t_batch
    return {
        "events_ingested_this_stage": events_to_add,
        "first_triple": first_triple,
        "last_triple": last_triple,
        "triples_touched_this_stage": last_triple - first_triple + 1,
        "batch_wall_seconds": round(batch_s, 2),
        "per_event": _percentiles(ingest_ms),
        "last_correlation_id": last_correlation_id,
    }


async def measure_reads(client, correlation_id: str, iterations: int) -> dict:
    reads: dict[str, dict] = {}
    for label, fn in {
        "list_page1_size50": lambda: _timed_get(client, f"{BASE}/api/v1/correlations/", {"page": 1, "page_size": 50}),
        "list_filtered_camera": lambda: _timed_get(
            client, f"{BASE}/api/v1/correlations/", {"page": 1, "page_size": 50, "camera_id": CAMERAS[0]}
        ),
        "correlation_detail": lambda: _timed_get(client, f"{BASE}/api/v1/correlations/{correlation_id}"),
        "history": lambda: _timed_get(client, f"{BASE}/api/v1/correlations/{correlation_id}/history", {"limit": 100}),
        "relationships": lambda: _timed_get(client, f"{BASE}/api/v1/correlations/{correlation_id}/relationships"),
    }.items():
        samples: list[float] = []
        for _ in range(iterations):
            ms, code = await fn()
            if code != 200:
                raise StepFailed(f"{label} returned HTTP {code}")
            samples.append(ms)
        reads[label] = _percentiles(samples)
    return reads


async def run(stages: list[int], iterations: int) -> dict:
    import httpx

    report: dict = {
        "started_at": datetime.now(timezone.utc).isoformat(),
        "base_url": BASE,
        "database": DB_REL,
        "environment_note": (
            "Measured on this development machine (SQLite via aiosqlite, single "
            "uvicorn process, sequential ingest over HTTP). Observations only — "
            "NOT a production-capacity claim (§61)."
        ),
        "stages": [],
        "failures": [],
    }

    async with httpx.AsyncClient() as client:
        await wait_for_health(client)
        cumulative_events = 0
        for stage_events in stages:
            _log(f"stage: {cumulative_events + stage_events} cumulative events")
            first_triple, first_slot = divmod(cumulative_events, 3)
            ingest_stats = await seed_stage(
                client, first_triple, first_slot, stage_events
            )
            cumulative_events += stage_events

            probe, code = await _timed_get(client, f"{BASE}/api/v1/correlations/", {"page": 1, "page_size": 1})
            if code != 200:
                raise StepFailed(f"list probe failed: {code}")
            listing = await client.get(f"{BASE}/api/v1/correlations/", params={"page": 1, "page_size": 1}, timeout=30.0)
            total_groups = listing.json().get("total")
            expected_groups = math.ceil(cumulative_events / 3)
            if total_groups != expected_groups:
                raise StepFailed(
                    f"group-count mismatch at {cumulative_events} events: "
                    f"total={total_groups}, expected={expected_groups} "
                    "(grouping deviates from the contiguous-triple model)"
                )

            sample_id = ingest_stats["last_correlation_id"]
            if not sample_id:
                raise StepFailed("no correlation id returned by the last ingest")
            detail = await client.get(f"{BASE}/api/v1/correlations/{sample_id}", timeout=30.0)
            if detail.status_code != 200:
                raise StepFailed(f"detail probe failed: {detail.status_code}")
            detail_payload = detail.json()
            member_count = len(detail_payload.get("members") or [])

            reads = await measure_reads(client, sample_id, iterations)
            report["stages"].append(
                {
                    "cumulative_events": cumulative_events,
                    "groups_in_db": total_groups,
                    "ingest": ingest_stats,
                    "reads": reads,
                    "sample": {
                        "correlation_id": sample_id,
                        "members_in_sample": member_count,
                        "relationships_in_sample": len(detail_payload.get("relationships") or []),
                        "note": "sample = the group formed by the last triple of this stage",
                    },
                }
            )
            _log(
                f"  done: groups={total_groups}, list p50={reads['list_page1_size50']['p50_ms']}ms "
                f"p95={reads['list_page1_size50']['p95_ms']}ms"
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
    parser.add_argument("--stages", default="100,1000,10000", help="comma-separated cumulative event counts")
    parser.add_argument("--iterations", type=int, default=30, help="read samples per endpoint per stage")
    args = parser.parse_args()
    stages = [int(s) for s in args.stages.split(",")]

    report: dict = {}
    server = None
    try:
        bootstrap_schema()
        server = start_server()
        report = asyncio.run(run(stages, args.iterations))
        _emit(report)
        for stage in report["stages"]:
            r = stage["reads"]
            _log(
                f"{stage['cumulative_events']:>6} events | "
                f"list p50/p95/max {r['list_page1_size50']['p50_ms']}/{r['list_page1_size50']['p95_ms']}/{r['list_page1_size50']['max_ms']} ms | "
                f"detail {r['correlation_detail']['p50_ms']}/{r['correlation_detail']['p95_ms']}/{r['correlation_detail']['max_ms']} ms | "
                f"history {r['history']['p50_ms']}/{r['history']['p95_ms']}/{r['history']['max_ms']} ms | "
                f"relationships {r['relationships']['p50_ms']}/{r['relationships']['p95_ms']}/{r['relationships']['max_ms']} ms"
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
