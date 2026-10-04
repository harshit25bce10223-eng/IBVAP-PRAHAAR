#!/usr/bin/env python
"""
PRHAAR C5 -- convert Open Images V7 acquisition artifacts to YOLO labels.

Inputs (produced by acquire_openimages.py):
    datasets/sources/openimages_v7/annotations/annotations_raw.jsonl
    datasets/sources/openimages_v7/acquisition_manifest.jsonl
    datasets/sources/openimages_v7/images/{split}/{id}.jpg

Outputs (staging, per-source):
    datasets/staging/oi_yolo/labels/{image_id}.txt   YOLO lines: cls cx cy w h
    datasets/staging/oi_yolo/index.jsonl             per-image provenance index
    datasets/staging/oi_yolo/conversion_report.json  exact measured counts

Conversion policy (explicit, counted, never silent -- spec 46/61):
  - depiction==1 boxes are DROPPED (non-photographic content, e.g. posters).
  - occluded / truncated boxes are KEPT (occlusion diversity required, spec 11).
  - group_of==1 boxes are KEPT by default (--drop-group-of removes them);
    their count is recorded either way.
  - coordinates clipped to [0,1]; degenerate boxes (w<=0 or h<=0 after clip)
    are dropped and counted.
  - images not downloaded (manifest downloaded=false) or whose file is missing
    are skipped and counted.
  - images left with zero boxes are skipped and counted.

Paths in index.jsonl are relative to ml/c5_detection/ (C5 root) -- they start
with "datasets/", matching qa_dataset.py/build_composite.py defaults.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from c5_taxonomy import CLASS_INDEX, CLASSES, OI_TO_CANONICAL, PRHAAR_C5_TAXONOMY_VERSION

LOG = logging.getLogger("convert_oi_yolo")
IST = timezone(timedelta(hours=5, minutes=30))

HERE = Path(__file__).resolve()
C5_ROOT = HERE.parents[1]
DATASETS = C5_ROOT / "datasets"
DEFAULT_SRC = DATASETS / "sources" / "openimages_v7"
DEFAULT_OUT = DATASETS / "staging" / "oi_yolo"


def now_ist() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def load_jsonl(path: Path):
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", type=Path, default=DEFAULT_SRC)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--drop-group-of", action="store_true",
                    help="drop IsGroupOf==1 boxes instead of keeping them")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    t0 = time.time()

    ann_path = args.src / "annotations" / "annotations_raw.jsonl"
    man_path = args.src / "acquisition_manifest.jsonl"
    for p in (ann_path, man_path):
        if not p.exists():
            LOG.error("missing input: %s", p)
            return 2

    out: Path = args.out
    (out / "labels").mkdir(parents=True, exist_ok=True)

    manifest = {}
    for m in load_jsonl(man_path):
        manifest[m["image_id"]] = m
    LOG.info("manifest entries: %d", len(manifest))

    counts = Counter()
    per_class_boxes = Counter()
    per_class_images = Counter()
    idx_lines: list[dict] = []

    for rec in load_jsonl(ann_path):
        counts["images_in"] += 1
        img = rec["image_id"]
        man = manifest.get(img)
        if man is None:
            counts["skipped_no_manifest"] += 1
            continue
        if not man.get("downloaded"):
            counts["skipped_not_downloaded"] += 1
            continue
        img_path = args.src / man["path"]
        if not img_path.exists():
            counts["skipped_missing_file"] += 1
            continue

        kept: list[str] = []
        img_classes: set[str] = set()
        flags = Counter()
        for b in rec["boxes"]:
            counts["boxes_in"] += 1
            if b.get("depiction"):
                counts["dropped_depiction"] += 1
                continue
            if b.get("group_of"):
                flags["group_of"] += 1
                if args.drop_group_of:
                    counts["dropped_group_of"] += 1
                    continue
            x1 = min(1.0, max(0.0, float(b["xmin"])))
            x2 = min(1.0, max(0.0, float(b["xmax"])))
            y1 = min(1.0, max(0.0, float(b["ymin"])))
            y2 = min(1.0, max(0.0, float(b["ymax"])))
            w, h = x2 - x1, y2 - y1
            if w <= 0.0 or h <= 0.0:
                counts["dropped_degenerate"] += 1
                continue
            cname = OI_TO_CANONICAL[b["oi_class"]]
            cid = CLASS_INDEX[cname]
            cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
            kept.append(f"{cid} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
            img_classes.add(cname)
            per_class_boxes[cname] += 1
            if b.get("occluded"):
                flags["occluded"] += 1
            if b.get("truncated"):
                flags["truncated"] += 1

        if not kept:
            counts["skipped_no_boxes"] += 1
            continue

        (out / "labels" / f"{img}.txt").write_text("\n".join(kept) + "\n", encoding="utf-8")
        counts["images_out"] += 1
        counts["boxes_kept"] += len(kept)
        for c in img_classes:
            per_class_images[c] += 1
        idx_lines.append({
            "image_id": img,
            "source": "openimages_v7",
            "source_split": rec["oi_split"],
            "image_path": f"datasets/sources/openimages_v7/{man['path']}",
            "classes": sorted(img_classes),
            "n_boxes": len(kept),
            "n_boxes_raw": rec["n_boxes"],
            "n_occluded": flags["occluded"],
            "n_truncated": flags["truncated"],
            "n_group_of": flags["group_of"],
            "license": man.get("license"),
            "author": man.get("author"),
            "sha256": man.get("sha256"),
        })

    with open(out / "index.jsonl", "w", encoding="utf-8") as f:
        for e in idx_lines:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    report = {
        "artifact": "PRHAAR C5 Open Images V7 -> YOLO conversion",
        "generated_ist": now_ist(),
        "elapsed_s": round(time.time() - t0, 1),
        "taxonomy_version": PRHAAR_C5_TAXONOMY_VERSION,
        "classes": CLASSES,
        "policy": {
            "drop_depiction": True,
            "drop_group_of": bool(args.drop_group_of),
            "keep_occluded": True,
            "keep_truncated": True,
            "clip_to_unit": True,
            "drop_degenerate": True,
        },
        "inputs": {
            "annotations_raw.jsonl": {
                "path": str(ann_path),
                "sha256": sha256_file(ann_path),
            },
            "acquisition_manifest.jsonl": {
                "path": str(man_path),
                "sha256": sha256_file(man_path),
            },
        },
        "counts": dict(sorted(counts.items())),
        "per_class_boxes": {c: per_class_boxes.get(c, 0) for c in CLASSES},
        "per_class_images": {c: per_class_images.get(c, 0) for c in CLASSES},
        "index_sha256": sha256_file(out / "index.jsonl"),
        "notes": [
            "source_split is the OI official split; group-based re-splitting "
            "happens in the composite dataset builder.",
            "ANIMAL merges OI Cattle/Sheep/Goat/Horse/Dog (recorded in "
            "annotations_raw.jsonl per-box oi_class).",
        ],
    }
    (out / "conversion_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    LOG.info("images out=%d (in=%d) boxes kept=%d/%d",
             counts["images_out"], counts["images_in"],
             counts["boxes_kept"], counts["boxes_in"])
    LOG.info("report -> %s", out / "conversion_report.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
