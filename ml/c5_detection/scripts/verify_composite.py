"""
Independent verification of datasets/PRHAAR-C5-DETECTION (spec sections 10, 18-20).

This script is intentionally written as a *second source of truth*: it does NOT
reuse build_composite.py internals. It re-reads the emitted artifacts plus the
staging conversion reports and re-checks, from scratch:

  1. manifest.jsonl integrity: every image + label file exists; label line
     count == manifest n_boxes; sha256 of a random sample of images matches the
     manifest record (hardlink landed intact).
  2. per-class box totals: sum(staging conversion reports) == sum(composite
     split report per_class_boxes_per_split). Any class mismatch is fatal.
  3. leakage: group_rep must map to exactly one split (grouped split held);
     exact-dup sha256 groups must map to exactly one split.
  4. split sanity: no image appears twice; train/val/test stems disjoint.
  5. reported hash: dataset_hash.txt == sha256 over sorted (image_id, sha256).

Exit 0 = all pass; exit 1 = problems (printed).
"""
from __future__ import annotations

import hashlib
import json
import random
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]          # ml/c5_detection
DS = ROOT / "datasets" / "PRHAAR-C5-DETECTION"
STAGING = ROOT / "datasets" / "staging"
STAGING_SOURCES = ["autorickshaw_yolo", "oi_yolo", "poribohon_yolo"]
SAMPLE_N = 40

issues: list[str] = []


def note_fail(msg: str) -> None:
    issues.append(msg)
    print(f"  FAIL: {msg}")


