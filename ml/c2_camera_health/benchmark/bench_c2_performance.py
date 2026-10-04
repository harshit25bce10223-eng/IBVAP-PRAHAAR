# -*- coding: utf-8 -*-
# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — C2 Camera-Health performance measurement (spec §42)
#
# Measures, at 1 / 10 / 100 / 1,000 observations (25 fps stream cadence):
#   image quality  — ImageQualityAnalyzer.analyze per frame
#   freeze         — FreezeDetector.analyze per frame (full compare path)
#   viewpoint      — ViewpointDetector.analyze per frame after reference set
#   state derivation — CameraHealthStateEngine.derive_state (no frame work)
#   full analyze_observation — the real orchestrator end-to-end per frame
#
# Records p50 / p95 / max (ms) per component per batch size.
#
# §42: local development timings only — these numbers must NOT be turned
# into production-capacity claims.
#
# Deterministic inputs: a 1,000-frame synthetic pool (one static scene, per-
# frame sensor noise, small moving object) rendered from the v1 generator's
# helpers — represents a live textured quiet feed, the steady-state case.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import json
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
BACKEND = Path(r"C:\SIH\ibvap-backend")
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(BACKEND))

import cv2  # noqa: E402

from run_c2_benchmark import CONFIG, ENGINE_FILES  # noqa: E402  (frozen harness config)
from gen_c2_corpus import (  # noqa: E402
    BASE_SEED, make_base_scene, add_sensor_noise, sha256_file,
)
from gen_c2_corpus_v11 import add_small_object  # noqa: E402

from app.domain.camera_health.analyzer import CameraHealthAnalyzer  # noqa: E402
from app.domain.camera_health.freeze import FreezeDetector  # noqa: E402
from app.domain.camera_health.image_quality import ImageQualityAnalyzer  # noqa: E402
from app.domain.camera_health.state_engine import (  # noqa: E402
    CameraHealthInput, CameraHealthStateEngine, FreezeMetrics, ImageQualityMetrics,
    NetworkMetrics, StreamHealthMetrics, ViewpointMetrics,
)
from app.domain.camera_health.viewpoint import ViewpointDetector  # noqa: E402

OUT_PATH = HERE / "c2_performance_results.json"
BATCHES = (1, 10, 100, 1000)
POOL_SEED = BASE_SEED + 500000


def build_pool(n: int) -> list[np.ndarray]:
    """One static textured scene; per-frame sensor noise + slow small object."""
    rng0 = np.random.default_rng(POOL_SEED)
    base = make_base_scene(rng0)
    frames = []
    for i in range(n):
        rng = np.random.default_rng(POOL_SEED + 10000 + i)
        f = add_small_object(base, x_pos=(0.04 + i * 0.01) % 0.9)
        f = add_sensor_noise(f, rng, 2.0)
        frames.append(f)
    return frames


def stats(times_ms: list[float]) -> dict | None:
    if not times_ms:
        return None
    arr = np.asarray(times_ms, dtype=np.float64)
    return dict(
        n_measured=len(times_ms),
        p50_ms=round(float(np.percentile(arr, 50)), 3),
        p95_ms=round(float(np.percentile(arr, 95)), 3),
        max_ms=round(float(np.max(arr)), 3),
    )


def time_it(fn) -> float:
    t0 = time.perf_counter()
    fn()
    return (time.perf_counter() - t0) * 1000.0


