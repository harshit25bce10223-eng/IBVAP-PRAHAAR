# -*- coding: utf-8 -*-
# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — C2 Camera-Health Benchmark Corpus Generator (spec §67/§68)
#
# Deterministic, fully synthetic, inputs-only corpus. No real imagery, no
# external downloads (spec §8). 180 samples across the ten §68 health classes
# plus documented supplementary state rows (STALE / telemetry-FROZEN /
# single-dim UNKNOWN). Every sample is reproducible from (seed, params).
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import cv2

HERE = Path(__file__).resolve().parent

FRAME_W = 320
FRAME_H = 180
SEQUENCE_LEN = 12          # default frames per sample
VIEWPOINT_SEQ_LEN = 8      # viewpoint samples: ref frame + 7 analyzed
BASE_SEED = 20260930
MANIFEST_PATH = HERE / "c2_corpus_manifest_v1.json"

CORPUS_NAME = "PRHAAR-C2-CAMERA-HEALTH-BENCH"
CORPUS_VERSION = "v1"


# ─────────────────────────────────────────────────────────────────────────────
# Scene synthesis (deterministic border outpost scene)
# ─────────────────────────────────────────────────────────────────────────────
def make_base_scene(rng: np.random.Generator) -> np.ndarray:
    """Synthesize a deterministic 320x180 BGR border-fence scene."""
    f = np.zeros((FRAME_H, FRAME_W, 3), dtype=np.uint8)

    # Sky gradient (rows 0..104)
    for y in range(105):
        t = y / 105.0
        b = int(205 + 30 * t)
        g = int(175 + 28 * t)
        r = int(125 + 32 * t)
        f[y, :, 0] = b
        f[y, :, 1] = g
        f[y, :, 2] = r

    # Ground gradient (rows 105..179)
    for y in range(105, FRAME_H):
        t = (y - 105) / (FRAME_H - 105)
        b = int(95 - 35 * t)
        g = int(105 - 30 * t)
        r = int(125 - 35 * t)
        f[y, :, 0] = b
        f[y, :, 1] = g
        f[y, :, 2] = r

    # Fence posts (9) with jitter, from y=55 down to y=152
    for k in range(9):
        x = 18 + k * 36 + int(rng.integers(-4, 5))
        x = min(max(x, 2), FRAME_W - 3)
        cv2.line(f, (x, 55), (x, 152), (110, 110, 110), 2)

    # 3 horizontal wires
    for wy in (72, 98, 124):
        cv2.line(f, (0, wy), (FRAME_W - 1, wy), (140, 140, 140), 1)

    # Bushes (5 filled circles on the ground)
    for _ in range(5):
        cx = int(rng.integers(10, FRAME_W - 10))
        cy = int(rng.integers(140, 172))
        rad = int(rng.integers(8, 17))
        cv2.circle(f, (cx, cy), rad, (35, 75, 35), -1)

    # Guard hut (right side)
    cv2.rectangle(f, (248, 88), (300, 132), (85, 70, 60), -1)
    cv2.rectangle(f, (244, 82), (304, 90), (60, 55, 50), -1)

    # Gravel speckle (300 dots)
    ys = rng.integers(0, FRAME_H, 300)
    xs = rng.integers(0, FRAME_W, 300)
    vals = rng.integers(-15, 16, 300)
    for y, x, v in zip(ys, xs, vals):
        f[y, x] = np.clip(f[y, x].astype(np.int16) + int(v), 0, 255).astype(np.uint8)

    return f


def add_sensor_noise(img: np.ndarray, rng: np.random.Generator, sigma: float) -> np.ndarray:
    """Additive zero-mean Gaussian noise (sigma in 0-255 pixel units)."""
    if sigma <= 0:
        return img.copy()
    noise = rng.normal(0.0, sigma, img.shape)
    return np.clip(img.astype(np.float32) + noise, 0, 255).astype(np.uint8)


