# -*- coding: utf-8 -*-
# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — C2 Camera Health Benchmark Corpus Generator
# PRHAAR-C2-CAMERA-HEALTH-BENCH v1  (spec §67 classical-CV benchmark corpus)
#
# Deterministic synthetic image corpus for benchmarking the EXISTING classical
# CV camera-health approach. No learned model is trained here (spec §67).
#
# §68 benchmark classes: ONLINE, DEGRADED, FROZEN, BLURRED, OBSTRUCTED,
# UNDEREXPOSED, OVEREXPOSED, SEVERE_COMPRESSION, VIEWPOINT_CHANGED,
# COVERAGE_COMPROMISED.
# Supplementary state-coverage rows (documented, beyond §68):
# STALE_FEED, STREAM_DROP_FROZEN, LOW_FPS_SINGLE_DIM.
#
# All pixels derive from seeded numpy RNGs -> fully regenerable.
# No real video, no downloaded data (spec §8).
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

FRAME_W = 320
FRAME_H = 180
SEQUENCE_LEN = 12          # frames per sequence sample (freeze persistence=10 needs >= 11 analyzed)
VIEWPOINT_SEQ_LEN = 8      # 1 reference + 7 warped (detector persistence=5)
BASE_SEED = 20260930

OUT_DIR = Path(__file__).resolve().parent
MANIFEST_PATH = OUT_DIR / "c2_corpus_manifest_v1.json"


# ─────────────────────────────────────────────────────────────────────────────
# Base scene synthesis (border outpost: sky/ground, fence posts, wires, texture)
# ─────────────────────────────────────────────────────────────────────────────
def make_base_scene(rng: np.random.Generator) -> np.ndarray:
    """Deterministic synthetic border-watch scene, BGR uint8 (FRAME_H, FRAME_W, 3)."""
    h, w = FRAME_H, FRAME_W
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)

    # Sky gradient (top ~55%) + ground gradient
    sky_line = int(h * 0.55)
    img = np.zeros((h, w, 3), np.float32)
    for y in range(h):
        if y < sky_line:
            t = y / sky_line
            img[y, :] = [90 + 70 * t, 140 + 40 * t, 170 + 30 * t]  # B,G,R
        else:
            t = (y - sky_line) / (h - sky_line)
            img[y, :] = [60 - 20 * t, 95 - 35 * t, 80 - 30 * t]

    # Distant tree/bush blobs on horizon (varied brightness patches)
    n_bush = int(rng.integers(6, 10))
    for _ in range(n_bush):
        cx = int(rng.integers(0, w))
        cw = int(rng.integers(14, 46))
        ch = int(rng.integers(6, 16))
        cy = sky_line - ch // 2 + int(rng.integers(-3, 4))
        x0, x1 = max(0, cx - cw // 2), min(w, cx + cw // 2)
        y0, y1 = max(0, cy - ch // 2), min(h, cy + ch // 2)
        tone = int(rng.integers(30, 70))
        img[y0:y1, x0:x1] = [tone * 0.6, tone, tone * 0.8]

    # Fence posts (vertical high-contrast bars) + 3 horizontal wires
    posts = np.linspace(8, w - 8, 9).astype(int) + rng.integers(-3, 4, 9)
    for px in posts:
        img[max(0, sky_line - 26):h, max(0, px - 1):px + 2] = [40, 45, 50]
    for wy in (sky_line + 8, sky_line + 22, sky_line + 38):
        img[wy:wy + 1, :] = [35, 40, 45]

    # Gravel/texture patches on ground (speckle)
    n_tex = int(rng.integers(120, 200))
    for _ in range(n_tex):
        cx = int(rng.integers(0, w))
        cy = int(rng.integers(sky_line + 4, h))
        tone = float(rng.normal(85, 25))
        img[cy, cx] = [tone * 0.9, tone, tone * 0.85]

    # Guard hut silhouette (structured object, good ORB corners)
    hx0, hx1 = int(w * 0.68), int(w * 0.86)
    hy0, hy1 = sky_line - 30, sky_line + 26
    img[hy0:hy1, hx0:hx1] = [55, 60, 65]
    img[hy0:hy0 + 2, hx0:hx1] = [30, 32, 35]

    return np.clip(img, 0, 255).astype(np.uint8)


def add_sensor_noise(frame: np.ndarray, rng: np.random.Generator, sigma: float) -> np.ndarray:
    if sigma <= 0:
        return frame.copy()
    noise = rng.normal(0.0, sigma, frame.shape).astype(np.float32)
    out = frame.astype(np.float32) + noise
    return np.clip(out, 0, 255).astype(np.uint8)


def add_motion_blob(frame: np.ndarray, rng: np.random.Generator, x_pos: float) -> np.ndarray:
    """A small vehicle-like blob moving horizontally (content change across frames)."""
    out = frame.copy()
    h, w = out.shape[:2]
    bw, bh = 26, 12
    x0 = int(x_pos * (w - bw))
    y0 = int(h * 0.72)
    out[y0:y0 + bh, x0:x0 + bw] = [25, 25, 28]          # body
    out[y0 + bh - 3:y0 + bh, x0 + 3:x0 + bw - 3] = [15, 15, 15]  # shadow/underbody
    return out


def apply_blur(frame: np.ndarray, rng: np.random.Generator, sigma: float) -> np.ndarray:
    import cv2
    k = int(rng.integers(21, 41)) | 1  # odd kernel
    return cv2.GaussianBlur(frame, (k, k), sigma)


def apply_obstruction(frame: np.ndarray, rng: np.random.Generator, cover: float) -> np.ndarray:
    """Near-black occlusion over `cover` fraction of frame area (lens blocked)."""
    out = frame.copy()
    h, w = out.shape[:2]
    bh, bw = int(h * np.sqrt(cover) * 1.15), int(w * np.sqrt(cover) * 1.15)
    y0 = int(rng.integers(0, max(1, h - bh)))
    x0 = int(rng.integers(0, max(1, w - bw)))
    shade = int(rng.integers(0, 3))
    out[y0:y0 + bh, x0:x0 + bw] = shade
    return out


def apply_exposure(frame: np.ndarray, rng: np.random.Generator, mode: str, factor: float) -> np.ndarray:
    out = frame.astype(np.float32) * factor
    return np.clip(out, 0, 255).astype(np.uint8)


def apply_compression(frame: np.ndarray, rng: np.random.Generator, quality: int) -> np.ndarray:
    import cv2
    ok, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, int(quality)])
    if not ok:
        raise RuntimeError("JPEG encode failed")
    return cv2.imdecode(buf, cv2.IMREAD_COLOR)


