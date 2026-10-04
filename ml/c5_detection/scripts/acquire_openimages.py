#!/usr/bin/env python
"""
PRHAAR C5 -- controlled Open Images V7 acquisition (Layer-B supplemental, generic).

Purpose
  Deterministically sample a bounded subset of Open Images boxable classes that map
  to the PRHAAR canonical taxonomy, download the images, and write:
    - annotations_raw.jsonl   (per-image, all boxes of target classes, raw OI flags)
    - acquisition_manifest.jsonl (per-image: path, sha256, license, author, urls)
    - acquisition_summary.json (exact counts per class/split, license histogram)
    - _metadata/file_hashes.json (sha256 of every metadata CSV used)

Design constraints (C5 spec)
  - No fabricated counts: every number written is measured.
  - Deterministic sampling (seed + sha1), reproducible.
  - Per-image license captured (OI images are Flickr, per-image license in the
    images-with-rotation CSVs; annotations are CC-BY-4.0).
  - Occlusion/truncation flags are PRESERVED (we do not discard them; downstream
    selection is a staging decision, not an acquisition decision).
  - Images whose license row cannot be found are DROPPED and counted, never guessed.

Source files (verified live 2026-10-03, as linked by the OI v7 download page):
  classes   : v7/oidv7-class-descriptions-boxable.csv
  train bbox: v6/oidv6-train-annotations-bbox.csv
  val bbox  : v5/validation-annotations-bbox.csv
  test bbox : v5/test-annotations-bbox.csv
  train info: v6/oidv6-train-images-with-labels-with-rotation.csv
              + 2018_04/train/train-images-boxable-with-rotation.csv
                (LAZY merge fallback: downloaded only if some kept train image
                 has no license row in the v6 file)
  val info  : 2018_04/validation/validation-images-with-rotation.csv
  test info : 2018_04/test/test-images-with-rotation.csv

Image bytes: path-style HTTPS GET against
https://s3.amazonaws.com/open-images-dataset/{split}/{id}.jpg (keep-alive,
retry on 429/5xx), fallback boto3 UNSIGNED on the same bucket. The GCS mirror
https://storage.googleapis.com/open-images-dataset/... is NOT usable: it answers
403 UserProjectAccountProblem ("closed billing account") for every image id.
Measured transports and the exact error bodies are recorded at download_one().

Usage
  smoke : python acquire_openimages.py --smoke
  full  : python acquire_openimages.py --workers 8
"""

from __future__ import annotations

import argparse
import concurrent.futures as cf
import hashlib
import io
import json
import logging
import os
import sys
import threading
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
import requests

LOG = logging.getLogger("acquire_openimages")
IST = timezone(timedelta(hours=5, minutes=30))

HERE = Path(__file__).resolve()
C5_ROOT = HERE.parents[1]                      # ml/c5_detection
DEFAULT_DEST = C5_ROOT / "datasets" / "sources" / "openimages_v7"
GCS_BASE = "https://storage.googleapis.com/openimages"
IMAGE_BUCKET = "open-images-dataset"           # S3-compatible public bucket (images)

# OI boxable class -> PRHAAR canonical class (spec 7). Van -> LIGHT_VEHICLE,
# Cattle/Sheep/Goat/Horse/Dog -> ANIMAL. Mapping recorded, not applied here.
TARGET_CLASSES = {
    "Person": "PERSON",
    "Bicycle": "BICYCLE",
    "Car": "CAR",
    "Motorcycle": "MOTORCYCLE",
    "Bus": "BUS",
    "Truck": "TRUCK",
    "Van": "LIGHT_VEHICLE",
    "Cattle": "ANIMAL",
    "Sheep": "ANIMAL",
    "Goat": "ANIMAL",
    "Horse": "ANIMAL",
    "Dog": "ANIMAL",
}

