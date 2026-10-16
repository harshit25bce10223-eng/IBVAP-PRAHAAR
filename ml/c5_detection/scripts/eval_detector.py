#!/usr/bin/env python
"""
PRHAAR C5 -- measured evaluation for a trained checkpoint (spec sections 27-29, 63).

Loads a checkpoint and MEASURES, on the requested split:
  - precision, recall, F1, mAP50, mAP50-95 (section 27)
  - per-class P / R / AP50 / AP50-95, confusion matrix, FP per image (section 27)
  - person / motorcycle / animal recall and GT-box-weighted vehicle recall (section 27)
  - batch-1 latency p50/p95 on THIS machine + process VRAM peak (sections 25, 43)
Writes evaluation/<experiment_id>_<split>_eval.json.

Confusion matrix notes (verified in the installed ultralytics 8.4.118 source):
  - ultralytics populates it ONLY via the plots path (models/yolo/detect/val.py:196
    gates process_batch behind `if self.args.plots:`) -- this script forces plots ON.
  - cm threshold is the ultralytics default 0.25 when conf is None (val.py:54),
    separate from the 0.001 NMS/mAP conf (engine/validator.py:138-139).
  - matrix convention: rows = predicted, cols = true, background = last row/col
    (utils/metrics.py:432-479). GT per class is therefore a COLUMN sum.
  Latency bench uses batch-1 predict at conf=0.25.

C5_EXPERIMENT_LOG.csv rows are written ONLY by this script (--append-log), and
every metric cell comes from measurement in this run. Metrics with no samples
or no label support are left EMPTY with the reason recorded in the report --
never estimated (sections 61/62/63).

Condition-wise metrics (section 28: DAY/NIGHT/RAIN/FOG/...): the current
datasets carry NO day/night/weather metadata. The report states this explicitly
per condition instead of inventing buckets; those columns stay empty in the log
until labeled data exists.

small_recall: not derivable from an ultralytics val pass alone; it is produced
by the size-bucketed error analysis (section 31-32, task #33) and cell stays
empty until then.

Log conventions: the "imgsz" column records the EVALUATION image size that
produced the metrics (train imgsz is in the run manifest); "lr" = the
configured lr0, or the literal 'default' if ultralytics' default was used.

Usage:
    python scripts/eval_detector.py --weights checkpoints/exp001_best.pt \
        --data datasets/PRHAAR-C5-DETECTION/data.yaml --split test \
        --experiment-id exp001_yolo26s_640 --imgsz 640 \
        --run-dir training/runs/exp001_yolo26s_640 --append-log
"""

from __future__ import annotations

import argparse
import json
import logging
import platform
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    import numpy as np
    import yaml
except ImportError as e:  # pragma: no cover
    print(f"FATAL: missing dependency: {e}", file=sys.stderr)
    sys.exit(2)

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parent
C5_ROOT = HERE.parents[1]

sys.path.insert(0, str(SCRIPT_DIR))
from c5_taxonomy import CLASSES, PRHAAR_C5_TAXONOMY_VERSION  # noqa: E402
from qa_dataset import sha256_file  # noqa: E402

LOG = logging.getLogger("eval_detector")
IST = timezone(timedelta(hours=5, minutes=30))
EVAL_DIR = C5_ROOT / "evaluation"
DEFAULT_LOG = C5_ROOT / "C5_EXPERIMENT_LOG.csv"

LOG_COLUMNS = [
    "experiment_id", "model", "dataset_version", "imgsz", "batch", "epochs", "lr",
    "augmentation", "seed", "precision", "recall", "mAP50", "mAP50_95",
    "small_recall", "night_recall", "occlusion_recall", "latency_p50",
    "latency_p95", "memory", "checkpoint_hash", "decision",
]

VEHICLE_GROUP = ("CAR", "LIGHT_VEHICLE", "TRUCK", "BUS", "AUTO_RICKSHAW")
IMG_SUFFIXES = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def now_ist() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")


