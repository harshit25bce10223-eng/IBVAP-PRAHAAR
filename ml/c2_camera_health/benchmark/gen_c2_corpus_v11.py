# -*- coding: utf-8 -*-
# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — C2 Camera-Health Benchmark Corpus Generator v1.1 (spec §27/§28)
#
# EXTENDS the frozen v1 corpus (gen_c2_corpus.py, manifest SHA-256
# f251e908cd2f397f0793fe043032b39e9e9c99d5b288260f382a1d2fc602e30a).
# The first 180 samples are produced by importing the v1 generator unchanged —
# they MUST remain byte-identical (verified by the v1.1 runner before scoring).
#
# New v1.1 coverage (§27): quiet scenes / small object motion / low-texture
# viewpoint scenes / network jitter / clock skew / gradual viewpoint shift /
# partial obstruction / mixed degradations.
#
# Same discipline as v1 (§8/§28): deterministic, fully synthetic, inputs-only,
# no external data. Thresholds in the locked engines are NOT tuned against this
# expanded set; expectations are fixed by construction and measured honestly.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import cv2

import gen_c2_corpus as v1
from gen_c2_corpus import (
    BASE_SEED,
    CORPUS_NAME,
    FRAME_H,
    FRAME_W,
    SEQUENCE_LEN,
    TELEMETRY,
    Sample,
    add_motion_blob,
    add_sensor_noise,
    apply_blur,
    apply_compression,
    apply_exposure,
    apply_obstruction,
    make_base_scene,
    materialize_frames,
    sha256_file,
    warp_viewpoint,
)

HERE = Path(__file__).resolve().parent
MANIFEST_PATH = HERE / "c2_corpus_manifest_v11.json"
V1_MANIFEST_PATH = HERE / "c2_corpus_manifest_v1.json"

CORPUS_VERSION = "v1.1"
RELEASE_NAME = "PRHAAR-C2-v1.1"
V1_MANIFEST_SHA256 = "f251e908cd2f397f0793fe043032b39e9e9c99d5b288260f382a1d2fc602e30a"

# §27 expansion classes (the eight requested categories; network jitter is
# split mild/severe so each class carries a single constructed expectation).
V11_NEW_CLASSES = [
    "QUIET_SCENE",
    "SMALL_OBJECT_MOTION",
    "LOW_TEXTURE_VIEWPOINT",
    "NETWORK_JITTER_MILD",
    "NETWORK_JITTER_SEVERE",
    "CLOCK_SKEW",
    "GRADUAL_VIEWPOINT_SHIFT",
    "PARTIAL_OBSTRUCTION",
    "MIXED_DEGRADATION",
]

V11_CLASS_EXPECTATIONS = {
    "QUIET_SCENE": "ONLINE",             # still scene, sensor noise only — quiet != frozen
    "SMALL_OBJECT_MOTION": "ONLINE",     # a distant small object moves — live feed
    "LOW_TEXTURE_VIEWPOINT": "ONLINE",   # grainy low-texture feed; geometry unestablished is not degradation
    "NETWORK_JITTER_MILD": "ONLINE",     # jitter variance below the 100 ms network threshold
    "NETWORK_JITTER_SEVERE": "DEGRADED", # jitter variance above the 100 ms threshold
    "CLOCK_SKEW": "ONLINE",              # |skew| bounded; nothing actually degraded
    "GRADUAL_VIEWPOINT_SHIFT": "DEGRADED",
    "PARTIAL_OBSTRUCTION": "DEGRADED",
    "MIXED_DEGRADATION": "DEGRADED",
}

# v1 classes whose frames are rendered per-frame with fresh scenes + motion
# blob; v1.1 classes reuse that mechanic unless listed below.
_STATIC_BASE_CLASSES = ("QUIET_SCENE", "SMALL_OBJECT_MOTION", "LOW_TEXTURE_VIEWPOINT")


