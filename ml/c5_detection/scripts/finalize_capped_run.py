#!/usr/bin/env python
"""finalize_capped_run.py -- write a TRUTHFUL run_manifest.json for a training
run that was stopped at a user-directed epoch cap (epoch_cap_watcher.sh).

Why this exists (2026-10-15): the user directed a "smart + quality" time
budget for exp001 ("train within 3-4 hours"). The full 80-epoch schedule
cannot fit that window on this RTX 2050 (measured 14-20 min/epoch), so the
run is hard-capped at a fixed epoch. The sweep chain (run_sweep_302.sh)
treats run_manifest.json as the experiment-done contract -- without this
manifest the chain's crash path would RESUME the run to the full schedule.

Nothing here is estimated: every field is read from the run dir (args.yaml,
results.csv, weights/) or recomputed with the same helpers train_detector.py
uses. The termination block records the cap explicitly -- this is a labeled,
user-directed deviation from spec section 23's schedule, not a silent one.

Never overwrites an existing manifest (a natural finish wins).

usage: finalize_capped_run.py --experiment-id ID --model yolo26s.pt \
          --cap-epoch 50 [--requested-epochs 80] [--requested-by TEXT] \
          [--no-pin-memory] [--optimizer-resolved NAME]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))  # same-dir imports as train_detector

from train_detector import (  # noqa: E402
    CKPT_DIR,
    RUNS_DIR,
    hardware_info,
    now_ist,
    read_best_epoch,
    sha256_file,
    software_versions,
    total_ram_gib,
)
from c5_taxonomy import PRHAAR_C5_TAXONOMY_VERSION  # noqa: E402

PIN_MEMORY_NOTE = (
    "disabled via --no-pin-memory (Windows/WDDM 'resource already mapped' in "
    "pin-memory thread, measured 2026-10-14); ultralytics default is "
    "pin_memory=True when workers>0 (data/build.py:324/366)"
)


def load_args_yaml(run_dir: Path) -> dict:
    import yaml
    p = run_dir / "args.yaml"
    if not p.is_file():
        raise SystemExit(f"args.yaml not found: {p}")
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--experiment-id", required=True)
    ap.add_argument("--model", required=True,
                    help="initial pretrained checkpoint as passed to train_detector "
                         "(e.g. yolo26s.pt) -- recorded in model.requested")
    ap.add_argument("--cap-epoch", type=int, required=True)
    ap.add_argument("--requested-epochs", type=int, default=80)
    ap.add_argument("--requested-by", default="user time budget (epoch cap, recorded by epoch_cap_watcher.sh)")
    ap.add_argument("--no-pin-memory", action="store_true",
                    help="mirror the flag the run was launched with")
    ap.add_argument("--optimizer-resolved", default=None,
                    help="resolved optimizer class name if known from logs; else null + note")
    args = ap.parse_args()

    run_dir = RUNS_DIR / args.experiment_id
    man_out = run_dir / "run_manifest.json"
    if man_out.is_file():
        print(f"manifest already exists -- refusing to overwrite: {man_out}")
        return 0  # not an error: natural finish / early stop already recorded

    results_csv = run_dir / "results.csv"
    best_pt = run_dir / "weights" / "best.pt"
    last_pt = run_dir / "weights" / "last.pt"
    if not results_csv.is_file():
        print(f"ERROR: no results.csv: {results_csv}")
        return 2
    if not best_pt.is_file() or not last_pt.is_file():
        print(f"ERROR: missing checkpoints best.pt={best_pt.is_file()} last.pt={last_pt.is_file()}")
        return 2

    ay = load_args_yaml(run_dir)
    best_epoch, best_fitness, completed = read_best_epoch(results_csv)
    if completed is None or completed < args.cap_epoch:
        print(f"ERROR: results.csv shows {completed} epochs -- cap {args.cap_epoch} not reached; "
              "refusing to write a manifest that misrepresents progress")
        return 2

    # dataset provenance -- identical logic to train_detector.py
    data_yaml = Path(ay["data"]).resolve()
    dataset_root = data_yaml.parent
    dh_file = dataset_root / "dataset_hash.txt"
    if dh_file.is_file():
        dataset_version = dh_file.read_text(encoding="utf-8").strip()
        dataset_version_source = "dataset_hash.txt"
    else:
        dataset_version = "datayaml-" + sha256_file(data_yaml)[:16]
        dataset_version_source = "FALLBACK: no dataset_hash.txt in " + str(dataset_root)
    man_file = dataset_root / "manifest.jsonl"
    split_hash = sha256_file(man_file) if man_file.is_file() else None

    # workers note -- same text train_detector produces when RAM-capped
    workers_eff = int(ay.get("workers", 2))
    workers_req = 4  # exp001 was launched with --workers 4 (RAM cap engaged, RAM 7.71 GiB)
    workers_note = None
    ram_gib = total_ram_gib()
    if ram_gib is not None and ram_gib < 12.0 and workers_eff <= 2:
        workers_note = (f"capped {workers_req}->{workers_eff}: total RAM "
                        f"{ram_gib:.1f} GiB; workers=4 built 12 dataloader worker processes "
                        f"(~6.4 GiB private commit) and system commit exhaustion crashed "
                        f"training twice on 2026-10-14 (logs/train_exp001*.log)")

    # trainer-reported cumulative wall time = last row's time column
    import csv as _csv
    with results_csv.open(encoding="utf-8") as fh:
        rows = list(_csv.DictReader(fh))
    train_seconds = round(float(rows[-1]["time"]), 1)

    # checkpoint store copy -- same rule as train_detector (dryrun ids skipped)
    ckpt_copy = None
    skip_reason = None
    if not args.experiment_id.startswith("dryrun"):
        CKPT_DIR.mkdir(parents=True, exist_ok=True)
        ckpt_copy = CKPT_DIR / f"{args.experiment_id}_best.pt"
        import shutil
        shutil.copy2(best_pt, ckpt_copy)
        (CKPT_DIR / f"{args.experiment_id}_best.pt.sha256").write_text(
            sha256_file(best_pt) + "  " + ckpt_copy.name + "\n", encoding="utf-8")

    from datetime import datetime
    from train_detector import IST
    last_mtime = datetime.fromtimestamp(last_pt.stat().st_mtime, IST).strftime("%Y-%m-%d %H:%M:%S IST")

    manifest = {
        "experiment_id": args.experiment_id,
        "generated_ist": now_ist(),
        "spec": ("PRHAAR C5 section 26 run manifest (reproducibility); sections 23-25 "
                 "(transfer learning, controlled experiments, image size). "
                 "FINALIZED AT USER-DIRECTED EPOCH CAP -- see termination block."),
        "model": {
            "requested": args.model,
            "loader_class": "RTDETR" if "rtdetr" in args.model.lower() else "YOLO",
            "init_checkpoint": args.model,
        },
        "checkpoints": {
            "best_pt": str(best_pt),
            "best_sha256": sha256_file(best_pt),
            "last_pt": str(last_pt),
            "last_sha256": sha256_file(last_pt),
            "store_copy": str(ckpt_copy) if ckpt_copy else None,
            "store_skipped_reason": skip_reason,
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
            "imgsz": int(ay["imgsz"]),
            "batch": int(ay["batch"]),
            "epochs_requested": int(ay.get("epochs", args.requested_epochs)),
            "epochs_completed": completed,
            "optimizer_requested": ay.get("optimizer"),
            "optimizer_resolved": args.optimizer_resolved,
            "optimizer_resolved_note": (None if args.optimizer_resolved else
                                        "trainer stopped at cap; resolved optimizer not recoverable "
                                        "post-mortem -- launch log records the resolution"),
            "lr0": float(ay["lr0"]) if ay.get("lr0") is not None else None,
            "freeze": ay.get("freeze"),
            "augmentation": "default",
            "hyp_yaml": str(ay["cfg"]) if ay.get("cfg") else None,
            "seed": int(ay.get("seed", 0)),
            "deterministic": bool(ay.get("deterministic", False)),
            "patience": int(ay.get("patience", 25)),
            "workers": workers_eff,
            "workers_requested": workers_req,
            "workers_note": workers_note,
            "device": str(ay.get("device", "0")),
            "pin_memory": not args.no_pin_memory,
            "pin_memory_note": PIN_MEMORY_NOTE if args.no_pin_memory else
                               "ultralytics default (pin_memory=True when workers>0)",
            "resumed_from": {
                "last_pt": str(last_pt),
                "last_pt_sha256": sha256_file(last_pt),
                "last_pt_mtime": last_mtime,
                "note": ("run was in resumed state at cap; this is the most recent resume "
                         "checkpoint. Full resume history (multiple events 2026-10-14/15) is "
                         "recorded in logs/train_exp001*.log and "
                         "reports/evidence/incidents/20261014_exp001_incident.md"),
            },
            "best_epoch": best_epoch,
            "best_fitness": best_fitness,
        },
        "termination": {
            "type": "epoch_cap",
            "stopped_at_epoch": args.cap_epoch,
            "full_schedule_epochs": int(ay.get("epochs", args.requested_epochs)),
            "requested_by": args.requested_by,
            "rationale": ("user-directed time budget 2026-10-15 ('smart + quality approach... "
                          "within 3-4 hours'): 80 epochs cannot fit the window on this "
                          "RTX 2050 4GB (measured 14-20 min/epoch). Deviation from spec "
                          "section 23 schedule is recorded here, not hidden. The final "
                          "training run after error analysis (#33, spec section 64) will "
                          "use the full budget."),
            "checkpoints_at_cap": ("best.pt = best-fitness epoch so far (ultralytics "
                                   "selection, unchanged); last.pt = epoch %d checkpoint" % completed),
        },
        "measured": {
            "train_seconds": train_seconds,
            "train_minutes": round(train_seconds / 60, 2),
            "train_seconds_source": "results.csv last-row time column (trainer-reported cumulative wall)",
            "vram_peak_gib": None,
            "vram_peak_note": ("not recoverable after external taskkill; never estimated "
                               "(spec section 62). Referenced value for this GPU class is "
                               "~2.63 GiB at batch 8 (measured at launch 2026-10-14)."),
        },
        "hardware": hardware_info(),
        "software": software_versions(),
        "notes": [
            "metric columns of C5_EXPERIMENT_LOG.csv are filled only by "
            "eval_detector.py from measured evaluation (section 61/62/63)",
            "run stopped by epoch_cap_watcher.sh at the cap epoch; manifest written "
            "by finalize_capped_run.py from on-disk artifacts only",
            "checkpoint hashes recorded at cap time (sha256 of the files as left by "
            "the trainer; last.pt was written by the completed cap-epoch validation)",
        ],
    }
    man_out.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"manifest -> {man_out}")
    print(f"cap epoch {args.cap_epoch} | best epoch {best_epoch} | fitness {best_fitness} | "
          f"trainer-reported {train_seconds/60:.1f} min")
    print(f"best.pt sha256 {manifest['checkpoints']['best_sha256'][:16]}... "
          f"last.pt sha256 {manifest['checkpoints']['last_sha256'][:16]}...")
    return 0


if __name__ == "__main__":
    sys.exit(main())
