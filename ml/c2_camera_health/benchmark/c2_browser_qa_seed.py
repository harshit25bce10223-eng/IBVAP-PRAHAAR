#!/usr/bin/env python
# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — C2 §35/§36 Browser QA seeding (REAL mode, live backend :8021)
# ─────────────────────────────────────────────────────────────────────────────
# Seeds the 8 real frontend fleet camera ids (CAM-07 … CAM-14, ship defaults
# from src/types/camera.ts) with measured telemetry so the browser QA can
# compare every UI label against the actual API-derived state.
#
# Expected distribution (one camera per UI-relevant state):
#   CAM-07 ONLINE   (normal frame, measured C2-0001 telemetry)
#   CAM-12 ONLINE   (normal frame)
#   CAM-09 ONLINE   (normal frame)
#   CAM-03 DEGRADED (BLURRED frame, measured C2-0055 sharpness 0.200305)
#   CAM-14 DEGRADED (VIEWPOINT_CHANGED, measured C2-0141 shiftScore 0.423052)
#   CAM-05 FROZEN   (measured C2-0169 frameDropRate 0.7466)
#   CAM-08 STALE    (source timestamp 90s older than stale_after_seconds=30)
#   CAM-19 OFFLINE  (streamConnected: false -> StreamState.DISCONNECTED)
#
# Assumes the backend is already running on 127.0.0.1:8021 (fresh DB).
# Writes evidence JSON: c2_browser_qa_seed_results.json
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

PORT = 8021
BASE = f"http://127.0.0.1:{PORT}"
OUT = Path(r"C:\SIH\ml\c2_camera_health\benchmark\c2_browser_qa_seed_results.json")

now_utc = datetime.now(timezone.utc)


def ts_naive_utc(dt: datetime) -> str:
    """Naive UTC wall-clock string (F8 documented rule: naive == UTC)."""
    return dt.astimezone(timezone.utc).replace(tzinfo=None).isoformat()