def warp_viewpoint(frame: np.ndarray, rng: np.random.Generator,
                   tx: float, ty: float, rot_deg: float, zoom: float) -> np.ndarray:
    import cv2
    h, w = frame.shape[:2]
    theta = np.deg2rad(rot_deg)
    M = np.float32([
        [zoom * np.cos(theta), -zoom * np.sin(theta), tx],
        [zoom * np.sin(theta),  zoom * np.cos(theta), ty],
    ])
    return cv2.warpAffine(frame, M, (w, h), flags=cv2.INTER_LINEAR,
                          borderMode=cv2.BORDER_CONSTANT, borderValue=(0, 0, 0))


# ─────────────────────────────────────────────────────────────────────────────
# Telemetry recipes (documented per class; deterministic jitter from seed)
# ─────────────────────────────────────────────────────────────────────────────
def _j(rng, lo, hi):
    return round(float(rng.uniform(lo, hi)), 3)


def telemetry_normal(rng) -> dict:
    return dict(connected=True, observed_fps=_j(rng, 24.0, 25.5),
                frame_drop_rate=_j(rng, 0.0, 0.01),
                latency_ms=_j(rng, 22, 70), latency_variance_ms=_j(rng, 2, 15),
                packet_loss_percent=_j(rng, 0.0, 0.3), heartbeat_age_sec=_j(rng, 0.5, 4),
                source_age_sec=_j(rng, 0.5, 3))


def telemetry_net_degraded(rng) -> dict:
    t = telemetry_normal(rng)
    t.update(latency_ms=_j(rng, 240, 430), latency_variance_ms=_j(rng, 110, 230),
             packet_loss_percent=_j(rng, 1.2, 3.0), heartbeat_age_sec=_j(rng, 4, 25))
    return t


def telemetry_net_offline(rng) -> dict:
    t = telemetry_normal(rng)
    t.update(heartbeat_age_sec=_j(rng, 150, 400), latency_ms=_j(rng, 350, 900),
             packet_loss_percent=_j(rng, 2, 8))
    return t