# per-class total caps (across splits); chosen so OI stays supplemental and
# no single class dominates. Tractor / AUTO_RICKSHAW / buffalo: NOT in OI.
DEFAULT_CAPS = {
    "Person": 2000, "Car": 2500, "Truck": 2000, "Bus": 1500,
    "Motorcycle": 1500, "Bicycle": 1500, "Van": 1500,
    "Dog": 1000, "Cattle": 1000, "Goat": 1000, "Sheep": 1000, "Horse": 700,
}
SPLIT_FRACTION = {"train": 0.70, "validation": 0.15, "test": 0.15}

METADATA_FILES = {
    "class_descriptions": "v7/oidv7-class-descriptions-boxable.csv",
    "train_bbox": "v6/oidv6-train-annotations-bbox.csv",
    "validation_bbox": "v5/validation-annotations-bbox.csv",
    "test_bbox": "v5/test-annotations-bbox.csv",
    "train_info_v6": "v6/oidv6-train-images-with-labels-with-rotation.csv",
    "train_info_v4": "2018_04/train/train-images-boxable-with-rotation.csv",
    "validation_info": "2018_04/validation/validation-images-with-rotation.csv",
    "test_info": "2018_04/test/test-images-with-rotation.csv",
}
BBOX_COLS = ["ImageID", "LabelName", "XMin", "XMax", "YMin", "YMax",
             "IsOccluded", "IsTruncated", "IsGroupOf", "IsDepiction", "IsInside"]
BBOX_DTYPES = {"ImageID": "str", "LabelName": "str", "XMin": "float32", "XMax": "float32",
               "YMin": "float32", "YMax": "float32", "IsOccluded": "int8",
               "IsTruncated": "int8", "IsGroupOf": "int8", "IsDepiction": "int8",
               "IsInside": "int8"}
INFO_COLS = ["ImageID", "Subset", "OriginalURL", "OriginalLandingURL", "License",
             "AuthorProfileURL", "Author", "Title", "Rotation"]
CHUNK_ROWS = 400_000


def sha1_frac(*parts: str) -> float:
    h = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def now_ist() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S %z")


# --------------------------------------------------------------------------- #
# metadata download
# --------------------------------------------------------------------------- #
class _IncompleteDownload(Exception):
    """Raised when a metadata stream ends short of the server-declared size."""


