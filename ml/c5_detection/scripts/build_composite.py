#!/usr/bin/env python
"""
PRHAAR C5 -- composite dataset builder (PRHAAR-C5-DETECTION), spec sections 18-20.

Assembles datasets/PRHAAR-C5-DETECTION/ from one or more staging dirs
(datasets/staging/<source>_yolo/ with index.jsonl + labels/ + a §17
dataset_quality_report.json that passed structural validation).

Pipeline:
  1. load + validate staging dirs (QA report required; structural pass required)
  2. recompute per-image SHA-256 + dHash-64 (self-contained; same algorithm and
     thresholds as qa_dataset.py)
  3. build leakage groups (§19): union-find over
       - exact-duplicate images (same SHA-256)
       - near-duplicate / burst pairs (dHash-64 Hamming <= threshold)
       - OI author union for authors with <= --group-by-author-max images
         (author is a capture-context proxy; capped so one prolific account
         cannot destabilize the split; caps are recorded in the report)
  4. split WHOLE GROUPS ~70/15/15 (deterministic greedy: largest group first,
     assigned to the split furthest below its scaled target; tie-break by
     sha1(seed + group key)) -- never split by random frame (§19/§20)
  5. materialize images/ + labels/ (hardlink default, copy fallback COUNTS
     recorded -- no silent fallback), manifest.jsonl, data.yaml
  6. verify: no group straddles splits, files exist, counts match -> split_report.json

PRHAAR-HARD-TEST (§20/§21) is NOT built here: it is Layer D, built from
PRHAAR/SSB footage once available (user action; see catalog section 4).

Usage:
    python scripts/build_composite.py                       # auto-discover all valid staging dirs
    python scripts/build_composite.py --sources poribohon_yolo autorickshaw_yolo
    python scripts/build_composite.py --out datasets/PRHAAR-C5-DETECTION --force
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import json
import os
import shutil
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from c5_taxonomy import CLASSES, CONDITIONAL_CLASSES, PRHAAR_C5_TAXONOMY_VERSION  # noqa: E402
from qa_dataset import sha256_file, dhash64, union_find_clusters  # noqa: E402

SCRIPT_DIR = Path(__file__).resolve().parent
C5_ROOT = SCRIPT_DIR.parent
DEFAULT_BASE = C5_ROOT
DEFAULT_STAGING_ROOT = C5_ROOT / "datasets" / "staging"
DEFAULT_OUT = C5_ROOT / "datasets" / "PRHAAR-C5-DETECTION"

# source field -> (short tag for composite filenames, license note for manifest)
SOURCE_META = {
    "openimages_v7": ("oi", "annotations CC BY 4.0; image license per-image (manifest)"),
    "kaggle_poribohon_bd": ("pbh", "CC BY 4.0 assumed (stricter of CC0/CC BY conflict)"),
    "kaggle_autorickshaw_apache2": ("ars", "Apache 2.0 (Kaggle page; Roboflow files say Public Domain)"),
}

SPLITS = ("train", "val", "test")
TARGETS = {"train": 0.70, "val": 0.15, "test": 0.15}


def load_staging(staging_dir: Path, base: Path):
    """Load one staging dir; enforce QA gate. Returns list of normalized records."""
    index_path = staging_dir / "index.jsonl"
    qa_path = staging_dir / "dataset_quality_report.json"
    if not index_path.is_file():
        raise SystemExit(f"FATAL: {staging_dir}: index.jsonl missing")
    if not qa_path.is_file():
        raise SystemExit(f"FATAL: {staging_dir}: dataset_quality_report.json missing "
                         f"-- run scripts/qa_dataset.py first (§17 gate)")
    qa = json.loads(qa_path.read_text(encoding="utf-8"))
    if not qa.get("gates", {}).get("structural_validation_pass"):
        raise SystemExit(f"FATAL: {staging_dir}: §17 structural validation did NOT pass "
                         f"-- fix issues before composite build")

    recs = []
    with index_path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            e = json.loads(line)
            src = e.get("source")
            if src not in SOURCE_META:
                raise SystemExit(f"FATAL: unknown source '{src}' in {index_path}; "
                                 f"add it to SOURCE_META (no silent fallback)")
            img_path = (base / e["image_path"]).resolve()
            if not img_path.is_file():
                raise SystemExit(f"FATAL: image missing: {img_path}")
            label_path = (staging_dir / e["label_file"]).resolve()
            if not label_path.is_file():
                raise SystemExit(f"FATAL: label missing: {label_path}")
            stem = img_path.stem
            tag = SOURCE_META[src][0]
            recs.append({
                "image_id": e.get("image_id"),
                "source": src, "tag": tag,
                "source_split": e.get("source_split"),
                "image_path": img_path,
                "label_path": label_path,
                "composite_stem": f"{tag}__{stem}",
                "n_boxes": e.get("n_boxes"),
                "classes": e.get("classes") or [],
                "author": e.get("author") or None,
                "license": e.get("license") or SOURCE_META[src][1],
                "staging": staging_dir.name,
            })
    return recs


def hash_one(rec):
    rec = dict(rec)
    rec["sha256"] = sha256_file(rec["image_path"])
    rec["dhash"] = dhash64(rec["image_path"])
    return rec


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--staging-root", type=Path, default=DEFAULT_STAGING_ROOT)
    ap.add_argument("--sources", nargs="*", default=None,
                    help="staging dir names to include (default: all with index.jsonl + passing QA)")
    ap.add_argument("--base", type=Path, default=DEFAULT_BASE)
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--seed", default="prahaar-c5-v1")
    ap.add_argument("--near-dup-threshold", type=int, default=5)
    ap.add_argument("--group-by-author-max", type=int, default=64,
                    help="OI author union only for authors with <= N images in subset (default 64)")
    ap.add_argument("--link-mode", choices=("hardlink", "copy"), default="hardlink")
    ap.add_argument("--workers", type=int, default=12)
    ap.add_argument("--force", action="store_true",
                    help="delete existing --out dir before building (explicit)")
    args = ap.parse_args()

    t0 = time.time()
    staging_root = args.staging_root.resolve()
    base = args.base.resolve()
    out = args.out.resolve()

    # ---------- discover + load ----------
    if args.sources:
        names = args.sources
    else:
        names = sorted(p.parent.name for p in staging_root.glob("*/index.jsonl"))
    names = [n for n in names if (staging_root / n / "index.jsonl").is_file()]
    if not names:
        raise SystemExit("FATAL: no staging dirs found")
    print(f"sources: {names}")
    recs = []
    for n in names:
        r = load_staging(staging_root / n, base)
        print(f"  {n}: {len(r)} entries")
        recs.extend(r)

    # collision check on composite stems
    stems = Counter(r["composite_stem"] for r in recs)
    dup_stems = [s for s, c in stems.items() if c > 1]
    if dup_stems:
        raise SystemExit(f"FATAL: composite stem collisions ({len(dup_stems)}): {dup_stems[:10]}")
    # collision check on image_id (feeds split verification + dataset hash; must be unique)
    ids = Counter(r["image_id"] for r in recs)
    dup_ids = [s for s, c in ids.items() if c > 1]
    if dup_ids:
        raise SystemExit(f"FATAL: image_id collisions across sources ({len(dup_ids)}): {dup_ids[:10]}")

    # ---------- hashes ----------
    print(f"hashing {len(recs)} images (sha256 + dhash64)...")
    with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
        recs = list(ex.map(hash_one, recs))

    # ---------- groups (leakage control §19) ----------
    n = len(recs)
    sha_groups = defaultdict(list)
    for i, r in enumerate(recs):
        sha_groups[r["sha256"]].append(i)
    exact_pairs = []
    for v in sha_groups.values():
        for k in range(len(v) - 1):
            exact_pairs.append((v[0], v[k + 1]))

    import numpy as np
    H = np.asarray([r["dhash"] for r in recs], dtype=np.uint64)
    near_pairs = []
    for i in range(n):
        if i + 1 >= n:
            break
        d = np.bitwise_count(H[i] ^ H[i + 1:])
        for jj in np.nonzero(d <= args.near_dup_threshold)[0]:
            near_pairs.append((i, int(i + 1 + jj)))

    # author union (capped)
    author_idx = defaultdict(list)
    for i, r in enumerate(recs):
        if r["author"]:
            author_idx[r["author"]].append(i)
    author_pairs = []
    capped_authors = []
    for a, idxs in sorted(author_idx.items()):
        if len(idxs) < 2:
            continue
        if len(idxs) <= args.group_by_author_max:
            for k in range(len(idxs) - 1):
                author_pairs.append((idxs[0], idxs[k + 1]))
        else:
            capped_authors.append({"author": a, "images": len(idxs)})

    all_pairs = exact_pairs + near_pairs + author_pairs
    clusters = union_find_clusters(n, all_pairs) if all_pairs else []
    group_of = list(range(n))  # singleton default
    for gi, members in enumerate(clusters):
        for m in members:
            group_of[m] = members[0]  # canonical rep = smallest member index
    groups = defaultdict(list)
    for i in range(n):
        groups[group_of[i]].append(i)
    print(f"groups: {len(groups)} (exact_pairs {len(exact_pairs)}, near_pairs {len(near_pairs)}, "
          f"author_pairs {len(author_pairs)}, capped authors {len(capped_authors)})")

    # ---------- split by group ----------
    def gkey(rep):
        return hashlib.sha1(f"{args.seed}:{recs[rep]['image_id']}".encode()).hexdigest()

    ordered = sorted(groups.items(), key=lambda kv: (-len(kv[1]), gkey(kv[0])))
    counts = {s: 0 for s in SPLITS}
    total = n
    for rep, members in ordered:
        size = len(members)
        target = {s: (counts[s] + size) / (TARGETS[s] * total) for s in SPLITS}
        s = min(SPLITS, key=lambda x: (target[x], x))
        counts[s] += size
        for m in members:
            recs[m]["split"] = s

    # ---------- materialize ----------
    if out.exists():
        if not args.force:
            raise SystemExit(f"FATAL: {out} exists -- use --force to rebuild")
        print(f"--force: removing {out}")
        shutil.rmtree(out)
    for s in SPLITS:
        (out / "images" / s).mkdir(parents=True, exist_ok=True)
        (out / "labels" / s).mkdir(parents=True, exist_ok=True)

    linked = copied = fallback = 0
    fallback_samples = []
    for r in recs:
        s = r["split"]
        dst_img = out / "images" / s / f"{r['composite_stem']}{r['image_path'].suffix}"
        dst_lbl = out / "labels" / s / f"{r['composite_stem']}.txt"
        if args.link_mode == "hardlink":
            try:
                os.link(r["image_path"], dst_img)
                linked += 1
            except OSError as e:
                shutil.copy2(r["image_path"], dst_img)
                copied += 1
                fallback += 1
                if len(fallback_samples) < 20:
                    fallback_samples.append(f"{r['image_id']}: {e}")
        else:
            shutil.copy2(r["image_path"], dst_img)
            copied += 1
        shutil.copy2(r["label_path"], dst_lbl)

    # ---------- verify ----------
    problems = []
    # 1) file existence
    for r in recs:
        s = r["split"]
        if not (out / "images" / s / f"{r['composite_stem']}{r['image_path'].suffix}").is_file():
            problems.append(f"missing image {r['composite_stem']}")
        if not (out / "labels" / s / f"{r['composite_stem']}.txt").is_file():
            problems.append(f"missing label {r['composite_stem']}")
    # 2) leakage: every group must live in exactly one split
    split_of = {r["image_id"]: r["split"] for r in recs}
    cross_groups = []
    for rep, members in groups.items():
        ss = {recs[m]["split"] for m in members}
        if len(ss) > 1:
            cross_groups.append({"group_rep": recs[rep]["image_id"], "splits": sorted(ss),
                                 "n": len(members)})
    if cross_groups:
        problems.append(f"{len(cross_groups)} groups straddle splits")
    # 3) exact-dup groups straddling
    cross_sha = sum(1 for v in sha_groups.values()
                    if len({split_of[recs[i]["image_id"]] for i in v}) > 1)
    if cross_sha:
        problems.append(f"{cross_sha} exact-dup groups straddle splits (should be 0)")

    # ---------- artifacts ----------
    rep_by_stem = {recs[i]["composite_stem"]: recs[group_of[i]]["image_id"] for i in range(n)}
    manifest_path = out / "manifest.jsonl"
    with manifest_path.open("w", encoding="utf-8") as f:
        for r in sorted(recs, key=lambda x: (x["split"], x["composite_stem"])):
            f.write(json.dumps({
                "image_id": r["image_id"], "source": r["source"], "tag": r["tag"],
                "source_split": r["source_split"], "split": r["split"],
                "image": f"images/{r['split']}/{r['composite_stem']}{r['image_path'].suffix}",
                "label": f"labels/{r['split']}/{r['composite_stem']}.txt",
                "sha256": r["sha256"], "dhash64": f"{r['dhash']:016x}",
                "group_rep": rep_by_stem[r["composite_stem"]],
                "author": r["author"], "license": r["license"],
                "n_boxes": r["n_boxes"], "classes": r["classes"],
            }) + "\n")

    with (out / "data.yaml").open("w", encoding="utf-8") as f:
        f.write(f"# PRHAAR-C5-DETECTION (auto-generated by scripts/build_composite.py)\n")
        f.write(f"# taxonomy v{PRHAAR_C5_TAXONOMY_VERSION}; conditional classes: {sorted(CONDITIONAL_CLASSES)}\n")
        f.write(f"path: {out.as_posix()}\n")
        f.write("train: images/train\nval: images/val\ntest: images/test\n")
        f.write(f"nc: {len(CLASSES)}\nnames:\n")
        for i, c in enumerate(CLASSES):
            f.write(f"  {i}: {c}\n")

    # canonical dataset hash: sha256 over sorted (image_id, sha256)
    h = hashlib.sha256()
    for r in sorted(recs, key=lambda x: x["image_id"]):
        h.update(f"{r['image_id']}\t{r['sha256']}\n".encode())
    dataset_sha = h.hexdigest()
    (out / "dataset_hash.txt").write_text(dataset_sha + "\n", encoding="utf-8")

    # ---------- report ----------
    per_split = {s: Counter() for s in SPLITS}
    per_split_boxes = {s: 0 for s in SPLITS}
    per_source_split = {s: Counter() for s in SPLITS}
    cls_split = {c: Counter() for c in CLASSES}
    for r in recs:
        s = r["split"]
        per_split[s]["images"] += 1
        per_split_boxes[s] += r["n_boxes"] or 0
        per_source_split[s][r["source"]] += 1
    # per-class boxes per split: recount from labels (join to recs by split)
    for r in recs:
        s = r["split"]
        labels_text = r["label_path"].read_text(encoding="utf-8")
        for line in labels_text.splitlines():
            line = line.strip()
            if not line:
                continue
            cid = int(float(line.split()[0]))
            cls_split[CLASSES[cid]][s] += 1
    n_groups_per_split = {s: len({group_of[i] for i in range(n) if recs[i]["split"] == s})
                          for s in SPLITS}

    report = {
        "spec": "PRHAAR C5 sections 18-20 (duplicate control, leakage prevention, grouped split)",
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "taxonomy_version": PRHAAR_C5_TAXONOMY_VERSION,
        "seed": args.seed,
        "staging_sources": names,
        "out_dir": str(out),
        "counts": {
            "images": n,
            "groups": len(groups),
            "boxes": sum((r["n_boxes"] or 0) for r in recs),
        },
        "per_split": {
            s: {"images": per_split[s]["images"],
                "boxes": per_split_boxes[s],
                "n_groups": n_groups_per_split[s],
                "sources": dict(sorted(per_source_split[s].items()))}
            for s in SPLITS
        },
        "per_class_boxes_per_split": {c: dict(cls_split[c]) for c in CLASSES},
        "conditional_class_boxes": {
            c: sum(cls_split[c].values()) for c in CONDITIONAL_CLASSES if sum(cls_split[c].values())},
        "grouping": {
            "exact_dup_pairs": len(exact_pairs),
            "near_dup_pairs_dhash64_le": {"threshold": args.near_dup_threshold, "pairs": len(near_pairs)},
            "author_pairs": len(author_pairs),
            "author_union_cap": args.group_by_author_max,
            "authors_capped": capped_authors,
        },
        "materialization": {
            "link_mode": args.link_mode, "hardlinked": linked,
            "copied": copied, "hardlink_fallbacks_to_copy": fallback,
            "fallback_samples": fallback_samples,
        },
        "leakage_check": {
            "cross_split_groups": cross_groups,
            "cross_split_exact_dup_groups": cross_sha,
            "pass": (not cross_groups) and (cross_sha == 0) and (not problems),
        },
        "problems": problems,
        "prhaar_hard_test": "not built here -- Layer D requires PRHAAR/SSB footage (user action; catalog section 4); built in task #34",
        "limitations": [
            "Open Images has no capture-session metadata; leakage control relies on near-dup clustering + capped author union (proxy only)",
            "Poribohon-BD/auto-rickshaw exports have no author/video metadata; near-dup clustering is the only grouping signal",
            "source_split (original Roboflow/OI split) is NOT preserved -- splits are rebuilt by group per section 19/20",
            "exact-duplicate images are retained (same group, one split); dropped only if labels disagree (not automated here)",
        ],
    }
    report_path = out / "split_report.json"
    with report_path.open("w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        f.write("\n")

    print(f"\nbuilt -> {out}")
    print(f"  images {n} | groups {len(groups)} | boxes {report['counts']['boxes']}")
    for s in SPLITS:
        print(f"  {s}: {per_split[s]['images']} images, {per_split_boxes[s]} boxes, "
              f"{n_groups_per_split[s]} groups")
    print(f"  leakage pass: {report['leakage_check']['pass']} | problems: {len(problems)}")
    if problems:
        for p in problems[:10]:
            print(f"    PROBLEM: {p}")
    print(f"  dataset hash: {dataset_sha[:16]}...")
    print(f"  runtime {time.time() - t0:.1f}s")
    return 0 if report["leakage_check"]["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
