#!/usr/bin/env python
# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — C2 §34 API Validation (REAL backend, clean environment)
# ─────────────────────────────────────────────────────────────────────────────
# Spec §34: "start the backend in a clean environment and call the actual
# camera-health observation endpoint. Verify: HTTP 200 / valid state / valid
# derived context / valid timestamps for: normal frame / degraded frame /
# frozen sample / viewpoint sample / network-degraded sample"
#
# This script:
#   1. Creates a FRESH SQLite database in a temp dir (DATABASE_URL env override)
#   2. Runs `alembic upgrade head` against it
#   3. Starts the real uvicorn backend on 127.0.0.1:8021 (ENV=development)
#   4. POSTs 5 health observations whose telemetry mirrors the measured
#      evidence of real benchmark samples:
#        normal frame        <- C2-0001 (ONLINE)            measured IQ + telemetry
#        degraded frame      <- C2-0055 (BLURRED)           measured IQ
#        frozen sample       <- C2-0169 (STREAM_DROP_FROZEN) frame_drop_rate 0.7466
#        viewpoint sample    <- C2-0141 (VIEWPOINT_CHANGED) measured vp evidence
#        network-degraded    <- C2-0236 (NETWORK_JITTER_SEVERE)
#   5. GETs the real /health endpoint for each camera and validates: HTTP 200,
#      valid state, valid derived context (viewpoint note/status, image/
#      network/stream statuses), valid timestamps (ISO, recent).
#   6. Calls the camera wall endpoint and the C1 evaluation endpoint over HTTP
#      to verify the derived health context is consumed end-to-end.
#   7. Writes a full evidence JSON next to the other C2 artifacts.
#
# Exit code 0 = all checks passed; 1 = at least one check failed.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

BACKEND = Path(r"C:\SIH\ibvap-backend")
PY = BACKEND / "venv" / "Scripts" / "python.exe"
TMP = Path(r"C:\Users\harsh\.qoder\tmp\c2_api_clean")
DB_FILE = TMP / "clean.db"
DB_URL = "sqlite+aiosqlite:///" + str(DB_FILE).replace("\\", "/")
PORT = 8021
BASE = f"http://127.0.0.1:{PORT}"
OUT = Path(r"C:\SIH\ml\c2_camera_health\benchmark\c2_api_validation_results.json")
UVICORN_LOG = TMP / "uvicorn_8021.log"

IST = timezone(timedelta(hours=5, minutes=30))

now_utc = datetime.now(timezone.utc)


def ts_naive_utc(dt: datetime) -> str:
    """Naive UTC wall-clock string (F8 documented rule: naive == UTC)."""
    return dt.astimezone(timezone.utc).replace(tzinfo=None).isoformat()


def stream_payload(drop_rate: float = 0.0) -> dict:
    return {
        "streamConnected": True,
        "sequenceNumber": 1,
        "expectedFps": 25.0,
        "observedFps": 25.0,
        "frameDropRate": drop_rate,
        "frameAgeMs": 1000.0,
        "reconnectCount": 0,
    }


NET_NORMAL = {
    "latencyMs": 25.0,
    "latencyVarianceMs": 8.0,
    "packetLossPercent": 0.1,
    "heartbeatAgeSec": 2.0,
}
NET_SEVERE = {
    "latencyMs": 169.6,       # measured: C2-0236 manifest telemetry
    "latencyVarianceMs": 130.9,
    "packetLossPercent": 0.97,
    "heartbeatAgeSec": 2.0,
}

