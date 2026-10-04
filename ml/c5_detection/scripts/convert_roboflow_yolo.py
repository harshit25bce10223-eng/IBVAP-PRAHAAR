#!/usr/bin/env python
"""
PRHAAR C5 -- convert a Roboflow-format YOLO export to canonical staging.

Inputs (Roboflow YOLO export, e.g. Kaggle auto-rickshaw):
    <src>/data.yaml                       splits + names
    <src>/<split>/images/*.jpg            images
    <src>/<split>/labels/*.txt            YOLO labels, source class indices

Outputs (staging, per-source):
    datasets/staging/<name>/labels/{split}__{stem}.txt   remapped labels
    datasets/staging/<name>/index.jsonl                  per-image provenance
    datasets/staging/<name>/conversion_report.json       exact measured counts

Class remap: source index -> canonical name via --class-map, e.g.
    --class-map '{"0": "AUTO_RICKSHAW"}'
Unknown source indices are ABORTED with a clear list (no silent drop, spec 46)
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
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).parent))
from c5_taxonomy import CLASSES, CLASS_INDEX, PRHAAR_C5_TAXONOMY_VERSION

LOG = logging.getLogger("convert_roboflow_yolo")
IST = timezone(timedelta(hours=5, minutes=30))

HERE = Path(__file__).resolve()
C5_ROOT = HERE.parents[1]
DATASETS = C5_ROOT / "datasets"

IMG_EXTS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
# yaml split key -> preferred on-disk dir names (order of resolution attempts)
SPLIT_DIRS = {
    "train": ["train", "training"],
    "val": ["valid", "val", "validation"],
    "valid": ["valid", "val", "validation"],
    "test": ["test", "testing"],
}


def now_ist() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def resolve_images_dir(src: Path, split: str, raw_value: str) -> Path | None:
    cands = []
    v = str(raw_value).replace("\\", "/")
    cands.append(src / v)
    while v.startswith("../"):
        v = v[3:]
        cands.append(src / v)
    for d in SPLIT_DIRS.get(split, [split]):
        cands.append(src / d / "images")
    for c in cands:
        try:
            if c.is_dir():
                return c
        except OSError:
            pass
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--src", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--source-name", required=True)
    ap.add_argument("--class-map", required=True, help='JSON: {"<src idx or name>": "CANONICAL"}')
    ap.add_argument("--allow-skip", action="store_true",
                    help="skip unmapped/malformed lines instead of aborting")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    t0 = time.time()

    src: Path = args.src
    yml_path = src / "data.yaml"
    if not yml_path.exists():
        LOG.error("missing %s", yml_path)
        return 2
    data = yaml.safe_load(yml_path.read_text(encoding="utf-8")) or {}
    names = data.get("names", {})
    if isinstance(names, list):
        names = {str(i): n for i, n in enumerate(names)}
    else:
        names = {str(k): n for k, n in names.items()}
    LOG.info("source names: %s", names)

    class_map: dict[str, str] = json.loads(args.class_map)
    for k, v in class_map.items():
        if v not in CLASS_INDEX:
            LOG.error("class-map target %r not in canonical taxonomy", v)
            return 2
    # validate coverage against declared names
    missing = [k for k in names if k not in class_map and str(names[k]) not in class_map]
    if missing:
        LOG.error("class-map does not cover source indices %s (names %s)",
                  missing, {k: names[k] for k in missing})
        if not args.allow_skip:
            return 2

    out: Path = args.out
    (out / "labels").mkdir(parents=True, exist_ok=True)

    counts = Counter()
    per_class_boxes = Counter()
    per_class_images = Counter()
    per_source_class_boxes = Counter()
    per_split = {}
    idx_lines: list[dict] = []
    unmapped_detail = Counter()
    unmapped_examples: list[str] = []

    for split in ["train", "val", "valid", "test"]:
        if split not in data:
            continue
        img_dir = resolve_images_dir(src, split, data[split])
        if img_dir is None:
            counts[f"unresolved_split:{split}"] += 1
            LOG.warning("split %r declared but images dir not found", split)
            continue
        lbl_dir = img_dir.parent / "labels"
        s_counts = Counter()
        for img_path in sorted(img_dir.iterdir()):
            if img_path.suffix.lower() not in IMG_EXTS:
                continue
            s_counts["images"] += 1
            counts["images_in"] += 1
            stem = img_path.stem
            lbl_path = lbl_dir / f"{stem}.txt"
            if not lbl_path.exists():
                counts["images_missing_label"] += 1
                continue
            kept: list[str] = []
            img_classes: set[str] = set()
            for line in lbl_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) < 5:
                    counts["malformed_lines"] += 1
                    if not args.allow_skip:
                        LOG.error("malformed label line in %s: %r", lbl_path, line)
                        return 2
                    continue
                try:
                    cid = parts[0]
                    vals = [float(x) for x in parts[1:5]]
                except ValueError:
                    counts["malformed_lines"] += 1
                    if not args.allow_skip:
                        LOG.error("non-numeric label line in %s: %r", lbl_path, line)
                        return 2
                    continue
                per_source_class_boxes[str(names.get(cid, cid))] += 1
                tgt = class_map.get(cid) or class_map.get(str(names.get(cid, "")))
                if tgt is None:
                    counts["unmapped_lines"] += 1
                    unmapped_detail[str(names.get(cid, cid))] += 1
                    if len(unmapped_examples) < 10:
                        unmapped_examples.append(f"{lbl_path.name}: {line}")
                    if not args.allow_skip:
                        LOG.error("unmapped class %r in %s (use --allow-skip to skip)",
                                  names.get(cid, cid), lbl_path)
                        return 2
                    continue
                cx, cy, w, h = vals
                cx = min(1.0, max(0.0, cx))
                cy = min(1.0, max(0.0, cy))
                w = min(1.0, w)
                h = min(1.0, h)
                if w <= 0.0 or h <= 0.0:
                    counts["dropped_degenerate"] += 1
                    continue
                kept.append(f"{CLASS_INDEX[tgt]} {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}")
                img_classes.add(tgt)
                per_class_boxes[tgt] += 1
                counts["boxes_kept"] += 1

            if not kept:
                counts["skipped_no_boxes"] += 1
                continue
            for c in img_classes:
                per_class_images[c] += 1
            out_name = f"{split}__{stem}"
            (out / "labels" / f"{out_name}.txt").write_text(
                "\n".join(kept) + "\n", encoding="utf-8")
            counts["images_out"] += 1
            try:
                rel = img_path.relative_to(C5_ROOT).as_posix()
            except ValueError:
                rel = img_path.as_posix()
            idx_lines.append({
                "image_id": f"{args.source_name}/{split}/{stem}",
                "source": args.source_name,
                "source_split": split,
                "image_path": rel,
                "label_file": f"labels/{out_name}.txt",
                "classes": sorted(img_classes),
                "n_boxes": len(kept),
            })
        s_counts["images_out"] = sum(1 for e in idx_lines if e["source_split"] == split)
        per_split[split] = dict(sorted(s_counts.items()))
        LOG.info("split %s: %s", split, dict(s_counts))

    with open(out / "index.jsonl", "w", encoding="utf-8") as f:
        for e in idx_lines:
            f.write(json.dumps(e, ensure_ascii=False) + "\n")

    report = {
        "artifact": f"PRHAAR C5 Roboflow YOLO -> canonical conversion ({args.source_name})",
        "generated_ist": now_ist(),
        "elapsed_s": round(time.time() - t0, 1),
        "taxonomy_version": PRHAAR_C5_TAXONOMY_VERSION,
        "classes": CLASSES,
        "source": {
            "path": str(src),
            "data_yaml_sha256": sha256_file(yml_path),
            "names": names,
            "roboflow": data.get("roboflow"),
        },
        "class_map": class_map,
        "counts": dict(sorted(counts.items())),
        "unmapped_detail": dict(unmapped_detail),
        "unmapped_examples": unmapped_examples,
        "per_source_class_boxes": dict(per_source_class_boxes.most_common()),
        "per_split": per_split,
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