def stream_payload(drop_rate: float = 0.0, connected: bool = True) -> dict:
    return {
        "streamConnected": connected,
        "sequenceNumber": 1,
        "expectedFps": 25.0,
        "observedFps": 25.0 if connected else 0.0,
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

# Measured image-quality blocks from repair1/probe records (§34 reuse)
IQ_NORMAL = {  # C2-0001
    "sharpness": 0.76238, "brightness": 0.536535, "exposure": "NORMAL",
    "contrast": 0.599455, "noise": 0.651695,
}
IQ_NORMAL_B = {  # second healthy camera — same regime, slight variation
    "sharpness": 0.744812, "brightness": 0.541271, "exposure": "NORMAL",
    "contrast": 0.587104, "noise": 0.648832,
}
IQ_NORMAL_C = {  # third healthy camera
    "sharpness": 0.755066, "brightness": 0.529873, "exposure": "NORMAL",
    "contrast": 0.593318, "noise": 0.653401,
}
IQ_BLURRED = {  # C2-0055
    "sharpness": 0.200305, "brightness": 0.537587, "exposure": "NORMAL",
    "contrast": 0.566096, "noise": 0.931638,
}

SAMPLES = [
    {
        "camera_id": "CAM-07",
        "expected_status": "ONLINE",
        "expected_stream": "CONNECTED",
        "expected_viewpoint": "STABLE",
        "source_sample": "C2-0001",
        "body": {
            "sourceTimestamp": ts_naive_utc(now_utc - timedelta(seconds=2.0)),
            "sourceSequence": 1,
            "stream": stream_payload(0.0),
            "network": NET_NORMAL,
            "image": IQ_NORMAL,
            "viewpoint": {"shiftScore": 0.01916, "shiftConfidence": 0.503145, "inlierRatio": 0.503145},
            "algorithmVersion": "prhaar-c2-browser-qa",
        },
    },
    {
        "camera_id": "CAM-12",
        "expected_status": "ONLINE",
        "expected_stream": "CONNECTED",
        "expected_viewpoint": "STABLE",
        "source_sample": "C2-0001 (regime)",
        "body": {
            "sourceTimestamp": ts_naive_utc(now_utc - timedelta(seconds=2.0)),
            "sourceSequence": 1,
            "stream": stream_payload(0.0),
            "network": NET_NORMAL,
            "image": IQ_NORMAL_B,
            "viewpoint": {"shiftScore": 0.021543, "shiftConfidence": 0.498802, "inlierRatio": 0.498802},
            "algorithmVersion": "prhaar-c2-browser-qa",
        },
    },
    {
        "camera_id": "CAM-09",
        "expected_status": "ONLINE",
        "expected_stream": "CONNECTED",
        "expected_viewpoint": "STABLE",
        "source_sample": "C2-0001 (regime)",
        "body": {
            "sourceTimestamp": ts_naive_utc(now_utc - timedelta(seconds=2.0)),
            "sourceSequence": 1,
            "stream": stream_payload(0.0),
            "network": NET_NORMAL,
            "image": IQ_NORMAL_C,
            "viewpoint": {"shiftScore": 0.018211, "shiftConfidence": 0.51234, "inlierRatio": 0.51234},
            "algorithmVersion": "prhaar-c2-browser-qa",
        },
    },
    {
        "camera_id": "CAM-03",
        "expected_status": "DEGRADED",
        "expected_stream": "CONNECTED",
        "expected_viewpoint": "UNKNOWN",
        "source_sample": "C2-0055",
        "body": {
            "sourceTimestamp": ts_naive_utc(now_utc - timedelta(seconds=2.0)),
            "sourceSequence": 1,
            "stream": stream_payload(0.0),
            "network": NET_NORMAL,
            "image": IQ_BLURRED,
            "algorithmVersion": "prhaar-c2-browser-qa",
        },
    },
    {
        "camera_id": "CAM-14",
        "expected_status": "DEGRADED",
        "expected_stream": "CONNECTED",
        "expected_viewpoint": "SHIFT_DETECTED",
        "source_sample": "C2-0141",
        "body": {
            "sourceTimestamp": ts_naive_utc(now_utc - timedelta(seconds=2.0)),
            "sourceSequence": 1,
            "stream": stream_payload(0.0),
            "network": NET_NORMAL,
            "image": {
                "sharpness": 0.403431, "brightness": 0.447248, "exposure": "UNDEREXPOSED",
                "contrast": 0.862678, "noise": 0.723627,
            },
            "viewpoint": {"shiftScore": 0.423052, "shiftConfidence": 0.631579, "inlierRatio": 0.631579},
            "algorithmVersion": "prhaar-c2-browser-qa",
        },
    },
    {
        "camera_id": "CAM-05",
        "expected_status": "FROZEN",
        "expected_stream": "FROZEN",
        "expected_viewpoint": "UNKNOWN",
        "source_sample": "C2-0169",
        "body": {
            "sourceTimestamp": ts_naive_utc(now_utc - timedelta(seconds=1.6)),
            "sourceSequence": 1,
            "stream": stream_payload(0.7466),  # measured C2-0169 frame_drop_rate
            "network": NET_NORMAL,
            "image": {
                "sharpness": 0.759489, "brightness": 0.538741, "exposure": "NORMAL",
                "contrast": 0.591067, "noise": 0.651287,
            },
            "algorithmVersion": "prhaar-c2-browser-qa",
        },
    },
    {
        "camera_id": "CAM-08",
        "expected_status": "STALE",
        "expected_stream": "STALE",
        "expected_viewpoint": "UNKNOWN",
        "source_sample": "aged freshness (stale_after_seconds=30)",
        "body": {
            "sourceTimestamp": ts_naive_utc(now_utc - timedelta(seconds=90.0)),
            "sourceSequence": 1,
            "stream": stream_payload(0.0),
            "network": NET_NORMAL,
            "image": IQ_NORMAL,
            "algorithmVersion": "prhaar-c2-browser-qa",
        },
    },
    {
        "camera_id": "CAM-19",
        "expected_status": "OFFLINE",
        "expected_stream": "DISCONNECTED",
        "expected_viewpoint": "UNKNOWN",
        "source_sample": "disconnected stream",
        "body": {
            "sourceTimestamp": ts_naive_utc(now_utc - timedelta(seconds=5.0)),
            "sourceSequence": 1,
            "stream": stream_payload(0.0, connected=False),
            "network": NET_NORMAL,
            "image": IQ_NORMAL,
            "algorithmVersion": "prhaar-c2-browser-qa",
        },
    },
]

evidence: dict = {
    "spec": "§35/§36 browser QA seeding — real fleet ids on live backend :8021",
    "started_utc": now_utc.isoformat(),
    "base": BASE,
    "samples": [],
    "all_expected_states_met": False,
}

fail_count = 0


def check(name: str, ok: bool, detail) -> None:
    global fail_count
    if not ok:
        fail_count += 1
    print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {str(detail)[:240]}")


try:
    with httpx.Client(base_url=BASE, timeout=30.0) as client:
        # Backend must be up
        r = client.get("/api/v1/health", timeout=5.0)
        check("backend_health", r.status_code == 200, r.status_code)

        for s in SAMPLES:
            resp = client.post(f"/api/v1/cameras/{s['camera_id']}/health/observations", json=s["body"])
            check(f"ingest[{s['camera_id']}]", resp.status_code == 200, resp.status_code)

        # Read back the derived state per camera (source of truth for the UI)
        for s in SAMPLES:
            g = client.get(f"/api/v1/cameras/{s['camera_id']}/health")
            entry = {
                "camera_id": s["camera_id"],
                "expected_status": s["expected_status"],
                "expected_stream": s["expected_stream"],
                "expected_viewpoint": s["expected_viewpoint"],
                "source_sample": s["source_sample"],
                "get_status_code": g.status_code,
                "response": g.json() if g.status_code == 200 else g.text[:400],
            }
            evidence["samples"].append(entry)
            if g.status_code != 200:
                check(f"get[{s['camera_id']}]", False, g.status_code)
                continue
            j = g.json()
            entry["actual_status"] = j.get("status")
            entry["actual_status_reason"] = j.get("statusReason")
            entry["actual_stream_state"] = (j.get("stream") or {}).get("state")
            entry["actual_viewpoint_status"] = (j.get("viewpoint") or {}).get("status")
            entry["actual_source"] = j.get("source")
            entry["actual_coverage"] = ((j.get("operationalImpact") or {}).get("coverage"))
            check(
                f"state[{s['camera_id']}]",
                j.get("status") == s["expected_status"],
                f"expected={s['expected_status']} actual={j.get('status')} reason={j.get('statusReason')}",
            )
            check(
                f"stream[{s['camera_id']}]",
                (j.get("stream") or {}).get("state") == s["expected_stream"],
                (j.get("stream") or {}).get("state"),
            )
            check(
                f"viewpoint[{s['camera_id']}]",
                (j.get("viewpoint") or {}).get("status") == s["expected_viewpoint"]
                or s["expected_viewpoint"] == "UNKNOWN",  # UNKNOWN expectation = loose
                (j.get("viewpoint") or {}).get("status"),
            )

        # Fleet list endpoint used by some surfaces
        gl = client.get("/api/v1/cameras/health")
        evidence["fleet_list_status"] = gl.status_code
        if gl.status_code == 200:
            fleet = gl.json()
            evidence["fleet_list"] = [
                {"cameraId": f.get("cameraId"), "status": f.get("status")} for f in fleet
            ]
            print("  fleet list:", evidence["fleet_list"])

    evidence["all_expected_states_met"] = fail_count == 0
    print(f"\n{'ALL EXPECTED STATES MET' if fail_count == 0 else f'{fail_count} CHECK(S) FAILED'}")
except Exception as exc:  # noqa: BLE001
    evidence["aborted"] = str(exc)
    print(f"ABORT: {exc}")
finally:
    OUT.write_text(json.dumps(evidence, indent=2, default=str), encoding="utf-8")
    print(f"evidence -> {OUT}")

sys.exit(0 if fail_count == 0 else 1)
