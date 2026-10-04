#!/usr/bin/env python
"""
PRHAAR C5 -- synthetic mini-dataset generator (TEST UTILITY, not pipeline).

Purpose: exercise train_detector.py / eval_detector.py wiring without touching
any real dataset (no contamination concerns, runs in seconds). Generates a
tiny valid YOLO dataset with the C5 taxonomy class names, drawing simple
colored rectangles for PERSON / MOTORCYCLE / CAR over deterministic noisy
backgrounds.

Output (default datasets/_synthetic_smoke/):
    images/{train,val}/*.jpg, labels/{train,val}/*.txt, data.yaml

The resulting checkpoints are plumbing artifacts only -- train_detector.py
refuses to copy "dryrun*" runs into the candidate checkpoint store, and dry
runs are never appended to C5_EXPERIMENT_LOG.csv.

Usage:
    python scripts/make_synthetic_dataset.py [--out datasets/_synthetic_smoke]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import numpy as np
    from PIL import Image, ImageDraw
except ImportError as e:  # pragma: no cover
    print(f"FATAL: missing dependency: {e}", file=sys.stderr)
    sys.exit(2)

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parent))
from c5_taxonomy import CLASSES  # noqa: E402

C5_ROOT = HERE.parents[1]
DEFAULT_OUT = C5_ROOT / "datasets" / "_synthetic_smoke"

# class index -> draw color (PERSON=0, MOTORCYCLE=1, BICYCLE=2 used; others omitted)
DRAW_PLAN = {0: (220, 40, 40), 1: (40, 220, 40), 2: (40, 40, 220)}
N_TRAIN, N_VAL = 16, 6
IMG_W, IMG_H = 640, 640


def make_image(rng: np.random.Generator, boxes):
    bg = rng.integers(90, 140, size=(IMG_H, IMG_W, 3), dtype=np.uint8)
    noise = rng.integers(-25, 26, size=(IMG_H, IMG_W, 3), dtype=np.int16)
    arr = np.clip(bg.astype(np.int16) + noise, 0, 255).astype(np.uint8)
    img = Image.fromarray(arr)
    draw = ImageDraw.Draw(img)
    lines = []
    for cid, (x1, y1, x2, y2) in boxes:
        draw.rectangle([x1, y1, x2, y2], fill=DRAW_PLAN[cid], outline=(255, 255, 255))
        cx, cy = (x1 + x2) / 2 / IMG_W, (y1 + y2) / 2 / IMG_H
        w, h = (x2 - x1) / IMG_W, (y2 - y1) / IMG_H
        lines.append(f"{cid} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
    return img, lines


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    out: Path = args.out
    if out.exists():
        print(f"FATAL: {out} exists -- delete it first (no silent overwrite)", file=sys.stderr)
        return 2
    rng = np.random.default_rng(args.seed)

    for split, n in (("train", N_TRAIN), ("val", N_VAL)):
        (out / "images" / split).mkdir(parents=True)
        (out / "labels" / split).mkdir(parents=True)
        for i in range(n):
            boxes = []
            for cid in DRAW_PLAN:
                if rng.random() < 0.8:  # most images have most classes
                    w = int(rng.integers(48, 160))
                    h = int(rng.integers(48, 160))
                    x1 = int(rng.integers(0, IMG_W - w))
                    y1 = int(rng.integers(0, IMG_H - h))
                    boxes.append((cid, (x1, y1, x1 + w, y1 + h)))
            img, lines = make_image(rng, boxes)
            img.save(out / "images" / split / f"synthetic_{split}_{i:03d}.jpg", quality=90)
            (out / "labels" / split / f"synthetic_{split}_{i:03d}.txt").write_text(
                "\n".join(lines) + "\n", encoding="utf-8")

    (out / "data.yaml").write_text(
        "# synthetic plumbing-test dataset (NOT training data) -- make_synthetic_dataset.py\n"
        f"path: {out.as_posix()}\n"
        "train: images/train\nval: images/val\ntest: images/val\n"
        f"nc: {len(CLASSES)}\nnames:\n"
        + "".join(f"  {i}: {c}\n" for i, c in enumerate(CLASSES)),
        encoding="utf-8")

    print(f"synthetic dataset -> {out} ({N_TRAIN} train / {N_VAL} val)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