def _download_metadata_one(url: str, out: Path, tmp: Path) -> None:
    """One download attempt for a metadata CSV, resuming from an existing .part.

    GCS honours HTTP Range, so an interrupted multi-GB download continues from
    the stored byte offset instead of restarting. Never appends to a stream the
    server did not position (a 200 answer to a Range request means "here is the
    whole file" -> restart from 0), because appending there would silently
    corrupt the CSV.
    """
    have = tmp.stat().st_size if tmp.exists() else 0
    headers = {"Range": f"bytes={have}-"} if have else {}
    LOG.info("downloading %s -> %s (%s)", url, out.name,
             f"resuming from {have / 1e6:.1f} MB" if have else "fresh")
    t0 = time.time()
    # progress marks are relative to the resumed offset, otherwise a resume that
    # starts past 256 MB would log every single 1 MB chunk
    next_report = have + (256 << 20)
    with requests.get(url, stream=True, timeout=(30, 300), headers=headers) as r:
        if have and r.status_code == 416:
            LOG.info("  server: range not satisfiable -- %s already complete", tmp.name)
            os.replace(tmp, out)
            return
        r.raise_for_status()
        if have and r.status_code != 206:
            LOG.warning("  server answered %s to Range request -- restarting from 0",
                        r.status_code)
            have = 0
        expected = None
        cr = r.headers.get("Content-Range")
        if cr and "/" in cr:
            tail = cr.rsplit("/", 1)[1].strip()
            expected = int(tail) if tail.isdigit() else None
        if expected is None:
            cl = r.headers.get("Content-Length")
            expected = (have + int(cl)) if (cl and cl.isdigit()) else None
        written = have
        with open(tmp, "ab" if have else "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
                written += len(chunk)
                if written >= next_report:
                    LOG.info("  ... %.0f MB (%.0fs elapsed)", written / 1e6, time.time() - t0)
                    next_report += 256 << 20
    if expected is not None and written != expected:
        raise _IncompleteDownload(f"{out.name}: got {written} of {expected} bytes")
    os.replace(tmp, out)
    LOG.info("  %.1f MB in %.0fs", out.stat().st_size / 1e6, time.time() - t0)


def ensure_metadata(meta_dir: Path, needed: list[str], force: bool) -> dict:
    """Acquire metadata CSVs with resume + retry; hash only COMPLETE files.

    A failed attempt keeps its .part so the next attempt resumes; after
    MAX_ATTEMPTS the run aborts loudly (spec section 46: no silent fallback,
    spec section 10: never report a partial file as acquired).
    """
    MAX_ATTEMPTS = 6
    meta_dir.mkdir(parents=True, exist_ok=True)
    hashes = {}
    for key in needed:
        rel = METADATA_FILES[key]
        out = meta_dir / Path(rel).name
        tmp = out.with_suffix(out.suffix + ".part")
        if force and tmp.exists():
            tmp.unlink()
        if force or not out.exists() or out.stat().st_size == 0:
            url = f"{GCS_BASE}/{rel}"
            last_err = None
            for attempt in range(1, MAX_ATTEMPTS + 1):
                try:
                    _download_metadata_one(url, out, tmp)
                    last_err = None
                    break
                except (_IncompleteDownload, requests.RequestException, OSError) as e:
                    last_err = e
                    kept = tmp.stat().st_size if tmp.exists() else 0
                    LOG.warning("  attempt %d/%d failed (%s) -- %.1f MB kept for resume",
                                attempt, MAX_ATTEMPTS, e, kept / 1e6)
                    if attempt < MAX_ATTEMPTS:
                        time.sleep(min(60, 5 * attempt))
            if last_err is not None:
                raise SystemExit(
                    f"metadata download failed after {MAX_ATTEMPTS} attempts: {url} ({last_err}). "
                    f"Partial file kept at {tmp} -- relaunch to resume. NOT counted as acquired.")
        hashes[out.name] = {"source": f"{GCS_BASE}/{rel}",
                            "sha256": sha256_file(out),
                            "bytes": out.stat().st_size}
    return hashes


def load_class_mids(class_csv: Path) -> dict[str, str]:
    df = pd.read_csv(class_csv, header=None, names=["mid", "name"])
    name_to_mid = dict(zip(df["name"], df["mid"]))
    missing = [c for c in TARGET_CLASSES if c not in name_to_mid]
    if missing:
        raise SystemExit(f"OI class names not found in class CSV: {missing}")
    return {c: name_to_mid[c] for c in TARGET_CLASSES}


# --------------------------------------------------------------------------- #
# bbox scanning (split-aware)
# --------------------------------------------------------------------------- #
def scan_train(bbox_csv: Path, cls_mid: dict[str, str], caps: dict[str, int],
               seed: str, max_chunks: int | None):
    """3 passes over the big train CSV: count -> sample -> collect full rows."""
    mid_cls = {m: c for c, m in cls_mid.items()}
    mids = set(mid_cls)

    # pass 1: approximate unique-image counts per class
    counts = {c: 0 for c in cls_mid}
    reader = pd.read_csv(bbox_csv, usecols=["ImageID", "LabelName"], dtype=BBOX_DTYPES,
                         chunksize=CHUNK_ROWS)
    for i, chunk in enumerate(reader):
        if max_chunks is not None and i >= max_chunks:
            break
        s = chunk[chunk["LabelName"].isin(mids)]
        if not s.empty:
            u = s.drop_duplicates(["LabelName", "ImageID"])
            for mid, n in u.groupby("LabelName").size().items():
                counts[mid_cls[mid]] += int(n)
    LOG.info("pass1 train approx image counts: %s", counts)

    # pass 2: deterministic per-(class,image) sampling
    rates = {c: min(1.0, (caps[c] * 1.15) / max(counts[c], 1)) for c in cls_mid}
    LOG.info("pass2 sampling rates: %s", {c: round(r, 4) for c, r in rates.items()})
    sampled_ids = {c: set() for c in cls_mid}
    reader = pd.read_csv(bbox_csv, usecols=["ImageID", "LabelName"], dtype=BBOX_DTYPES,
                         chunksize=CHUNK_ROWS)
    for i, chunk in enumerate(reader):
        if max_chunks is not None and i >= max_chunks:
            break
        s = chunk[chunk["LabelName"].isin(mids)]
        if s.empty:
            continue
        cls_of = s["LabelName"].map(mid_cls)
        keep = [sha1_frac(seed, c, img) < rates[c]
                for c, img in zip(cls_of, s["ImageID"])]
        s = s[pd.Series(keep, index=s.index)]
        for c, g in s.groupby(cls_of[s.index]):
            sampled_ids[c].update(g["ImageID"].tolist())
    if max_chunks is not None:
        LOG.warning("max_chunks=%s used: counts/rates are partial (test mode)", max_chunks)

    # cap per class, ordered deterministically by hash
    kept = set()
    per_class_kept = {}
    for c in cls_mid:
        ids = sorted(sampled_ids[c], key=lambda img: (sha1_frac(seed, c, img), img))
        take = ids[: caps[c]]
        per_class_kept[c] = len(take)
        kept.update(take)
    LOG.info("pass2 kept per class (train): %s; union=%d", per_class_kept, len(kept))

    # pass 3: collect ALL target rows for union images (all classes, full boxes)
    rows = {c: [] for c in cls_mid}
    reader = pd.read_csv(bbox_csv, usecols=BBOX_COLS, dtype=BBOX_DTYPES,
                         chunksize=CHUNK_ROWS)
    for i, chunk in enumerate(reader):
        if max_chunks is not None and i >= max_chunks:
            break
        s = chunk[chunk["ImageID"].isin(kept) & chunk["LabelName"].isin(mids)]
        if not s.empty:
            for mid, g in s.groupby("LabelName"):
                rows[mid_cls[mid]].extend(g.itertuples(index=False, name=None))
    all_rows = [r for c in rows for r in rows[c]]
    return counts, per_class_kept, all_rows


def scan_small(bbox_csv: Path, cls_mid: dict[str, str], caps: dict[str, int],
               seed: str):
    """val/test: single pass, collect all target rows, then cap."""
    mid_cls = {m: c for c, m in cls_mid.items()}
    mids = set(mid_cls)
    frames = []
    for chunk in pd.read_csv(bbox_csv, usecols=BBOX_COLS, dtype=BBOX_DTYPES,
                             chunksize=CHUNK_ROWS):
        s = chunk[chunk["LabelName"].isin(mids)]
        if not s.empty:
            frames.append(s)
    df = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=BBOX_COLS)
    counts = {c: 0 for c in cls_mid}
    for mid, n in df.drop_duplicates(["LabelName", "ImageID"]).groupby("LabelName").size().items():
        counts[mid_cls[mid]] = int(n)
    kept = set()
    per_class_kept = {}
    for c, mid in cls_mid.items():
        ids = sorted(df.loc[df["LabelName"] == mid, "ImageID"].unique(),
                     key=lambda img: (sha1_frac(seed, c, img), img))
        take = ids[: caps[c]]
        per_class_kept[c] = len(take)
        kept.update(take)
    df = df[df["ImageID"].isin(kept)]
    return counts, per_class_kept, list(df.itertuples(index=False, name=None))


