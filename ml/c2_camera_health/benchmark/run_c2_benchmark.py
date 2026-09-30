# -*- coding: utf-8 -*-
# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — C2 Classical CV Camera-Health Benchmark Harness (spec §67)
#
# Evaluates the EXISTING classical CV approach:
#   A. Component level  — ImageQualityAnalyzer / FreezeDetector / ViewpointDetector
#   B. End-to-end       — real CameraHealthAnalyzer.analyze_observation wiring
#                         (measures the pipeline exactly as production runs it)
#
# No locked component is modified (spec §125). OpenCV RNG is pinned per sample
# for RANSAC reproducibility (documented; production does not do this).
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import hashlib
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
BACKEND = Path(r"C:\SIH\ibvap-backend")
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(BACKEND))

import cv2  # noqa: E402

from gen_c2_corpus import (  # noqa: E402
    BASE_SEED, FRAME_H, FRAME_W, MANIFEST_PATH, SEQUENCE_LEN,
    build_samples, materialize_frames, sha256_file,
)

from app.domain.camera_health.analyzer import CameraHealthAnalyzer  # noqa: E402
from app.domain.camera_health.freeze import FreezeDetector  # noqa: E402
from app.domain.camera_health.image_quality import ImageQualityAnalyzer  # noqa: E402
from app.domain.camera_health.state_engine import (  # noqa: E402
    ImageQualityMetrics, NetworkMetrics, StreamHealthMetrics, ViewpointMetrics,
)
from app.domain.camera_health.viewpoint import ViewpointDetector  # noqa: E402

RUN_TAG = sys.argv[1] if len(sys.argv) > 1 else "run1"
OUT_PATH = HERE / f"c2_benchmark_results_{RUN_TAG}.json"


# ─────────────────────────────────────────────────────────────────────────────
# Harness-side config mirror (CameraHealthConfig model defaults; no DB)
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class BenchConfig:
    camera_id: str = "CAM-BENCH"
    expected_fps: float = 25.0
    stale_after_seconds: int = 30
    offline_after_seconds: int = 120
    freeze_window_seconds: int = 10
    viewpoint_shift_threshold: float = 0.3
    min_feature_matches: int = 10
    min_ransac_inlier_ratio: float = 0.5
    sharpness_degraded_threshold: float | None = None   # engine fallback 0.5
    brightness_low_threshold: float | None = None       # engine fallback 0.1
    brightness_high_threshold: float | None = None      # engine fallback 0.9


CONFIG = BenchConfig()

ENGINE_FILES = [
    "app/domain/camera_health/analyzer.py",
    "app/domain/camera_health/state_engine.py",
    "app/domain/camera_health/image_quality.py",
    "app/domain/camera_health/freeze.py",
    "app/domain/camera_health/viewpoint.py",
    "app/domain/camera_health/baseline_engine.py",
    "app/domain/camera_health/trend_engine.py",
    "app/core/config.py",
]

BROKEN_VISUAL_CLASSES = {
    "FROZEN", "BLURRED", "OBSTRUCTED", "UNDEREXPOSED",
    "OVEREXPOSED", "SEVERE_COMPRESSION", "COVERAGE_COMPROMISED",
}


def r6(x):
    if x is None:
        return None
    try:
        return round(float(x), 6)
    except (TypeError, ValueError):
        return None


# ─────────────────────────────────────────────────────────────────────────────
# Component-level evaluations
# ─────────────────────────────────────────────────────────────────────────────
def eval_image_quality(frames: list[np.ndarray]) -> dict:
    a = ImageQualityAnalyzer()
    f = frames[-1]
    res = a.analyze(f)
    return dict(
        sharpness=r6(res.sharpness), brightness=r6(res.brightness),
        exposure=res.exposure, contrast=r6(res.contrast), noise=r6(res.noise),
        illumination_regime=res.illumination_regime,
    )


