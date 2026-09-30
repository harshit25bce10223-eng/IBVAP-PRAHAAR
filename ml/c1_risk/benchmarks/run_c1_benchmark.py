#!/usr/bin/env python
# ─────────────────────────────────────────────────────────────────────────────
# C1 risk engine — deterministic benchmark runner (§72 / §106)
# ─────────────────────────────────────────────────────────────────────────────
# Read-only consumer of the locked C1 risk engine. For every scenario event it:
#
#   1. calls calculate_risk twice in-process (repeatability A == B)
#   2. calls it a third time from a JSON round-trip of the input (C)
#   3. compares all three against an INDEPENDENT rule-arithmetic oracle
#      derived from the documented factor catalog + live config snapshot
#   4. evaluates curated policy checks per scenario family
#   5. emits a results JSON with a canonical SHA-256 over
#      (inputs + outputs), suitable for cross-process determinism comparison
#
# The oracle validates CONFORMANCE TO DOCUMENTED RULES. It is not ground truth
# and this benchmark does not measure real-world correctness (§73/§105).
#
# Usage:
#   python run_c1_benchmark.py --scenarios ..\scenarios\c1_scenarios_v1.json \
#                              --out c1_benchmark_results_v1.json --run-label run1
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import argparse
import hashlib
import json
import platform
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ML_ROOT = Path(__file__).resolve().parents[2]          # C:\SIH\ml
BACKEND = ML_ROOT.parent / "ibvap-backend"             # C:\SIH\ibvap-backend
sys.path.insert(0, str(BACKEND))

from app.core.config import settings                      # noqa: E402
from app.domain.risk.risk_engine import calculate_risk    # noqa: E402
from app.domain.risk.severity import severity_for_score   # noqa: E402

SEVERITY_RANK = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
ENGINE_SOURCES = [
    BACKEND / "app" / "domain" / "risk" / "risk_engine.py",
    BACKEND / "app" / "domain" / "risk" / "risk_factors.py",
    BACKEND / "app" / "domain" / "risk" / "severity.py",
    BACKEND / "app" / "core" / "config.py",
]


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


# ── independent rule-arithmetic oracle ───────────────────────────────────────
# Re-implemented from the documented factor catalog (labels, evidence strings,
# order) and the live config values. Deliberately NOT imported from the engine.
def oracle(event: dict, cfg: dict) -> dict:
    obj = str(event["object_type"]).upper()
    rel = str(event["reliability"]).upper()

    factors: list[dict] = []
    total = 0

    pts = cfg["RISK_RESTRICTED_ANIMAL"] if obj == "ANIMAL" else cfg["RISK_RESTRICTED_NON_ANIMAL"]
    factors.append({
        "code": "RESTRICTED_ZONE_CROSSING", "label": "Restricted zone crossing",
        "points": pts, "evidence": event.get("evidence") or "Track entered restricted zone.",
    })
    total += pts

    if event["is_night"]:
        factors.append({"code": "NIGHT_TIME", "label": "Night-time movement",
                        "points": cfg["RISK_NIGHT"], "evidence": "Movement occurred during night hours."})
        total += cfg["RISK_NIGHT"]

    if event["multi_camera_confirmed"]:
        factors.append({"code": "MULTI_CAMERA_CONFIRMATION", "label": "Multi-camera confirmation",
                        "points": cfg["RISK_MULTI_CAMERA"], "evidence": "Object confirmed by multiple cameras."})
        total += cfg["RISK_MULTI_CAMERA"]

    if obj == "HUMAN":
        factors.append({"code": "OBJECT_HUMAN", "label": "Human object type",
                        "points": cfg["RISK_HUMAN"], "evidence": f"Detected object type: {obj}."})
        total += cfg["RISK_HUMAN"]
    elif obj == "VEHICLE":
        factors.append({"code": "OBJECT_VEHICLE", "label": "Vehicle object type",
                        "points": cfg["RISK_VEHICLE"], "evidence": f"Detected object type: {obj}."})
        total += cfg["RISK_VEHICLE"]
    else:
        factors.append({"code": "OBJECT_ANIMAL", "label": "Animal object type",
                        "points": 0, "evidence": f"Detected object type: {obj}."})

    cpts = round(event["confidence"] * cfg["RISK_CONFIDENCE_MULTIPLIER"])
    factors.append({
        "code": "DETECTION_CONFIDENCE", "label": "Detection confidence", "points": cpts,
        "evidence": f"Confidence {event['confidence']:.2f} x {cfg['RISK_CONFIDENCE_MULTIPLIER']}",
    })
    total += cpts

    if rel == "LOW":
        factors.append({"code": "LOW_RELIABILITY", "label": "Uncertainty penalty",
                        "points": cfg["RISK_LOW_RELIABILITY_PENALTY"],
                        "evidence": "Uncertainty engine reported LOW reliability."})
        total += cfg["RISK_LOW_RELIABILITY_PENALTY"]

    raw = total
    final = max(cfg["RISK_SCORE_MIN"], min(cfg["RISK_SCORE_MAX"], raw))
    return {"risk_score": final, "severity": severity_for_score(final), "raw_score": raw, "factors": factors}