# --------------------------------------------------------------------------- #
# info CSV (license lookup) + rows -> per-image records
# --------------------------------------------------------------------------- #
def load_info_rows(info_csvs: list[Path], image_ids: set[str]) -> dict[str, dict]:
    """Resolve per-image license/provenance rows from the OI *-images-with-rotation CSVs.

    Two efficiency guards matter here on an 8 GB machine: only INFO_COLS are
    parsed (these files are ~2.7 GB with ~20 columns), and once every requested
    ImageID is resolved the remaining files/chunks are skipped instead of being
    streamed pointlessly. Results are identical either way -- v6 is consulted
    before the v4 fallback, and the first row found for an ID wins.
    """
    found = {}
    keep = set(INFO_COLS)
    for csv in info_csvs:
        if not (image_ids - set(found)):
            LOG.info("all %d license rows resolved -- skipping %s", len(found), csv.name)
            continue
        reader = pd.read_csv(csv, dtype="str", chunksize=CHUNK_ROWS,
                             usecols=lambda c: c in keep)
        try:
            for chunk in reader:
                cols = [c for c in INFO_COLS if c in chunk.columns]
                s = chunk[chunk["ImageID"].isin(image_ids - set(found))]
                for row in s[cols].itertuples(index=False, name=None):
                    rec = dict(zip(cols, row))
                    found[rec["ImageID"]] = rec
                if not (image_ids - set(found)):
                    LOG.info("all %d license rows resolved within %s", len(found), csv.name)
                    break
        finally:
            reader.close()  # do not leave a Windows handle open on a multi-GB CSV
        LOG.info("license rows resolved so far: %d (from %s)", len(found), csv.name)
    return found