def eval_freeze(frames: list[np.ndarray], seed: int, base_ts: datetime) -> dict:
    det = FreezeDetector()
    last = None
    sims = []
    consec_max = 0
    for i, f in enumerate(frames):
        ts = base_ts + timedelta(seconds=float(i))
        res = det.analyze(f, ts)
        last = res
        if res.similarity_score:
            sims.append(r6(res.similarity_score))
    return dict(
        frozen_final=bool(last.frozen) if last else None,
        similarity_max=max(sims) if sims else None,
        similarity_mean=r6(float(np.mean(sims))) if sims else None,
        consecutive_similar_max=det._consecutive_similar,
        reason=last.reason if last else None,
    )


def eval_viewpoint(frames: list[np.ndarray], seed: int) -> dict:
    det = ViewpointDetector()
    cv2.setRNGSeed(int(seed))  # pin OpenCV global RNG for RANSAC reproducibility
    ref_ok = det.set_reference(frames[0])
    results = []
    for i in range(1, len(frames)):
        cv2.setRNGSeed(int(seed) + i)
        results.append(det.analyze(frames[i]))
    last = results[-1] if results else None
    first_detected_idx = next((i + 1 for i, r in enumerate(results) if r.shift_detected), None)
    return dict(
        reference_set=bool(ref_ok),
        shift_detected_final=bool(last.shift_detected) if last else None,
        first_detected_frame_index=first_detected_idx,
        shift_score=r6(last.shift_score) if last else None,
        confidence=r6(last.confidence) if last else None,
        inlier_ratio=r6(last.inlier_ratio) if last else None,
        translation=[r6(v) for v in last.translation] if last and last.translation else None,
        reason=last.reason if last else None,
    )


