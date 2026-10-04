#!/usr/bin/env python
"""
PRHAAR C5 -- dataset QA + duplicate detection for a staging directory.

Implements spec section 17 (automated validation -> dataset_quality_report.json):
    image exists / label exists / class valid / bbox valid / bbox inside image /
    bbox width > 0 / bbox height > 0 / no malformed files / no corrupt images
and spec section 18 (duplicate detection, before splitting):
    exact duplicate images (SHA-256) / near-duplicate images (dHash-64 via PIL,
    since `imagehash` is not installed) / burst-suspect clusters (dHash distance
    very small) / same-source-split leakage warnings.
Also produces the spec section 12 bounding-box area distribution + very_far
counts (threshold declared in the report, section 12 gives no numeric cutoff).

Input: a staging dir produced by the convert_* scripts:
    <staging>/index.jsonl    (image_path relative to the C5 root; label_file
                              relative to the staging dir)
    <staging>/labels/*.txt

Output: <staging>/dataset_quality_report.json (default; override with --out).
Counts only -- nothing in the report is estimated; every number is measured
from the files on disk at run time.

Usage:
    python scripts/qa_dataset.py --staging datasets/staging/poribohon_yolo
    python scripts/qa_dataset.py --staging datasets/staging/autorickshaw_yolo --workers 12
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import math
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

try:
    import numpy as np
    from PIL import Image
except ImportError as e:  # pragma: no cover
    print(f"FATAL: missing dependency: {e}", file=sys.stderr)
    sys.exit(2)

sys.path.insert(0, str(Path(__file__).resolve().parent))
from c5_taxonomy import CLASSES, CONDITIONAL_CLASSES, PRHAAR_C5_TAXONOMY_VERSION  # noqa: E402

SCRIPT_DIR = Path(__file__).resolve().parent
C5_ROOT = SCRIPT_DIR.parent          # ml/c5_detection
DEFAULT_BASE = C5_ROOT               # image_path is relative to this

BOUNDS_EPS = 1e-6
VERY_FAR_AREA = 0.002                # normalized bbox area threshold (declared policy)
AREA_BUCKETS = [                     # (label, lo_inclusive, hi_exclusive) on normalized area
    ("tiny", 0.0, 0.001),
    ("small", 0.001, 0.01),
    ("medium", 0.01, 0.1),
    ("large", 0.1, math.inf),
]
VERY_FAR_CLASSES = ["PERSON", "MOTORCYCLE", "CAR", "TRUCK"]  # spec section 12


def sha256_file(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while True:
            b = f.read(chunk)
            if not b:
                break
            h.update(b)
    return h.hexdigest()


def dhash64(path: Path, hash_size: int = 8) -> int:
    """64-bit difference hash (PIL implementation; imagehash not installed)."""
    with Image.open(path) as im:
        im = im.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.LANCZOS)
        px = im.tobytes()  # mode L: one byte per pixel, row-major
    bits = 0
    for row in range(hash_size):
        base = row * (hash_size + 1)
        for col in range(hash_size):
            bits = (bits << 1) | (1 if px[base + col] > px[base + col + 1] else 0)
    return bits


def parse_label_file(path: Path):
    """Return (boxes, line_issues). boxes = list of (cls, x, y, w, h)."""
    issues = {"malformed": [], "class_invalid": [], "degenerate": [],
              "out_of_bounds": [], "blank_lines": 0}
    boxes = []
    try:
        text = path.read_text(encoding="utf-8", errors="strict")
    except (UnicodeDecodeError, OSError) as e:
        issues["malformed"].append(f"unreadable: {e}")
        return boxes, issues
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            issues["blank_lines"] += 1
            continue
        tok = line.split()
        if len(tok) != 5:
            issues["malformed"].append(f"line {lineno}: {len(tok)} tokens")
            continue
        try:
            vals = [float(t) for t in tok]
        except ValueError:
            issues["malformed"].append(f"line {lineno}: non-numeric")
            continue
        if not all(math.isfinite(v) for v in vals):
            issues["malformed"].append(f"line {lineno}: non-finite")
            continue
        cls_f, x, y, w, h = vals
        if cls_f < 0 or abs(cls_f - round(cls_f)) > 0 or round(cls_f) >= len(CLASSES):
            issues["class_invalid"].append(f"line {lineno}: class {cls_f}")
            continue
        cls = int(round(cls_f))
        if w <= 0 or h <= 0:
            issues["degenerate"].append(f"line {lineno}: w={w} h={h}")
            continue
        if (x - w / 2 < -BOUNDS_EPS or x + w / 2 > 1 + BOUNDS_EPS
                or y - h / 2 < -BOUNDS_EPS or y + h / 2 > 1 + BOUNDS_EPS
                or x < -BOUNDS_EPS or x > 1 + BOUNDS_EPS
                or y < -BOUNDS_EPS or y > 1 + BOUNDS_EPS):
            issues["out_of_bounds"].append(
                f"line {lineno}: x={x:.4f} y={y:.4f} w={w:.4f} h={h:.4f}")
            continue
        boxes.append((cls, x, y, w, h))
    return boxes, issues


def check_entry(entry: dict, base: Path, staging: Path):
    """Validate one index entry: image + label. Returns a result record."""
    rec = {
        "image_id": entry.get("image_id"),
        "source": entry.get("source"),
        "source_split": entry.get("source_split"),
        "image_ok": False, "image_error": None, "dims": None,
        "label_ok": False, "label_error": None,
        "boxes": [], "line_issues": None,
        "sha256": None, "dhash": None,
        "index_n_boxes": entry.get("n_boxes"),
    }
    img_path = base / entry["image_path"]

    # image checks
    if not img_path.is_file():
        rec["image_error"] = "missing"
    else:
        try:
            with Image.open(img_path) as im:
                im.load()
                rec["dims"] = [im.width, im.height]
            rec["image_ok"] = True
        except Exception as e:
            rec["image_error"] = f"corrupt: {type(e).__name__}: {e}"
        if rec["image_ok"]:
            try:
                rec["sha256"] = sha256_file(img_path)
                rec["dhash"] = dhash64(img_path)
            except Exception as e:
                rec["image_error"] = f"hash-fail: {type(e).__name__}: {e}"
                rec["image_ok"] = False

    # label checks
    label_rel = entry.get("label_file")
    if not label_rel:
        rec["label_error"] = "no label_file field"
    else:
        label_path = staging / label_rel
        if not label_path.is_file():
            rec["label_error"] = "missing"
        else:
            boxes, issues = parse_label_file(label_path)
            rec["boxes"] = boxes
            rec["line_issues"] = issues
            rec["label_ok"] = True
    return rec


def union_find_clusters(n: int, pairs):
    parent = list(range(n))

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for a, b in pairs:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra
    clusters = defaultdict(list)
    for i in range(n):
        clusters[find(i)].append(i)
    return [m for m in clusters.values() if len(m) > 1]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--staging", required=True, type=Path,
                    help="staging dir containing index.jsonl + labels/")
    ap.add_argument("--base", type=Path, default=DEFAULT_BASE,
                    help="base for resolving index image_path (default: C5 root)")
    ap.add_argument("--out", type=Path, default=None,
                    help="report path (default: <staging>/dataset_quality_report.json)")
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--near-dup-threshold", type=int, default=5,
                    help="dHash-64 Hamming distance <= this = near-duplicate (default 5)")
    ap.add_argument("--burst-threshold", type=int, default=2,
                    help="cluster min pairwise distance <= this = burst-suspect (default 2)")
    ap.add_argument("--max-issues", type=int, default=50,
                    help="max issue rows kept per category in the report (default 50)")
    ap.add_argument("--limit", type=int, default=None,
                    help="debug: only process first N index entries")
    args = ap.parse_args()

    staging = args.staging.resolve()
    base = args.base.resolve()
    index_path = staging / "index.jsonl"
    if not index_path.is_file():
        print(f"FATAL: {index_path} not found", file=sys.stderr)
        return 2

    t0 = time.time()
    index_sha = sha256_file(index_path)
    entries = []
    with index_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    if args.limit:
        entries = entries[: args.limit]
    print(f"index: {len(entries)} entries (sha256 {index_sha[:16]}...)")

    results = []
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        futs = [ex.submit(check_entry, e, base, staging) for e in entries]
        for i, fut in enumerate(cf.as_completed(futs), 1):
            results.append(fut.result())
            if i % 1000 == 0:
                print(f"  checked {i}/{len(entries)}")
    # deterministic order = index order
    order = {e.get("image_id"): i for i, e in enumerate(entries)}
    results.sort(key=lambda r: order.get(r["image_id"], 1 << 30))
    print(f"checked in {time.time() - t0:.1f}s; duplicate analysis...")

    # ---- aggregate validation counts ----
    c = Counter()
    issues_out = defaultdict(list)
    class_boxes = Counter()
    class_images = Counter()
    area_values = defaultdict(list)       # class -> normalized areas
    all_areas = []
    very_far = Counter()
    dims_w, dims_h = [], []
    exact_groups = defaultdict(list)      # sha256 -> [result idx]
    dhash_ok_idx = []
    dhash_vals = []
    mismatches = 0

    for r in results:
        c["index_entries"] += 1
        if r["image_ok"]:
            c["images_ok"] += 1
            dims_w.append(r["dims"][0])
            dims_h.append(r["dims"][1])
            if r["sha256"]:
                exact_groups[r["sha256"]].append(r["image_id"])
            if r["dhash"] is not None:
                dhash_ok_idx.append(len(dhash_ok_idx))
                dhash_vals.append(r["dhash"])
        else:
            c["images_bad"] += 1
            if r["image_error"] == "missing":
                c["images_missing"] += 1
            else:
                c["images_corrupt"] += 1
            if len(issues_out["images_bad"]) < args.max_issues:
                issues_out["images_bad"].append(
                    {"image_id": r["image_id"], "error": r["image_error"]})

        if r["label_ok"]:
            c["labels_ok"] += 1
            li = r["line_issues"]
            c["label_lines_malformed"] += len(li["malformed"])
            c["label_lines_class_invalid"] += len(li["class_invalid"])
            c["label_lines_degenerate"] += len(li["degenerate"])
            c["label_lines_out_of_bounds"] += len(li["out_of_bounds"])
            c["label_blank_lines"] += li["blank_lines"]
            for key in ("malformed", "class_invalid", "degenerate", "out_of_bounds"):
                for msg in li[key]:
                    if len(issues_out[f"label_lines_{key}"]) < args.max_issues:
                        issues_out[f"label_lines_{key}"].append(
                            {"image_id": r["image_id"], "detail": msg})
            if not r["boxes"]:
                c["labels_empty"] += 1
                if len(issues_out["labels_empty"]) < args.max_issues:
                    issues_out["labels_empty"].append(r["image_id"])
            if r["index_n_boxes"] is not None and r["index_n_boxes"] != len(r["boxes"]):
                mismatches += 1
                if len(issues_out["index_count_mismatch"]) < args.max_issues:
                    issues_out["index_count_mismatch"].append(
                        {"image_id": r["image_id"],
                         "index": r["index_n_boxes"], "label": len(r["boxes"])})
            seen_cls = set()
            for (cls, x, y, w, h) in r["boxes"]:
                c["boxes_total"] += 1
                name = CLASSES[cls]
                class_boxes[name] += 1
                seen_cls.add(name)
                area = w * h
                all_areas.append(area)
                area_values[name].append(area)
                if area < VERY_FAR_AREA and name in VERY_FAR_CLASSES:
                    very_far[name] += 1
            for name in seen_cls:
                class_images[name] += 1
        else:
            c["labels_bad"] += 1
            if len(issues_out["labels_bad"]) < args.max_issues:
                issues_out["labels_bad"].append(
                    {"image_id": r["image_id"], "error": r["label_error"]})

    # orphan labels: files in labels/ not referenced by index
    ref = {Path(e["label_file"]).name for e in entries if e.get("label_file")}
    present = {p.name for p in (staging / "labels").glob("*.txt")}
    orphans = sorted(present - ref)
    c["labels_orphan"] = len(orphans)

    # ---- exact duplicates ----
    exact_dup_groups = {k: v for k, v in exact_groups.items() if len(v) > 1}
    split_of = {r["image_id"]: r["source_split"] for r in results}
    exact_cross = sum(1 for v in exact_dup_groups.values()
                      if len({split_of.get(i) for i in v}) > 1)

    # ---- near duplicates (dHash, vectorized popcount) ----
    n = len(dhash_vals)
    H = np.asarray(dhash_vals, dtype=np.uint64)
    pairs = []
    for i in range(n):
        if i + 1 >= n:
            break
        d = np.bitwise_count(H[i] ^ H[i + 1:])
        js = np.nonzero(d <= args.near_dup_threshold)[0]
        for jj in js:
            pairs.append((i, int(i + 1 + jj)))
    clusters = union_find_clusters(n, pairs)

    cluster_reports = []
    cross_split_clusters = 0
    for members in clusters:
        idxs = [dhash_ok_idx[m] for m in members]
        ids = [results[k]["image_id"] for k in idxs]
        mh = H[members]
        # min pairwise distance within cluster
        md = 64
        for a in range(len(members)):
            if a + 1 >= len(members):
                break
            md = min(md, int(np.bitwise_count(mh[a] ^ mh[a + 1:]).min()))
        splits = {split_of.get(i) for i in ids}
        kind = "burst_suspect" if md <= args.burst_threshold else "near_dup"
        if len(splits) > 1:
            cross_split_clusters += 1
        cluster_reports.append({
            "kind": kind, "members": ids,
            "n_members": len(ids), "min_pairwise_dhash_dist": md,
            "cross_source_split": len(splits) > 1,
        })
    cluster_reports.sort(key=lambda x: (-x["n_members"], min(x["members"])))

    # ---- area distribution ----
    def pct(vals, p):
        if not vals:
            return None
        arr = np.asarray(vals)
        return float(np.percentile(arr, p))

    bucket_counts = Counter()
    for a in all_areas:
        for label, lo, hi in AREA_BUCKETS:
            if lo <= a < hi:
                bucket_counts[label] += 1
                break

    def dim_stats(vals):
        if not vals:
            return None
        arr = np.asarray(vals)
        return {"min": int(arr.min()), "p25": int(np.percentile(arr, 25)),
                "median": int(np.median(arr)), "p75": int(np.percentile(arr, 75)),
                "max": int(arr.max())}

    report = {
        "spec": "PRHAAR C5 section 17 (validation) + section 18 (duplicates) + section 12 (area distribution)",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "taxonomy_version": PRHAAR_C5_TAXONOMY_VERSION,
        "classes": CLASSES,
        "conditional_classes": sorted(CONDITIONAL_CLASSES),
        "staging_dir": str(staging),
        "base_dir": str(base),
        "index_file_sha256": index_sha,
        "index_entries_processed": len(entries),
        "near_dup_threshold_dhash64": args.near_dup_threshold,
        "burst_threshold_dhash64": args.burst_threshold,
        "very_far_area_threshold_normalized": VERY_FAR_AREA,
        "runtime_seconds": round(time.time() - t0, 1),
        "counts": dict(sorted(c.items())),
        "index_count_mismatch_images": mismatches,
        "class_stats": {
            name: {"boxes": class_boxes.get(name, 0),
                   "images": class_images.get(name, 0)}
            for name in CLASSES
        },
        "area_distribution": {
            "buckets_normalized": {label: bucket_counts.get(label, 0)
                                   for label, _, _ in AREA_BUCKETS},
            "all_boxes_percentiles": {p: pct(all_areas, p)
                                      for p in (5, 25, 50, 75, 95)},
            "per_class_percentiles": {
                name: {p: pct(area_values[name], p) for p in (5, 50, 95)}
                for name in CLASSES if area_values.get(name)
            },
            "very_far_boxes": {name: very_far.get(name, 0) for name in VERY_FAR_CLASSES},
        },
        "image_dimensions": {"width": dim_stats(dims_w), "height": dim_stats(dims_h)},
        "duplicates": {
            "exact_dup_groups": len(exact_dup_groups),
            "exact_dup_images": sum(len(v) for v in exact_dup_groups.values()),
            "exact_dup_groups_cross_source_split": exact_cross,
            "near_dup_clusters": len([x for x in cluster_reports if x["kind"] == "near_dup"]),
            "burst_suspect_clusters": len([x for x in cluster_reports if x["kind"] == "burst_suspect"]),
            "clusters_cross_source_split": cross_split_clusters,
            "exact_dup_groups_list": [
                {"sha256": k, "members": v} for k, v in
                sorted(exact_dup_groups.items(), key=lambda kv: -len(kv[1]))[: args.max_issues]
            ],
            "clusters_list": cluster_reports[: args.max_issues],
            "clusters_total": len(cluster_reports),
            "images_in_near_dup_clusters": sum(x["n_members"] for x in cluster_reports),
        },
        "issues": {k: v for k, v in issues_out.items()},
        "orphan_labels": {"count": len(orphans), "sample": orphans[: args.max_issues]},
    }

    structural_ok = all(c.get(k, 0) == 0 for k in (
        "images_missing", "images_corrupt", "labels_bad",
        "label_lines_malformed", "label_lines_class_invalid",
        "label_lines_degenerate", "label_lines_out_of_bounds", "labels_empty"))
    report["gates"] = {
        "structural_validation_pass": structural_ok,
        "note_structural": ("section 17 checks: image/label presence, class validity, "
                            "bbox validity/bounds/size, malformed files, corrupt images"),
        "leakage_note": ("section 18/19: duplicate clusters must not straddle the final "
                         "train/val/test split; cross_source_split counts reflect the "
                         "source's OWN splits and become actionable at composite build"),
    }

    out = args.out or (staging / "dataset_quality_report.json")
    with out.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        f.write("\n")

    print(f"\nreport -> {out}")
    print(f"  images ok {c.get('images_ok', 0)}/{c.get('index_entries', 0)} "
          f"(missing {c.get('images_missing', 0)}, corrupt {c.get('images_corrupt', 0)})")
    print(f"  labels ok {c.get('labels_ok', 0)}, bad {c.get('labels_bad', 0)}, "
          f"orphans {c.get('labels_orphan', 0)}")
    print(f"  boxes total {c.get('boxes_total', 0)}; malformed lines "
          f"{c.get('label_lines_malformed', 0)}, class-invalid {c.get('label_lines_class_invalid', 0)}, "
          f"degenerate {c.get('label_lines_degenerate', 0)}, out-of-bounds {c.get('label_lines_out_of_bounds', 0)}")
    print(f"  exact dup groups {len(exact_dup_groups)} (cross-split {exact_cross}); "
          f"near-dup/burst clusters {len(cluster_reports)} (cross-split {cross_split_clusters})")
    print(f"  structural validation pass: {structural_ok}")
    return 0 if structural_ok else 1


if __name__ == "__main__":
    sys.exit(main())