def add_motion_blob(img: np.ndarray, rng: np.random.Generator, x_pos: float) -> np.ndarray:
    """Draw a 26x12 dark vehicle blob at horizontal position x_pos in [0,1]."""
    f = img.copy()
    x = int(x_pos * (FRAME_W - 34)) + 4
    y = 138
    cv2.rectangle(f, (x, y), (x + 26, y + 12), (25, 25, 80), -1)
    cv2.rectangle(f, (x + 3, y + 2), (x + 23, y + 6), (40, 40, 110), -1)
    return f


def apply_blur(img: np.ndarray, kernel: int) -> np.ndarray:
    k = int(kernel) | 1
    return cv2.GaussianBlur(img, (k, k), 0)


def apply_obstruction(img: np.ndarray, cover_fraction: float, shade: int) -> np.ndarray:
    """Near-black cover over `cover_fraction` of frame width from the left."""
    f = img.copy()
    w = int(cover_fraction * FRAME_W)
    cv2.rectangle(f, (0, 0), (w, FRAME_H - 1), (shade, shade, shade), -1)
    return f


def apply_exposure(img: np.ndarray, factor: float) -> np.ndarray:
    return np.clip(img.astype(np.float32) * factor, 0, 255).astype(np.uint8)


def apply_compression(img: np.ndarray, quality: int) -> np.ndarray:
    ok, enc = cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, int(quality)])
    if not ok:
        return img.copy()
    return cv2.imdecode(enc, cv2.IMREAD_COLOR)


def warp_viewpoint(img: np.ndarray, tx: float, ty: float, rot_deg: float, zoom: float) -> np.ndarray:
    """Affine shift: rotation+zoom about center, then translation (BORDER_CONSTANT black)."""
    M = cv2.getRotationMatrix2D((FRAME_W / 2.0, FRAME_H / 2.0), rot_deg, zoom)
    M[0, 2] += tx
    M[1, 2] += ty
    return cv2.warpAffine(img, M, (FRAME_W, FRAME_H), borderValue=(0, 0, 0))


# ─────────────────────────────────────────────────────────────────────────────
# Telemetry recipes (plain dicts; consumed by harness run_end_to_end)
# ─────────────────────────────────────────────────────────────────────────────
TELEMETRY = {
    "normal": dict(
        connected=True, observed_fps=25.0, frame_drop_rate=0.0,
        latency_ms=25.0, latency_variance_ms=8.0, packet_loss_percent=0.1,
        heartbeat_age_sec=2.0, source_age_sec=1.0,
    ),
    "net_degraded": dict(
        connected=True, observed_fps=25.0, frame_drop_rate=0.0,
        latency_ms=280.0, latency_variance_ms=40.0, packet_loss_percent=3.0,
        heartbeat_age_sec=2.0, source_age_sec=1.0,
    ),
    "low_fps": dict(
        connected=True, observed_fps=9.0, frame_drop_rate=0.0,
        latency_ms=25.0, latency_variance_ms=8.0, packet_loss_percent=0.1,
        heartbeat_age_sec=2.0, source_age_sec=1.0,
    ),
    "stream_drop": dict(
        connected=True, observed_fps=25.0, frame_drop_rate=0.7,
        latency_ms=25.0, latency_variance_ms=8.0, packet_loss_percent=0.1,
        heartbeat_age_sec=2.0, source_age_sec=1.0,
    ),
    "stale": dict(
        connected=True, observed_fps=25.0, frame_drop_rate=0.0,
        latency_ms=25.0, latency_variance_ms=8.0, packet_loss_percent=0.1,
        heartbeat_age_sec=2.0, source_age_sec=45.0,
    ),
    "disconnected": dict(
        connected=False, observed_fps=None, frame_drop_rate=0.0,
        latency_ms=25.0, latency_variance_ms=8.0, packet_loss_percent=0.1,
        heartbeat_age_sec=2.0, source_age_sec=1.0,
    ),
    "disconnected_offline": dict(
        connected=False, observed_fps=None, frame_drop_rate=0.0,
        latency_ms=None, latency_variance_ms=None, packet_loss_percent=None,
        heartbeat_age_sec=150.0, source_age_sec=1.0,
    ),
}