SAMPLES = [
    {
        "key": "normal_frame",
        "camera_id": "C2API-ONLINE",
        "source_sample": "C2-0001",
        "source_class": "ONLINE",
        "source_ts": ts_naive_utc(now_utc - timedelta(seconds=2.0)),  # naive -> UTC (F8)
        "body": {
            "sourceTimestamp": ts_naive_utc(now_utc - timedelta(seconds=2.0)),
            "sourceSequence": 1,
            "stream": stream_payload(0.0),
            "network": NET_NORMAL,
            "image": {  # measured: repair1/probe record C2-0001
                "sharpness": 0.76238,
                "brightness": 0.536535,
                "exposure": "NORMAL",
                "contrast": 0.599455,
                "noise": 0.651695,
            },
            "viewpoint": {  # measured: probe viewpoint row C2-0001
                "shiftScore": 0.01916,
                "shiftConfidence": 0.503145,
                "inlierRatio": 0.503145,
            },
            "algorithmVersion": "prhaar-c2-api-validation",
        },
        "expect": {
            "status": "ONLINE",
            "stream_state": "CONNECTED",
            "image_status": ("GOOD",),
            "network_status": "STABLE",
            "viewpoint_status": "STABLE",
            "shift_detected": False,
        },
    },
    {
        "key": "degraded_frame",
        "camera_id": "C2API-BLURRED",
        "source_sample": "C2-0055",
        "source_class": "BLURRED",
        "source_ts": ts_naive_utc(now_utc - timedelta(seconds=2.0)),  # naive -> UTC (F8)
        "body": {
            "sourceTimestamp": ts_naive_utc(now_utc - timedelta(seconds=2.0)),
            "sourceSequence": 1,
            "stream": stream_payload(0.0),
            "network": NET_NORMAL,
            "image": {  # measured: repair1 record C2-0055 (BLURRED, sharpness 0.20)
                "sharpness": 0.200305,
                "brightness": 0.537587,
                "exposure": "NORMAL",
                "contrast": 0.566096,
                "noise": 0.931638,
            },
            "algorithmVersion": "prhaar-c2-api-validation",
        },
        "expect": {
            "status": "DEGRADED",
            "stream_state": "CONNECTED",
            "image_status": ("DEGRADED", "FAILED"),
            "network_status": "STABLE",
            "viewpoint_status": "UNKNOWN",  # no viewpoint evidence supplied
            "shift_detected": False,
        },
    },
    {
        "key": "frozen_sample",
        "camera_id": "C2API-FROZEN",
        "source_sample": "C2-0169",
        "source_class": "STREAM_DROP_FROZEN",
        "source_ts": (now_utc - timedelta(seconds=1.6)).isoformat(),  # explicit UTC "Z"-equivalent
        "body": {
            "sourceTimestamp": (now_utc - timedelta(seconds=1.6)).isoformat(),
            "sourceSequence": 1,
            "stream": stream_payload(0.7466),  # measured: C2-0169 frame_drop_rate
            "network": NET_NORMAL,
            "image": {  # measured: probe record C2-0169
                "sharpness": 0.759489,
                "brightness": 0.538741,
                "exposure": "NORMAL",
                "contrast": 0.591067,
                "noise": 0.651287,
            },
            "algorithmVersion": "prhaar-c2-api-validation",
        },
        "expect": {
            "status": "FROZEN",
            "stream_state": "FROZEN",
            "image_status": ("GOOD",),
            "network_status": "STABLE",
            "viewpoint_status": "UNKNOWN",
            "shift_detected": False,
        },
    },
    {
        "key": "viewpoint_sample",
        "camera_id": "C2API-VIEWPOINT",
        "source_sample": "C2-0141",
        "source_class": "VIEWPOINT_CHANGED",
        "source_ts": (now_utc - timedelta(seconds=1.2)).astimezone(IST).isoformat(),  # IST offset
        "body": {
            "sourceTimestamp": (now_utc - timedelta(seconds=1.2)).astimezone(IST).isoformat(),
            "sourceSequence": 1,
            "stream": stream_payload(0.0),
            "network": NET_NORMAL,
            "image": {  # measured: probe record C2-0141
                "sharpness": 0.403431,
                "brightness": 0.447248,
                "exposure": "UNDEREXPOSED",
                "contrast": 0.862678,
                "noise": 0.723627,
            },
            "viewpoint": {  # measured: probe viewpoint row C2-0141 (persistent displacement)
                "shiftScore": 0.423052,
                "shiftConfidence": 0.631579,
                "inlierRatio": 0.631579,
            },
            "algorithmVersion": "prhaar-c2-api-validation",
        },
        "expect": {
            "status": "DEGRADED",
            "stream_state": "CONNECTED",
            "image_status": ("DEGRADED", "FAILED"),
            "network_status": "STABLE",
            "viewpoint_status": "SHIFT_DETECTED",
            "shift_detected": True,
        },
    },
    {
        "key": "network_degraded_sample",
        "camera_id": "C2API-NETSEV",
        "source_sample": "C2-0236",
        "source_class": "NETWORK_JITTER_SEVERE",
        "source_ts": (now_utc - timedelta(seconds=0.8)).isoformat(),
        "body": {
            "sourceTimestamp": (now_utc - timedelta(seconds=0.8)).isoformat(),
            "sourceSequence": 1,
            "stream": stream_payload(0.0),
            "network": NET_SEVERE,  # measured: C2-0236 manifest telemetry
            "image": {  # measured: probe record C2-0236
                "sharpness": 0.761899,
                "brightness": 0.538421,
                "exposure": "NORMAL",
                "contrast": 0.592221,
                "noise": 0.650618,
            },
            "algorithmVersion": "prhaar-c2-api-validation",
        },
        "expect": {
            "status": "DEGRADED",
            "stream_state": "CONNECTED",
            "image_status": ("GOOD",),
            "network_status": "DEGRADED",
            "viewpoint_status": "UNKNOWN",
            "shift_detected": False,
        },
    },
]