# ─────────────────────────────────────────────────────────────────────────────
# v1.1 scene helpers (synthetic, deterministic)
# ─────────────────────────────────────────────────────────────────────────────
def add_small_object(
    img: np.ndarray,
    x_pos: float,
    obj_w: int = 10,
    obj_h: int = 7,
    y: int = 138,
) -> np.ndarray:
    """Draw a small (10x7) dark object at horizontal position x_pos in [0,1].

    Represents a distant pedestrian/animal at the fence line — deliberately
    much smaller than the v1 vehicle blob so the freeze detector's movement
    guard, not scene-scale change, must keep the feed OUT of FROZEN.
    """
    f = img.copy()
    x = int(x_pos * (FRAME_W - obj_w - 4)) + 2
    x = min(max(x, 1), FRAME_W - obj_w - 2)
    cv2.rectangle(f, (x, y), (x + obj_w - 1, y + obj_h - 1), (30, 30, 85), -1)
    cv2.rectangle(f, (x + 2, y + 1), (x + obj_w - 3, y + 3), (45, 45, 115), -1)
    return f


def make_low_texture_scene(grad_top: list[int], grad_bot: list[int]) -> np.ndarray:
    """Smooth dusk gradient (no posts/hut/bushes) + three 1px wires.

    Low-detail feed as seen on an uncalibrated IR/dusk camera: almost no
    corner structure for viewpoint provisioning, but normal luminance and
    no clipping — a genuinely healthy, merely texture-poor, scene.
    """
    f = np.zeros((FRAME_H, FRAME_W, 3), dtype=np.uint8)
    for y in range(FRAME_H):
        t = y / (FRAME_H - 1)
        for c in range(3):
            f[y, :, c] = int(round(float(grad_top[c]) + (float(grad_bot[c]) - float(grad_top[c])) * t))
    for wy in (72, 98, 124):
        cv2.line(f, (0, wy), (FRAME_W - 1, wy), (165, 165, 165), 1)
    return f


