# -*- coding: utf-8 -*-
"""C2 F4/F11 evidence — freeze-detector false-positive benchmark (spec §9-§11).

Runs the REAL production FreezeDetector (app/domain/camera_health/freeze.py,
repaired: absolute per-region temporal activity, bit-exact short-circuit,
ROI-aware movement guard, persistence) against the §10 minimum category set:

  1. quiet static scene            (expect NOT frozen)
  2. quiet scene + sensor noise    (expect NOT frozen)
  3. quiet scene + tiny object movement   (expect NOT frozen)
  4. quiet scene + distant pedestrian    (expect NOT frozen)
  5. quiet scene + distant vehicle       (expect NOT frozen)
  6. normal environmental movement       (expect NOT frozen)
  7. true bit-exact freeze         (expect FROZEN)
  8. true repeated-frame freeze    (expect FROZEN)

Measures (spec §10): true-freeze recall and false-freeze rate. Everything is
fully synthetic and reproducible from (seed, params); no real imagery, no
downloads (spec §8). Production detector defaults only — no parameter is
tuned against this benchmark.

Not part of the frozen benchmark harness (§25). Output:
c2_freeze_false_positive_benchmark.json next to this script.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, r"C:\SIH\ibvap-backend")

import numpy as np  # noqa: E402
import cv2  # noqa: E402

gen = importlib.import_module("gen_c2_corpus")
from app.domain.camera_health.freeze import FreezeDetector  # noqa: E402

FRAME_W = gen.FRAME_W
FRAME_H = gen.FRAME_H
BASE_SEED = gen.BASE_SEED
FRAMES_PER_SAMPLE = 12      # first frame + 11 comparisons (persistence 10)
SAMPLES_PER_CATEGORY = 10
OUT_PATH = HERE / "c2_freeze_false_positive_benchmark.json"

CATEGORIES = [
    ("quiet_static_scene", "static scene, per-frame +-1 level encoder requantization dither", False),
    ("quiet_scene_sensor_noise", "static scene + per-frame Gaussian sensor noise sigma=2.0", False),
    ("quiet_tiny_object_movement", "sub-floor noise + 12x12 low-contrast object moving 3 px/frame", False),
    ("quiet_distant_pedestrian", "sub-floor noise + 6x14 low-contrast blob moving 4 px/frame", False),
    ("quiet_distant_vehicle", "sub-floor noise + 18x8 low-contrast blob moving 15 px/frame", False),
    ("normal_environmental_movement", "sigma=1.5 noise + vegetation sway (4 patches, 1 px/frame roll)", False),
    ("true_bit_exact_freeze", "identical frame repeated every second (encoder repeating a frame)", True),
    ("true_repeated_frame_freeze", "repeated frame + sub-floor re-encode dither every 5th frame", True),
]


# ─────────────────────────────────────────────────────────────────────────────
# Frame generators (deterministic; seed = BASE_SEED + cat*1000 + sample)
# ─────────────────────────────────────────────────────────────────────────────
def _dither(img: np.ndarray, rng: np.random.Generator, fraction: float) -> np.ndarray:
    """Add +-1 level quantization dither to a `fraction` of pixels."""
    f = img.astype(np.int16)
    mask = rng.random((FRAME_H, FRAME_W, 1)) < fraction
    delta = rng.integers(-1, 2, (FRAME_H, FRAME_W, 1))
    f += (delta * mask).astype(np.int16)
    return np.clip(f, 0, 255).astype(np.uint8)


def _draw_blob(img: np.ndarray, x: int, y: int, w: int, h: int, delta: int) -> np.ndarray:
    f = img.astype(np.int16)
    x0 = max(0, min(x, FRAME_W - 1))
    y0 = max(0, min(y, FRAME_H - 1))
    f[y0:y0 + h, x0:x0 + w] += delta
    return np.clip(f, 0, 255).astype(np.uint8)


def build_frames(cat: str, seed: int) -> list[np.ndarray]:
    rng = np.random.default_rng(seed)
    base = gen.make_base_scene(rng)
    frames: list[np.ndarray] = []

    if cat == "quiet_static_scene":
        for _ in range(FRAMES_PER_SAMPLE):
            frames.append(_dither(base, rng, fraction=1.0))

    elif cat == "quiet_scene_sensor_noise":
        for _ in range(FRAMES_PER_SAMPLE):
            frames.append(gen.add_sensor_noise(base, rng, sigma=2.0))

    elif cat == "quiet_tiny_object_movement":
        for i in range(FRAMES_PER_SAMPLE):
            f = gen.add_sensor_noise(base, rng, sigma=0.15)  # sub-floor native noise
            f = _draw_blob(f, 200 + i * 3, 60, 12, 12, +55)
            frames.append(f)

    elif cat == "quiet_distant_pedestrian":
        for i in range(FRAMES_PER_SAMPLE):
            f = gen.add_sensor_noise(base, rng, sigma=0.15)
            f = _draw_blob(f, 40 + i * 4, 104, 6, 14, +35)
            frames.append(f)

    elif cat == "quiet_distant_vehicle":
        for i in range(FRAMES_PER_SAMPLE):
            f = gen.add_sensor_noise(base, rng, sigma=0.15)
            f = _draw_blob(f, 30 + i * 15, 96, 18, 8, +45)
            frames.append(f)

    elif cat == "normal_environmental_movement":
        for i in range(FRAMES_PER_SAMPLE):
            f = gen.add_sensor_noise(base, rng, sigma=1.5)
            for x0 in (20, 100, 180, 250):  # vegetation patches swaying 1 px/frame
                patch = f[150:170, x0:x0 + 24].copy()
                f[150:170, x0:x0 + 24] = np.roll(patch, (i % 3) - 1, axis=1)
            frames.append(f)

    elif cat == "true_bit_exact_freeze":
        for _ in range(FRAMES_PER_SAMPLE):
            frames.append(base.copy())

    elif cat == "true_repeated_frame_freeze":
        current = base.copy()
        for i in range(FRAMES_PER_SAMPLE):
            if i > 0 and i % 5 == 0:
                # re-encode dither on the SAME duplicated scene (sub-floor)
                current = _dither(current, rng, fraction=0.2)
            frames.append(current.copy())

    else:
        raise ValueError(cat)

    return frames


# ─────────────────────────────────────────────────────────────────────────────
# Evaluation
# ─────────────────────────────────────────────────────────────────────────────
def run() -> dict:
    t0 = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    results: dict[str, dict] = {}

    for cat_idx, (cat, desc, expect_frozen) in enumerate(CATEGORIES):
        samples = []
        for s_idx in range(SAMPLES_PER_CATEGORY):
            seed = BASE_SEED + cat_idx * 1000 + s_idx
            frames = build_frames(cat, seed)
            det = FreezeDetector()  # production defaults
            verdicts = []
            for i, frame in enumerate(frames):
                r = det.analyze(frame, t0 + timedelta(seconds=i))
                verdicts.append(bool(r.frozen))
            first_frozen = next((i for i, v in enumerate(verdicts) if v), None)
            samples.append(
                dict(
                    seed=int(seed),
                    frozen_final=verdicts[-1],
                    frozen_any=any(verdicts[1:]),
                    first_frozen_frame=first_frozen,
                )
            )

        n = len(samples)
        frozen_final = sum(s["frozen_final"] for s in samples)
        frozen_any = sum(s["frozen_any"] for s in samples)
        results[cat] = dict(
            description=desc,
            expected_frozen=expect_frozen,
            n_samples=n,
            frozen_final_count=frozen_final,
            frozen_any_count=frozen_any,
            first_frozen_frames=[s["first_frozen_frame"] for s in samples],
            samples=samples,
        )
        if expect_frozen:
            results[cat]["true_freeze_recall"] = round(frozen_final / n, 4)
        else:
            results[cat]["false_freeze_rate_final"] = round(frozen_final / n, 4)
            results[cat]["false_freeze_rate_any"] = round(frozen_any / n, 4)

    quiet = [c for c, _, exp in CATEGORIES if not exp]
    true = [c for c, _, exp in CATEGORIES if exp]
    quiet_total = sum(results[c]["n_samples"] for c in quiet)
    quiet_fp_final = sum(results[c]["frozen_final_count"] for c in quiet)
    quiet_fp_any = sum(results[c]["frozen_any_count"] for c in quiet)
    true_total = sum(results[c]["n_samples"] for c in true)
    true_hits = sum(results[c]["frozen_final_count"] for c in true)

    manifest = dict(
        name="PRHAAR-C2-FREEZE-FALSE-POSITIVE",
        version="v1",
        frame_w=FRAME_W,
        frame_h=FRAME_H,
        frames_per_sample=FRAMES_PER_SAMPLE,
        samples_per_category=SAMPLES_PER_CATEGORY,
        base_seed=BASE_SEED,
        categories=[dict(name=c, description=d, expected_frozen=e) for c, d, e in CATEGORIES],
        detector=dict(
            persistence_frames=10,
            noise_floor=0.001,
            movement_spread_factor=8.0,
            region_grid=[4, 4],
            scale_factor=0.125,
        ),
    )
    manifest_sha = hashlib.sha256(
        json.dumps(manifest, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    summary = dict(
        false_freeze_rate_final=round(quiet_fp_final / quiet_total, 4),
        false_freeze_rate_any=round(quiet_fp_any / quiet_total, 4),
        true_freeze_recall=round(true_hits / true_total, 4),
        quiet_samples=quiet_total,
        true_samples=true_total,
    )

    out = dict(
        corpus_manifest=manifest,
        corpus_manifest_sha256=manifest_sha,
        summary=summary,
        per_category=results,
        environment=dict(
            python=sys.version.split()[0],
            numpy=np.__version__,
            cv2=cv2.__version__,
        ),
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    return out


def main() -> None:
    out = run()
    OUT_PATH.write_text(json.dumps(out, indent=2), encoding="utf-8")

    print(f"manifest sha256: {out['corpus_manifest_sha256']}")
    print(f"{'category':34s} {'expect':7s} {'frozen_final':>12s} {'frozen_any':>10s} {'rate_final':>10s}")
    for cat, _, exp in CATEGORIES:
        r = out["per_category"][cat]
        rate = r.get("true_freeze_recall", r.get("false_freeze_rate_final"))
        print(
            f"{cat:34s} {'FROZEN' if exp else 'alive':7s} "
            f"{r['frozen_final_count']:>7d}/{r['n_samples']:<4d} "
            f"{r['frozen_any_count']:>7d}/{r['n_samples']:<4d} "
            f"{rate:>10.4f}"
        )
    s = out["summary"]
    print()
    print(
        f"false-freeze rate (6 quiet categories): final {s['false_freeze_rate_final']:.4f} "
        f"({s['quiet_samples']} samples) | any {s['false_freeze_rate_any']:.4f}"
    )
    print(f"true-freeze recall (2 freeze categories): {s['true_freeze_recall']:.4f} ({s['true_samples']} samples)")
    print(f"wrote {OUT_PATH.name}")


if __name__ == "__main__":
    main()
