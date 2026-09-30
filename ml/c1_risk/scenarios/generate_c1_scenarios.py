#!/usr/bin/env python
# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR-C1-RISK-SCENARIOS — deterministic scenario generator (§72)
# ─────────────────────────────────────────────────────────────────────────────
# Generates an INPUTS-ONLY scenario dataset for the locked C1 risk engine:
#
#   * "rule_coverage_grid" — exhaustive cartesian grid of risk-engine inputs
#     (object_type x is_night x multi_camera_confirmed x reliability x confidence)
#
#   * scripted scenario families (§72 list):
#     zone crossing / multiple crossings / repeated visit / camera degraded /
#     correlated events / long duration / short duration / normal civilian
#     activity / animal movement / vehicle movement / night intrusion /
#     input case normalization / clamp boundary
#
# The dataset contains NO model outputs and NO fabricated labels. Expected
# outputs are derived at benchmark time by an independent rule-arithmetic
# oracle (see ml/c1_risk/benchmarks/run_c1_benchmark.py).
#
# No randomness is used: the dataset is a pure function of the generator code
# and the live risk configuration snapshot written into the file.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ML_ROOT = Path(__file__).resolve().parents[2]          # C:\SIH\ml
BACKEND = ML_ROOT.parent / "ibvap-backend"             # C:\SIH\ibvap-backend
sys.path.insert(0, str(BACKEND))

from app.core.config import settings  # noqa: E402

OUT_PATH = Path(__file__).resolve().parent / "c1_scenarios_v1.json"

CONFIDENCE_GRID = [round(i / 100.0, 2) for i in range(0, 101)]  # 0.00 .. 1.00


def config_snapshot() -> dict:
    return {
        "RISK_RESTRICTED_NON_ANIMAL": settings.RISK_RESTRICTED_NON_ANIMAL,
        "RISK_RESTRICTED_ANIMAL": settings.RISK_RESTRICTED_ANIMAL,
        "RISK_NIGHT": settings.RISK_NIGHT,
        "RISK_MULTI_CAMERA": settings.RISK_MULTI_CAMERA,
        "RISK_HUMAN": settings.RISK_HUMAN,
        "RISK_VEHICLE": settings.RISK_VEHICLE,
        "RISK_CONFIDENCE_MULTIPLIER": settings.RISK_CONFIDENCE_MULTIPLIER,
        "RISK_LOW_RELIABILITY_PENALTY": settings.RISK_LOW_RELIABILITY_PENALTY,
        "RISK_SCORE_MIN": settings.RISK_SCORE_MIN,
        "RISK_SCORE_MAX": settings.RISK_SCORE_MAX,
        "SEVERITY_MEDIUM_THRESHOLD": settings.SEVERITY_MEDIUM_THRESHOLD,
        "SEVERITY_HIGH_THRESHOLD": settings.SEVERITY_HIGH_THRESHOLD,
        "SEVERITY_CRITICAL_THRESHOLD": settings.SEVERITY_CRITICAL_THRESHOLD,
    }


def event(
    object_type: str,
    *,
    zone_crossed: bool = True,
    is_night: bool = False,
    multi_camera_confirmed: bool = False,
    confidence: float,
    reliability: str,
    evidence: str | None = None,
) -> dict:
    return {
        "object_type": object_type,
        "zone_crossed": zone_crossed,
        "is_night": is_night,
        "multi_camera_confirmed": multi_camera_confirmed,
        "confidence": confidence,
        "reliability": reliability,
        "evidence": evidence,
    }


def build_grid() -> list[dict]:
    scenarios = []
    idx = 0
    for object_type in ("HUMAN", "VEHICLE", "ANIMAL"):
        for is_night in (False, True):
            for multi_camera_confirmed in (False, True):
                for reliability in ("HIGH", "MEDIUM", "LOW"):
                    for confidence in CONFIDENCE_GRID:
                        idx += 1
                        scenarios.append(
                            {
                                "scenario_id": f"C1-SCN-G{idx:05d}",
                                "family": "rule_coverage_grid",
                                "title": (
                                    f"{object_type} night={is_night} multicam={multi_camera_confirmed} "
                                    f"rel={reliability} conf={confidence:.2f}"
                                ),
                                "meta": {
                                    "object_type": object_type,
                                    "source": "exhaustive cartesian grid, confidence step 0.01",
                                },
                                "events": [
                                    event(
                                        object_type,
                                        is_night=is_night,
                                        multi_camera_confirmed=multi_camera_confirmed,
                                        confidence=confidence,
                                        reliability=reliability,
                                        evidence=None,  # exercises engine default evidence path
                                    )
                                ],
                            }
                        )
    return scenarios