ZONE_POLYGON = [
    {"x": 0.2, "y": 0.2},
    {"x": 0.8, "y": 0.2},
    {"x": 0.8, "y": 0.8},
    {"x": 0.2, "y": 0.8},
]
EVAL_BBOX = {"x": 0.45, "y": 0.45, "width": 0.1, "height": 0.2}  # bottom-center = (0.5, 0.65)

evidence: dict = {
    "spec": "§34 — real API validation, clean environment",
    "started_utc": now_utc.isoformat(),
    "environment": {
        "backend": str(BACKEND),
        "python": str(PY),
        "database_url": DB_URL,
        "port": PORT,
        "env_mode": "development",
        "note": "Fresh DB file; alembic upgrade head; uvicorn real app. "
                "Payload telemetry mirrors measured benchmark records (see source_sample per entry).",
    },
    "checks": [],
    "samples": [],
    "camera_wall": None,
    "history": [],
    "c1_context_http": [],
}


def check(name: str, ok: bool, detail) -> bool:
    evidence["checks"].append({"name": name, "ok": bool(ok), "detail": detail})
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {str(detail)[:200]}")
    return ok


def fail(msg: str) -> None:
    print(f"ABORT: {msg}")
    evidence["aborted"] = msg
    OUT.write_text(json.dumps(evidence, indent=2, default=str), encoding="utf-8")
    sys.exit(1)


def port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