# ─────────────────────────────────────────────────────────────────────────────
# v1.1 sample construction (120 new samples; ids C2-0181..C2-0300)
# ─────────────────────────────────────────────────────────────────────────────
def build_samples_v11() -> list[Sample]:
    samples: list[Sample] = v1.build_samples()  # frozen first 180, unchanged
    sid = len(samples)

    def _next() -> int:
        nonlocal sid
        sid += 1
        return sid

    # 14) QUIET_SCENE x15 — static camera on a still scene: one background
    #     render per sample, sensor noise differs per frame. No blob motion.
    #     The freeze detector must NOT call this FROZEN (quiet != frozen).
    for i in range(15):
        n = _next()
        sigma = (2.0, 2.5, 3.0)[i % 3]
        samples.append(Sample(
            sample_id=f"C2-{n:04d}", cls="QUIET_SCENE", subvariant=f"sigma{sigma:g}",
            expected_state="ONLINE", n_frames=SEQUENCE_LEN,
            seed=BASE_SEED + 200000 + i,
            params=dict(base_sigma=sigma, motion=False, static_base=True, quiet=True),
            telemetry=dict(TELEMETRY["normal"]), telemetry_mode="normal",
        ))

    # 15) SMALL_OBJECT_MOTION x15 — same quiet background; a 10x7 object walks
    #     ~2% of frame width per frame. The movement guard must veto freeze,
    #     and the feed must stay ONLINE.
    for i in range(15):
        n = _next()
        samples.append(Sample(
            sample_id=f"C2-{n:04d}", cls="SMALL_OBJECT_MOTION", subvariant="tiny",
            expected_state="ONLINE", n_frames=SEQUENCE_LEN,
            seed=BASE_SEED + 201000 + i,
            params=dict(base_sigma=2.5, motion=False, static_base=True,
                        small_object=True, obj_step=0.02),
            telemetry=dict(TELEMETRY["normal"]), telemetry_mode="normal",
        ))

    # 16) LOW_TEXTURE_VIEWPOINT x15 — smooth dusk gradient + wires + grain.
    #     Viewpoint provisioning may fail (low texture) — that must surface as
    #     UNKNOWN geometry, NOT as a false shift; image must stay GOOD, so the
    #     F13 online gate must keep the camera ONLINE.
    for i in range(15):
        n = _next()
        rng = np.random.default_rng(BASE_SEED + 202000 + i)
        sigma = (5.5, 5.75, 6.0)[i % 3]
        tb = int(rng.integers(142, 156))
        tg = tb - int(rng.integers(14, 22))
        tr = tg - int(rng.integers(18, 26))
        bb = int(rng.integers(56, 68))
        bg = bb - int(rng.integers(10, 16))
        br = bg - int(rng.integers(12, 20))
        samples.append(Sample(
            sample_id=f"C2-{n:04d}", cls="LOW_TEXTURE_VIEWPOINT", subvariant="grainy",
            expected_state="ONLINE", n_frames=SEQUENCE_LEN,
            seed=BASE_SEED + 202000 + i,
            params=dict(base_sigma=sigma, motion=False, static_base=True,
                        low_texture=True,
                        grad_top=[tb, tg, tr], grad_bot=[bb, bg, br]),
            telemetry=dict(TELEMETRY["normal"]), telemetry_mode="normal",
        ))

    # 17) NETWORK_JITTER_MILD x10 — latency variance 40-90 ms (below the
    #     engine's 100 ms DEGRADED threshold), loss <= 0.9%. Healthy visuals.
    for i in range(10):
        n = _next()
        rng = np.random.default_rng(BASE_SEED + 203000 + i)
        samples.append(Sample(
            sample_id=f"C2-{n:04d}", cls="NETWORK_JITTER_MILD", subvariant="mild",
            expected_state="ONLINE", n_frames=SEQUENCE_LEN,
            seed=BASE_SEED + 203000 + i,
            params=dict(base_sigma=2.0, motion=True),
            telemetry=dict(
                TELEMETRY["normal"],
                latency_ms=round(float(rng.uniform(90, 180)), 1),
                latency_variance_ms=round(float(rng.uniform(40, 90)), 1),
                packet_loss_percent=round(float(rng.uniform(0.3, 0.9)), 2),
            ),
            telemetry_mode="net_jitter_mild",
        ))

    # 18) NETWORK_JITTER_SEVERE x5 — latency variance 120-160 ms (> 100 ms
    #     threshold), latency itself < 200 ms so jitter is the isolated trigger.
    for i in range(5):
        n = _next()
        rng = np.random.default_rng(BASE_SEED + 204000 + i)
        samples.append(Sample(
            sample_id=f"C2-{n:04d}", cls="NETWORK_JITTER_SEVERE", subvariant="severe",
            expected_state="DEGRADED", n_frames=SEQUENCE_LEN,
            seed=BASE_SEED + 204000 + i,
            params=dict(base_sigma=2.0, motion=True),
            telemetry=dict(
                TELEMETRY["normal"],
                latency_ms=round(float(rng.uniform(120, 190)), 1),
                latency_variance_ms=round(float(rng.uniform(120, 160)), 1),
                packet_loss_percent=round(float(rng.uniform(0.5, 1.0)), 2),
            ),
            telemetry_mode="net_jitter_severe",
        ))

    # 19) CLOCK_SKEW x15 — healthy visuals/telemetry; source timestamp is
    #     behind (8-28 s, still under the 30 s stale threshold) or slightly
    #     ahead (6-24 s) of the receive clock. Nothing is degraded: ONLINE.
    for i in range(15):
        n = _next()
        rng = np.random.default_rng(BASE_SEED + 205000 + i)
        if i < 8:
            skew = -round(float(rng.uniform(6, 24)), 1)
            mode = "clock_skew_ahead"
            sub = "ahead"
        else:
            skew = round(float(rng.uniform(8, 28)), 1)
            mode = "clock_skew_behind"
            sub = "behind"
        samples.append(Sample(
            sample_id=f"C2-{n:04d}", cls="CLOCK_SKEW", subvariant=sub,
            expected_state="ONLINE", n_frames=SEQUENCE_LEN,
            seed=BASE_SEED + 205000 + i,
            params=dict(base_sigma=2.0, motion=True),
            telemetry=dict(TELEMETRY["normal"], source_age_sec=skew),
            telemetry_mode=mode,
        ))

    # 20) GRADUAL_VIEWPOINT_SHIFT x15 — camera pans/drifts slowly: frame i is
    #     the reference warped by i steps (~9-12 px translation per step plus
    #     slow rotation/zoom). A slow drift must not defeat shift detection.
    for i in range(15):
        n = _next()
        rng = np.random.default_rng(BASE_SEED + 206000 + i)
        samples.append(Sample(
            sample_id=f"C2-{n:04d}", cls="GRADUAL_VIEWPOINT_SHIFT", subvariant="linear",
            expected_state="DEGRADED", n_frames=SEQUENCE_LEN,
            seed=BASE_SEED + 206000 + i,
            params=dict(base_sigma=2.0, motion=False,
                        warp_tx_step=round(float(rng.uniform(9.0, 12.0)), 2),
                        warp_ty_step=round(float(rng.uniform(0.3, 0.8)), 2),
                        warp_rot_step=round(float(rng.uniform(0.03, 0.08)), 3),
                        warp_zoom_step=round(float(rng.uniform(0.003, 0.005)), 4)),
            telemetry=dict(TELEMETRY["normal"]), telemetry_mode="normal",
        ))

    # 21) PARTIAL_OBSTRUCTION x15 — near-black cover over 45-58% of the frame
    #     (exposure-clip channel) and dark-gray cover over 55-68% (sharpness
    #     channel), both far short of the v1 82-90% full obstruction.
    for i in range(15):
        n = _next()
        rng = np.random.default_rng(BASE_SEED + 207000 + i)
        if i < 10:
            cover = round(float(rng.uniform(0.45, 0.58)), 4)
            shade = int(rng.integers(0, 3))
            sub = "black"
        else:
            cover = round(float(rng.uniform(0.55, 0.68)), 4)
            shade = int(rng.integers(20, 41))
            sub = "gray"
        samples.append(Sample(
            sample_id=f"C2-{n:04d}", cls="PARTIAL_OBSTRUCTION", subvariant=sub,
            expected_state="DEGRADED", n_frames=SEQUENCE_LEN,
            seed=BASE_SEED + 207000 + i,
            params=dict(base_sigma=2.0, motion=True,
                        cover_fraction=cover, cover_shade=shade),
            telemetry=dict(TELEMETRY["normal"]), telemetry_mode="normal",
        ))

    # 22) MIXED_DEGRADATION x15 — three combinators of blur / darkness /
    #     severe compression / network degradation on healthy streams.
    for i in range(15):
        n = _next()
        rng = np.random.default_rng(BASE_SEED + 208000 + i)
        if i < 5:
            sub = "blur_dark_net"
            params = dict(base_sigma=2.0, motion=True,
                          blur_kernel=int(rng.integers(15, 26)) | 1,
                          exposure_factor=round(float(rng.uniform(0.10, 0.15)), 4))
            telemetry = dict(TELEMETRY["net_degraded"])
            mode = "net_degraded"
        elif i < 10:
            sub = "blur_jpeg"
            params = dict(base_sigma=2.0, motion=True,
                          blur_kernel=int(rng.integers(11, 18)) | 1,
                          jpeg_quality=int(rng.integers(4, 7)))
            telemetry = dict(TELEMETRY["normal"])
            mode = "normal"
        else:
            sub = "dark_jpeg_net"
            params = dict(base_sigma=2.0, motion=True,
                          exposure_factor=round(float(rng.uniform(0.05, 0.08)), 4),
                          jpeg_quality=int(rng.integers(5, 9)))
            telemetry = dict(
                TELEMETRY["normal"],
                latency_ms=round(float(rng.uniform(120, 190)), 1),
                latency_variance_ms=round(float(rng.uniform(125, 155)), 1),
            )
            mode = "net_jitter_severe"
        samples.append(Sample(
            sample_id=f"C2-{n:04d}", cls="MIXED_DEGRADATION", subvariant=sub,
            expected_state="DEGRADED", n_frames=SEQUENCE_LEN,
            seed=BASE_SEED + 208000 + i,
            params=params, telemetry=telemetry, telemetry_mode=mode,
        ))

    return samples