def build_scripted() -> list[dict]:
    zones = "ZONE-C1-BENCH"
    scripted: list[dict] = []

    scripted.append({
        "scenario_id": "C1-SCN-S001", "family": "zone_crossing",
        "title": "Single human zone crossing (day, single camera)",
        "meta": {"expected_note": "baseline crossing; restricted-zone factor must appear at 25 pts"},
        "events": [event("HUMAN", confidence=0.80, reliability="HIGH",
                         evidence=f"Track TRK-C1-BENCH-0001 entered zone {zones}.")],
    })

    scripted.append({
        "scenario_id": "C1-SCN-S002", "family": "multiple_crossings",
        "title": "Same track crosses the restricted zone 3 times",
        "meta": {"crossing_count": 3,
                 "expected_note": "risk engine is per-event; identical vectors must yield identical outputs"},
        "events": [
            event("HUMAN", is_night=True, confidence=0.75, reliability="MEDIUM",
                  evidence=f"Track TRK-C1-BENCH-0002 entered zone {zones} (crossing 1)."),
            event("HUMAN", is_night=True, confidence=0.75, reliability="MEDIUM",
                  evidence=f"Track TRK-C1-BENCH-0002 entered zone {zones} (crossing 2)."),
            event("HUMAN", is_night=True, confidence=0.75, reliability="MEDIUM",
                  evidence=f"Track TRK-C1-BENCH-0002 entered zone {zones} (crossing 3)."),
        ],
    })

    scripted.append({
        "scenario_id": "C1-SCN-S003", "family": "repeated_visit",
        "title": "Same vehicle visits the zone twice with identical conditions",
        "meta": {"visit_count": 2, "expected_note": "stateless per-event scoring"},
        "events": [
            event("VEHICLE", confidence=0.85, reliability="HIGH",
                  evidence=f"Track TRK-C1-BENCH-0003 entered zone {zones} (visit 1)."),
            event("VEHICLE", confidence=0.85, reliability="HIGH",
                  evidence=f"Track TRK-C1-BENCH-0003 entered zone {zones} (visit 2)."),
        ],
    })

    scripted.append({
        "scenario_id": "C1-SCN-S004", "family": "camera_degraded",
        "title": "Degraded camera feed — uncertainty engine reports LOW reliability",
        "meta": {"camera_state": "DEGRADED",
                 "assumption": "C2 camera state maps to reliability labels at the provider boundary; benchmark consumes the reliability label",
                 "expected_note": "LOW_RELIABILITY factor (-15) must be present"},
        "events": [
            event("HUMAN", confidence=0.30, reliability="LOW",
                  evidence=f"Track TRK-C1-BENCH-0004 entered zone {zones} (degraded feed)."),
            event("VEHICLE", is_night=True, confidence=0.15, reliability="LOW",
                  evidence=f"Track TRK-C1-BENCH-0005 entered zone {zones} (degraded feed, night)."),
        ],
    })

    scripted.append({
        "scenario_id": "C1-SCN-S005", "family": "correlated_events",
        "title": "Same track confirmed by two cameras (multi-camera confirmation)",
        "meta": {"expected_note": "MULTI_CAMERA_CONFIRMATION factor (+15) must be present"},
        "events": [
            event("HUMAN", is_night=True, multi_camera_confirmed=True, confidence=0.90, reliability="HIGH",
                  evidence=f"Track TRK-C1-BENCH-0006 entered zone {zones} (cam A)."),
            event("HUMAN", is_night=True, multi_camera_confirmed=True, confidence=0.90, reliability="HIGH",
                  evidence=f"Track TRK-C1-BENCH-0006 entered zone {zones} (cam B, correlation confirmed)."),
        ],
    })

    scripted.append({
        "scenario_id": "C1-SCN-S006", "family": "long_duration",
        "title": "Long dwell event (900 s) inside restricted zone",
        "meta": {"duration_s": 900,
                 "expected_note": "duration is not a risk-engine input in the locked implementation; input vector identical to short_duration family"},
        "events": [event("HUMAN", confidence=0.70, reliability="HIGH",
                         evidence=f"Track TRK-C1-BENCH-0007 lingered in zone {zones} for 900 s.")],
    })

    scripted.append({
        "scenario_id": "C1-SCN-S007", "family": "short_duration",
        "title": "Short dwell event (5 s) inside restricted zone",
        "meta": {"duration_s": 5,
                 "expected_note": "same input vector as long_duration; outputs must match it exactly"},
        "events": [event("HUMAN", confidence=0.70, reliability="HIGH",
                         evidence=f"Track TRK-C1-BENCH-0008 crossed zone {zones} in 5 s.")],
    })

    scripted.append({
        "scenario_id": "C1-SCN-S008", "family": "normal_civilian_activity",
        "title": "Civilian traffic crossing during daylight with clear imagery",
        "meta": {"expected_note": "policy band: restricted-zone base keeps benign crossings <= MEDIUM"},
        "events": [
            event("HUMAN", confidence=0.95, reliability="HIGH",
                  evidence=f"Track TRK-C1-BENCH-0009 (civilian) entered zone {zones}."),
            event("VEHICLE", confidence=0.95, reliability="HIGH",
                  evidence=f"Track TRK-C1-BENCH-0010 (civilian vehicle) entered zone {zones}."),
        ],
    })

    scripted.append({
        "scenario_id": "C1-SCN-S009", "family": "animal_movement",
        "title": "Animal movement across the zone (day / night+multicam / low-confidence)",
        "meta": {"expected_note": "animal crossing counts 4 pts; day events must stay LOW"},
        "events": [
            event("ANIMAL", confidence=0.80, reliability="HIGH",
                  evidence=f"Track TRK-C1-BENCH-0011 (animal) entered zone {zones}."),
            event("ANIMAL", is_night=True, multi_camera_confirmed=True, confidence=0.90, reliability="HIGH",
                  evidence=f"Track TRK-C1-BENCH-0012 (animal) entered zone {zones} at night."),
            event("ANIMAL", confidence=0.20, reliability="LOW",
                  evidence=f"Track TRK-C1-BENCH-0013 (animal, uncertain) entered zone {zones}."),
        ],
    })

    scripted.append({
        "scenario_id": "C1-SCN-S010", "family": "vehicle_movement",
        "title": "Vehicle movement across the zone (day / night+multicam)",
        "meta": {"expected_note": "vehicle crossing counts 25 pts base + 10 pts object type"},
        "events": [
            event("VEHICLE", confidence=0.60, reliability="HIGH",
                  evidence=f"Track TRK-C1-BENCH-0014 (vehicle) entered zone {zones}."),
            event("VEHICLE", is_night=True, multi_camera_confirmed=True, confidence=0.75, reliability="HIGH",
                  evidence=f"Track TRK-C1-BENCH-0015 (vehicle) entered zone {zones} at night."),
        ],
    })

    scripted.append({
        "scenario_id": "C1-SCN-S011", "family": "night_intrusion",
        "title": "Human night intrusion, single camera, high-confidence detection",
        "meta": {"expected_note": "design intent: night human intrusion >= HIGH"},
        "events": [event("HUMAN", is_night=True, confidence=0.85, reliability="HIGH",
                         evidence=f"Track TRK-C1-BENCH-0016 entered zone {zones} at night.")],
    })

    scripted.append({
        "scenario_id": "C1-SCN-S012", "family": "input_case_normalization",
        "title": "Lowercase inputs must behave identically to uppercase",
        "meta": {"expected_note": "engine normalizes object_type and reliability via .upper()"},
        "events": [
            event("human", confidence=0.60, reliability="high",
                  evidence=f"Track TRK-C1-BENCH-0017 entered zone {zones}."),
            event("HUMAN", confidence=0.60, reliability="HIGH",
                  evidence=f"Track TRK-C1-BENCH-0017 entered zone {zones}."),
        ],
    })

    scripted.append({
        "scenario_id": "C1-SCN-S013", "family": "clamp_boundary",
        "title": "Clamp boundaries: negative raw (floor) and measured maximum raw",
        "meta": {"expected_note": "animal+LOW+conf0.0 -> raw -11 clamped to 0; max observable raw = 95 (human night multicam conf 1.0)"},
        "events": [
            event("ANIMAL", confidence=0.0, reliability="LOW",
                  evidence=f"Track TRK-C1-BENCH-0018 (animal) entered zone {zones}, zero confidence."),
            event("HUMAN", is_night=True, multi_camera_confirmed=True, confidence=1.0, reliability="HIGH",
                  evidence=f"Track TRK-C1-BENCH-0019 entered zone {zones}, worst case."),
        ],
    })

    return scripted