def measure_batch(frames: list[np.ndarray], n: int, base_ts: datetime) -> dict:
    view = frames[:n]

    # 1. Image quality — stateless per-frame analysis
    iq = ImageQualityAnalyzer()
    iq_times = [time_it(lambda f=f: iq.analyze(f)) for f in view]

    # 2. Freeze — streaming detector; 0.6 s cadence keeps every call on the
    #    full compare path (min_frame_interval is 0.5 s in the detector)
    det = FreezeDetector()
    fr_times = []
    for i, f in enumerate(view):
        ts = base_ts + timedelta(seconds=0.6 * i)
        fr_times.append(time_it(lambda f=f, ts=ts: det.analyze(f, ts)))

    # 3. Viewpoint — reference from frame 0, then per-frame analysis
    vp = ViewpointDetector()
    cv2.setRNGSeed(POOL_SEED)
    vp.set_reference(view[0])
    vp_times = []
    for i in range(1, n):
        cv2.setRNGSeed(POOL_SEED + i)
        vp_times.append(time_it(lambda f=view[i]: vp.analyze(f)))

    # 4. State derivation only — engine with prepared metrics (no frame work)
    engine = CameraHealthStateEngine()
    st_times = []
    for i in range(n):
        inp = CameraHealthInput(
            camera_id=f"CAM-PERF-{n}",
            config=CONFIG,
            source_timestamp=base_ts + timedelta(seconds=0.04 * i),
            received_at=base_ts + timedelta(seconds=0.04 * i),
            stream=StreamHealthMetrics(connected=True, observed_fps=25.0,
                                       frame_drop_rate=0.0),
            image=ImageQualityMetrics(sharpness=0.8, brightness=0.5,
                                      exposure="NORMAL", contrast=0.4, noise=0.02),
            network=NetworkMetrics(latency_ms=30.0, latency_variance_ms=10.0,
                                   packet_loss_percent=0.1, heartbeat_age_sec=2.0),
            viewpoint=ViewpointMetrics(shift_score=0.0, shift_confidence=0.0,
                                       inlier_ratio=0.9, reference_active=True),
            freeze=FreezeMetrics(frozen=False),
        )
        st_times.append(time_it(lambda inp=inp: engine.derive_state(inp)))

    # 5. Full analyze_observation — real orchestrator, fresh analyzer per batch
    analyzer = CameraHealthAnalyzer()
    full_times = []
    for i, f in enumerate(view):
        ts = base_ts + timedelta(seconds=0.04 * i)

        def call(f=f, ts=ts):
            analyzer.analyze_observation(
                camera_id=f"CAM-PERF-{n}", config=CONFIG,
                source_timestamp=ts, received_at=ts,
                stream=StreamHealthMetrics(connected=True, observed_fps=25.0,
                                           frame_drop_rate=0.0),
                network=NetworkMetrics(latency_ms=30.0, latency_variance_ms=10.0,
                                       packet_loss_percent=0.1, heartbeat_age_sec=2.0),
                viewpoint=None, frame=f,
            )

        full_times.append(time_it(call))

    return dict(
        n=n,
        image_quality=stats(iq_times),
        freeze=stats(fr_times),
        viewpoint=stats(vp_times),
        state_derivation=stats(st_times),
        full_analyze_observation=stats(full_times),
    )


def main():
    t0 = time.time()
    frames = build_pool(1000)
    base_ts = datetime.now(timezone.utc).replace(tzinfo=None)

    rows = [measure_batch(frames, n, base_ts) for n in BATCHES]

    out = dict(
        benchmark="PRHAAR-C2-PERFORMANCE",
        version="v1",
        run_utc=datetime.now(timezone.utc).isoformat(),
        wall_seconds=round(time.time() - t0, 3),
        frame_w=int(frames[0].shape[1]), frame_h=int(frames[0].shape[0]),
        pool_size=len(frames), pool_seed=POOL_SEED,
        cadence=dict(streamp_fps=25.0, freeze_interval_sec=0.6),
        note="Local development timings — no production-capacity claims (§42).",
        environment=dict(cv2_version=cv2.__version__, numpy_version=np.__version__),
        module_hashes={f: sha256_file(BACKEND / f) for f in ENGINE_FILES},
        results=rows,
    )
    OUT_PATH.write_bytes(json.dumps(out, indent=2, sort_keys=True).encode("utf-8"))

    hdr = f"{'n':>5} {'component':28s} {'p50 ms':>8} {'p95 ms':>8} {'max ms':>8}"
    print(hdr)
    for row in rows:
        for key in ("image_quality", "freeze", "viewpoint",
                    "state_derivation", "full_analyze_observation"):
            s = row.get(key)
            if s:
                print(f"{row['n']:>5} {key:28s} {s['p50_ms']:>8.3f} "
                      f"{s['p95_ms']:>8.3f} {s['max_ms']:>8.3f}")
            else:
                print(f"{row['n']:>5} {key:28s} {'n/a':>8}")
    print(f"wall={out['wall_seconds']}s wrote {OUT_PATH.name}")


if __name__ == "__main__":
    main()