def rows_to_records(all_rows: list[tuple], split: str):
    """(ImageID, LabelName, XMin, XMax, YMin, YMax, occ, trunc, grp, dep, ins)"""
    mid_cls = {m: c for c, m in CURRENT_MIDS.items()}
    per_image = {}
    for (img, mid, xmin, xmax, ymin, ymax, occ, trunc, grp, dep, ins) in all_rows:
        rec = per_image.setdefault(img, {"image_id": img, "oi_split": split,
                                         "boxes": [], "classes": set()})
        cname = mid_cls[mid]
        rec["classes"].add(cname)
        rec["boxes"].append({
            "oi_class": cname, "mid": mid,
            "xmin": float(xmin), "xmax": float(xmax),
            "ymin": float(ymin), "ymax": float(ymax),
            "occluded": int(occ), "truncated": int(trunc), "group_of": int(grp),
            "depiction": int(dep), "inside": int(ins)})
    for rec in per_image.values():
        rec["classes"] = sorted(rec["classes"])
        rec["n_boxes"] = len(rec["boxes"])
    return per_image


# --------------------------------------------------------------------------- #
# image download
#
# Transport order is MEASURED on this machine/network, not assumed
# (2026-10-04, while a concurrent metadata stream was also running):
#   https://s3.amazonaws.com/open-images-dataset/train/<id>.jpg  -> 200, 12/12 ok,
#       12 threads: 3.56 MB in 5.5 s  = 0.652 MB/s aggregate
#   boto3 UNSIGNED s3.download_fileobj (same bucket, vhost endpoint) -> 12/12 ok,
#       12 threads: 4.18 MB in 10.0 s = 0.419 MB/s aggregate
#   https://storage.googleapis.com/open-images-dataset/train/<id>.jpg -> 403 for
#       EVERY id tried, body: UserProjectAccountProblem "The project to be billed
#       is associated with a closed billing account." => the GCS mirror of the
#       image bucket is dead; it was the old "fallback" and could never work.
#   https://storage.googleapis.com/openimages/train/<id>.jpg -> 403 AccessDenied.
# So: path-style HTTPS GET first (thread-local Session => keep-alive, which is
# where most of the win comes from), boto3 UNSIGNED as the real fallback. The
# method actually used is recorded per image in acquisition_manifest.jsonl, and a
# failure records BOTH exception types -- never a silent success (spec 46/61).
# --------------------------------------------------------------------------- #
IMAGE_HTTPS_BASE = f"https://s3.amazonaws.com/{IMAGE_BUCKET}"
_TLS = threading.local()


def _tls_session() -> requests.Session:
    """One keep-alive Session per worker thread (requests.Session is not thread-safe)."""
    s = getattr(_TLS, "session", None)
    if s is None:
        s = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=2, pool_maxsize=2)
        s.mount("https://", adapter)
        s.mount("http://", adapter)
        _TLS.session = s
    return s


def make_s3():
    import boto3, botocore
    return boto3.client("s3", config=botocore.config.Config(
        signature_version=botocore.UNSIGNED, retries={"max_attempts": 3}))