# ─────────────────────────────────────────────────────────────────────────────
# End-to-end evaluation through the real orchestrator
# ─────────────────────────────────────────────────────────────────────────────
def run_end_to_end(sample, frames: list[np.ndarray], base_ts: datetime) -> dict:
    analyzer = CameraHealthAnalyzer()
    t = sample.telemetry

    def metrics(fresh_source_ts: datetime):
        net = NetworkMetrics(
            latency_ms=t.get("latency_ms"),
            latency_variance_ms=t.get("latency_variance_ms"),
            packet_loss_percent=t.get("packet_loss_percent"),
            heartbeat_age_sec=t.get("heartbeat_age_sec"),
        )
        return net

    vp_injected = None
    if sample.viewpoint_injected:
        vp_injected = ViewpointMetrics(
            shift_score=sample.viewpoint_injected.get("shift_score"),
            shift_confidence=sample.viewpoint_injected.get("shift_confidence"),
            inlier_ratio=sample.viewpoint_injected.get("inlier_ratio"),
        )

    result = None
    exc_info = None
    try:
        if sample.n_frames == 0:
            source_ts = base_ts - timedelta(seconds=float(t.get("source_age_sec", 1.0)))
            stream = StreamHealthMetrics(
                connected=bool(t.get("connected", True)),
                observed_fps=t.get("observed_fps"),
                frame_drop_rate=t.get("frame_drop_rate", 0.0),
            )
            result = analyzer.analyze_observation(
                camera_id=sample.sample_id, config=CONFIG,
                source_timestamp=source_ts, received_at=base_ts,
                stream=stream, network=metrics(base_ts),
                viewpoint=vp_injected, frame=None,
            )
        else:
            for i, f in enumerate(frames):
                source_ts = base_ts + timedelta(seconds=float(i)) - timedelta(seconds=float(t.get("source_age_sec", 1.0)))
                stream = StreamHealthMetrics(
                    connected=bool(t.get("connected", True)),
                    observed_fps=t.get("observed_fps"),
                    frame_drop_rate=t.get("frame_drop_rate", 0.0),
                )
                result = analyzer.analyze_observation(
                    camera_id=sample.sample_id, config=CONFIG,
                    source_timestamp=source_ts, received_at=base_ts + timedelta(seconds=float(i)),
                    stream=stream, network=metrics(source_ts),
                    viewpoint=vp_injected, frame=f,
                )
    except Exception as exc:
        # Locked-code defects are recorded as outcomes, not hidden (§125:
        # harness adapts, locked code untouched). Known crash sites measured
        # here: analyzer.py:264 KeyError('reason') on nominal paths;
        # analyzer.py:320 AttributeError on image-degraded paths.
        exc_info = f"{type(exc).__name__}: {exc}"

    if exc_info is not None:
        return dict(
            overall_status="ENGINE_EXCEPTION", exception=exc_info,
            stream_state=None, image_status=None, network_status=None,
            viewpoint_status=None, reliability=None, status_reason=None,
            impact_level=None, maintenance_recommended=None, n_issues=None,
            shift_detected_field=None, ctx_viewpoint_shift_detected=None,
            ctx_fence_confidence_override=None, ctx_geometry_confidence=None,
            ctx_reliability=None,
        )

    ctx = analyzer.get_health_context_for_component1(sample.sample_id)
    return dict(
        overall_status=result.overall_status.value,
        stream_state=result.stream_state,
        image_status=result.image_status,
        network_status=result.network_status,
        viewpoint_status=result.viewpoint_status,
        reliability=result.reliability,
        status_reason=result.status_reason,
        impact_level=result.impact_level,
        maintenance_recommended=bool(result.maintenance_recommended),
        n_issues=len((result.issues_json or {}).get("issues", [])),
        shift_detected_field=bool(result.shift_detected),
        ctx_viewpoint_shift_detected=bool(ctx["viewpoint_shift_detected"]) if ctx else None,
        ctx_fence_confidence_override=ctx["fence_confidence_override"] if ctx else None,
        ctx_geometry_confidence=ctx["geometry_confidence"] if ctx else None,
        ctx_reliability=ctx["reliability"] if ctx else None,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Freeze noise-sensitivity diagnostic (quiet scene, ONLINE content, σ sweep)
# ─────────────────────────────────────────────────────────────────────────────
def freeze_noise_sweep() -> list[dict]:
    from gen_c2_corpus import add_motion_blob, add_sensor_noise, make_base_scene
    rows = []
    for sigma in (1.5, 2.0, 3.0, 4.0, 6.0):
        for motion in (False, True):
            frozen_count = 0
            n_seq = 8
            for k in range(n_seq):
                rng = np.random.default_rng(BASE_SEED + 90000 + int(sigma * 10) + (1000 if motion else 0) + k)
                base = make_base_scene(rng)
                det = FreezeDetector()
                last = None
                for i in range(SEQUENCE_LEN):
                    f = add_motion_blob(base, rng, x_pos=(i * 0.06) % 1.0) if motion else base
                    f = add_sensor_noise(f, rng, sigma)
                    last = det.analyze(f, datetime.now() + timedelta(seconds=i))
                frozen_count += int(bool(last.frozen))
            rows.append(dict(noise_sigma=sigma, motion=motion, n_sequences=n_seq,
                             frozen_final_count=frozen_count,
                             false_freeze_rate=round(frozen_count / n_seq, 4)))
    return rows


# ─────────────────────────────────────────────────────────────────────────────
# Aggregation
# ─────────────────────────────────────────────────────────────────────────────
def aggregate(records: list[dict]) -> dict:
    classes = sorted({r["cls"] for r in records})
    states = sorted({r["engine"]["overall_status"] for r in records})

    confusion = {c: {s: 0 for s in states} for c in classes}
    for r in records:
        confusion[r["cls"]][r["engine"]["overall_status"]] += 1

    per_class = {}
    for c in classes:
        rows = [r for r in records if r["cls"] == c]
        n = len(rows)
        expected = rows[0]["expected_state"]
        correct = sum(1 for r in rows if r["engine"]["overall_status"] == expected)
        online = sum(1 for r in rows if r["engine"]["overall_status"] == "ONLINE")
        per_class[c] = dict(
            n=n, expected_state=expected,
            recall_vs_expected=round(correct / n, 4),
            online_rate=round(online / n, 4),
            predicted_distribution=confusion[c],
        )

    # per-state precision/recall/F1 vs expected labels
    per_state = {}
    for s in states:
        tp = sum(1 for r in records if r["engine"]["overall_status"] == s and r["expected_state"] == s)
        fp = sum(1 for r in records if r["engine"]["overall_status"] == s and r["expected_state"] != s)
        fn = sum(1 for r in records if r["engine"]["overall_status"] != s and r["expected_state"] == s)
        prec = tp / (tp + fp) if (tp + fp) else 0.0
        rec = tp / (tp + fn) if (tp + fn) else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) else 0.0
        per_state[s] = dict(precision=round(prec, 4), recall=round(rec, 4), f1=round(f1, 4),
                            support=sum(1 for r in records if r["expected_state"] == s))

    macro_f1 = round(float(np.mean([v["f1"] for v in per_state.values()])), 4)

    broken = [r for r in records if r["cls"] in BROKEN_VISUAL_CLASSES]
    strict_fo = sum(1 for r in broken if r["engine"]["overall_status"] == "ONLINE")
    broad = [r for r in records if r["cls"] in BROKEN_VISUAL_CLASSES
             or r["cls"] in ("DEGRADED", "VIEWPOINT_CHANGED", "STALE_FEED", "STREAM_DROP_FROZEN")]
    broad_fo = sum(1 for r in broad if r["engine"]["overall_status"] == "ONLINE")

    false_online = dict(
        strict_classes=sorted(BROKEN_VISUAL_CLASSES),
        strict_false_online=f"{strict_fo}/{len(broken)}",
        strict_false_online_rate=round(strict_fo / len(broken), 4) if broken else None,
        broad_classes=sorted({r["cls"] for r in broad}),
        broad_false_online=f"{broad_fo}/{len(broad)}",
        broad_false_online_rate=round(broad_fo / len(broad), 4) if broad else None,
        per_class_online_rate={c: per_class[c]["online_rate"] for c in classes},
    )

    return dict(confusion=confusion, per_class=per_class, per_state=per_state,
                macro_f1=macro_f1, false_online=false_online)


