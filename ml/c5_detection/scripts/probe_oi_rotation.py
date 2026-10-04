#!/usr/bin/env python
"""
PRHAAR C5 -- Open Images V7 rotation & integrity probe (one-off investigation).

Two questions this answers with MEASURED evidence, before any full acquisition run:

Q1. Are the bytes we download from
    https://s3.amazonaws.com/open-images-dataset/{split}/{id}.jpg
    the *original* Flickr files? The *-images-with-rotation.csv files carry
    OriginalMD5 and OriginalSize per image, so this is directly testable:
    recompute MD5 locally and compare. (It matters because OI documents
    "Rotation" as the CCW degrees needed "to match the Flickr user intended
    orientation", i.e. the stored file may not be upright.)

Q2. In which coordinate frame are the bounding boxes? Normalized [0,1] boxes
    look plausible either way, so this is settled visually: for images whose
    Rotation is 90/180/270 we draw the OI boxes twice -- once on the raw stored
    pixels, once on the image rotated CCW by the documented angle -- and write a
    labelled montage a human can inspect. Whichever panel has boxes sitting on
    the objects is the frame the annotations use.

Measured rotation prevalence (full info CSVs, this script's sources):
    validation (41,620 rows): 0.0 -> 35,826 | unknown/blank -> 5,318 | 270 -> 333 | 90 -> 113 | 180 -> 30
    test      (125,436 rows): 0.0 -> 107,668 | unknown/blank -> 16,258 | 270 -> 1,036 | 90 -> 377 | 180 -> 97
So ~1.1-1.2% of images need a rotation and ~12.8-13.0% have no rotation
information at all ("nan means that this information is not available" -- OI
download docs). Neither number is negligible enough to ignore silently.

Outputs (evidence only -- nothing here enters the dataset):
    reports/evidence/oi_rotation_probe/probe_report.json
    reports/evidence/oi_rotation_probe/raw/<id>.jpg
    reports/evidence/oi_rotation_probe/montage_<id>.png
    reports/evidence/oi_rotation_probe/contact_sheet.png

Usage: python scripts/probe_oi_rotation.py
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
import time
from collections import Counter
from datetime import datetime, timedelta, timezone
from pathlib import Path

import cv2
import numpy as np
import requests

HERE = Path(__file__).resolve()
C5_ROOT = HERE.parents[1]
sys.path.insert(0, str(HERE.parent))
from c5_taxonomy import OI_TO_CANONICAL  # noqa: E402

LOG = lambda *a: print(*a, flush=True)
IST = timezone(timedelta(hours=5, minutes=30))
SRC = C5_ROOT / "datasets" / "sources" / "openimages_v7"
META = SRC / "_metadata"
OUT = C5_ROOT / "reports" / "evidence" / "oi_rotation_probe"
IMAGE_HTTPS_BASE = "https://s3.amazonaws.com/open-images-dataset"

INFO_FILES = {
    "train": META / "oidv6-train-images-with-labels-with-rotation.csv",
    "validation": META / "validation-images-with-rotation.csv",
    "test": META / "test-images-with-rotation.csv",
}
# train info lacks OriginalMD5 in some releases -- measure, never assume
WANT = ["ImageID", "OriginalMD5", "OriginalSize", "Rotation", "License", "Author", "Title"]

ROT_CV = {
    90: cv2.ROTATE_90_COUNTERCLOCKWISE,
    180: cv2.ROTATE_180,
    270: cv2.ROTATE_90_CLOCKWISE,
}

# filled in by _load_mids(): OI LabelName (mid) -> display name, and the subset
# of mids that map into the PRHAAR canonical taxonomy
OI_MID_TO_NAME: dict[str, str] = {}
OI_TO_CANONICAL_MIDS: set[str] = set()


def md5_of(path: Path) -> str:
    h = hashlib.md5()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def lookup_info(split: str, ids: set[str]) -> dict[str, dict]:
    """Single streaming pass over one info CSV with correct quoting (csv module).

    A naive line.split(",") is WRONG here: Title/URL fields are quoted and can
    contain commas -- an early version of this probe mis-read Rotation as a
    Flickr URL for 5/100 rows because of exactly that.
    """
    found: dict[str, dict] = {}
    remaining = set(ids)
    with open(INFO_FILES[split], encoding="utf-8", errors="replace", newline="") as f:
        for row in csv.DictReader(f):
            iid = row.get("ImageID")
            if iid in remaining:
                found[iid] = {k: row.get(k) for k in WANT}
                remaining.discard(iid)
                if not remaining:
                    break
    return found


def part_q1() -> dict:
    man = [json.loads(l) for l in
           (SRC / "acquisition_manifest.jsonl").read_text().splitlines() if l.strip()]
    by_split: dict[str, set[str]] = {}
    for m in man:
        by_split.setdefault(m["oi_split"], set()).add(m["image_id"])

    info: dict[str, dict] = {}
    for split, ids in by_split.items():
        info.update(lookup_info(split, ids))
    LOG(f"Q1: info rows resolved for {len(info)}/{len(man)} acquired images")

    res = Counter()
    mismatches = []
    for m in man:
        row = info.get(m["image_id"])
        p = SRC / m["path"]
        if row is None:
            res["no_info_row"] += 1
            continue
        if not p.exists():
            res["file_missing"] += 1
            continue
        local_md5 = md5_of(p)
        local_size = p.stat().st_size
        o_md5 = (row.get("OriginalMD5") or "").strip()
        o_size = (row.get("OriginalSize") or "").strip()
        if not o_md5:
            res["csv_has_no_md5_column_value"] += 1
        elif o_md5.lower() == local_md5:
            res["md5_match"] += 1
        else:
            res["md5_mismatch"] += 1
            mismatches.append({"image_id": m["image_id"], "local": local_md5, "csv": o_md5})
        if o_size.isdigit():
            res["size_match" if int(o_size) == local_size else "size_mismatch"] += 1
        else:
            res["csv_has_no_size"] += 1
        res[f"rotation_{row.get('Rotation') or 'blank'}"] += 1

    return {"checked_images": len(man),
            "info_rows_resolved": len(info),
            "counts": dict(sorted(res.items())),
            "md5_mismatch_samples": mismatches[:5],
            "csv_columns_seen": sorted({k for v in info.values() for k in v})}


def pick_rotated_val_ids(n: int = 4) -> list[dict]:
    """Validation IDs with a documented non-zero Rotation AND >=1 target-class box."""
    rot_ids = {}
    with open(INFO_FILES["validation"], encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            r = (row.get("Rotation") or "").strip()
            if r in ("90.0", "180.0", "270.0"):
                rot_ids[row["ImageID"]] = r
    LOG(f"Q2: validation images with non-zero documented rotation: {len(rot_ids)}")

    boxes: dict[str, list] = {}
    with open(META / "validation-annotations-bbox.csv", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            iid = row["ImageID"]
            if iid not in rot_ids or row["LabelName"] not in OI_TO_CANONICAL_MIDS:
                continue
            if int(row["IsDepiction"] or 0) == 1:
                continue
            boxes.setdefault(iid, []).append(row)
    cands = sorted((i for i in boxes if len(boxes[i]) >= 1))
    # prefer one example per distinct rotation angle, largest box first
    out, seen = [], Counter()
    for iid in sorted(cands, key=lambda i: -max(
            (float(b["XMax"]) - float(b["XMin"])) * (float(b["YMax"]) - float(b["YMin"]))
            for b in boxes[i])):
        ang = rot_ids[iid]
        if seen[ang] >= 2:
            continue
        seen[ang] += 1
        out.append({"image_id": iid, "rotation": ang, "boxes": boxes[iid]})
        if len(out) >= n:
            break
    return out


def _load_mids() -> dict[str, str]:
    with open(META / "oidv7-class-descriptions-boxable.csv", encoding="utf-8", newline="") as f:
        for row in csv.reader(f):
            if len(row) >= 2:
                OI_MID_TO_NAME[row[0]] = row[1]
    return OI_MID_TO_NAME


def draw(img: np.ndarray, boxes: list[dict], title: str) -> np.ndarray:
    h, w = img.shape[:2]
    out = img.copy()
    for b in boxes:
        x1 = int(float(b["XMin"]) * w); x2 = int(float(b["XMax"]) * w)
        y1 = int(float(b["YMin"]) * h); y2 = int(float(b["YMax"]) * h)
        cv2.rectangle(out, (x1, y1), (x2, y2), (0, 0, 255), max(2, w // 400))
        name = OI_MID_TO_NAME.get(b["LabelName"], b["LabelName"])
        cv2.putText(out, name, (x1, max(18, y1 - 6)),
                    cv2.FONT_HERSHEY_SIMPLEX, max(0.5, w / 1200), (0, 255, 255), 2)
    bar = np.full((46, w, 3), 20, np.uint8)
    cv2.putText(bar, title, (8, 31), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
    return np.vstack([bar, out])


def part_q2() -> dict:
    _load_mids()
    picked = pick_rotated_val_ids(4)
    if not picked:
        return {"error": "no rotated validation image with a target-class box was found"}
    (OUT / "raw").mkdir(parents=True, exist_ok=True)
    panels, recs = [], []
    for it in picked:
        iid, ang = it["image_id"], int(float(it["rotation"]))
        url = f"{IMAGE_HTTPS_BASE}/validation/{iid}.jpg"
        t0 = time.time()
        r = requests.get(url, timeout=60)
        raw_path = OUT / "raw" / f"{iid}.jpg"
        raw_path.write_bytes(r.content)
        img = cv2.imdecode(np.frombuffer(r.content, np.uint8), cv2.IMREAD_COLOR)
        if img is None:
            recs.append({"image_id": iid, "rotation": ang, "status": "decode_failed",
                         "http": r.status_code})
            continue
        rot = cv2.rotate(img, ROT_CV[ang])
        left = draw(img, it["boxes"], f"{iid} RAW pixels (as downloaded, {img.shape[1]}x{img.shape[0]})")
        right = draw(rot, it["boxes"],
                     f"{iid} rotated CCW {ang} deg ({rot.shape[1]}x{rot.shape[0]})")
        # scale both to a common height so the pair is side-by-side readable
        hgt = 520
        pair = []
        for p in (left, right):
            s = hgt / p.shape[0]
            pair.append(cv2.resize(p, (int(p.shape[1] * s), hgt)))
        montage = np.hstack(pair)
        mp = OUT / f"montage_{iid}.png"
        cv2.imwrite(str(mp), montage)
        panels.append(montage)
        recs.append({"image_id": iid, "rotation": ang, "http": r.status_code,
                     "bytes": len(r.content), "raw_wh": [img.shape[1], img.shape[0]],
                     "rot_wh": [rot.shape[1], rot.shape[0]],
                     "n_boxes_drawn": len(it["boxes"]),
                     "classes": sorted({OI_MID_TO_NAME.get(b["LabelName"], b["LabelName"])
                                        for b in it["boxes"]}),
                     "download_s": round(time.time() - t0, 2),
                     "montage": str(mp.relative_to(C5_ROOT))})
        LOG(f"  {iid} rot={ang} boxes={len(it['boxes'])} raw={img.shape[1]}x{img.shape[0]} "
            f"-> montage {mp.name}")
    if panels:
        w = min(p.shape[1] for p in panels)
        sheet = np.vstack([cv2.resize(p, (w, int(p.shape[0] * w / p.shape[1]))) for p in panels])
        cv2.imwrite(str(OUT / "contact_sheet.png"), sheet)
    return {"images_probed": len(recs), "records": recs,
            "contact_sheet": str((OUT / "contact_sheet.png").relative_to(C5_ROOT))}


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    global OI_TO_CANONICAL_MIDS
    _load_mids()
    OI_TO_CANONICAL_MIDS = {mid for mid, name in OI_MID_TO_NAME.items()
                            if name in OI_TO_CANONICAL}
    LOG(f"target OI mids: {len(OI_TO_CANONICAL_MIDS)}")

    q1 = part_q1()
    q2 = part_q2()
    report = {
        "artifact": "PRHAAR C5 Open Images rotation + integrity probe",
        "generated_ist": datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST"),
        "q1_downloaded_bytes_are_originals": q1,
        "q2_annotation_coordinate_frame": q2,
        "interpretation": "FILLED IN AFTER VISUAL INSPECTION OF contact_sheet.png -- "
                          "do not trust this file until that line is replaced.",
    }
    (OUT / "probe_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    LOG(f"report -> {OUT / 'probe_report.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