def telemetry_low_fps(rng) -> dict:
    t = telemetry_normal(rng)
    t.update(observed_fps=_j(rng, 7, 11), frame_drop_rate=_j(rng, 0.15, 0.35))
    return t


def telemetry_stream_drop(rng) -> dict:
    t = telemetry_normal(rng)
    t.update(frame_drop_rate=_j(rng, 0.55, 0.9))
    return t


def telemetry_stale(rng) -> dict:
    t = telemetry_normal(rng)
    t.update(source_age_sec=_j(rng, 40, 55))
    return t


def telemetry_disconnected(rng) -> dict:
    return dict(connected=False, observed_fps=0.0, frame_drop_rate=1.0,
                latency_ms=None, latency_variance_ms=None, packet_loss_percent=None,
                heartbeat_age_sec=_j(rng, 0.5, 5), source_age_sec=_j(rng, 0.5, 3))


# ─────────────────────────────────────────────────────────────────────────────
# Sample construction
# ─────────────────────────────────────────────────────────────────────────────
@dataclass
class Sample:
    sample_id: str
    cls: str                       # §68 class or supplementary row name
    subvariant: str
    expected_state: str            # operational expectation (documented mapping)
    n_frames: int
    seed: int
    params: dict = field(default_factory=dict)
    telemetry: dict = field(default_factory=dict)
    telemetry_mode: str = "normal"
    viewpoint_injected: dict | None = None   # agent-reported viewpoint metrics (frame=None)