def main() -> None:
    grid = build_grid()
    scripted = build_scripted()
    scenarios = grid + scripted

    family_counts: dict[str, int] = {}
    event_counts: dict[str, int] = {}
    for s in scenarios:
        family_counts[s["family"]] = family_counts.get(s["family"], 0) + 1
        event_counts[s["family"]] = event_counts.get(s["family"], 0) + len(s["events"])

    payload = {
        "meta": {
            "name": "PRHAAR-C1-RISK-SCENARIOS",
            "version": "v1",
            "generated_by": "ml/c1_risk/scenarios/generate_c1_scenarios.py",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "inputs_only": True,
            "randomness": "none — exhaustive grid + fixed scripted families",
            "risk_config_snapshot_at_generation": config_snapshot(),
            "counts": {
                "scenarios": len(scenarios),
                "events": sum(len(s["events"]) for s in scenarios),
                "grid_scenarios": len(grid),
                "scripted_scenarios": len(scripted),
                "scenarios_per_family": family_counts,
                "events_per_family": event_counts,
            },
        },
        "scenarios": scenarios,
    }

    text = json.dumps(payload, indent=2, sort_keys=False, ensure_ascii=True)
    raw = text.encode("utf-8")
    OUT_PATH.write_bytes(raw)  # byte-exact write: printed digest == file digest
    digest = hashlib.sha256(raw).hexdigest()
    print(f"wrote {OUT_PATH}")
    print(f"scenarios={len(scenarios)} events={payload['meta']['counts']['events']}")
    print(f"sha256={digest}")


if __name__ == "__main__":
    main()