def total_ram_gib():
    """Total physical RAM in GiB via GlobalMemoryStatusEx (no extra deps)."""
    import ctypes

    class _MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    st = _MEMORYSTATUSEX()
    st.dwLength = ctypes.sizeof(_MEMORYSTATUSEX)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(st)):
        return None
    return st.ullTotalPhys / 2 ** 30


def resolve_split_dir(data_yaml: Path, split: str) -> Path | None:
    y = yaml.safe_load(data_yaml.read_text(encoding="utf-8"))
    rel = y.get(split)
    if not rel:
        return None
    p = Path(rel)
    if not p.is_absolute():
        root = Path(y.get("path", data_yaml.parent))
        if not root.is_absolute():
            root = (data_yaml.parent / root).resolve()
        p = root / p
    return p


def per_class_from_metric_values(vals, ap_class_index):
    """Map ultralytics metric arrays to {class_id: value} robustly.

    Arrays may be class-aligned (len == nc) or sparse (aligned with
    ap_class_index) depending on ultralytics version. Never guess silently:
    unmappable sizes return None and the caller records that.
    """
    if vals is None:
        return None
    v = np.atleast_1d(np.asarray(vals, dtype=float))
    idx = np.atleast_1d(np.asarray(ap_class_index, dtype=int)) if ap_class_index is not None else None
    if v.size == len(CLASSES):
        return {i: float(v[i]) for i in range(len(CLASSES)) if np.isfinite(v[i])}
    if idx is not None and v.size == idx.size:
        return {int(idx[k]): float(v[k]) for k in range(v.size) if np.isfinite(v[k])}
    return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--weights", required=True, type=Path)
    ap.add_argument("--data", required=True, type=Path, help="data.yaml of the composite dataset")
    ap.add_argument("--split", choices=("val", "test", "train"), default="val")
    ap.add_argument("--experiment-id", required=True)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--batch", type=int, default=8, help="eval batch")
    ap.add_argument("--workers", type=int, default=4,
                    help="val dataloader workers; low-RAM machines (< 12 GiB) are capped to 2 "
                         "(ultralytics default would be 8 -- commit-exhaustion crash risk, "
                         "measured 2026-10-14)")
    ap.add_argument("--device", default="0")
    ap.add_argument("--latency-n", type=int, default=100,
                    help="images for the batch-1 latency bench (min with split size)")
    ap.add_argument("--run-dir", type=Path, default=None,
                    help="training run dir with run_manifest.json (required with --append-log)")
    ap.add_argument("--append-log", action="store_true",
                    help="append the completed 21-column row to C5_EXPERIMENT_LOG.csv")
    ap.add_argument("--log", type=Path, default=DEFAULT_LOG, help="experiment log path (test override)")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    t0 = time.time()

    # ---- low-RAM worker cap (measured 2026-10-14; mirrors train_detector.py) ----
    workers_effective = args.workers
    ram_gib = total_ram_gib()
    if ram_gib is not None and ram_gib < 12.0 and workers_effective > 2:
        LOG.warning("workers capped %d -> 2 (RAM %.1f GiB: commit-exhaustion workaround)",
                    workers_effective, ram_gib)
        workers_effective = 2

    weights = args.weights.resolve()
    if not weights.is_file():
        LOG.error("weights not found: %s", weights)
        return 2
    data_yaml = args.data.resolve()
    if not data_yaml.is_file():
        LOG.error("data.yaml not found: %s", data_yaml)
        return 2
    if args.append_log and not args.run_dir:
        LOG.error("--append-log requires --run-dir (config cells come from run_manifest.json)")
        return 2

    manifest = None
    if args.run_dir:
        man_path = args.run_dir.resolve() / "run_manifest.json"
        if not man_path.is_file():
            LOG.error("run_manifest.json not found: %s", man_path)
            return 2
        manifest = json.loads(man_path.read_text(encoding="utf-8"))

    import torch
    import ultralytics
    from ultralytics import RTDETR, YOLO

    ckpt_sha = sha256_file(weights)
    y = yaml.safe_load(data_yaml.read_text(encoding="utf-8"))
    split_dir = resolve_split_dir(data_yaml, args.split)
    if split_dir is None or not split_dir.is_dir():
        LOG.error("cannot resolve split '%s' images dir from %s -- no FP/image without it",
                  args.split, data_yaml)
        return 2
    split_images = sorted(p for p in split_dir.iterdir() if p.suffix.lower() in IMG_SUFFIXES)
    n_images = len(split_images)
    LOG.info("eval %s | split %s (%d images) | imgsz %d | batch %d",
             args.experiment_id, args.split, n_images, args.imgsz, args.batch)

    # loader selection: a run's best.pt is always named best.pt, so the model
    # family cannot be read from the filename -- it comes from the checkpoint's
    # own recorded train_args (set by train_detector.py), never guessed.
    loader_cls = YOLO
    try:
        _ck = torch.load(str(weights), map_location="cpu", weights_only=False)
        _ta = _ck.get("train_args", {}) if isinstance(_ck, dict) else {}
        _mname = str(_ta.get("model", ""))
        if "rtdetr" in _mname.lower():
            loader_cls = RTDETR
        LOG.info("checkpoint train_args model=%r -> loader %s", _mname, loader_cls.__name__)
        del _ck
    except Exception as e:
        LOG.warning("could not read train_args from checkpoint (%s) -- defaulting to YOLO loader", e)

    model = loader_cls(str(weights))
    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()

    val_t0 = time.time()
    # conf/iou deliberately NOT overridden: ultralytics' own val protocol is
    # NMS/mAP conf 0.001 (engine/validator.py:138-139) with the confusion matrix
    # at its 0.25 default (models/yolo/detect/val.py:54). plots=True is REQUIRED,
    # not cosmetic: val.py:196 gates confusion_matrix.process_batch behind it.
    m = model.val(data=str(data_yaml), split=args.split, imgsz=args.imgsz,
                  batch=args.batch, device=args.device,
                  plots=True, verbose=False,
                  workers=workers_effective,
                  project=str(EVAL_DIR / "runs"), name=f"{args.experiment_id}_{args.split}",
                  exist_ok=True)
    val_s = time.time() - val_t0

    box = m.box
    P = float(box.mp)
    R = float(box.mr)
    f1 = (2.0 * P * R / (P + R)) if (P + R) > 0 else None
    ap50 = float(box.map50)
    ap = float(box.map)

    ap_class_index = getattr(box, "ap_class_index", None)
    c_p = per_class_from_metric_values(getattr(box, "p", None), ap_class_index)
    c_r = per_class_from_metric_values(getattr(box, "r", None), ap_class_index)
    c_ap50 = per_class_from_metric_values(getattr(box, "ap50", None), ap_class_index)
    c_ap = per_class_from_metric_values(getattr(box, "maps", None), ap_class_index)

    def normalize_names(n):
        if isinstance(n, dict):
            return {int(k): v for k, v in n.items()}
        if isinstance(n, (list, tuple)):
            return {i: v for i, v in enumerate(n)}
        return {}

    names = normalize_names(getattr(m, "names", None))
    y_names = normalize_names(y.get("names"))

    # Confusion matrix: rows = predicted class, cols = true class, background =
    # index nc (last row/col) -- verified against installed utils/metrics.py:432-479
    # (`self.matrix[dc, self.nc] += 1  # FP` / `self.matrix[self.nc, gc] += 1  # FN`
    # / `self.matrix[dc, gc] += 1`). GT counts are therefore COLUMN sums; FP are
    # rows 0..nc-1 in the background column; FN are cols 0..nc-1 in the
    # background row. cm threshold: ultralytics 0.25 default (conf arg not passed;
    # val.py:54). The ConfusionMatrix object does not persist its threshold, so it
    # is recorded from the source-verified derivation, not from introspection.
    cm = None
    cm_conf = 0.25  # val.py:54 -- 0.25 when conf is None (this run passes no conf)
    fp_total = fn_total = None
    n_cm_classes = None
    try:
        raw_cm = np.asarray(m.confusion_matrix.matrix, dtype=float)
        if raw_cm.ndim == 2 and raw_cm.shape[0] == raw_cm.shape[1] and raw_cm.shape[0] > 1:
            cm = raw_cm
            n_cm_classes = cm.shape[0] - 1  # last index = background
            fp_total = float(cm[:n_cm_classes, n_cm_classes].sum())
            fn_total = float(cm[n_cm_classes, :n_cm_classes].sum())
            if n_cm_classes != len(CLASSES):
                LOG.warning("confusion matrix has %d classes but taxonomy has %d -- "
                            "per-class GT counts stay in matrix order", n_cm_classes, len(CLASSES))
        else:
            LOG.warning("confusion matrix shape unexpected (%s) -- treated as unavailable",
                        raw_cm.shape)
    except Exception as e:
        LOG.warning("confusion matrix unavailable: %s", e)

    def cls_id_by_name(name: str):
        src = y_names or names
        for i, n in src.items():
            if str(n).upper() == name:
                return int(i)
        return None

    def class_metric(table, cname):
        cid = cls_id_by_name(cname)
        if cid is None or table is None:
            return None
        return table.get(cid)

    # GT box counts per class from the confusion matrix COLUMNS (true-class sums).
    # Column i sums every row that ends in true-class i (correct, misclassified,
    # and background/missed), so it equals the GT instance count of class i
    # regardless of how many predictions the model made.
    gt_per_class = None
    if cm is not None:
        gt_per_class = {i: float(cm[:, i].sum()) for i in range(n_cm_classes)}

    def weighted_vehicle_recall():
        if c_r is None or gt_per_class is None:
            return None, None
        num = den = 0.0
        used = {}
        for cname in VEHICLE_GROUP:
            cid = cls_id_by_name(cname)
            if cid is None or cid not in c_r:
                continue
            n = gt_per_class.get(cid, 0.0)
            if n <= 0:
                continue
            used[cname] = {"gt_boxes": int(n), "recall": round(c_r[cid], 6)}
            num += n * c_r[cid]
            den += n
        if den <= 0:
            return None, used
        return num / den, used

    veh_recall, veh_detail = weighted_vehicle_recall()

    # batch-1 latency bench on THIS machine (section 43: no assumed hardware)
    latency = {"n": 0, "p50_ms": None, "p95_ms": None, "device": args.device,
               "note": "batch-1 predict at conf 0.25, warmup 3, torch.cuda.synchronize per image"}
    if torch.cuda.is_available() or args.device == "cpu":
        import statistics
        sample = split_images[: max(3, min(args.latency_n, n_images))]
        for p in sample[:3]:  # warmup
            model.predict(source=str(p), imgsz=args.imgsz, device=args.device, verbose=False, conf=0.25)
        times_ms = []
        for p in sample[3:]:
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            t1 = time.perf_counter()
            model.predict(source=str(p), imgsz=args.imgsz, device=args.device, verbose=False, conf=0.25)
            if torch.cuda.is_available():
                torch.cuda.synchronize()
            times_ms.append((time.perf_counter() - t1) * 1000.0)
        if times_ms:
            latency = {
                "n": len(times_ms),
                "p50_ms": round(float(np.percentile(times_ms, 50)), 2),
                "p95_ms": round(float(np.percentile(times_ms, 95)), 2),
                "mean_ms": round(float(statistics.fmean(times_ms)), 2),
                "device": args.device,
                "note": "batch-1 predict at conf 0.25, warmup 3, torch.cuda.synchronize per image",
            }

    vram_peak_gib = (round(torch.cuda.max_memory_allocated() / 2 ** 30, 3)
                     if torch.cuda.is_available() else None)

    per_class_report = {}
    for cid in range(len(CLASSES)):
        cname = (y_names or names).get(cid, CLASSES[cid] if cid < len(CLASSES) else str(cid))
        entry = {
            "p": None if c_p is None else c_p.get(cid),
            "r": None if c_r is None else c_r.get(cid),
            "ap50": None if c_ap50 is None else c_ap50.get(cid),
            "ap50_95": None if c_ap is None else c_ap.get(cid),
            "gt_boxes": None if gt_per_class is None else gt_per_class.get(cid),
        }
        if any(v is not None for v in entry.values()):
            per_class_report[str(cname)] = entry

    # section 28: dataset carries no condition metadata -- disclose per condition
    conditions = ["DAY", "NIGHT", "RAIN", "FOG", "FOREST", "HILL", "AGRICULTURE",
                  "SETTLEMENT", "LONG-RANGE", "SMALL-OBJECT", "OCCLUSION",
                  "LOW-RESOLUTION", "DEGRADED-CAMERA"]
    condition_report = {
        c: {"precision": None, "recall": None, "f1": None,
            "reason": "no condition labels in dataset metadata (no day/night/weather source fields)"}
        for c in conditions
    }

    report = {
        "spec": ("PRHAAR C5 sections 27-29 (metrics, condition-wise metrics, target); "
                 "evaluation-only: no estimates, empty means not measurable from this data"),
        "generated_ist": now_ist(),
        "experiment_id": args.experiment_id,
        "checkpoint": {
            "weights": str(weights),
            "sha256": ckpt_sha,
        },
        "dataset": {
            "data_yaml": str(data_yaml),
            "data_yaml_sha256": sha256_file(data_yaml),
            "taxonomy_version": PRHAAR_C5_TAXONOMY_VERSION,
            "split": args.split,
            "n_images": n_images,
            "dataset_version": (manifest or {}).get("dataset", {}).get("dataset_version"),
            "split_hash": (manifest or {}).get("dataset", {}).get("split_hash"),
        },
        "eval_config": {
            "imgsz": args.imgsz, "batch": args.batch,
            "conf": "ultralytics default (not passed): NMS/mAP 0.001 "
                    "(engine/validator.py:138-139); confusion matrix 0.25 (val.py:54)",
            "iou": "ultralytics default 0.7",
            "plots": True,
        },
        "software": {
            "python": platform.python_version(),
            "ultralytics": ultralytics.__version__,
            "torch": torch.__version__,
            "note": "recorded so the cited ultralytics source lines stay traceable",
        },
        "metrics": {
            "precision": round(P, 6),
            "recall": round(R, 6),
            "f1": None if f1 is None else round(f1, 6),
            "mAP50": round(ap50, 6),
            "mAP50_95": round(ap, 6),
            "per_class": per_class_report,
            "confusion_matrix": None if cm is None else cm.tolist(),
            "confusion_matrix_conf": cm_conf,
            "confusion_matrix_conf_source": "ultralytics 0.25 default when conf arg is None "
                                            "(models/yolo/detect/val.py:54); not introspectable from metrics",
            "confusion_matrix_convention": "rows = predicted class, cols = true class, "
                                           "background = last row/col "
                                           "(utils/metrics.py:432-479)",
            "fp_total": fp_total,
            "fn_total": fn_total,
            "fp_per_image": None if (fp_total is None or not n_images) else round(fp_total / n_images, 6),
            "fp_per_image_note": "fp_total (cm background column at conf 0.25) / split image count",
            "recall_groups": {
                "person_recall": class_metric(c_r, "PERSON"),
                "motorcycle_recall": class_metric(c_r, "MOTORCYCLE"),
                "animal_recall": class_metric(c_r, "ANIMAL"),
                "vehicle_recall_gt_weighted": None if veh_recall is None else round(veh_recall, 6),
                "vehicle_recall_detail": veh_detail,
                "vehicle_recall_note": "recall weighted by GT box counts over " + ",".join(VEHICLE_GROUP),
            },
        },
        "latency": latency,
        "memory": {"vram_peak_gib": vram_peak_gib,
                   "note": "process peak across val + latency bench"},
        "condition_wise": condition_report,
        "runtime_seconds": round(time.time() - t0, 1),
        "val_seconds": round(val_s, 1),
        "not_measured": {
            "small_recall": "produced by size-bucketed error analysis (task #33); cell stays empty",
            "night_recall": "no night-condition labels in dataset",
            "occlusion_recall": "no occlusion-condition labels in dataset",
        },
    }

    # dataset_version cell: shorten ONLY a raw 64-hex digest (the composite's
    # dataset_hash.txt); a fallback id like "datayaml-<16hex>" stays whole so the
    # log never shows a truncated non-hash string
    dsv = report["dataset"]["dataset_version"] or ""
    if len(dsv) == 64 and all(c in "0123456789abcdef" for c in dsv):
        dsv = dsv[:16]

    # log row (complete table; only measured cells filled)
    lr_val = None
    if manifest:
        lr_val = manifest["training"].get("lr0")
    row = {
        "experiment_id": args.experiment_id,
        "model": (manifest or {}).get("model", {}).get("requested", ""),
        "dataset_version": dsv,
        "imgsz": args.imgsz,
        "batch": (manifest or {}).get("training", {}).get("batch", ""),
        "epochs": (manifest or {}).get("training", {}).get("epochs_completed", ""),
        "lr": "default" if lr_val is None else lr_val,
        "augmentation": (manifest or {}).get("training", {}).get("augmentation", ""),
        "seed": (manifest or {}).get("training", {}).get("seed", ""),
        "precision": report["metrics"]["precision"],
        "recall": report["metrics"]["recall"],
        "mAP50": report["metrics"]["mAP50"],
        "mAP50_95": report["metrics"]["mAP50_95"],
        "small_recall": "",
        "night_recall": "",
        "occlusion_recall": "",
        "latency_p50": latency["p50_ms"] if latency["p50_ms"] is not None else "",
        "latency_p95": latency["p95_ms"] if latency["p95_ms"] is not None else "",
        "memory": vram_peak_gib if vram_peak_gib is not None else "",
        "checkpoint_hash": ckpt_sha,
        "decision": "",
    }
    report["experiment_log_row"] = row

    EVAL_DIR.mkdir(parents=True, exist_ok=True)
    out = EVAL_DIR / f"{args.experiment_id}_{args.split}_eval.json"
    out.write_text(json.dumps(report, indent=2), encoding="utf-8")
    LOG.info("metrics: P=%.4f R=%.4f mAP50=%.4f mAP50-95=%.4f | fp/img=%s | lat p50=%sms",
             P, R, ap50, ap, report["metrics"]["fp_per_image"],
             latency["p50_ms"])
    LOG.info("report -> %s", out)

    if args.append_log:
        log_path = args.log.resolve()
        if not log_path.is_file():
            LOG.error("log not found: %s", log_path)
            return 2
        lines = log_path.read_text(encoding="utf-8").splitlines()
        header = lines[0].split(",") if lines else []
        if header != LOG_COLUMNS:
            LOG.error("log header mismatch (spec section 63 exact columns) -- refusing to append")
            return 2
        existing = {ln.split(",")[0] for ln in lines[1:] if ln.strip()}
        if args.experiment_id in existing:
            LOG.error("experiment_id '%s' already present in log -- refusing duplicate", args.experiment_id)
            return 2
        line = ",".join(str(row[c]) for c in LOG_COLUMNS)
        with log_path.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
        LOG.info("appended to %s", log_path)

    return 0


if __name__ == "__main__":
    sys.exit(main())