def build_samples() -> list[Sample]:
    samples: list[Sample] = []
    seq = 0

    def nxt(cls, sub, expected, n_frames, seed, params, tmode="normal", t=None, vp=None):
        nonlocal seq
        seq += 1
        samples.append(Sample(
            sample_id=f"C2-{seq:04d}", cls=cls, subvariant=sub, expected_state=expected,
            n_frames=n_frames, seed=seed, params=params, telemetry=t or {},
            telemetry_mode=tmode, viewpoint_injected=vp))

    # 1. ONLINE — quiet border scene, sensor noise σ sweep + small motion blob
    for i, sigma in enumerate([2.0, 3.0]):
        for j in range(12):
            nxt("ONLINE", f"noise_sigma_{sigma}", "ONLINE", SEQUENCE_LEN,
                BASE_SEED + seq, dict(noise_sigma=sigma, motion=True, blob_speed=_j(np.random.default_rng(BASE_SEED + seq), 0.03, 0.09)))

    # 2. DEGRADED — genuinely >=2 degraded dimensions (engine's own threshold)
    for j in range(6):   # (a) blurred image + degraded network
        nxt("DEGRADED", "blur_plus_network", "DEGRADED", SEQUENCE_LEN, BASE_SEED + seq,
            dict(blur_sigma=12.0), tmode="net_degraded")
    for j in range(6):   # (b) low FPS stream + underexposed image
        nxt("DEGRADED", "lowfps_plus_underexposed", "DEGRADED", SEQUENCE_LEN, BASE_SEED + seq,
            dict(exposure_factor=0.05), tmode="low_fps")
    # (c) agent-reported moderate viewpoint shift + degraded network (frame=None; shift from component detector)
    for j in range(6):
        nxt("DEGRADED", "viewpoint_shift_plus_network", "DEGRADED", 0, BASE_SEED + seq,
            dict(), tmode="net_degraded", vp=dict(shift_score=0.45, shift_confidence=0.8, inlier_ratio=0.8))

    # 3. FROZEN — encoder repeats last frame bit-exact; timestamps advance
    for j in range(12):
        nxt("FROZEN", "pixel_frozen_normal_telemetry", "FROZEN", SEQUENCE_LEN, BASE_SEED + seq,
            dict(noise_sigma=0.0, frozen=True))

    # 4. BLURRED — defocused lens
    for j in range(18):
        nxt("BLURRED", "gaussian_defocus", "DEGRADED", SEQUENCE_LEN, BASE_SEED + seq,
            dict(blur_sigma=float(np.random.default_rng(BASE_SEED + seq).uniform(8, 20))))

    # 5. OBSTRUCTED — near-black occlusion covering most of the frame
    for j in range(15):
        nxt("OBSTRUCTED", "lens_blocked", "DEGRADED", SEQUENCE_LEN, BASE_SEED + seq,
            dict(cover=float(np.random.default_rng(BASE_SEED + seq).uniform(0.82, 0.9)), noise_sigma=2.0))

    # 6. UNDEREXPOSED
    for j in range(15):
        nxt("UNDEREXPOSED", "dark_frame", "DEGRADED", SEQUENCE_LEN, BASE_SEED + seq,
            dict(exposure_factor=float(np.random.default_rng(BASE_SEED + seq).uniform(0.03, 0.08)), noise_sigma=2.0))

    # 7. OVEREXPOSED
    for j in range(15):
        nxt("OVEREXPOSED", "saturated_frame", "DEGRADED", SEQUENCE_LEN, BASE_SEED + seq,
            dict(exposure_factor=float(np.random.default_rng(BASE_SEED + seq).uniform(7.0, 11.0)), noise_sigma=2.0))

    # 8. SEVERE_COMPRESSION — heavy JPEG artifacts
    for q in (3, 5, 8):
        for j in range(6):
            nxt("SEVERE_COMPRESSION", f"jpeg_q{q}", "DEGRADED", SEQUENCE_LEN, BASE_SEED + seq,
                dict(jpeg_quality=q, noise_sigma=2.0))

    # 9. VIEWPOINT_CHANGED — geometric warp vs reference (moderate + severe)
    for j in range(9):   # moderate pan
        rng = np.random.default_rng(BASE_SEED + seq)
        nxt("VIEWPOINT_CHANGED", "moderate_pan", "DEGRADED", VIEWPOINT_SEQ_LEN, BASE_SEED + seq,
            dict(tx=_j(rng, 55, 95), ty=_j(rng, -8, 8), rot_deg=_j(rng, 0.5, 3.0),
                 zoom=_j(rng, 1.0, 1.06), noise_sigma=2.0))
    for j in range(6):   # severe pan + zoom
        rng = np.random.default_rng(BASE_SEED + seq)
        nxt("VIEWPOINT_CHANGED", "severe_pan_zoom", "DEGRADED", VIEWPOINT_SEQ_LEN, BASE_SEED + seq,
            dict(tx=_j(rng, 110, 160), ty=_j(rng, -15, 15), rot_deg=_j(rng, 4.0, 8.0),
                 zoom=_j(rng, 1.12, 1.25), noise_sigma=2.0))

    # 10. COVERAGE_COMPROMISED — feed lost / heartbeat lost
    for j in range(9):
        nxt("COVERAGE_COMPROMISED", "stream_disconnected", "OFFLINE", 0, BASE_SEED + seq,
            dict(), tmode="disconnected")
    for j in range(3):
        nxt("COVERAGE_COMPROMISED", "disconnected_plus_heartbeat_lost", "OFFLINE", 0, BASE_SEED + seq,
            dict(), tmode="disconnected_offline")

    # Supplementary state-coverage rows (documented beyond §68)
    for j in range(6):
        nxt("STALE_FEED", "frames_stale_40_55s", "STALE", SEQUENCE_LEN, BASE_SEED + seq,
            dict(noise_sigma=2.0, motion=True, blob_speed=0.06), tmode="stale")
    for j in range(6):
        nxt("STREAM_DROP_FROZEN", "drop_rate_0.55_0.9", "FROZEN", SEQUENCE_LEN, BASE_SEED + seq,
            dict(noise_sigma=2.0, motion=True, blob_speed=0.06), tmode="stream_drop")
    for j in range(6):
        nxt("LOW_FPS_SINGLE_DIM", "fps_7_11_only", "UNKNOWN", SEQUENCE_LEN, BASE_SEED + seq,
            dict(noise_sigma=2.0, motion=True, blob_speed=0.06), tmode="low_fps")

    return samples


TELEMETRY_FUNCS = {
    "normal": telemetry_normal,
    "net_degraded": telemetry_net_degraded,
    "net_offline": telemetry_net_offline,
    "low_fps": telemetry_low_fps,
    "stream_drop": telemetry_stream_drop,
    "stale": telemetry_stale,
    "disconnected": telemetry_disconnected,
    "disconnected_offline": lambda rng: {**telemetry_disconnected(rng),
                                         **{k: v for k, v in telemetry_net_offline(rng).items() if k.startswith("heartbeat") or k.startswith("latency") or k.startswith("packet")}},
}


