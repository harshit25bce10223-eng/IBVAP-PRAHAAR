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

Windows/WDDM + long-run notes (measured 2026-10-14, RTX 2050 / WDDM):
  * ultralytics hardcodes pin_memory=True whenever workers>0
    (site-packages/ultralytics/data/build.py:324/366) -- on a display-attached
    WDDM GPU this crashed epoch-1 validation with
    "CUDA error: resource already mapped" raised inside the pin-memory thread.
    --no-pin-memory patches torch.Tensor.pin_memory to a pass-through BEFORE
    model.train() and the deviation is recorded in the run manifest.
  * multi-hour runs on this machine can die to driver/OS events; --resume
    restarts from training/runs/<id>/weights/last.pt with epoch, optimizer
    state and args restored by ultralytics from the checkpoint. The manifest
    records the resume checkpoint's SHA-256 (evidence, not assumption).
  * low-RAM commit-exhaustion cap (measured 2026-10-14, same machine): with
    workers=4 ultralytics builds 12 dataloader worker processes (~6.4 GiB
    private commit; train+test+validator pools spawn EAGERLY via
    InfiniteDataLoader at setup). System commit reached 31.37/31.58 GiB and
    training died twice with "numpy ..._ArrayMemoryError: Unable to allocate
    1.17 MiB" (raised as SystemError by cv2.merge, masking the MemoryError).
    On machines with < 12 GiB total RAM this wrapper caps workers at 2
    (logged + recorded in the manifest as workers_requested / workers_note).
    Resume passes the capped value explicitly -- ultralytics check_resume
    applies a workers override by design ("allow arg updates to reduce memory
    on resume", engine/trainer.py).

Usage:
    python scripts/train_detector.py --data datasets/PRHAAR-C5-DETECTION/data.yaml \
        --model yolo26s.pt --experiment-id exp001_yolo26s_640 --imgsz 640 --batch 8 \
        --no-pin-memory
    python scripts/train_detector.py --resume --data datasets/PRHAAR-C5-DETECTION/data.yaml \
        --model yolo26s.pt --experiment-id exp001_yolo26s_640 --no-pin-memory
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
    ap.add_argument("--workers", type=int, default=4,
                    help="dataloader workers (low-RAM machines are capped to 2; see module docstring)")
    ap.add_argument("--device", default="0", help="'0' (CUDA) or 'cpu' (explicit only)")
    ap.add_argument("--no-pin-memory", action="store_true",
                    help="disable pinned-memory transfers (Windows/WDDM workaround for "
                         "'CUDA error: resource already mapped' in the pin-memory thread; "
                         "ultralytics hardcodes pin_memory=True when workers>0, data/build.py:324/366)")
    ap.add_argument("--resume", action="store_true",
                    help="resume from training/runs/<id>/weights/last.pt (crash recovery); "
                         "ultralytics restores epoch/optimizer/args from the checkpoint")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    t0 = time.time()

    # ---- low-RAM worker cap (measured 2026-10-14; see module docstring) ----
    workers_requested = args.workers
    workers_effective = args.workers
    workers_note = None
    ram_gib = total_ram_gib()
    if ram_gib is not None and ram_gib < 12.0 and workers_effective > 2:
        workers_effective = 2
        workers_note = (f"capped {workers_requested}->{workers_effective}: total RAM "
                        f"{ram_gib:.1f} GiB; workers=4 built 12 dataloader worker processes "
                        f"(~6.4 GiB private commit) and system commit exhaustion crashed "
                        f"training twice on 2026-10-14 (logs/train_exp001*.log)")
        LOG.warning("workers capped %d -> %d (RAM %.1f GiB: commit-exhaustion workaround)",
                    workers_requested, workers_effective, ram_gib)

    data_yaml = args.data.resolve()
    if not data_yaml.is_file():
        LOG.error("data.yaml not found: %s", data_yaml)
        return 2
    run_dir = RUNS_DIR / args.experiment_id
    resume_meta = None
    if args.resume:
        last_pt = run_dir / "weights" / "last.pt"
        if not last_pt.is_file():
            LOG.error("--resume given but no checkpoint exists: %s", last_pt)
            return 2
        resume_meta = {
            "last_pt": str(last_pt),
            "last_pt_sha256": sha256_file(last_pt),
            "last_pt_mtime": datetime.fromtimestamp(last_pt.stat().st_mtime, IST)
                            .strftime("%Y-%m-%d %H:%M:%S IST"),
        }
        LOG.info("resume: last.pt sha256 %s... (mtime %s)",
                 resume_meta["last_pt_sha256"][:16], resume_meta["last_pt_mtime"])
    elif run_dir.exists():
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
    if args.resume:
        model = loader_cls(str(run_dir / "weights" / "last.pt"))
    else:
        model = loader_cls(args.model)

    # Windows/WDDM workaround (see module docstring): ultralytics hardcodes
    # pin_memory=True when workers>0 (data/build.py:324/366). The pin-memory
    # thread crashed with "CUDA error: resource already mapped" during epoch-1
    # validation (measured 2026-10-14). Patching Tensor.pin_memory to a
    # pass-through disables the actual CUDA host registration; transfers then
    # go through the ordinary pageable path (slightly slower, always correct).
    if args.no_pin_memory:
        import torch
        if not getattr(torch.Tensor.pin_memory, "_prahaar_noop", False):
            def _pin_memory_noop(self, device=None):
                return self
            _pin_memory_noop._prahaar_noop = True  # type: ignore[attr-defined]
            torch.Tensor.pin_memory = _pin_memory_noop  # type: ignore[assignment]
        LOG.warning("pin_memory disabled -- Windows/WDDM workaround "
                    "(recorded in run manifest; NOT an ultralytics default)")

    train_kwargs = dict(
        data=str(data_yaml),
        imgsz=args.imgsz,
        batch=args.batch,
        epochs=args.epochs,
        optimizer=args.optimizer,
        seed=args.seed,
        deterministic=args.deterministic,
        patience=args.patience,
        workers=workers_effective,
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
    if args.resume:
        # ultralytics restores epoch, optimizer state and full training args
        # from the checkpoint on resume; workers is deliberately overridden
        # (check_resume allows it "to reduce memory on resume").
        model.train(resume=True, workers=workers_effective)
    else:
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
            "workers": workers_effective,
            "workers_requested": workers_requested,
            "workers_note": workers_note,
            "device": args.device,
            "pin_memory": not args.no_pin_memory,
            "pin_memory_note": ("disabled via --no-pin-memory (Windows/WDDM 'resource already "
                                "mapped' in pin-memory thread, measured 2026-10-14); ultralytics "
                                "default is pin_memory=True when workers>0 (data/build.py:324/366)"
                                if args.no_pin_memory else
                                "ultralytics default (pin_memory=True when workers>0)"),
            "resumed_from": resume_meta,
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
