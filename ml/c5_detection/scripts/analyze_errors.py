"""
PRHAAR C5 -- per-box error analysis (spec sections 12, 28, 31-33, 63).

Purpose: produce the size-bucketed and condition-sliced recall numbers that
eval_detector.py deliberately leaves empty (it only sees ultralytics aggregate
metrics). This script does its own prediction + IoU-0.5 class-aware greedy
matching against the ground-truth labels of a split, so every number it
reports has an explicit denominator ("where sample counts permit", section 28).

Prediction capture runs at --capture-conf (default 0.001, the ultralytics
mAP/NMS protocol floor); recall is then reported at several confidence floors
by filtering the SAME captured predictions (no second pass, no estimates).
The headline/confusion-matrix-comparable floor is 0.25.

Occlusion slice: Open Images subset only. Per-box `IsOccluded` flags are
reconstructed in label-file order from `annotations_raw.jsonl` by replaying
the converter's exact keep-policy (depiction always dropped; group_of dropped;
degenerate dropped -- convert_openimages_to_yolo.py:126-153). For every image
the reconstructed flag list length MUST equal the label line count; any
mismatch excludes the image from the slice and is counted in the report
(never silently misattributed). Other sources carry no occlusion labels and
are excluded from slice denominators.

Usage:
    python scripts/analyze_errors.py --weights training/runs/<id>/weights/best.pt \
        --data datasets/PRHAAR-C5-DETECTION/data.yaml \
        --split test --imgsz 640 --experiment-id exp001_yolo26s_640
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

import numpy as np

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parent
C5_ROOT = HERE.parents[1]

sys.path.insert(0, str(SCRIPT_DIR))
from c5_taxonomy import CLASSES  # noqa: E402

LOG = logging.getLogger("analyze_errors")
IST = timezone(timedelta(hours=5, minutes=30))
DEFAULT_OUT_DIR = C5_ROOT / "reports" / "error_analysis"

SIZE_BUCKETS = {"small": (0.0, 32 * 32), "medium": (32 * 32, 96 * 96),
                "large": (96 * 96, float("inf"))}
CONF_FLOORS = (0.001, 0.10, 0.25, 0.50)
MAIN_FLOOR = 0.25


def now_ist() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")


def size_bucket(area_px: float) -> str:
    for name, (lo, hi) in SIZE_BUCKETS.items():
        if lo <= area_px < hi:
            return name
    return "large"


def iou_matrix(gt: np.ndarray, pr: np.ndarray) -> np.ndarray:
    """gt: (N,4) xyxy, pr: (M,4) xyxy -> (N,M) IoU."""
    if len(gt) == 0 or len(pr) == 0:
        return np.zeros((len(gt), len(pr)), dtype=float)
    gx1, gy1, gx2, gy2 = gt[:, 0:1], gt[:, 1:2], gt[:, 2:3], gt[:, 3:4]
    px1, py1, px2, py2 = pr[:, 0], pr[:, 1], pr[:, 2], pr[:, 3]
    ix1 = np.maximum(gx1, px1)
    iy1 = np.maximum(gy1, py1)
    ix2 = np.minimum(gx2, px2)
    iy2 = np.minimum(gy2, py2)
    iw = np.clip(ix2 - ix1, 0, None)
    ih = np.clip(iy2 - iy1, 0, None)
    inter = iw * ih
    ga = np.clip(gx2 - gx1, 0, None) * np.clip(gy2 - gy1, 0, None)
    pa = np.clip(px2 - px1, 0, None) * np.clip(py2 - py1, 0, None)
    union = ga + pa - inter
    return np.where(union > 0, inter / union, 0.0)


def match_image(gt_cls: np.ndarray, gt_xyxy: np.ndarray, pr_cls: np.ndarray,
                pr_xyxy: np.ndarray, pr_conf: np.ndarray, iou_thr: float = 0.5):
    """Greedy class-aware matching by descending confidence.

    Returns (gt_matched: bool array, pred_matched: bool array).
    """
    gt_matched = np.zeros(len(gt_cls), dtype=bool)
    pr_matched = np.zeros(len(pr_cls), dtype=bool)
    if len(pr_cls) == 0:
        return gt_matched, pr_matched
    order = np.argsort(-pr_conf, kind="stable")
    for pi in order:
        cand = np.where((gt_cls == pr_cls[pi]) & (~gt_matched))[0]
        if len(cand) == 0:
            continue
        ious = iou_matrix(gt_xyxy[cand], pr_xyxy[pi: pi + 1])[:, 0]
        best = cand[int(np.argmax(ious))]
        if ious.max() >= iou_thr:
            gt_matched[best] = True
            pr_matched[pi] = True
    return gt_matched, pr_matched


def load_gt(label_path: Path, img_w: int, img_h: int):
    """YOLO txt -> (cls array, xyxy pixel array)."""
    cls, xyxy = [], []
    if label_path.is_file():
        for line in label_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line:
                continue
            c, xc, yc, w, h = line.split()[:5]
            c, xc, yc, w, h = int(float(c)), float(xc), float(yc), float(w), float(h)
            x1 = (xc - w / 2) * img_w
            y1 = (yc - h / 2) * img_h
            x2 = (xc + w / 2) * img_w
            y2 = (yc + h / 2) * img_h
            cls.append(c)
            xyxy.append([x1, y1, x2, y2])
    return (np.array(cls, dtype=int), np.array(xyxy, dtype=float).reshape(-1, 4))


def load_occlusion_flags_by_id() -> dict[str, list[int]]:
    """image_id -> per-kept-box occluded flags, in label-file order.

    Replays convert_openimages_to_yolo.py keep-policy (:126-153):
      drop depiction==1 (always); drop group_of==1 (real build used
      --drop-group-of); drop degenerate clamped w/h<=0; keep the rest in order.
    """
    raw = C5_ROOT / "datasets" / "sources" / "openimages_v7" / "annotations" / "annotations_raw.jsonl"
    out: dict[str, list[int]] = {}
    if not raw.is_file():
        return out
    with raw.open(encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            flags = []
            for b in r["boxes"]:
                if b.get("depiction"):
                    continue
                if b.get("group_of"):
                    continue
                x1 = min(1.0, max(0.0, float(b["xmin"])))
                x2 = min(1.0, max(0.0, float(b["xmax"])))
                y1 = min(1.0, max(0.0, float(b["ymin"])))
                y2 = min(1.0, max(0.0, float(b["ymax"])))
                if (x2 - x1) <= 0.0 or (y2 - y1) <= 0.0:
                    continue
                flags.append(1 if b.get("occluded") else 0)
            if flags:
                out[r["image_id"]] = flags
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--weights", required=True, type=Path)
    ap.add_argument("--data", required=True, type=Path, help="data.yaml of the composite dataset")
    ap.add_argument("--split", choices=("val", "test", "train"), default="test")
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--batch", type=int, default=8)
    ap.add_argument("--capture-conf", type=float, default=0.001,
                    help="NMS confidence floor for CAPTURING predictions (ultralytics "
                         "mAP/NMS protocol floor 0.001); recall floors are computed from these")
    ap.add_argument("--iou", type=float, default=0.7, help="NMS IoU (ultralytics default 0.7)")
    ap.add_argument("--device", default="0")
    ap.add_argument("--experiment-id", required=True)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    t0 = time.time()

    import torch
    import yaml
    from ultralytics import RTDETR, YOLO

    cfg = yaml.safe_load(args.data.read_text(encoding="utf-8"))
    root = Path(cfg["path"])
    split_dir = root / cfg[args.split]
    images = sorted([p for p in split_dir.iterdir()
                     if p.suffix.lower() in (".jpg", ".jpeg", ".png")])
    LOG.info("split %s: %d images | weights %s | imgsz %d", args.split, len(images),
             args.weights, args.imgsz)

    h = hashlib.sha256()
    with open(args.weights, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    ckpt_sha = h.hexdigest()

    # image_id by stem (composite manifest)
    manifest_path = root / "manifest.jsonl"
    id_by_stem: dict[str, str] = {}
    if manifest_path.is_file():
        with manifest_path.open(encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                id_by_stem[Path(r["image"]).stem] = r["image_id"]

    occ_flags = load_occlusion_flags_by_id()
    LOG.info("per-box occlusion flags reconstructed for %d OI images", len(occ_flags))

    # loader selection from the checkpoint's own train_args (best.pt filename
    # carries no family information; never guessed -- see eval_detector.py)
    loader_cls = YOLO
    try:
        _ck = torch.load(str(args.weights), map_location="cpu", weights_only=False)
        _ta = _ck.get("train_args", {}) if isinstance(_ck, dict) else {}
        _mname = str(_ta.get("model", ""))
        if "rtdetr" in _mname.lower():
            loader_cls = RTDETR
        LOG.info("checkpoint train_args model=%r -> loader %s", _mname, loader_cls.__name__)
        del _ck
    except Exception as e:
        LOG.warning("could not read train_args from checkpoint (%s) -- defaulting to YOLO loader", e)

    model = loader_cls(str(args.weights))
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()

    # accumulators -- main floor + per-floor recall
    gt_total = Counter()                       # bucket -> n (GT, same for all floors)
    gt_hit = {f: Counter() for f in CONF_FLOORS}
    cls_gt = Counter()                         # (class,bucket) -> n
    cls_hit = Counter()                        # main floor
    occ_gt = occ_hit = nonocc_gt = nonocc_hit = 0
    occ_cls_gt = Counter()
    occ_cls_hit = Counter()
    occ_join_mismatch = 0
    occ_join_checked = 0
    fp_bucket = Counter()                      # main floor
    fp_cls = Counter()

    predict_t0 = time.time()
    results_iter = model.predict(source=str(split_dir), imgsz=args.imgsz,
                                 conf=args.capture_conf, iou=args.iou,
                                 device=args.device, stream=True,
                                 verbose=False, batch=args.batch)
    done = 0
    for res in results_iter:
        img_path = Path(res.path)
        h_img, w_img = res.orig_shape[:2]
        stem = img_path.stem
        label_path = root / "labels" / args.split / f"{stem}.txt"
        gt_cls, gt_xy = load_gt(label_path, w_img, h_img)
        if res.boxes is None or len(res.boxes) == 0:
            pr_cls = np.zeros(0, dtype=int)
            pr_xy = np.zeros((0, 4), dtype=float)
            pr_cf = np.zeros(0, dtype=float)
        else:
            pr_cls = res.boxes.cls.cpu().numpy().astype(int)
            pr_xy = res.boxes.xyxy.cpu().numpy()
            pr_cf = res.boxes.conf.cpu().numpy()

        # per-floor matching (same captured predictions, filtered by conf)
        per_floor_matched: dict[float, np.ndarray] = {}
        per_floor_prmatched: dict[float, np.ndarray] = {}
        for floor in CONF_FLOORS:
            keep = pr_cf >= floor
            gm, pm = match_image(gt_cls, gt_xy, pr_cls[keep], pr_xy[keep],
                                 pr_cf[keep], iou_thr=0.5)
            per_floor_matched[floor] = gm
            # scatter pm back to full pred indexing for FP counting at main floor
            if floor == MAIN_FLOOR:
                full = np.zeros(len(pr_cls), dtype=bool)
                full[np.where(keep)[0]] = pm
                per_floor_prmatched[floor] = full

        gt_areas = np.clip(gt_xy[:, 2] - gt_xy[:, 0], 0, None) * \
                   np.clip(gt_xy[:, 3] - gt_xy[:, 1], 0, None)
        for i in range(len(gt_cls)):
            cname = CLASSES[gt_cls[i]] if gt_cls[i] < len(CLASSES) else str(gt_cls[i])
            b = size_bucket(float(gt_areas[i]))
            gt_total[b] += 1
            cls_gt[(cname, b)] += 1
            for floor in CONF_FLOORS:
                if per_floor_matched[floor][i]:
                    gt_hit[floor][b] += 1
            if per_floor_matched[MAIN_FLOOR][i]:
                cls_hit[(cname, b)] += 1

        # occlusion slice -- only when the per-box flag join verifies
        image_id = id_by_stem.get(stem)
        flags = occ_flags.get(image_id) if image_id else None
        if flags is not None:
            n_lines = len(gt_cls)
            occ_join_checked += 1
            if len(flags) != n_lines:
                occ_join_mismatch += 1  # excluded, counted, never guessed
            else:
                for i in range(n_lines):
                    cname = CLASSES[gt_cls[i]] if gt_cls[i] < len(CLASSES) else str(gt_cls[i])
                    if flags[i]:
                        occ_gt += 1
                        occ_cls_gt[cname] += 1
                        if per_floor_matched[MAIN_FLOOR][i]:
                            occ_hit += 1
                            occ_cls_hit[cname] += 1
                    else:
                        nonocc_gt += 1
                        if per_floor_matched[MAIN_FLOOR][i]:
                            nonocc_hit += 1

        pm = per_floor_prmatched[MAIN_FLOOR]
        for j in range(len(pr_cls)):
            if not pm[j]:
                area = max(0.0, pr_xy[j, 2] - pr_xy[j, 0]) * max(0.0, pr_xy[j, 3] - pr_xy[j, 1])
                fp_bucket[size_bucket(float(area))] += 1
                cname = CLASSES[pr_cls[j]] if pr_cls[j] < len(CLASSES) else str(pr_cls[j])
                fp_cls[cname] += 1

        done += 1
        if done % 500 == 0 or done == len(images):
            LOG.info("  %d/%d (%.0fs)", done, len(images), time.time() - predict_t0)

    predict_s = time.time() - predict_t0
    vram_peak_gib = (round(torch.cuda.max_memory_allocated() / 2 ** 30, 3)
                     if torch.cuda.is_available() else None)

    def ratio(num: int, den: int):
        return round(num / den, 6) if den else None

    report = {
        "spec": "PRHAAR C5 sections 12/28/31-33 + 63 columns small_recall/occlusion_recall",
        "generated_ist": now_ist(),
        "experiment_id": args.experiment_id,
        "weights": str(args.weights),
        "weights_sha256": ckpt_sha,
        "split": args.split,
        "n_images": len(images),
        "eval_config": {"imgsz": args.imgsz, "capture_conf": args.capture_conf,
                        "iou": args.iou, "match_iou_threshold": 0.5,
                        "matching": "greedy, class-aware, by descending confidence",
                        "main_conf_floor": MAIN_FLOOR, "device": args.device},
        "definitions": {
            "size_buckets_px_area": {k: [v[0], v[1]] for k, v in SIZE_BUCKETS.items()},
            "size_bucket_note": "GT box area in original image pixels (COCO-style thresholds)",
            "occlusion_slice": ("Open Images subset only; per-box IsOccluded flags replayed "
                                "in label order from annotations_raw.jsonl with converter "
                                "policy; per-image flag-count cross-checked against label "
                                "line count (mismatches excluded + counted). NEVER "
                                "representative of surveillance occlusion."),
        },
        "size_bucketed_recall": {
            "main_floor": MAIN_FLOOR,
            "buckets": {
                b: {"gt": gt_total[b], "hit": gt_hit[MAIN_FLOOR][b],
                    "recall": ratio(gt_hit[MAIN_FLOOR][b], gt_total[b])}
                for b in SIZE_BUCKETS
            },
        },
        "recall_by_conf_floor": {
            str(floor): {b: {"gt": gt_total[b], "hit": gt_hit[floor][b],
                             "recall": ratio(gt_hit[floor][b], gt_total[b])}
                         for b in SIZE_BUCKETS}
            for floor in CONF_FLOORS
        },
        "per_class_size_recall_main_floor": {
            f"{c}|{b}": {"gt": cls_gt[(c, b)], "hit": cls_hit[(c, b)],
                         "recall": ratio(cls_hit[(c, b)], cls_gt[(c, b)])}
            for (c, b) in sorted(cls_gt)
        },
        "occlusion_slice_main_floor": {
            "occluded_gt": occ_gt, "occluded_hit": occ_hit,
            "occluded_recall": ratio(occ_hit, occ_gt),
            "nonoccluded_gt": nonocc_gt, "nonoccluded_hit": nonocc_hit,
            "nonoccluded_recall": ratio(nonocc_hit, nonocc_gt),
            "per_class_occluded": {
                c: {"gt": occ_cls_gt[c], "hit": occ_cls_hit[c],
                    "recall": ratio(occ_cls_hit[c], occ_cls_gt[c])}
                for c in sorted(occ_cls_gt)
            },
            "join_integrity": {"images_checked": occ_join_checked,
                               "images_excluded_flag_count_mismatch": occ_join_mismatch,
                               "source": "Open Images V7 subset only"},
        },
        "false_positives": {
            "total": int(sum(fp_bucket.values())),
            "by_size_bucket": dict(fp_bucket),
            "by_class": dict(fp_cls),
            "conf_floor": MAIN_FLOOR,
        },
        "measured": {"predict_seconds": round(predict_s, 1),
                     "vram_peak_gib": vram_peak_gib,
                     "checkpoint_sha256": ckpt_sha},
        "runtime_seconds": round(time.time() - t0, 1),
    }

    args.out_dir.mkdir(parents=True, exist_ok=True)
    out = args.out_dir / f"{args.experiment_id}_{args.split}_errors.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    LOG.info("small recall: %s | medium: %s | large: %s (floor %s)",
             ratio(gt_hit[MAIN_FLOOR]["small"], gt_total["small"]),
             ratio(gt_hit[MAIN_FLOOR]["medium"], gt_total["medium"]),
             ratio(gt_hit[MAIN_FLOOR]["large"], gt_total["large"]), MAIN_FLOOR)
    LOG.info("occluded recall (OI subset): %s over %d GT boxes | join mismatches %d",
             ratio(occ_hit, occ_gt), occ_gt, occ_join_mismatch)
    LOG.info("report -> %s (%.1fs)", out, report["runtime_seconds"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