def main() -> int:
    # ---------- load artifacts ----------
    man = [json.loads(l) for l in
           (DS / "manifest.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    report = json.loads((DS / "split_report.json").read_text(encoding="utf-8"))
    print(f"manifest records: {len(man)}")
    print(f"report images  : {report['counts']['images']}")
    if len(man) != report["counts"]["images"]:
        note_fail(f"manifest {len(man)} != report {report['counts']['images']}")

    # ---------- 1. manifest integrity ----------
    print("[1] manifest integrity (files, label line counts, sampled sha256)")
    by_split = Counter(r["split"] for r in man)
    for s, n in sorted(by_split.items()):
        print(f"  split {s}: {n}")
    n_missing = 0
    n_boxmismatch = 0
    for r in man:
        img = DS / r["image"]
        lbl = DS / r["label"]
        if not img.is_file() or not lbl.is_file():
            n_missing += 1
            if n_missing <= 5:
                print(f"    missing: {img} / {lbl}")
            continue
        lines = [l for l in lbl.read_text(encoding="utf-8").splitlines() if l.strip()]
        if len(lines) != r["n_boxes"]:
            n_boxmismatch += 1
            if n_boxmismatch <= 5:
                print(f"    box count mismatch {r['image_id']}: "
                      f"manifest {r['n_boxes']} vs file {len(lines)}")
    if n_missing:
        note_fail(f"{n_missing} manifest records missing files")
    if n_boxmismatch:
        note_fail(f"{n_boxmismatch} label line-count mismatches")
    rng = random.Random(20261014)
    sample = rng.sample(man, min(SAMPLE_N, len(man)))
    bad_hash = 0
    for r in sample:
        h = hashlib.sha256((DS / r["image"]).read_bytes()).hexdigest()
        if h != r["sha256"]:
            bad_hash += 1
            print(f"    hash mismatch: {r['image_id']}")
    print(f"  sampled {len(sample)} images, hash mismatches: {bad_hash}")
    if bad_hash:
        note_fail(f"{bad_hash}/{len(sample)} sampled image hashes do not match")

    # ---------- 2. per-class reconciliation vs staging ----------
    print("[2] per-class boxes: sum(staging conversion reports) vs composite")
    staging_cls: Counter = Counter()
    staging_boxes = 0
    for src in STAGING_SOURCES:
        rep = json.loads((STAGING / src / "conversion_report.json")
                         .read_text(encoding="utf-8"))
        pc = rep["per_class_boxes"]
        src_total = sum(pc.values())
        staging_boxes += src_total
        print(f"  {src}: {src_total} boxes {dict(sorted(pc.items()))}")
        for k, v in pc.items():
            staging_cls[k] += v
    comp_cls = {c: sum(v.values())
                for c, v in report["per_class_boxes_per_split"].items()}
    comp_boxes = sum(comp_cls.values())
    print(f"  staging total {staging_boxes} vs composite total {comp_boxes}")
    if staging_boxes != comp_boxes:
        note_fail(f"box totals differ: staging {staging_boxes} vs composite {comp_boxes}")
    for c in sorted(set(staging_cls) | set(comp_cls)):
        a, b = staging_cls.get(c, 0), comp_cls.get(c, 0)
        flag = "" if a == b else "  <-- MISMATCH"
        if a != b:
            note_fail(f"class {c}: staging {a} vs composite {b}")
        print(f"  {c:15s} staging {a:6d} composite {b:6d}{flag}")

    # ---------- 3. leakage ----------
    print("[3] leakage: group_rep single-split; exact-dup sha256 single-split")
    split_by_stem = {Path(r["image"]).stem: r["split"] for r in man}
    rep_splits: dict[str, set] = defaultdict(set)
    for r in man:
        # group_rep is an image_id of the group representative; map to its stem
        rep_splits[r["group_rep"]].add(r["split"])
    cross = {k: v for k, v in rep_splits.items() if len(v) > 1}
    print(f"  groups (by rep): {len(rep_splits)}; cross-split: {len(cross)}")
    if cross:
        for k, v in list(cross.items())[:5]:
            print(f"    cross: {k} -> {sorted(v)}")
        note_fail(f"{len(cross)} groups straddle splits")
    sha_splits: dict[str, set] = defaultdict(set)
    sha_count: Counter = Counter()
    for r in man:
        sha_splits[r["sha256"]].add(r["split"])
        sha_count[r["sha256"]] += 1
    dups = {k: c for k, c in sha_count.items() if c > 1}
    cross_sha = {k: v for k, v in sha_splits.items() if len(v) > 1 and sha_count[k] > 1}
    print(f"  exact-dup groups: {len(dups)}; cross-split: {len(cross_sha)}")
    if cross_sha:
        note_fail(f"{len(cross_sha)} exact-dup groups straddle splits")
    # groups count from manifest perspective
    rep_count = len(rep_splits)
    print(f"  distinct group reps in manifest: {rep_count} "
          f"(report says {report['counts']['groups']})")
    if rep_count != report["counts"]["groups"]:
        note_fail(f"group rep count {rep_count} != report groups "
                  f"{report['counts']['groups']}")

    # ---------- 4. stem uniqueness ----------
    print("[4] image_id / stem uniqueness across the dataset")
    ids = [r["image_id"] for r in man]
    stems = [Path(r["image"]).stem for r in man]
    if len(set(ids)) != len(ids):
        note_fail(f"duplicate image_ids: {len(ids) - len(set(ids))}")
    if len(set(stems)) != len(stems):
        note_fail(f"duplicate stems: {len(stems) - len(set(stems))}")
    print(f"  unique ids {len(set(ids))}, unique stems {len(set(stems))}, n {len(man)}")

    # ---------- 5. dataset hash ----------
    print("[5] dataset_hash.txt reproducibility")
    h = hashlib.sha256()
    for r in sorted(man, key=lambda x: x["image_id"]):
        h.update(f"{r['image_id']}\t{r['sha256']}\n".encode())
    rec_hash = h.hexdigest()
    disk_hash = (DS / "dataset_hash.txt").read_text(encoding="utf-8").strip()
    print(f"  recomputed {rec_hash[:24]}...")
    print(f"  on disk    {disk_hash[:24]}...")
    if rec_hash != disk_hash:
        note_fail("dataset hash mismatch")

    print()
    if issues:
        print(f"RESULT: {len(issues)} PROBLEM(S)")
        return 1
    print("RESULT: ALL CHECKS PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