# ─────────────────────────────────────────────────────────────────────────────
# Deterministic materialization (v1 classes delegate to the frozen generator)
# ─────────────────────────────────────────────────────────────────────────────
def materialize_frames_v11(sample: Sample) -> list[np.ndarray]:
    """Render sample frames deterministically from (seed, params)."""
    if sample.cls not in V11_NEW_CLASSES:
        return materialize_frames(sample)  # v1 classes: byte-identical frames

    rng = np.random.default_rng(sample.seed)
    p = sample.params
    n = sample.n_frames
    frames: list[np.ndarray] = []

    if sample.cls in _STATIC_BASE_CLASSES:
        # One background render; per-frame sensor noise (quiet camera).
        if sample.cls == "LOW_TEXTURE_VIEWPOINT":
            base = make_low_texture_scene(p["grad_top"], p["grad_bot"])
        else:
            base = make_base_scene(rng)
        for i in range(n):
            f = base
            if sample.cls == "SMALL_OBJECT_MOTION":
                f = add_small_object(f, x_pos=(0.04 + i * float(p.get("obj_step", 0.02))) % 0.9)
            f = add_sensor_noise(f, rng, float(p["base_sigma"]))
            frames.append(f)
        return frames

    if sample.cls == "GRADUAL_VIEWPOINT_SHIFT":
        base = make_base_scene(rng)
        f0 = add_sensor_noise(base, rng, float(p["base_sigma"]))
        frames.append(f0)
        for i in range(1, n):
            frames.append(warp_viewpoint(
                f0,
                tx=i * float(p["warp_tx_step"]),
                ty=i * float(p["warp_ty_step"]),
                rot_deg=i * float(p["warp_rot_step"]),
                zoom=1.0 + i * float(p["warp_zoom_step"]),
            ))
        return frames

    # v1-loop mechanics (fresh scene + moving vehicle blob per frame), with the
    # v1.1 class-specific degradations applied in the same order as v1.
    for i in range(n):
        f = make_base_scene(rng)
        f = add_motion_blob(f, rng, x_pos=(0.08 + i * 0.06) % 1.0)
        if "exposure_factor" in p:
            f = apply_exposure(f, float(p["exposure_factor"]))
        if "blur_kernel" in p:
            f = apply_blur(f, int(p["blur_kernel"]))
        if "jpeg_quality" in p:
            f = apply_compression(f, int(p["jpeg_quality"]))
        f = add_sensor_noise(f, rng, float(p["base_sigma"]))
        if "cover_fraction" in p:
            f = apply_obstruction(f, float(p["cover_fraction"]), int(p["cover_shade"]))
        frames.append(f)
    return frames


