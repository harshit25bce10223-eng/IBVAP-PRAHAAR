#!/usr/bin/env python
"""
PRHAAR C5 -- controlled training run wrapper (spec sections 23-26, 63).

Trains ONE detector configuration with explicit, recorded hyperparameters and
emits a complete run manifest (spec section 26) -- no anonymous best.pt, no
invented numbers. Metric columns of C5_EXPERIMENT_LOG.csv are NEVER written
here; only eval_detector.py fills them, from measurement.

What this script does:
  1. validates inputs (data.yaml, dataset_hash.txt / manifest.jsonl when present)
  2. runs ultralytics training (YOLO for yolo26*/yolo11*, RTDETR for rtdetr*)
  3. records the section-26 run manifest: experiment_id, model, checkpoint(s) +
     SHA-256, dataset_version, annotation_version, split_hash, image_size, batch,
     epochs (requested/completed), optimizer (requested/resolved), lr,
     augmentation, seed, hardware, software versions, best epoch, best fitness,
     VRAM peak, runtime -- written to training/runs/<experiment_id>/run_manifest.json
  4. copies best.pt to checkpoints/<experiment_id>_best.pt (+ .sha256 sidecar)
     unless --experiment-id starts with "dryrun" (plumbing tests must not enter
     the candidate checkpoint store)

Reproducibility: every value in the manifest is what was actually used/measured
by this run; nothing is assumed. If dataset_hash.txt / manifest.jsonl are
missing, the manifest records the fallback used (never silently).

Usage:
    python scripts/train_detector.py --data datasets/PRHAAR-C5-DETECTION/data.yaml \
        --model yolo26s.pt --experiment-id exp001_yolo26s_640 --imgsz 640 --batch 8
"""

from __future__ import annotations

import argparse
import csv
import json
import logging
import platform
import shutil
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve()
SCRIPT_DIR = HERE.parent
C5_ROOT = HERE.parents[1]

sys.path.insert(0, str(SCRIPT_DIR))
from c5_taxonomy import PRHAAR_C5_TAXONOMY_VERSION  # noqa: E402
from qa_dataset import sha256_file  # noqa: E402

LOG = logging.getLogger("train_detector")
IST = timezone(timedelta(hours=5, minutes=30))
RUNS_DIR = C5_ROOT / "training" / "runs"
CKPT_DIR = C5_ROOT / "checkpoints"


def now_ist() -> str:
    return datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")


def software_versions() -> dict:
    import torch
    import ultralytics
    return {
        "python": platform.python_version(),
        "ultralytics": ultralytics.__version__,
        "torch": torch.__version__,
        "torch_cuda": torch.version.cuda,
        "platform": platform.platform(),
    }


def hardware_info() -> dict:
    import torch
    if not torch.cuda.is_available():
        return {"cuda_available": False}
    p = torch.cuda.get_device_properties(0)
    return {
        "cuda_available": True,
        "gpu_name": p.name,
        "gpu_total_vram_gib": round(p.total_memory / 2 ** 30, 2),
        "gpu_count": torch.cuda.device_count(),
    }