proc = None
try:
    # ── 0. Clean temp dir ────────────────────────────────────────────────────
    TMP.mkdir(parents=True, exist_ok=True)
    for f in (DB_FILE, Path(str(DB_FILE) + "-wal"), Path(str(DB_FILE) + "-shm")):
        if f.exists():
            f.unlink()
    print(f"[0] fresh DB target: {DB_FILE}")

    if not port_free(PORT):
        fail(f"port {PORT} is already in use")

    env = os.environ.copy()
    env["DATABASE_URL"] = DB_URL
    env["ENV"] = "development"

    # ── 1. alembic upgrade head on the fresh DB ─────────────────────────────
    print("[1] alembic upgrade head ...")
    r = subprocess.run(
        [str(PY), "-m", "alembic", "upgrade", "head"],
        cwd=str(BACKEND), env=env, capture_output=True, text=True, timeout=240,
    )
    check("alembic_upgrade_head", r.returncode == 0,
          {"returncode": r.returncode, "stdout_tail": r.stdout[-600:], "stderr_tail": r.stderr[-400:]})
    if r.returncode != 0:
        fail("alembic upgrade failed")

    # ── 2. start real backend ───────────────────────────────────────────────
    print(f"[2] starting uvicorn on {BASE} ...")
    log_fh = open(UVICORN_LOG, "w", encoding="utf-8")
    proc = subprocess.Popen(
        [str(PY), "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(PORT), "--log-level", "info"],
        cwd=str(BACKEND), env=env, stdout=log_fh, stderr=subprocess.STDOUT,
    )
    health = None
    deadline = time.time() + 90
    while time.time() < deadline:
        if proc.poll() is not None:
            fail(f"uvicorn exited early rc={proc.returncode}; log: {UVICORN_LOG}")
        try:
            resp = httpx.get(f"{BASE}/api/v1/health", timeout=2.0)
            if resp.status_code == 200:
                health = resp.json()
                break
        except httpx.HTTPError:
            pass
        time.sleep(0.5)
    if health is None:
        fail("backend did not become healthy in 90s")
    check("backend_health", health.get("status") == "ok",
          {"response": health, "wall_to_healthy": "ok"})

    with httpx.Client(base_url=BASE, timeout=30.0) as client:
        # ── 3. ingest 5 observations ────────────────────────────────────────
        for s in SAMPLES:
            print(f"[3] POST observation: {s['key']} -> {s['camera_id']}")
            resp = client.post(f"/api/v1/cameras/{s['camera_id']}/health/observations", json=s["body"])
            entry = {
                "key": s["key"], "camera_id": s["camera_id"],
                "source_sample": s["source_sample"], "source_class": s["source_class"],
                "request": s["body"], "post_status_code": resp.status_code,
                "post_response": resp.json() if resp.headers.get("content-type", "").startswith("application/json") else resp.text[:400],
            }
            ok200 = resp.status_code == 200
            check(f"ingest_http200[{s['key']}]", ok200, resp.status_code)
            if ok200:
                j = entry["post_response"]
                check(f"ingest_accepted[{s['key']}]",
                      j.get("accepted") is True and isinstance(j.get("observationId"), int) and j.get("observationId", 0) >= 1,
                      {"accepted": j.get("accepted"), "observationId": j.get("observationId")})
                check(f"ingest_derived_status[{s['key']}]", j.get("currentStatus") == s["expect"]["status"],
                      {"expected": s["expect"]["status"], "got": j.get("currentStatus")})
            evidence["samples"].append(entry)

        # ── 4. GET /health per camera — valid state/context/timestamps ──────
        for s in SAMPLES:
            print(f"[4] GET /health: {s['camera_id']}")
            resp = client.get(f"/api/v1/cameras/{s['camera_id']}/health")
            check(f"get_health_http200[{s['key']}]", resp.status_code == 200, resp.status_code)
            if resp.status_code != 200:
                continue
            h = resp.json()
            entry = next(e for e in evidence["samples"] if e["key"] == s["key"])
            entry["health_response"] = h
            exp = s["expect"]

            check(f"state[{s['key']}]", h.get("status") == exp["status"],
                  {"expected": exp["status"], "got": h.get("status")})
            check(f"source_LIVE[{s['key']}]", h.get("source") == "LIVE", h.get("source"))

            # timestamps
            lu = h.get("lastUpdated")
            lu_dt = None
            try:
                lu_dt = datetime.fromisoformat(lu) if lu else None
            except ValueError:
                lu_dt = None
            fresh = lu_dt is not None and abs((datetime.now(timezone.utc) - lu_dt.astimezone(timezone.utc)).total_seconds()) < 300
            check(f"lastUpdated_valid_iso_recent[{s['key']}]", fresh,
                  {"lastUpdated": lu, "parsed": str(lu_dt)})

            vp = h.get("viewpoint") or {}
            check(f"viewpoint_status[{s['key']}]", vp.get("status") == exp["viewpoint_status"],
                  {"expected": exp["viewpoint_status"], "got": vp.get("status")})
            check(f"viewpoint_shiftDetected[{s['key']}]", vp.get("shiftDetected") == exp["shift_detected"],
                  vp.get("shiftDetected"))
            if exp["shift_detected"]:
                note = vp.get("fenceConfidenceNote")
                da = vp.get("detectedAt")
                da_ok = False
                try:
                    da_ok = da is not None and datetime.fromisoformat(da) is not None
                except ValueError:
                    da_ok = False
                check(f"viewpoint_derived_context[{s['key']}]",
                      bool(note) and da_ok,
                      {"fenceConfidenceNote": note, "detectedAt": da})

            img = h.get("image") or {}
            check(f"image_status[{s['key']}]", img.get("status") in exp["image_status"],
                  {"expected_any": list(exp["image_status"]), "got": img.get("status")})
            sent_sharp = s["body"].get("image", {}).get("sharpness")
            got_sharp = next((m.get("value") for m in (img.get("metrics") or []) if m.get("metric") == "sharpness"), None)
            check(f"image_sharpness_echo[{s['key']}]",
                  sent_sharp is not None and got_sharp is not None and abs(float(got_sharp) - sent_sharp) < 1e-6,
                  {"sent": sent_sharp, "got": got_sharp})

            net = h.get("network") or {}
            check(f"network_status[{s['key']}]", net.get("status") == exp["network_status"],
                  {"expected": exp["network_status"], "got": net.get("status")})
            st = h.get("stream") or {}
            check(f"stream_state[{s['key']}]", st.get("state") == exp["stream_state"],
                  {"expected": exp["stream_state"], "got": st.get("state")})

            reason = h.get("statusReason")
            if exp["status"] != "ONLINE":
                check(f"statusReason_present[{s['key']}]", bool(reason), reason)

        # ── 5. camera wall endpoint ─────────────────────────────────────────
        print("[5] GET /cameras/health?ids=... (camera wall)")
        ids = ",".join(s["camera_id"] for s in SAMPLES)
        resp = client.get(f"/api/v1/cameras/health", params={"ids": ids})
        check("camera_wall_http200", resp.status_code == 200, resp.status_code)
        if resp.status_code == 200:
            wall = resp.json()
            evidence["camera_wall"] = wall
            by_id = {w.get("cameraId"): w for w in wall}
            check("camera_wall_all_5_present", all(s["camera_id"] in by_id for s in SAMPLES),
                  sorted(by_id.keys()))
            for s in SAMPLES:
                w = by_id.get(s["camera_id"], {})
                check(f"camera_wall_state[{s['key']}]", w.get("status") == s["expect"]["status"],
                      {"expected": s["expect"]["status"], "got": w.get("status")})
            degraded_ids = [s["camera_id"] for s in SAMPLES if s["expect"]["status"] != "ONLINE"]
            false_online = [cid for cid in degraded_ids if by_id.get(cid, {}).get("status") == "ONLINE"]
            check("camera_wall_no_false_online", not false_online, false_online)

        # ── 6. history timestamps (supplementary F8 evidence) ───────────────
        print("[6] GET /health/history (timestamp round-trip)")
        for cid in ("C2API-ONLINE", "C2API-VIEWPOINT"):
            resp = client.get(f"/api/v1/cameras/{cid}/health/history",
                              params={"resolution": "1m", "limit": 10})
            ok = resp.status_code == 200
            rec = {"camera_id": cid, "http": resp.status_code}
            if ok:
                j = resp.json()
                rec["points"] = j.get("points")
                pts = j.get("points") or []
                good = False
                if pts:
                    try:
                        pt = datetime.fromisoformat(pts[0]["timestamp"])
                        good = abs((datetime.now(timezone.utc) - pt.astimezone(timezone.utc)).total_seconds()) < 300
                    except (ValueError, KeyError):
                        good = False
                check(f"history_point_recent[{cid}]", good, rec.get("points"))
            else:
                check(f"history_http200[{cid}]", False, resp.status_code)
            evidence["history"].append(rec)

        # ── 7. C1 context consumption over HTTP ─────────────────────────────
        print("[7] C1 integration over HTTP: zones + track_and_evaluate")
        eval_specs = [
            {
                "name": "viewpoint_camera_context",
                "camera_id": "C2API-VIEWPOINT",
                "track_id": "TRK-API-VIEW-1",
                "expect_low_reliability_factor": True,   # health context override (SHIFT_DETECTED -> LOW)
            },
            {
                "name": "online_camera_context",
                "camera_id": "C2API-ONLINE",
                "track_id": "TRK-API-ONLINE-1",
                "expect_low_reliability_factor": False,  # healthy context -> caller HIGH retained
            },
        ]
        for es in eval_specs:
            zresp = client.post("/api/v1/zones", json={
                "camera_id": es["camera_id"],
                "name": f"API validation zone ({es['camera_id']})",
                "polygon": ZONE_POLYGON,
                "active": True,
            })
            zrec = {"name": es["name"], "zone_http": zresp.status_code,
                    "zone": zresp.json() if zresp.status_code in (200, 201) else zresp.text[:300]}
            check(f"zone_create[{es['name']}]", zresp.status_code in (200, 201), zresp.status_code)

            eresp = client.post("/api/v1/evaluation/track_and_evaluate", json={
                "track_id": es["track_id"],
                "camera_id": es["camera_id"],
                "object_type": "HUMAN",
                "bbox": EVAL_BBOX,
                "confidence": 0.9,
                "is_night": False,
                "multi_camera_confirmed": False,
                "reliability": "HIGH",  # caller says HIGH; context may override
            })
            zrec["eval_http"] = eresp.status_code
            check(f"track_and_evaluate_http200[{es['name']}]", eresp.status_code == 200, eresp.status_code)
            if eresp.status_code == 200:
                ej = eresp.json()
                zrec["eval_response"] = ej
                incident = ej.get("incident") or {}
                factors = incident.get("factors") or []
                factor_keys = [f.get("code") for f in factors]  # real factor dicts: {code,label,points,evidence}
                has_low = "LOW_RELIABILITY" in factor_keys
                check(f"c1_incident_created[{es['name']}]", bool(incident.get("incident_id") or incident.get("risk_score") is not None),
                      {"incident": {k: incident.get(k) for k in ("incident_id", "risk_score", "severity")}})
                check(f"c1_low_reliability_factor[{es['name']}]",
                      has_low == es["expect_low_reliability_factor"],
                      {"expected": es["expect_low_reliability_factor"], "factor_keys": factor_keys})
            evidence["c1_context_http"].append(zrec)

    # ── summary ─────────────────────────────────────────────────────────────
    total = len(evidence["checks"])
    failed = [c for c in evidence["checks"] if not c["ok"]]
    evidence["finished_utc"] = datetime.now(timezone.utc).isoformat()
    evidence["summary"] = {"checks_total": total, "checks_failed": len(failed),
                           "failed_names": [c["name"] for c in failed]}
    OUT.write_text(json.dumps(evidence, indent=2, default=str), encoding="utf-8")
    print(f"\nchecks: {total - len(failed)}/{total} passed; failed: {[c['name'] for c in failed]}")
    print(f"evidence -> {OUT}")
    sys.exit(0 if not failed else 1)

finally:
    if proc is not None and proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(timeout=8)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("[9] backend stopped")