def materialize_frames(sample: Sample) -> list[np.ndarray]:
    """Generate the frame sequence for a sample (deterministic from sample.seed)."""
    if sample.n_frames == 0:
        return []
    rng = np.random.default_rng(sample.seed)
    base = make_base_scene(rng)
    frames: list[np.ndarray] = []
    p = sample.params
    sigma = float(p.get("noise_sigma", 2.0))

    if sample.cls == "FROZEN" or p.get("frozen"):
        f0 = add_sensor_noise(base, rng, sigma)
        return [f0.copy() for _ in range(sample.n_frames)]

    for i in range(sample.n_frames):
        f = base.copy()
        if p.get("motion", False):
            speed = float(p.get("blob_speed", 0.06))
            f = add_motion_blob(f, rng, x_pos=(i * speed) % 1.0)
        if "exposure_factor" in p:
            f = apply_exposure(f, rng, "scale", float(p["exposure_factor"]))
        if "blur_sigma" in p:
            f = apply_blur(f, rng, float(p["blur_sigma"]))
        if "cover" in p:
            f = apply_obstruction(f, rng, float(p["cover"]))
        if "jpeg_quality" in p:
            f = apply_compression(f, rng, int(p["jpeg_quality"]))
        if i == 0 or sample.cls != "VIEWPOINT_CHANGED":
            # non-viewpoint classes: independent per-frame sensor noise
            f = add_sensor_noise(f, rng, sigma)
        frames.append(f)

    if sample.cls == "VIEWPOINT_CHANGED":
        ref = frames[0]
        warped = [ref]
        for i in range(1, sample.n_frames):
            w = warp_viewpoint(ref, rng, tx=float(p["tx"]), ty=float(p["ty"]),
                               rot_deg=float(p["rot_deg"]), zoom=float(p["zoom"]))
            warped.append(add_sensor_noise(w, rng, sigma))
        return warped

    return frames


def build_manifest(samples: list[Sample]) -> dict:
    rows = []
    for s in samples:
        rng = np.random.default_rng(s.seed)
        tel = dict(TELEMETRY_FUNCS[s.telemetry_mode](rng))
        s.telemetry = tel
        rows.append(dict(sample_id=s.sample_id, cls=s.cls, subvariant=s.subvariant,
                         expected_state=s.expected_state, n_frames=s.n_frames,
                         seed=s.seed, params=s.params, telemetry_mode=s.telemetry_mode,
                         telemetry=tel, viewpoint_injected=s.viewpoint_injected))
    manifest = dict(
        corpus_name="PRHAAR-C2-CAMERA-HEALTH-BENCH",
        version="v1",
        generated_at=datetime.now(timezone.utc).isoformat(),
        frame_w=FRAME_W, frame_h=FRAME_H, base_seed=BASE_SEED,
        classes=sorted({s.cls for s in samples}),
        n_samples=len(samples),
        notes=[
            "Deterministic synthetic corpus; regenerable from gen_c2_corpus.py.",
            "No real video or downloaded data (spec §8).",
            "expected_state = operational expectation documented in C2 report; "
            "it is the benchmark's mapping decision, not a spec-quoted engine contract.",
        ],
        samples=rows,
    )
    return manifest


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> dict:
    samples = build_samples()
    manifest = build_manifest(samples)
    text = json.dumps(manifest, indent=2, sort_keys=True)
    raw = text.encode("utf-8")
    MANIFEST_PATH.write_bytes(raw)
    manifest["manifest_sha256"] = hashlib.sha256(raw).hexdigest()
    gen_sha = sha256_file(Path(__file__).resolve())
    manifest["generator_sha256"] = gen_sha

    counts: dict[str, int] = {}
    for s in samples:
        counts[s.cls] = counts.get(s.cls, 0) + 1
    print(f"samples: {len(samples)}")
    for k in sorted(counts):
        print(f"  {k:24s} {counts[k]}")
    print(f"manifest: {MANIFEST_PATH.name}  sha256={manifest['manifest_sha256']}")
    print(f"generator sha256={gen_sha}")
    return manifest


if __name__ == "__main__":
    main()
