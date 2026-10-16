#!/usr/bin/env python
"""PRHAAR C5 #33 prep -- dataset composition profile (CPU-only).

Measures the PRHAAR-C5-DETECTION composition BEFORE any error analysis:
per-class box/image counts, COCO box-size buckets on REAL image dims
(small <32^2 px, medium <96^2 px, large >=96^2), per-source split via the
filename prefix the composite build stamped (oi__/ars__/pbd__/...),
boxes-per-image histogram, box aspect-ratio buckets.

Every number here is measured from label files + image headers on this
run (spec 61/62). Nothing is estimated. No GPU is touched -- safe to run
while training occupies the GPU.

Output: reports/error_analysis/dataset_profile.json
"""

from __future__ import annotations

import json
import logging
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

try:
    from PIL import Image
except ImportError:
    Image = None

C5_ROOT = Path(__file__).resolve().parents[1]
DATA_YAML = C5_ROOT / "datasets" / "PRHAAR-C5-DETECTION" / "data.yaml"
OUT = C5_ROOT / "reports" / "error_analysis" / "dataset_profile.json"

SIZE_EDGES = (32.0, 96.0)  # COCO px thresholds
AR_BUCKETS = ((0.5, "tall<0.5"), (1.0, "square~1"), (2.0, "wide1-2"), (float("inf"), "verywide>2"))
BPI_BUCKETS = ((1, "1"), (2, "2"), (3, "3"), (4, "4"), (5, "5"), (10, "6-10"), (10**9, "11+"))

LOG = logging.getLogger("dataset_profile")


def size_bucket(px_area: float) -> str:
    if px_area < SIZE_EDGES[0] ** 2:
        return "small"
    if px_area < SIZE_EDGES[1] ** 2:
        return "medium"
    return "large"


def ar_bucket(ratio: float) -> str:
    for edge, name in AR_BUCKETS:
        if ratio < edge:
            return name
    return AR_BUCKETS[-1][1]


def bpi_bucket(n: int) -> str:
    for edge, name in BPI_BUCKETS:
        if n <= edge:
            return name
    return BPI_BUCKETS[-1][1]


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    if Image is None:
        LOG.error("PIL unavailable -- cannot measure real image dims (no silent fallback, spec 46)")
        return 2

    y = yaml.safe_load(DATA_YAML.read_text(encoding="utf-8"))
    names = y["names"]
    if isinstance(names, dict):
        names = [names[k] for k in sorted(names)]
    root = Path(y["path"])

    profile = {"dataset": "PRHAAR-C5-DETECTION", "splits": {}}
    totals = Counter()

    for split in ("train", "val", "test"):
        img_dir = (root / y[split]).resolve()
        lab_dir = (root / "labels" / split).resolve()
        if not lab_dir.is_dir():
            LOG.error("labels dir missing for %s: %s", split, lab_dir)
            return 2

        per_class = {c: {"boxes": 0, "images": 0, "size": Counter(),
                         "ar": Counter()} for c in names}
        sources = Counter()
        bpi = Counter()
        n_images = 0
        n_boxes = 0
        corrupt_labels = 0

        stems = sorted(p.stem for p in lab_dir.glob("*.txt"))
        for i, stem in enumerate(stems):
            if i and i % 5000 == 0:
                LOG.info("%s: %d/%d", split, i, len(stems))
            src = stem.split("__", 1)[0] if "__" in stem else stem[:12]
            sources[src] += 1
            n_images += 1

            img_path = img_dir / f"{stem}.jpg"
            if not img_path.is_file():
                img_path = next(img_dir.glob(f"{stem}.*"), None)
            if img_path is None or not Path(img_path).is_file():
                LOG.warning("image missing for stem %s -- skipped for px buckets", stem)
                W = H = None
            else:
                with Image.open(img_path) as im:
                    W, H = im.size

            try:
                lines = (lab_dir / f"{stem}.txt").read_text(encoding="utf-8").splitlines()
            except Exception as e:  # noqa: BLE001
                LOG.warning("label unreadable %s: %s", stem, e)
                corrupt_labels += 1
                lines = []

            seen_classes = set()
            for ln in lines:
                ln = ln.strip()
                if not ln:
                    continue
                parts = ln.split()
                if len(parts) != 5:
                    corrupt_labels += 1
                    continue
                try:
                    cls = int(float(parts[0]))
                    bw, bh = float(parts[3]), float(parts[4])
                except ValueError:
                    corrupt_labels += 1
                    continue
                if cls < 0 or cls >= len(names):
                    corrupt_labels += 1
                    continue
                cname = names[cls]
                per_class[cname]["boxes"] += 1
                seen_classes.add(cname)
                n_boxes += 1
                if W and H:
                    px_area = (bw * W) * (bh * H)
                    per_class[cname]["size"][size_bucket(px_area)] += 1
                r = (bw * W) / max(bh * H, 1e-9) if W and H else None
                if r:
                    per_class[cname]["ar"][ar_bucket(r)] += 1

            bpi[bpi_bucket(len(lines))] += 1
            for c in seen_classes:
                per_class[c]["images"] += 1

        split_out = {
            "images": n_images,
            "boxes": n_boxes,
            "corrupt_label_lines": corrupt_labels,
            "sources_images": dict(sources),
            "boxes_per_image": dict(bpi),
            "per_class": {
                c: {"boxes": d["boxes"], "images_with_class": d["images"],
                    "size_buckets_px": dict(d["size"]),
                    "aspect_buckets": dict(d["ar"])}
                for c, d in per_class.items()
            },
        }
        profile["splits"][split] = split_out
        totals["images"] += n_images
        totals["boxes"] = totals.get("boxes", 0) + n_boxes
        LOG.info("%s done: %d images / %d boxes / %d corrupt lines",
                 split, n_images, n_boxes, corrupt_labels)

    profile["totals"] = dict(totals)
    profile["notes"] = [
        "size buckets use REAL image dims (PIL header reads), COCO px thresholds 32/96",
        "source = filename prefix stamped by build_composite (oi__=OpenImages, ars__=auto-rickshaw, pbd__=Poribohon-BD)",
        "TRACTOR is a declared empty class (taxonomy v1.0 conditional) -- zero boxes is expected, not an error",
    ]
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(profile, indent=2), encoding="utf-8")

    t = profile["totals"]
    LOG.info("profile written: %s", OUT.relative_to(C5_ROOT))
    LOG.info("TOTALS: %d images / %d boxes", t["images"], t["boxes"])
    for split, s in profile["splits"].items():
        top = sorted(s["per_class"].items(), key=lambda kv: -kv[1]["boxes"])[:4]
        LOG.info("  %s: %d img / %d boxes | top: %s",
                 split, s["images"], s["boxes"],
                 ", ".join(f"{c}={d['boxes']}" for c, d in top))
    return 0


if __name__ == "__main__":
    sys.exit(main())