def _fetch_https(url: str, tmp: Path, attempts: int = 3) -> None:
    """GET to a temp file, retrying transient throttling before giving up.

    Measured on this link (2026-10-04): 8 concurrent keep-alive connections
    sustained 0.905 MB/s with 24/24 successes, while a 12-connection run saw
    failures that forced the slower boto3 path (0.155 MB/s aggregate). So
    retry-with-backoff buys more than extra parallelism here.
    """
    last: Exception | None = None
    for i in range(1, attempts + 1):
        try:
            with _tls_session().get(url, stream=True, timeout=(15, 120)) as r:
                if r.status_code in (429, 500, 502, 503, 504):
                    last = requests.HTTPError(f"HTTP {r.status_code}", response=r)
                else:
                    r.raise_for_status()
                    with open(tmp, "wb") as f:
                        for chunk in r.iter_content(1 << 18):
                            f.write(chunk)
                    return
        except (requests.Timeout, requests.ConnectionError) as e:
            last = e
        time.sleep(min(8.0, 0.7 * i))
    raise last if last is not None else requests.RequestException(f"unreachable: {url}")


def download_one(s3, split: str, image_id: str, out_path: Path) -> tuple[bool, str, int]:
    if out_path.exists() and out_path.stat().st_size > 0:
        with open(out_path, "rb") as f:
            if f.read(2) == b"\xff\xd8":
                return True, "cached", out_path.stat().st_size
    # created here, not only in main(): without it the per-split directory is
    # missing and BOTH transports fail with FileNotFoundError, which would be
    # counted as a download failure for every single image (spec 10/61: a
    # plumbing bug must never masquerade as "source unavailable").
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(".part")
    try:
        _fetch_https(f"{IMAGE_HTTPS_BASE}/{split}/{image_id}.jpg", tmp)
        method = "https-s3-pathstyle"
    except Exception as e1:  # fallback: boto3 UNSIGNED against the same bucket
        try:
            with open(tmp, "wb") as f:
                s3.download_fileobj(IMAGE_BUCKET, f"{split}/{image_id}.jpg", f)
            method = "s3-unsigned"
        except Exception as e2:
            tmp.unlink(missing_ok=True)
            return False, f"{type(e1).__name__}/{type(e2).__name__}", 0
    with open(tmp, "rb") as f:
        if f.read(2) != b"\xff\xd8":
            tmp.unlink(missing_ok=True)
            return False, "not-jpeg", 0
    os.replace(tmp, out_path)
    return True, method, out_path.stat().st_size