# ─────────────────────────────────────────────────────────────────────────────
# Manifest
# ─────────────────────────────────────────────────────────────────────────────
def build_manifest_v11() -> dict:
    samples = build_samples_v11()
    counts: dict[str, int] = {}
    for s in samples:
        counts[s.cls] = counts.get(s.cls, 0) + 1

    rows = []
    for s in samples:
        rows.append(dict(
            sample_id=s.sample_id, cls=s.cls, subvariant=s.subvariant,
            expected_state=s.expected_state, n_frames=s.n_frames, seed=s.seed,
            params=s.params, telemetry=s.telemetry, telemetry_mode=s.telemetry_mode,
            viewpoint_injected=s.viewpoint_injected,
        ))

    payload = dict(
        corpus=CORPUS_NAME, version=CORPUS_VERSION, release=RELEASE_NAME,
        extends_version=v1.CORPUS_VERSION, extends_manifest_sha256=V1_MANIFEST_SHA256,
        spec_classes_ten=["ONLINE", "DEGRADED", "FROZEN", "BLURRED", "OBSTRUCTED",
                          "UNDEREXPOSED", "OVEREXPOSED", "SEVERE_COMPRESSION",
                          "VIEWPOINT_CHANGED", "COVERAGE_COMPROMISED"],
        supplementary_classes=["STALE_FEED", "STREAM_DROP_FROZEN", "LOW_FPS_SINGLE_DIM"],
        v11_classes=list(V11_NEW_CLASSES),
        v11_class_expectations=dict(V11_CLASS_EXPECTATIONS),
        frame_w=FRAME_W, frame_h=FRAME_H,
        sequence_len=SEQUENCE_LEN, viewpoint_seq_len=v1.VIEWPOINT_SEQ_LEN,
        base_seed=BASE_SEED, n_samples=len(samples), class_counts=counts,
        generator_sha256=sha256_file(Path(__file__)),
        v1_generator_sha256=sha256_file(Path(v1.__file__).resolve()),
        samples=rows,
    )
    payload_bytes = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
    manifest = dict(payload)
    manifest["manifest_sha256"] = hashlib.sha256(payload_bytes).hexdigest()
    return manifest


def main():
    manifest = build_manifest_v11()
    raw = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")
    MANIFEST_PATH.write_bytes(raw)
    print(f"samples={manifest['n_samples']} version={manifest['version']}")
    for cls, c in sorted(manifest["class_counts"].items()):
        print(f"  {cls:24s} {c}")
    print(f"manifest_sha256={manifest['manifest_sha256']}")
    print(f"wrote {MANIFEST_PATH.name}")


if __name__ == "__main__":
    main()