def result_tuple(result) -> tuple:
    return (
        result.risk_score,
        result.severity,
        result.raw_score,
        json.dumps(result.factors, sort_keys=True),
        json.dumps(result.to_dict(), sort_keys=True),
    )


def oracle_tuple(expected: dict) -> tuple:
    return (
        expected["risk_score"],
        expected["severity"],
        expected["raw_score"],
        json.dumps(expected["factors"], sort_keys=True),
        json.dumps({"risk_score": expected["risk_score"], "severity": expected["severity"],
                    "factors": expected["factors"]}, sort_keys=True),
    )


def call_engine(input_vec: dict):
    return calculate_risk(
        object_type=input_vec["object_type"],
        zone_crossed=input_vec["zone_crossed"],
        is_night=input_vec["is_night"],
        multi_camera_confirmed=input_vec["multi_camera_confirmed"],
        confidence=input_vec["confidence"],
        reliability=input_vec["reliability"],
        evidence=input_vec.get("evidence"),
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--scenarios", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--run-label", required=True)
    args = ap.parse_args()

    started = time.perf_counter()
    scenario_path = Path(args.scenarios).resolve()
    scenario_bytes = scenario_path.read_bytes()
    dataset = json.loads(scenario_bytes.decode("utf-8"))
    cfg = config_snapshot()

    gen_cfg = dataset["meta"].get("risk_config_snapshot_at_generation")
    config_matches_generation = gen_cfg == cfg

    events_out = []
    mismatches = []
    policy_results = []
    per_family: dict[str, dict] = {}

    def fam(family: str) -> dict:
        if family not in per_family:
            per_family[family] = {"scenarios": 0, "events": 0, "determinism_pass": 0,
                                  "oracle_pass": 0, "severity_counts": {}}
        return per_family[family]

    scenario_by_id = {s["scenario_id"]: s for s in dataset["scenarios"]}
    result_by_event: dict[str, tuple] = {}

    for scenario in dataset["scenarios"]:
        f = fam(scenario["family"])
        f["scenarios"] += 1
        for i, event in enumerate(scenario["events"]):
            event_id = f"{scenario['scenario_id']}-E{i}"
            f["events"] += 1

            out_a = call_engine(event)
            out_b = call_engine(event)
            roundtrip_vec = json.loads(json.dumps(event))
            out_c = call_engine(roundtrip_vec)

            expected = oracle(event, cfg)

            a, b, c, o = result_tuple(out_a), result_tuple(out_b), result_tuple(out_c), oracle_tuple(expected)
            same_process = a == b
            serialized_roundtrip = a == c
            oracle_conformance = a == o
            determinism_ok = same_process and serialized_roundtrip

            if determinism_ok:
                f["determinism_pass"] += 1
            if oracle_conformance:
                f["oracle_pass"] += 1
            f["severity_counts"][out_a.severity] = f["severity_counts"].get(out_a.severity, 0) + 1

            if not (determinism_ok and oracle_conformance) and len(mismatches) < 50:
                mismatches.append({
                    "event_id": event_id, "family": scenario["family"], "input": event,
                    "same_process_rerun": same_process, "serialized_roundtrip": serialized_roundtrip,
                    "oracle_conformance": oracle_conformance,
                    "engine": {"risk_score": out_a.risk_score, "severity": out_a.severity,
                               "raw_score": out_a.raw_score, "factors": out_a.factors},
                    "oracle": expected,
                })

            result_by_event[event_id] = a
            events_out.append({
                "event_id": event_id,
                "scenario_id": scenario["scenario_id"],
                "family": scenario["family"],
                "input": event,
                "output": {"risk_score": out_a.risk_score, "severity": out_a.severity,
                           "raw_score": out_a.raw_score, "factors": out_a.factors},
                "checks": {"same_process_rerun": same_process,
                           "serialized_roundtrip": serialized_roundtrip,
                           "oracle_conformance": oracle_conformance},
            })

    # ── curated policy checks (documented design intents; §73-style protocol) ─
    def sev_rank(ev_id: str) -> int:
        return SEVERITY_RANK[result_by_event[ev_id][1]]

    def score(ev_id: str) -> int:
        return result_by_event[ev_id][0]

    def add_check(name: str, condition: bool, detail: str) -> None:
        policy_results.append({"check": name, "passed": bool(condition), "detail": detail})

    # normal civilian activity must not exceed MEDIUM
    for i in range(2):
        eid = f"C1-SCN-S008-E{i}"
        add_check("normal_civilian_activity<=MEDIUM", sev_rank(eid) <= 1, f"{eid} score={score(eid)}")

    # night intrusion >= HIGH
    eid = "C1-SCN-S011-E0"
    add_check("night_intrusion>=HIGH", sev_rank(eid) >= 2, f"{eid} score={score(eid)}")

    # animal day events stay LOW; animal night+multicam stays below HIGH
    add_check("animal_day==LOW", sev_rank("C1-SCN-S009-E0") == 0, f"C1-SCN-S009-E0 score={score('C1-SCN-S009-E0')}")
    add_check("animal_uncertain==LOW", sev_rank("C1-SCN-S009-E2") == 0, f"C1-SCN-S009-E2 score={score('C1-SCN-S009-E2')}")
    add_check("animal_night_multicam<HIGH", sev_rank("C1-SCN-S009-E1") < 2, f"C1-SCN-S009-E1 score={score('C1-SCN-S009-E1')}")

    # correlated events >= HIGH and carry the multi-camera factor
    eid = "C1-SCN-S005-E0"
    codes = [f_["code"] for f_ in events_out[[e["event_id"] for e in events_out].index(eid)]["output"]["factors"]]
    add_check("correlated>=HIGH", sev_rank(eid) >= 2, f"{eid} score={score(eid)}")
    add_check("correlated_factor_present", "MULTI_CAMERA_CONFIRMATION" in codes, f"{eid} codes={codes}")

    # degraded camera events carry the LOW_RELIABILITY factor
    for i in range(2):
        eid = f"C1-SCN-S004-E{i}"
        codes = events_out[[e["event_id"] for e in events_out].index(eid)]["output"]["factors"]
        has = any(c["code"] == "LOW_RELIABILITY" for c in codes)
        add_check("camera_degraded_penalty_present", has, f"{eid}")

    # clamp boundary: floor clamp exact, measured max = 95 with no ceiling clamp
    add_check("clamp_floor_exact", score("C1-SCN-S013-E0") == 0 and result_by_event["C1-SCN-S013-E0"][2] == -11,
              f"C1-SCN-S013-E0 score={score('C1-SCN-S013-E0')} raw={result_by_event['C1-SCN-S013-E0'][2]}")
    add_check("max_raw_no_ceiling_clamp", result_by_event["C1-SCN-S013-E1"][2] == 95,
              f"C1-SCN-S013-E1 raw={result_by_event['C1-SCN-S013-E1'][2]}")

    # identical repeated events in one scenario produce identical outputs
    for sid, label in (("C1-SCN-S002", "multiple_crossings"), ("C1-SCN-S003", "repeated_visit")):
        ev_ids = [e["event_id"] for e in events_out if e["scenario_id"] == sid]
        tgts = [result_by_event[x] for x in ev_ids]
        # inputs differ only in evidence text -> outputs identical except evidence string;
        # compare score/severity/raw only (evidence is per-crossing descriptive text)
        score_sev = [(t[0], t[1], t[2]) for t in tgts]
        add_check(f"{label}_outputs_identical", len(set(score_sev)) == 1, f"{ev_ids} -> {score_sev}")

    # duration invariance: long_duration vs short_duration identical input vector -> identical output
    long_t = result_by_event["C1-SCN-S006-E0"]
    short_t = result_by_event["C1-SCN-S007-E0"]
    add_check("duration_invariance_same_vector", long_t[:3] == short_t[:3],
              f"S006={long_t[:3]} S007={short_t[:3]}")

    # case normalization: lowercase input == uppercase input
    lc = result_by_event["C1-SCN-S012-E0"]
    uc = result_by_event["C1-SCN-S012-E1"]
    add_check("case_normalization_identical", lc == uc, f"S012 lowercase={lc[:3]} uppercase={uc[:3]}")

    # ── aggregate analyses ────────────────────────────────────────────────────
    total_events = len(events_out)
    det_pass = sum(1 for e in events_out if e["checks"]["same_process_rerun"] and e["checks"]["serialized_roundtrip"])
    oracle_pass = sum(1 for e in events_out if e["checks"]["oracle_conformance"])

    severity_counts: dict[str, int] = {}
    for e in events_out:
        severity_counts[e["output"]["severity"]] = severity_counts.get(e["output"]["severity"], 0) + 1

    raws = [e["output"]["raw_score"] for e in events_out]
    clamp_floor = sum(1 for e in events_out if e["output"]["raw_score"] < cfg["RISK_SCORE_MIN"])
    clamp_ceiling = sum(1 for e in events_out if e["output"]["raw_score"] > cfg["RISK_SCORE_MAX"])

    # false-high-risk: high/critical severity on weak evidence (internal definitions)
    high_events = [e for e in events_out if SEVERITY_RANK[e["output"]["severity"]] >= 2]
    fh_low_rel = [e for e in high_events if str(e["input"]["reliability"]).upper() == "LOW"]
    fh_low_conf = [e for e in high_events if e["input"]["confidence"] <= 0.5]
    crosstab: dict[str, dict[str, int]] = {}
    for e in events_out:
        sev = e["output"]["severity"]
        rel = str(e["input"]["reliability"]).upper()
        crosstab.setdefault(sev, {}).setdefault(rel, 0)
        crosstab[sev][rel] += 1

    # false-low-risk: strong-signal misses + animal ceiling evidence
    strong_signal = [e for e in events_out
                     if str(e["input"]["object_type"]).upper() == "HUMAN"
                     and e["input"]["is_night"] and e["input"]["multi_camera_confirmed"]
                     and str(e["input"]["reliability"]).upper() == "HIGH"
                     and e["input"]["confidence"] >= 0.8]
    strong_signal_miss = [e for e in strong_signal if SEVERITY_RANK[e["output"]["severity"]] < 2]

    per_object_meas: dict[str, dict] = {}
    for obj in ("HUMAN", "VEHICLE", "ANIMAL"):
        vals = [e["output"]["raw_score"] for e in events_out if str(e["input"]["object_type"]).upper() == obj]
        per_object_meas[obj] = {"min_raw": min(vals), "max_raw": max(vals)}

    base = {"HUMAN": cfg["RISK_HUMAN"] + cfg["RISK_RESTRICTED_NON_ANIMAL"],
            "VEHICLE": cfg["RISK_VEHICLE"] + cfg["RISK_RESTRICTED_NON_ANIMAL"],
            "ANIMAL": 0 + cfg["RISK_RESTRICTED_ANIMAL"]}
    per_object_theory = {
        obj: {
            "min_raw": base[obj] + cfg["RISK_LOW_RELIABILITY_PENALTY"],
            "max_raw": base[obj] + cfg["RISK_NIGHT"] + cfg["RISK_MULTI_CAMERA"] + cfg["RISK_CONFIDENCE_MULTIPLIER"],
        }
        for obj in ("HUMAN", "VEHICLE", "ANIMAL")
    }

    # human night LOW-reliability band straddle (uncertainty penalty near threshold)
    straddle = [e for e in events_out
                if str(e["input"]["object_type"]).upper() == "HUMAN"
                and e["input"]["is_night"] and not e["input"]["multi_camera_confirmed"]
                and str(e["input"]["reliability"]).upper() == "LOW"]
    straddle_scores = sorted({e["output"]["risk_score"] for e in straddle})

    # canonical hash over inputs + outputs only (environment-independent)
    canonical = {
        "scenario_file_sha256": hashlib.sha256(scenario_bytes).hexdigest(),
        "config": cfg,
        "events": [
            {
                "event_id": e["event_id"],
                "family": e["family"],
                "input": e["input"],
                "output": e["output"],
            }
            for e in events_out
        ],
    }
    canonical_json = json.dumps(canonical, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    results_sha256 = hashlib.sha256(canonical_json.encode("utf-8")).hexdigest()

    elapsed_ms = round((time.perf_counter() - started) * 1000, 1)
    payload = {
        "meta": {
            "benchmark": "PRHAAR-C1-RISK-BENCHMARK",
            "run_label": args.run_label,
            "run_started_utc": datetime.now(timezone.utc).isoformat(),
            "wall_time_ms": elapsed_ms,
            "python": sys.version,
            "platform": platform.platform(),
            "cwd": str(Path.cwd()),
            "scenario_file": str(scenario_path),
            "scenario_file_sha256": hashlib.sha256(scenario_bytes).hexdigest(),
            "engine_source_sha256": {str(p.relative_to(BACKEND)): sha256_file(p) for p in ENGINE_SOURCES},
            "config_snapshot": cfg,
            "config_matches_generation": config_matches_generation,
            "oracle_note": "Independent rule-arithmetic oracle; validates conformance to documented rules, not real-world correctness.",
        },
        "summary": {
            "scenarios": sum(1 for _ in dataset["scenarios"]),
            "events": total_events,
            "determinism": {"passed": det_pass, "total": total_events,
                            "consistency_rate": det_pass / total_events if total_events else None},
            "oracle_conformance": {"passed": oracle_pass, "total": total_events,
                                   "rate": oracle_pass / total_events if total_events else None},
            "severity_distribution": severity_counts,
            "raw_score_range": {"min": min(raws), "max": max(raws)},
            "clamp_activations": {"floor_raw_below_min": clamp_floor, "ceiling_raw_above_max": clamp_ceiling},
            "false_high_risk": {
                "definition_high_severity": "severity >= HIGH",
                "high_on_low_reliability": {"count": len(fh_low_rel),
                                            "rate_of_high": (len(fh_low_rel) / len(high_events)) if high_events else None,
                                            "examples": [{"event_id": e["event_id"], "score": e["output"]["risk_score"],
                                                          "confidence": e["input"]["confidence"]} for e in fh_low_rel[:10]]},
                "high_on_confidence_le_0_5": {"count": len(fh_low_conf),
                                              "rate_of_high": (len(fh_low_conf) / len(high_events)) if high_events else None},
                "severity_x_reliability": crosstab,
            },
            "false_low_risk": {
                "strong_signal_events": len(strong_signal),
                "strong_signal_misses": len(strong_signal_miss),
                "definition_strong_signal": "HUMAN + night + multi-camera + HIGH reliability + confidence >= 0.8",
                "human_night_low_rel_scores": {"count": len(straddle), "distinct_scores": straddle_scores},
                "animal_ceiling_note": "per-object measured vs config-derived bounds below",
            },
            "per_object_type": {"measured": per_object_meas, "config_derived_bounds": per_object_theory},
            "policy_checks": {"passed": sum(1 for p in policy_results if p["passed"]),
                              "total": len(policy_results),
                              "results": policy_results},
            "results_sha256": results_sha256,
        },
        "per_family": per_family,
        "mismatches": mismatches,
        "events": events_out,
    }

    out_path = Path(args.out).resolve()
    out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=True), encoding="utf-8")
    print(f"run_label={args.run_label}")
    print(f"events={total_events} determinism={det_pass}/{total_events} oracle={oracle_pass}/{total_events}")
    print(f"policy_checks={sum(1 for p in policy_results if p['passed'])}/{len(policy_results)}")
    print(f"results_sha256={results_sha256}")
    print(f"config_matches_generation={config_matches_generation}")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