# ─────────────────────────────────────────────────────────────────────────────
# Sample container
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class Sample:
    sample_id: str
    cls: str
    subvariant: str
    expected_state: str
    n_frames: int
    seed: int
    params: dict = field(default_factory=dict)
    telemetry: dict = field(default_factory=dict)
    telemetry_mode: str = "normal"
    viewpoint_injected: dict | None = None


# ─────────────────────────────────────────────────────────────────────────────
# Corpus construction (180 samples)
# ─────────────────────────────────────────────────────────────────────────────
def build_samples() -> list[Sample]:
    samples: list[Sample] = []
    sid = 0

    def _next() -> int:
        nonlocal sid
        sid += 1
        return sid

    # 1) ONLINE x24 — clean feed, two noise levels
    for sub, sigma in (("sigma2", 2.0), ("sigma3", 3.0)):
        for i in range(12):
            n = _next()
            samples.append(Sample(
                sample_id=f"C2-{n:04d}", cls="ONLINE", subvariant=sub,
                expected_state="ONLINE", n_frames=SEQUENCE_LEN,
                seed=BASE_SEED + 10000 + i,
                params=dict(base_sigma=float(sigma), motion=True),
                telemetry=dict(TELEMETRY["normal"]), telemetry_mode="normal",
            ))

    # 2) DEGRADED x18 — genuine multi-dimension degradation
    for i in range(6):  # blur + network (2 dims: image, network)
        n = _next()
        rng = np.random.default_rng(BASE_SEED + 20000 + i)
        samples.append(Sample(
            sample_id=f"C2-{n:04d}", cls="DEGRADED", subvariant="blur_net",
            expected_state="DEGRADED", n_frames=SEQUENCE_LEN,
            seed=BASE_SEED + 20000 + i,
            params=dict(base_sigma=2.0, motion=True,
                        blur_kernel=int(rng.integers(21, 42)) | 1),
            telemetry=dict(TELEMETRY["net_degraded"]), telemetry_mode="net_degraded",
        ))
    for i in range(6):  # low fps + underexposed (2 dims: stream, image)
        n = _next()
        rng = np.random.default_rng(BASE_SEED + 21000 + i)
        samples.append(Sample(
            sample_id=f"C2-{n:04d}", cls="DEGRADED", subvariant="lowfps_underexposed",
            expected_state="DEGRADED", n_frames=SEQUENCE_LEN,
            seed=BASE_SEED + 21000 + i,
            params=dict(base_sigma=1.5, motion=True,
                        exposure_factor=round(float(rng.uniform(0.05, 0.08)), 4)),
            telemetry=dict(TELEMETRY["low_fps"]), telemetry_mode="low_fps",
        ))
    for i in range(6):  # injected viewpoint shift + network (2 dims: viewpoint, network)
        n = _next()
        samples.append(Sample(
            sample_id=f"C2-{n:04d}", cls="DEGRADED", subvariant="vp_injected_net",
            expected_state="DEGRADED", n_frames=0,
            seed=BASE_SEED + 22000 + i,
            params=dict(),
            telemetry=dict(TELEMETRY["net_degraded"]), telemetry_mode="net_degraded",
            viewpoint_injected=dict(shift_score=0.45, shift_confidence=0.85, inlier_ratio=0.6),
        ))

    # 3) FROZEN x12 — bit-exact duplicate frames, healthy telemetry
    for i in range(12):
        n = _next()
        samples.append(Sample(
            sample_id=f"C2-{n:04d}", cls="FROZEN", subvariant="bitexact",
            expected_state="FROZEN", n_frames=SEQUENCE_LEN,
            seed=BASE_SEED + 30000 + i,
            params=dict(base_sigma=2.0, motion=True),
            telemetry=dict(TELEMETRY["normal"]), telemetry_mode="normal",
        ))

    # 4) BLURRED x18 — mild (11-19) and heavy (21-41) Gaussian blur
    for sub, lo, hi in (("mild", 11, 20), ("heavy", 21, 42)):
        for i in range(9):
            n = _next()
            rng = np.random.default_rng(BASE_SEED + 40000 + i)
            samples.append(Sample(
                sample_id=f"C2-{n:04d}", cls="BLURRED", subvariant=sub,
                expected_state="DEGRADED", n_frames=SEQUENCE_LEN,
                seed=BASE_SEED + 40000 + i,
                params=dict(base_sigma=2.0, motion=True,
                            blur_kernel=int(rng.integers(lo, hi)) | 1),
                telemetry=dict(TELEMETRY["normal"]), telemetry_mode="normal",
            ))

    # 5) OBSTRUCTED x15 — near-black cover 82-90% of frame
    for i in range(15):
        n = _next()
        rng = np.random.default_rng(BASE_SEED + 50000 + i)
        samples.append(Sample(
            sample_id=f"C2-{n:04d}", cls="OBSTRUCTED", subvariant="cover",
            expected_state="DEGRADED", n_frames=SEQUENCE_LEN,
            seed=BASE_SEED + 50000 + i,
            params=dict(base_sigma=2.0, motion=True,
                        cover_fraction=round(float(rng.uniform(0.82, 0.90)), 4),
                        cover_shade=int(rng.integers(8, 26))),
            telemetry=dict(TELEMETRY["normal"]), telemetry_mode="normal",
        ))

    # 6) UNDEREXPOSED x15
    for i in range(15):
        n = _next()
        rng = np.random.default_rng(BASE_SEED + 60000 + i)
        samples.append(Sample(
            sample_id=f"C2-{n:04d}", cls="UNDEREXPOSED", subvariant="dark",
            expected_state="DEGRADED", n_frames=SEQUENCE_LEN,
            seed=BASE_SEED + 60000 + i,
            params=dict(base_sigma=1.5, motion=True,
                        exposure_factor=round(float(rng.uniform(0.03, 0.08)), 4)),
            telemetry=dict(TELEMETRY["normal"]), telemetry_mode="normal",
        ))

    # 7) OVEREXPOSED x15
    for i in range(15):
        n = _next()
        rng = np.random.default_rng(BASE_SEED + 70000 + i)
        samples.append(Sample(
            sample_id=f"C2-{n:04d}", cls="OVEREXPOSED", subvariant="bright",
            expected_state="DEGRADED", n_frames=SEQUENCE_LEN,
            seed=BASE_SEED + 70000 + i,
            params=dict(base_sigma=1.5, motion=True,
                        exposure_factor=round(float(rng.uniform(7.0, 11.0)), 4)),
            telemetry=dict(TELEMETRY["normal"]), telemetry_mode="normal",
        ))

    # 8) SEVERE_COMPRESSION x18 — JPEG quality 3 / 5 / 8
    for q in (3, 5, 8):
        for i in range(6):
            n = _next()
            samples.append(Sample(
                sample_id=f"C2-{n:04d}", cls="SEVERE_COMPRESSION", subvariant=f"q{q}",
                expected_state="DEGRADED", n_frames=SEQUENCE_LEN,
                seed=BASE_SEED + 80000 + q * 100 + i,
                params=dict(base_sigma=2.0, motion=True, jpeg_quality=q),
                telemetry=dict(TELEMETRY["normal"]), telemetry_mode="normal",
            ))

    # 9) VIEWPOINT_CHANGED x15 — moderate x9 / severe x6 warps
    for sub, tx_r, rot_r, zoom_r, count in (
        ("moderate", (55, 95), (0.5, 3.0), (1.00, 1.06), 9),
        ("severe", (110, 160), (4.0, 8.0), (1.12, 1.25), 6),
    ):
        for i in range(count):
            n = _next()
            rng = np.random.default_rng(BASE_SEED + 90000 + i)
            samples.append(Sample(
                sample_id=f"C2-{n:04d}", cls="VIEWPOINT_CHANGED", subvariant=sub,
                expected_state="DEGRADED", n_frames=VIEWPOINT_SEQ_LEN,
                seed=BASE_SEED + 90000 + i,
                params=dict(base_sigma=2.0, motion=False,
                            warp_tx=round(float(rng.uniform(*tx_r)), 2),
                            warp_ty=round(float(rng.uniform(-8, 9)), 2),
                            warp_rot=round(float(rng.uniform(*rot_r)), 3),
                            warp_zoom=round(float(rng.uniform(*zoom_r)), 4)),
                telemetry=dict(TELEMETRY["normal"]), telemetry_mode="normal",
            ))

    # 10) COVERAGE_COMPROMISED x12 — disconnected (9 plain, 3 + heartbeat lost)
    for i in range(9):
        n = _next()
        samples.append(Sample(
            sample_id=f"C2-{n:04d}", cls="COVERAGE_COMPROMISED", subvariant="disc",
            expected_state="OFFLINE", n_frames=SEQUENCE_LEN,
            seed=BASE_SEED + 100000 + i,
            params=dict(base_sigma=2.0, motion=True),
            telemetry=dict(TELEMETRY["disconnected"]), telemetry_mode="disconnected",
        ))
    for i in range(3):
        n = _next()
        samples.append(Sample(
            sample_id=f"C2-{n:04d}", cls="COVERAGE_COMPROMISED", subvariant="disc_hb",
            expected_state="OFFLINE", n_frames=SEQUENCE_LEN,
            seed=BASE_SEED + 101000 + i,
            params=dict(base_sigma=2.0, motion=True),
            telemetry=dict(TELEMETRY["disconnected_offline"]),
            telemetry_mode="disconnected_offline",
        ))

    # 11) STALE_FEED x6 — healthy visuals, source timestamp 40-55s old
    for i in range(6):
        n = _next()
        rng = np.random.default_rng(BASE_SEED + 110000 + i)
        samples.append(Sample(
            sample_id=f"C2-{n:04d}", cls="STALE_FEED", subvariant="old_ts",
            expected_state="STALE", n_frames=SEQUENCE_LEN,
            seed=BASE_SEED + 110000 + i,
            params=dict(base_sigma=2.0, motion=True),
            telemetry=dict(TELEMETRY["stale"], source_age_sec=round(float(rng.uniform(40, 56)), 1)),
            telemetry_mode="stale",
        ))

    # 12) STREAM_DROP_FROZEN x6 — healthy visuals, frame_drop_rate 0.55-0.90
    for i in range(6):
        n = _next()
        rng = np.random.default_rng(BASE_SEED + 120000 + i)
        samples.append(Sample(
            sample_id=f"C2-{n:04d}", cls="STREAM_DROP_FROZEN", subvariant="drop",
            expected_state="FROZEN", n_frames=SEQUENCE_LEN,
            seed=BASE_SEED + 120000 + i,
            params=dict(base_sigma=2.0, motion=True),
            telemetry=dict(TELEMETRY["stream_drop"],
                           frame_drop_rate=round(float(rng.uniform(0.55, 0.91)), 4)),
            telemetry_mode="stream_drop",
        ))

    # 13) LOW_FPS_SINGLE_DIM x6 — one degraded dimension only (documented UNKNOWN row)
    for i in range(6):
        n = _next()
        rng = np.random.default_rng(BASE_SEED + 130000 + i)
        samples.append(Sample(
            sample_id=f"C2-{n:04d}", cls="LOW_FPS_SINGLE_DIM", subvariant="lowfps",
            expected_state="UNKNOWN", n_frames=SEQUENCE_LEN,
            seed=BASE_SEED + 130000 + i,
            params=dict(base_sigma=2.0, motion=True),
            telemetry=dict(TELEMETRY["low_fps"],
                           observed_fps=round(float(rng.uniform(8.0, 11.5)), 1)),
            telemetry_mode="low_fps",
        ))

    return samples


