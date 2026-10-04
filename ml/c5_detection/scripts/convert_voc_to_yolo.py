#!/usr/bin/env python
"""
PRHAAR C5 -- convert a Pascal VOC XML dataset to canonical YOLO staging.

Inputs:
    <annotations>/*.xml        VOC annotation files (size + object/bndbox)
    <images>/*.jpg             image files (stem-matched to XML)
    --class-map                JSON: {"<voc class name>": "CANONICAL"}

Outputs (staging, per-source):
    datasets/staging/<name>/labels/{stem}.txt   YOLO: cls cx cy w h
    datasets/staging/<name>/index.jsonl         per-image provenance
    datasets/staging/<name>/conversion_report.json

Modes:
    --list-classes   scan XMLs, print class-name histogram, exit (no map needed)

Unmapped VOC class names are ABORTED with a clear list (no silent drop, spec 46)
unless --allow-skip is given, in which case they are counted and skipped.
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
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from c5_taxonomy import CLASSES, CLASS_INDEX, PRHAAR_C5_TAXONOMY_VERSION

LOG = logging.getLogger("convert_voc_yolo")
IST = timezone(timedelta(hours=5, minutes=30))

HERE = Path(__file__).resolve()
C5_ROOT = HERE.parents[1]
DATASETS = C5_ROOT / "datasets"

IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def now_ist() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def xml_class_hist(ann_dir: Path) -> Counter:
    hist = Counter()
    for p in sorted(ann_dir.glob("*.xml")):
        try:
            root = ET.parse(p).getroot()
        except ET.ParseError:
            hist["<PARSE_ERROR>"] += 1
            continue
        for obj in root.findall("object"):
            name = (obj.findtext("name") or "").strip()
            hist[name] += 1
    return hist


def find_image(images_dir: Path, stem: str) -> Path | None:
    for ext in IMG_EXTS:
        for cand in (images_dir / f"{stem}{ext}", images_dir / f"{stem}{ext.upper()}"):
            if cand.is_file():
                return cand
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--annotations", type=Path, required=True)
    ap.add_argument("--images", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--source-name", required=True)
    ap.add_argument("--class-map", default="", help='JSON: {"<voc name>": "CANONICAL"}')
    ap.add_argument("--list-classes", action="store_true")
    ap.add_argument("--allow-skip", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    t0 = time.time()

    if args.list_classes:
        hist = xml_class_hist(args.annotations)
        print(f"VOC class histogram ({sum(hist.values())} objects, "
              f"{len(list(args.annotations.glob('*.xml')))} xml files):")
        for name, n in hist.most_common():
            print(f"  {n:7d}  {name}")
        return 0

    if not args.class_map:
        LOG.error("--class-map required for conversion (or use --list-classes)")
        return 2
    class_map: dict[str, str] = json.loads(args.class_map)
    for k, v in class_map.items():
        if v not in CLASS_INDEX:
            LOG.error("class-map target %r not in canonical taxonomy", v)
            return 2

    out: Path = args.out
    (out / "labels").mkdir(parents=True, exist_ok=True)

    counts = Counter()
    per_class_boxes = Counter()
    per_class_images = Counter()
    per_source_class_boxes = Counter()
    unmapped_detail = Counter()
    unmapped_examples: list[str] = []
    idx_lines: list[dict] = []

    for p in sorted(args.annotations.glob("*.xml")):
        counts["xml_files"] += 1
        try:
            root = ET.parse(p).getroot()
        except ET.ParseError:
            counts["xml_parse_errors"] += 1
            continue
        size = root.find("size")
        if size is None:
            counts["missing_size"] += 1
            continue
        try:
            W = float(size.findtext("width"))
            H = float(size.findtext("height"))
        except (TypeError, ValueError):
            counts["missing_size"] += 1
            continue
        if W <= 0 or H <= 0:
            counts["missing_size"] += 1
            continue

        kept: list[str] = []
        img_classes: set[str] = set()
        for obj in root.findall("object"):
            name = (obj.findtext("name") or "").strip()
            per_source_class_boxes[name] += 1
            tgt = class_map.get(name)
            if tgt is None:
                counts["unmapped_boxes"] += 1
                unmapped_detail[name] += 1
                if len(unmapped_examples) < 10:
                    unmapped_examples.append(f"{p.name}: {name}")
                if not args.allow_skip:
                    LOG.error("unmapped VOC class %r in %s (use --allow-skip to skip)",
                              name, p.name)
                    return 2
                continue
            bb = obj.find("bndbox")
            if bb is None:
                counts["missing_bndbox"] += 1
                continue
            try:
                x1 = float(bb.findtext("xmin")); y1 = float(bb.findtext("ymin"))
                x2 = float(bb.findtext("xmax")); y2 = float(bb.findtext("ymax"))
            except (TypeError, ValueError):
                counts["missing_bndbox"] += 1
                continue
            # normalize + clip to [0,1]
            nx1 = min(1.0, max(0.0, x1 / W)); nx2 = min(1.0, max(0.0, x2 / W))
            ny1 = min(1.0, max(0.0, y1 / H)); ny2 = min(1.0, max(0.0, y2 / H))
            w, h = nx2 - nx1, ny2 - ny1
            if w <= 0.0 or h <= 0.0:
                counts["dropped_degenerate"] += 1
                continue
            cx, cy = (nx1 + nx2) / 2.0, (ny1 + ny2) / 2.0
            kept.append(f"{CLASS_INDEX[tgt]} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
            img_classes.add(tgt)
            per_class_boxes[tgt] += 1
            counts["boxes_kept"] += 1

        img_path = find_image(args.images, p.stem)
        if img_path is None:
            counts["images_no_file"] += 1
            continue
        if not kept:
            counts["skipped_no_boxes"] += 1
            continue

        for c in img_classes:
            per_class_images[c] += 1
        (out / "labels" / f"{p.stem}.txt").write_text("\n".join(kept) + "\n", encoding="utf-8")
        counts["images_out"] += 1
        try:
            rel = img_path.relative_to(C5_ROOT).as_posix()
        except ValueError:
            rel = img_path.as_posix()
        idx_lines.append({
            "image_id": f"{args.source_name}/{p.stem}",
            "source": args.source_name,
            "source_split": "unsplit",
            "image_path": rel,
            "label_file": f"labels/{p.stem}.txt",
            "classes": sorted(img_classes),
            "n_boxes": len(kept),
        })

    with open(out / "index.jsonl", "w", encoding="utf-8") as f:
        for e in idx_lines:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    report = {
        "artifact": f"PRHAAR C5 VOC XML -> canonical YOLO conversion ({args.source_name})",
        "generated_ist": now_ist(),
        "elapsed_s": round(time.time() - t0, 1),
        "taxonomy_version": PRHAAR_C5_TAXONOMY_VERSION,
        "classes": CLASSES,
        "source": {
            "annotations_dir": str(args.annotations),
            "images_dir": str(args.images),
        },
        "class_map": class_map,
        "counts": dict(sorted(counts.items())),
        "unmapped_detail": dict(unmapped_detail),
        "unmapped_examples": unmapped_examples,
        "per_source_class_boxes": dict(per_source_class_boxes.most_common()),
        "per_class_boxes": {c: per_class_boxes.get(c, 0) for c in CLASSES},
        "per_class_images": {c: per_class_images.get(c, 0) for c in CLASSES},
        "index_sha256": sha256_file(out / "index.jsonl"),
    }
    (out / "conversion_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    LOG.info("images out=%d boxes kept=%d", counts["images_out"], counts["boxes_kept"])
    LOG.info("report -> %s", out / "conversion_report.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