# --------------------------------------------------------------------------- #
def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dest", type=Path, default=DEFAULT_DEST)
    ap.add_argument("--seed", default="prahaar-c5-v1")
    ap.add_argument("--caps", default="", help="class:cap,class:cap overrides")
    ap.add_argument("--splits", nargs="+", default=["train", "validation", "test"],
                    choices=["train", "validation", "test"])
    ap.add_argument("--workers", type=int, default=8,
                    help="concurrent image downloads (8 measured best on this link: "
                         "0.905 MB/s at 8 vs 0.155 MB/s at 12, which throttled)")
    ap.add_argument("--smoke", action="store_true",
                    help="tiny run: cap 3/class/split, max 2 chunks per CSV")
    ap.add_argument("--force-metadata", action="store_true")
    ap.add_argument("--max-chunks", type=int, default=None, help=argparse.SUPPRESS)
    ap.add_argument("--skip-download", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s")
    global CURRENT_MIDS

    caps = dict(DEFAULT_CAPS)
    for kv in filter(None, args.caps.split(",")):
        k, v = kv.split(":")
        caps[k] = int(v)
    if args.smoke:
        caps = {c: 3 for c in caps}
        args.max_chunks = args.max_chunks or 2
        args.workers = min(args.workers, 8)

    dest: Path = args.dest
    meta_dir = dest / "_metadata"
    (dest / "images").mkdir(parents=True, exist_ok=True)
    (dest / "annotations").mkdir(parents=True, exist_ok=True)

    t_start = time.time()
    run_meta = {"run_started_ist": now_ist(), "seed": args.seed,
                "caps": caps, "splits": args.splits, "smoke": bool(args.smoke)}

    needed = ["class_descriptions"]
    for s in args.splits:
        needed.append(f"{s}_bbox")
        needed.append({"train": None, "validation": "validation_info",
                       "test": "test_info"}[s] or "train_info_v6")
    needed = [n for n in needed if n]
    # NOTE: train_info_v4 ("train-images-boxable-with-rotation.csv", ~1.3 GB) is a
    # license FALLBACK for train images that the v6 info file does not cover. It is
    # acquired lazily below, only if some kept train image actually has no license
    # row -- otherwise the run pays 1.3 GB of download for nothing.
    hashes = ensure_metadata(meta_dir, needed, args.force_metadata)
    (meta_dir / "file_hashes.json").write_text(json.dumps(hashes, indent=2))

    cls_mid = load_class_mids(meta_dir / "oidv7-class-descriptions-boxable.csv")
    CURRENT_MIDS = cls_mid
    LOG.info("target classes resolved: %s", cls_mid)

    per_split_rows = {}
    split_stats = {}
    for split in args.splits:
        bbox_csv = meta_dir / Path(METADATA_FILES[f"{split}_bbox"]).name
        split_caps = {c: max(1, round(caps[c] * SPLIT_FRACTION[split]))
                      for c in cls_mid} if not args.smoke else {c: caps[c] for c in cls_mid}
        split_caps = {c: min(split_caps[c], caps[c]) for c in cls_mid}
        LOG.info("=== %s: scanning %s (caps %s)", split, bbox_csv.name, split_caps)
        if split == "train":
            counts, kept, rows = scan_train(bbox_csv, cls_mid, split_caps,
                                            args.seed, args.max_chunks)
        else:
            counts, kept, rows = scan_small(bbox_csv, cls_mid, split_caps, args.seed)
        per_split_rows[split] = rows
        split_stats[split] = {"available_images": counts, "kept_per_class": kept,
                              "kept_rows": len(rows)}
        LOG.info("%s done: kept rows=%d stats=%s", split, len(rows), kept)

    records = {}
    for split, rows in per_split_rows.items():
        records.update(rows_to_records(rows, split))
    LOG.info("union images across splits: %d", len(records))

    # license lookup
    info_files = []
    if "train" in args.splits:
        info_files.append(meta_dir / "oidv6-train-images-with-labels-with-rotation.csv")
    if "validation" in args.splits:
        info_files.append(meta_dir / "validation-images-with-rotation.csv")
    if "test" in args.splits:
        info_files.append(meta_dir / "test-images-with-rotation.csv")
    info = load_info_rows(info_files, set(records))

    missing = set(records) - set(info)
    if missing and "train" in args.splits:
        # Lazy fallback: only now pay for the ~1.3 GB v4 info CSV. The v6 file
        # already covers the vast majority of train IDs, so in the common case
        # this block never runs.
        v4_rel = METADATA_FILES["train_info_v4"]
        LOG.info("%d kept image(s) have no license row in the v6 info files -- "
                 "acquiring train_info_v4 fallback (%s)", len(missing), Path(v4_rel).name)
        hashes.update(ensure_metadata(meta_dir, ["train_info_v4"], args.force_metadata))
        (meta_dir / "file_hashes.json").write_text(json.dumps(hashes, indent=2))
        info.update(load_info_rows([meta_dir / Path(v4_rel).name], missing))
        LOG.info("after v4 fallback: license rows for %d/%d kept images",
                 len(info), len(records))

    dropped_no_license = sorted(set(records) - set(info))
    for img in dropped_no_license:
        records.pop(img, None)
    LOG.info("license rows found for %d; dropped (no license row): %d",
             len(info), len(dropped_no_license))

    # download
    results = {}
    if not args.skip_download and records:
        s3 = make_s3()
        items = [(rec["oi_split"], img) for img, rec in sorted(records.items())]
        LOG.info("downloading %d images with %d workers ...", len(items), args.workers)
        t0 = time.time()
        with cf.ThreadPoolExecutor(max_workers=args.workers) as ex:
            futs = {ex.submit(download_one, s3, split, img,
                              dest / "images" / split / f"{img}.jpg"): (split, img)
                    for split, img in items}
            done = 0
            for fut in cf.as_completed(futs):
                split, img = futs[fut]
                ok, method, size = fut.result()
                results[img] = {"ok": ok, "method": method, "bytes": size}
                done += 1
                if done % 500 == 0 or done == len(items):
                    LOG.info("  %d/%d downloaded (%.0fs)", done, len(items), time.time() - t0)

    # write artifacts
    manifest_path = dest / "acquisition_manifest.jsonl"
    ann_path = dest / "annotations" / "annotations_raw.jsonl"
    n_ok = n_fail = 0
    lic_hist: dict[str, int] = {}
    class_hist: dict[str, int] = {}
    total_bytes = 0
    with open(manifest_path, "w", encoding="utf-8") as mf, \
         open(ann_path, "w", encoding="utf-8") as af:
        for img, rec in sorted(records.items()):
            res = results.get(img, {"ok": False, "method": "skipped", "bytes": 0})
            path = dest / "images" / rec["oi_split"] / f"{img}.jpg"
            lic = info.get(img, {}).get("License", "UNKNOWN")
            entry = {
                "image_id": img, "oi_split": rec["oi_split"],
                "path": str(path.relative_to(dest)).replace("\\", "/"),
                "downloaded": res["ok"], "method": res["method"],
                "bytes": res["bytes"], "sha256": sha256_file(path) if path.exists() else None,
                "license": lic,
                "author": info.get(img, {}).get("Author"),
                "title": info.get(img, {}).get("Title"),
                "original_url": info.get(img, {}).get("OriginalURL"),
                "landing_url": info.get(img, {}).get("OriginalLandingURL"),
                "n_boxes": rec["n_boxes"], "classes": rec["classes"],
            }
            mf.write(json.dumps(entry, ensure_ascii=False) + "\n")
            af.write(json.dumps(rec, ensure_ascii=False) + "\n")
            if res["ok"]:
                n_ok += 1
                lic_hist[lic] = lic_hist.get(lic, 0) + 1
                total_bytes += res["bytes"]
                for c in rec["classes"]:
                    class_hist[c] = class_hist.get(c, 0) + 1
            else:
                n_fail += 1

    summary = {
        "artifact": "PRHAAR C5 Open Images V7 acquisition",
        "run_started_ist": run_meta["run_started_ist"], "run_finished_ist": now_ist(),
        "elapsed_s": round(time.time() - t_start, 1),
        "seed": args.seed, "caps": caps, "smoke": run_meta["smoke"],
        "split_stats": split_stats,
        "images_union_before_license_drop": len(records) + len(dropped_no_license),
        "dropped_no_license_row": {"count": len(dropped_no_license),
                                   "sample_ids": dropped_no_license[:20]},
        "downloaded_ok": n_ok, "downloaded_failed": n_fail,
        "total_bytes": total_bytes,
        "license_histogram": dict(sorted(lic_hist.items(), key=lambda kv: -kv[1])),
        "per_class_downloaded_images": dict(sorted(class_hist.items())),
        "annotations_raw_sha256": sha256_file(ann_path),
        "manifest_sha256": sha256_file(manifest_path),
        "metadata_hashes": hashes,
        "target_class_to_canonical": TARGET_CLASSES,
    }
    (dest / "acquisition_summary.json").write_text(json.dumps(summary, indent=2))
    LOG.info("DONE ok=%d failed=%d bytes=%.1f MB", n_ok, n_fail, total_bytes / 1e6)
    LOG.info("summary -> %s", dest / "acquisition_summary.json")
    return 0 if n_fail == 0 else 1


CURRENT_MIDS: dict[str, str] = {}

if __name__ == "__main__":
    sys.exit(main())