# ─────────────────────────────────────────────────────────────────────────────
# Deterministic materialization
# ─────────────────────────────────────────────────────────────────────────────
def materialize_frames(sample: Sample) -> list[np.ndarray]:
    """Render sample frames deterministically from (seed, params)."""
    if sample.n_frames == 0:
        return []

    rng = np.random.default_rng(sample.seed)
    p = sample.params
    base_sigma = float(p.get("base_sigma", 2.0))
    motion = bool(p.get("motion", True))

    frames: list[np.ndarray] = []

    if sample.cls == "FROZEN":
        # Single rendered frame, bit-exact duplicates (encoder-frozen feed)
        base = make_base_scene(rng)
        f0 = add_motion_blob(base, rng, 0.5) if motion else base
        f0 = add_sensor_noise(f0, rng, base_sigma)
        return [f0.copy() for _ in range(sample.n_frames)]

    if sample.cls == "VIEWPOINT_CHANGED":
        base = make_base_scene(rng)
        f0 = add_sensor_noise(base, rng, base_sigma)
        frames.append(f0)
        for _ in range(1, sample.n_frames):
            fw = warp_viewpoint(
                f0,
                tx=float(p["warp_tx"]), ty=float(p["warp_ty"]),
                rot_deg=float(p["warp_rot"]), zoom=float(p["warp_zoom"]),
            )
            frames.append(fw)
        return frames

    for i in range(sample.n_frames):
        base = make_base_scene(rng)
        if motion:
            base = add_motion_blob(base, rng, x_pos=(0.08 + i * 0.06) % 1.0)

        f = base
        if "exposure_factor" in p:
            f = apply_exposure(f, float(p["exposure_factor"]))
        if "blur_kernel" in p:
            f = apply_blur(f, int(p["blur_kernel"]))
        if "jpeg_quality" in p:
            f = apply_compression(f, int(p["jpeg_quality"]))

        f = add_sensor_noise(f, rng, base_sigma)

        if "cover_fraction" in p:
            f = apply_obstruction(f, float(p["cover_fraction"]), int(p["cover_shade"]))

        frames.append(f)

    return frames