def read_best_epoch(results_csv: Path):
    """Best epoch = argmax of ultralytics fitness on the training val curve."""
    if not results_csv.is_file():
        return None, None, None
    rows = list(csv.DictReader(results_csv.open(encoding="utf-8")))
    if not rows:
        return None, None, None
    best_epoch, best_fit = None, -1.0
    for r in rows:
        try:
            fit = 0.1 * float(r["metrics/mAP50(B)"]) + 0.9 * float(r["metrics/mAP50-95(B)"])
        except (KeyError, ValueError):
            continue
        if fit > best_fit:
            best_fit = fit
            best_epoch = int(float(r["epoch"]))
    last_epoch = int(float(rows[-1]["epoch"]))
    return best_epoch, (None if best_epoch is None else round(best_fit, 6)), last_epoch


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--data", required=True, type=Path, help="data.yaml of the composite dataset")
    ap.add_argument("--model", required=True,
                    help="pretrained checkpoint to fine-tune from (e.g. yolo26s.pt, yolo26m.pt, "
                         "yolo26l.pt, rtdetr-l.pt) -- transfer learning per spec section 23")
    ap.add_argument("--experiment-id", required=True,
                    help="unique run name, e.g. exp001_yolo26s_640 (also the run dir name)")
    ap.add_argument("--imgsz", type=int, default=640, help="training image size (spec section 25: 640/960/1280)")
    ap.add_argument("--batch", type=int, default=8, help="batch size (explicit for reproducibility)")
    ap.add_argument("--epochs", type=int, default=100)
    ap.add_argument("--lr0", type=float, default=None, help="initial LR (None = ultralytics default)")
    ap.add_argument("--optimizer", default="auto", help="optimizer (ultralytics names; 'auto' = its automatic choice)")
    ap.add_argument("--freeze", type=int, default=None, help="freeze first N layers (freeze/unfreeze strategy, spec section 24)")
    ap.add_argument("--augmentation", default="default",
                    help="augmentation preset label for the log (hyp yaml experiments use the yaml filename)")
    ap.add_argument("--hyp", type=Path, default=None, help="optional ultralytics hyp yaml (augmentation, spec section 22)")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--deterministic", action="store_true", help="ultralytics deterministic mode (slower)")
    ap.add_argument("--patience", type=int, default=50, help="early-stopping patience in epochs")
    ap.add_argument("--workers", type=int, default=4, help="dataloader workers (8 GB RAM machine)")
    ap.add_argument("--device", default="0", help="'0' (CUDA) or 'cpu' (explicit only)")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    t0 = time.time()

    data_yaml = args.data.resolve()
    if not data_yaml.is_file():
        LOG.error("data.yaml not found: %s", data_yaml)
        return 2
    run_dir = RUNS_DIR / args.experiment_id
    if run_dir.exists():
        LOG.error("run dir already exists (no silent overwrite): %s", run_dir)
        return 2
    hyp_path = args.hyp.resolve() if args.hyp else None
    if hyp_path and not hyp_path.is_file():
        LOG.error("hyp yaml not found: %s", hyp_path)
        return 2

    import torch
    if args.device != "cpu" and not torch.cuda.is_available():
        LOG.error("CUDA requested but not available -- no silent CPU fallback; pass --device cpu explicitly")
        return 2

    # dataset provenance (spec section 26: dataset_version / split_hash)
    dataset_root = data_yaml.parent
    dh_file = dataset_root / "dataset_hash.txt"
    man_file = dataset_root / "manifest.jsonl"
    if dh_file.is_file():
        dataset_version = dh_file.read_text(encoding="utf-8").strip()
        dataset_version_source = "dataset_hash.txt"
    else:
        dataset_version = "datayaml-" + sha256_file(data_yaml)[:16]
        dataset_version_source = "FALLBACK: no dataset_hash.txt in " + str(dataset_root)
        LOG.warning(dataset_version_source)
    if man_file.is_file():
        split_hash = sha256_file(man_file)
    else:
        split_hash = None
        LOG.warning("no manifest.jsonl in %s -- split_hash recorded as null (never estimated)", dataset_root)

    import ultralytics
    from ultralytics import RTDETR, YOLO
    loader_cls = RTDETR if "rtdetr" in args.model.lower() else YOLO

    LOG.info("experiment %s | model %s | imgsz %d | batch %d | epochs %d",
             args.experiment_id, args.model, args.imgsz, args.batch, args.epochs)
    model = loader_cls(args.model)

    train_kwargs = dict(
        data=str(data_yaml),
        imgsz=args.imgsz,
        batch=args.batch,
        epochs=args.epochs,
        optimizer=args.optimizer,
        seed=args.seed,
        deterministic=args.deterministic,
        patience=args.patience,
        workers=args.workers,
        device=args.device,
        project=str(RUNS_DIR),
        name=args.experiment_id,
        exist_ok=False,
        val=True,
        plots=True,
    )
    if args.lr0 is not None:
        train_kwargs["lr0"] = args.lr0
    if args.freeze is not None:
        train_kwargs["freeze"] = args.freeze
    if hyp_path is not None:
        train_kwargs["cfg"] = str(hyp_path)

    if torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()
    train_t0 = time.time()
    model.train(**train_kwargs)
    train_s = time.time() - train_t0
    vram_peak_gib = (round(torch.cuda.max_memory_allocated() / 2 ** 30, 3)
                     if torch.cuda.is_available() else None)

    # locate best.pt (ultralytics wrote it inside the run dir)
    best_pt = RUNS_DIR / args.experiment_id / "weights" / "best.pt"
    if not best_pt.is_file():
        LOG.error("best.pt not found after training: %s -- manifest NOT written", best_pt)
        return 1
    ckpt_sha = sha256_file(best_pt)

    # record resolved optimizer (ultralytics 'auto' picks during training)
    resolved_optimizer = None
    try:
        resolved_optimizer = type(model.trainer.optimizer).__name__
    except Exception:
        resolved_optimizer = None

    best_epoch, best_fitness, completed_epochs = read_best_epoch(
        RUNS_DIR / args.experiment_id / "results.csv")

    # checkpoint store copy (candidate store; dry runs excluded)
    ckpt_copy = None
    if not args.experiment_id.startswith("dryrun"):
        CKPT_DIR.mkdir(parents=True, exist_ok=True)
        ckpt_copy = CKPT_DIR / f"{args.experiment_id}_best.pt"
        shutil.copy2(best_pt, ckpt_copy)
        (CKPT_DIR / f"{args.experiment_id}_best.pt.sha256").write_text(
            ckpt_sha + "  " + ckpt_copy.name + "\n", encoding="utf-8")

    manifest = {
        "experiment_id": args.experiment_id,
        "generated_ist": now_ist(),
        "spec": ("PRHAAR C5 section 26 run manifest (reproducibility); sections 23-25 "
                 "(transfer learning, controlled experiments, image size)"),
        "model": {
            "requested": args.model,
            "loader_class": loader_cls.__name__,
            "init_checkpoint": args.model,
        },
        "checkpoints": {
            "best_pt": str(best_pt),
            "best_sha256": ckpt_sha,
            "store_copy": str(ckpt_copy) if ckpt_copy else None,
            "store_skipped_reason": "dryrun experiment id" if ckpt_copy is None else None,
        },
        "dataset": {
            "data_yaml": str(data_yaml),
            "data_yaml_sha256": sha256_file(data_yaml),
            "dataset_version": dataset_version,
            "dataset_version_source": dataset_version_source,
            "annotation_version": PRHAAR_C5_TAXONOMY_VERSION,
            "split_hash": split_hash,
            "split_hash_source": "sha256(manifest.jsonl)" if split_hash else "null: manifest.jsonl missing",
        },
        "training": {
            "imgsz": args.imgsz,
            "batch": args.batch,
            "epochs_requested": args.epochs,
            "epochs_completed": completed_epochs,
            "optimizer_requested": args.optimizer,
            "optimizer_resolved": resolved_optimizer,
            "lr0": args.lr0,
            "freeze": args.freeze,
            "augmentation": args.augmentation,
            "hyp_yaml": str(hyp_path) if hyp_path else None,
            "seed": args.seed,
            "deterministic": args.deterministic,
            "patience": args.patience,
            "workers": args.workers,
            "device": args.device,
            "best_epoch": best_epoch,
            "best_fitness": best_fitness,
        },
        "measured": {
            "train_seconds": round(train_s, 1),
            "train_minutes": round(train_s / 60, 2),
            "vram_peak_gib": vram_peak_gib,
        },
        "hardware": hardware_info(),
        "software": software_versions(),
        "notes": [
            "metric columns of C5_EXPERIMENT_LOG.csv are filled only by "
            "eval_detector.py from measured evaluation (section 61/62/63)",
        ],
    }
    man_out = RUNS_DIR / args.experiment_id / "run_manifest.json"
    man_out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    LOG.info("done in %.1f min | best epoch %s | VRAM peak %.3f GiB",
             train_s / 60, best_epoch, vram_peak_gib or -1)
    LOG.info("checkpoint sha256 %s", ckpt_sha)
    LOG.info("manifest -> %s", man_out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