def component_tables(records: list[dict]) -> dict:
    classes = sorted({r["cls"] for r in records})
    iq = {}
    fr = {}
    vp = []
    for c in classes:
        rows = [r for r in records if r["cls"] == c and r.get("iq")]
        if rows:
            keys = ("sharpness", "brightness", "contrast", "noise")
            iq[c] = {k: dict(min=r6(min(x["iq"][k] for x in rows if x["iq"][k] is not None)),
                             mean=r6(float(np.mean([x["iq"][k] for x in rows if x["iq"][k] is not None]))),
                             max=r6(max(x["iq"][k] for x in rows if x["iq"][k] is not None)))
                     for k in keys}
            iq[c]["exposure"] = {e: sum(1 for x in rows if x["iq"]["exposure"] == e) for e in
                                 ("NORMAL", "UNDEREXPOSED", "OVEREXPOSED", "UNKNOWN")}
            iq[c]["regime"] = {e: sum(1 for x in rows if x["iq"]["illumination_regime"] == e)
                               for e in ("DAY", "LOW_LIGHT", "NIGHT", "IR", "UNKNOWN")}
            iq[c]["sharpness_below_0.5"] = sum(1 for x in rows
                                               if x["iq"]["sharpness"] is not None and x["iq"]["sharpness"] < 0.5)
            iq[c]["brightness_below_0.1"] = sum(1 for x in rows
                                                if x["iq"]["brightness"] is not None and x["iq"]["brightness"] < 0.1)
            iq[c]["brightness_above_0.9"] = sum(1 for x in rows
                                                if x["iq"]["brightness"] is not None and x["iq"]["brightness"] > 0.9)
        rows_f = [r for r in records if r["cls"] == c and r.get("freeze")]
        if rows_f:
            fr[c] = dict(
                frozen_final=sum(1 for x in rows_f if x["freeze"]["frozen_final"]),
                n=len(rows_f),
                sim_mean_avg=r6(float(np.mean([x["freeze"]["similarity_mean"] or 0 for x in rows_f]))),
            )
    for r in records:
        if r.get("viewpoint"):
            vp.append(dict(sample_id=r["sample_id"], cls=r["cls"], subvariant=r["subvariant"],
                           **r["viewpoint"]))
    return dict(image_quality=iq, freeze=fr, viewpoint=vp)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main():
    t0 = time.time()
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    samples = build_samples()
    for s, row in zip(samples, manifest["samples"]):
        s.telemetry = row["telemetry"]

    module_hashes = {f: sha256_file(BACKEND / f) for f in ENGINE_FILES}
    # Naive wall clock that the locked engines can interpret as UTC:
    # - trend_engine compares sample timestamps against naive datetime.now()
    #   (it is not tz-aware), so we must feed naive timestamps or it crashes.
    # - the state engine normalizes naive source timestamps by attaching UTC,
    #   then compares against datetime.now(timezone.utc); on this IST host
    #   (UTC+5:30) naive datetime.now() is LOCAL wall time, which the engine
    #   would misread as UTC and produce negative frame ages (STALE never
    #   triggers). datetime.now(timezone.utc).replace(tzinfo=None) yields the
    #   naive representation of the current UTC wall clock, which the engine
    #   then interprets correctly (documented locked-code limitation, §125:
    #   harness adapts, locked code untouched).
    base_ts = datetime.now(timezone.utc).replace(tzinfo=None)

    records = []
    for s in samples:
        frames = materialize_frames(s)
        rec = dict(
            sample_id=s.sample_id, cls=s.cls, subvariant=s.subvariant,
            expected_state=s.expected_state, seed=s.seed,
            n_frames=len(frames),
        )
        if frames:
            rec["iq"] = eval_image_quality(frames)
            rec["freeze"] = eval_freeze(frames, s.seed, base_ts)
            if s.cls in ("VIEWPOINT_CHANGED", "ONLINE"):
                rec["viewpoint"] = eval_viewpoint(frames, s.seed)
        rec["engine"] = run_end_to_end(s, frames, base_ts)
        records.append(rec)

    sweep = freeze_noise_sweep()
    aggregates = aggregate(records)
    comp = component_tables(records)

    # Canonical determinism set: exclude status_reason (embeds wall-clock-derived
    # seconds, e.g. "No fresh frames for 45s") — keep it in the full output only.
    canonical_records = [
        {**r, "engine": {k: v for k, v in r["engine"].items() if k != "status_reason"}}
        for r in records
    ]
    canonical = dict(
        corpus_manifest_sha256=manifest["manifest_sha256"],
        config={k: v for k, v in CONFIG.__dict__.items()},
        module_hashes=module_hashes,
        cv2_version=cv2.__version__,
        numpy_version=np.__version__,
        records=canonical_records,
        freeze_noise_sweep=sweep,
    )
    text = json.dumps(canonical, indent=2, sort_keys=True, default=str)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()

    out = dict(
        benchmark="PRHAAR-C2-CAMERA-HEALTH-CLASSICAL-BENCH",
        version="v1",
        run_tag=RUN_TAG,
        run_utc=base_ts.isoformat(),
        wall_seconds=round(time.time() - t0, 3),
        spec_compliance=dict(
            s67="classical CV benchmark performed first; no neural camera-health model trained",
            s68_classes="ten benchmark classes + documented supplementary state rows",
            s125="no locked component modified; harness + corpus generator only",
            cv2_rng="pinned per sample via cv2.setRNGSeed for RANSAC reproducibility",
        ),
        n_samples=len(records),
        canonical_results_sha256=digest,
        aggregates=aggregates,
        component_tables=comp,
        canonical=canonical,
    )
    raw = json.dumps(out, indent=2, sort_keys=True, default=str).encode("utf-8")
    OUT_PATH.write_bytes(raw)

    agg = aggregates
    print(f"samples={len(records)} wall={out['wall_seconds']}s")
    print(f"results_sha256={digest}")
    print(f"macro_f1={agg['macro_f1']}")
    print(f"false_online strict={agg['false_online']['strict_false_online']} "
          f"({agg['false_online']['strict_false_online_rate']})  "
          f"broad={agg['false_online']['broad_false_online']} "
          f"({agg['false_online']['broad_false_online_rate']})")
    for c in sorted(agg["per_class"]):
        pc = agg["per_class"][c]
        print(f"  {c:24s} n={pc['n']:3d} expected={pc['expected_state']:12s} "
              f"recall={pc['recall_vs_expected']:.2f} online_rate={pc['online_rate']:.2f}")
    print(f"wrote {OUT_PATH.name}")


if __name__ == "__main__":
    main()