# ─────────────────────────────────────────────────────────────────────────────
# Manifest
# ─────────────────────────────────────────────────────────────────────────────
def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def build_manifest() -> dict:
    samples = build_samples()
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
        corpus=CORPUS_NAME, version=CORPUS_VERSION,
        spec_classes_ten=["ONLINE", "DEGRADED", "FROZEN", "BLURRED", "OBSTRUCTED",
                          "UNDEREXPOSED", "OVEREXPOSED", "SEVERE_COMPRESSION",
                          "VIEWPOINT_CHANGED", "COVERAGE_COMPROMISED"],
        supplementary_classes=["STALE_FEED", "STREAM_DROP_FROZEN", "LOW_FPS_SINGLE_DIM"],
        frame_w=FRAME_W, frame_h=FRAME_H,
        sequence_len=SEQUENCE_LEN, viewpoint_seq_len=VIEWPOINT_SEQ_LEN,
        base_seed=BASE_SEED, n_samples=len(samples), class_counts=counts,
        generator_sha256=sha256_file(Path(__file__)),
        samples=rows,
    )
    payload_bytes = json.dumps(payload, indent=2, sort_keys=True).encode("utf-8")
    manifest = dict(payload)
    manifest["manifest_sha256"] = hashlib.sha256(payload_bytes).hexdigest()
    return manifest


def main():
    manifest = build_manifest()
    raw = json.dumps(manifest, indent=2, sort_keys=True).encode("utf-8")
    MANIFEST_PATH.write_bytes(raw)
    print(f"samples={manifest['n_samples']}")
    for cls, c in sorted(manifest["class_counts"].items()):
        print(f"  {cls:24s} {c}")
    print(f"manifest_sha256={manifest['manifest_sha256']}")
    print(f"wrote {MANIFEST_PATH.name}")


if __name__ == "__main__":
    main()
