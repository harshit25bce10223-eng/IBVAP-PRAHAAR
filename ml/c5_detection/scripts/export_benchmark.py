#!/usr/bin/env python
"""PRHAAR C5 #34 prep -- export + deployment benchmark harness (spec 42-43).

Builds export artifacts from a checkpoint and measures export integrity
(size + sha256), runtime forward-pass sanity, and on-device latency.
CPU-only by design: the single RTX 2050 is on 24/7 training duty, so
TensorRT `engine` builds and cuda latency runs are REFUSED with a loud
error while any train_detector process is alive (spec 46: no silent
fallback). Engine benchmark is a deferral, never a skipped check.

Measured-only policy (spec 61/62): every number in the report JSON is
measured by this script. When the machine is simultaneously training a
run, the report is stamped measured_under_training_contention=true so
readers know latency numbers carry CPU/disk contention and a deployment
decision must re-measure on an idle machine.

Outputs: reports/export_benchmark/<experiment_id>_export.json
Nothing is appended to C5_EXPERIMENT_LOG.csv here -- 63 log rows come
only from eval_detector.py on measured val/test metrics.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import platform
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import yaml

C5_ROOT = Path(__file__).resolve().parents[1]
EXPORTS_DIR = C5_ROOT / "exports"
REPORTS_DIR = C5_ROOT / "reports" / "export_benchmark"
ALLOWED_FORMATS = ("onnx", "torchscript", "engine")

LOG = logging.getLogger("export_benchmark")

ORT_DTYPE_MAP = {
    "tensor(float)": np.float32,
    "tensor(float16)": np.float16,
    "tensor(double)": np.float64,
    "tensor(int64)": np.int64,
    "tensor(int32)": np.int32,
}


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def training_alive():
    """(alive_or_None, detail). Probe failure returns (None, error) --
    recorded in the report, never guessed (spec 46)."""
    try:
        out = subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             "(Get-CimInstance Win32_Process -Filter \"name='python.exe'\").CommandLine"
             " | Where-Object { $_ -match 'train_detector' } | Measure-Object"
             " | Select-Object -ExpandProperty Count"],
            capture_output=True, text=True, timeout=60)
        n = int((out.stdout or "0").strip() or "0")
        return n >= 1, n
    except Exception as e:  # noqa: BLE001 -- probe failure is data, not a crash
        return None, f"{type(e).__name__}: {e}"


def pick_loader(weights: Path):
    """Same rule as eval_detector.py: family from the checkpoint's own
    recorded train_args, never from the filename."""
    import torch
    from ultralytics import RTDETR, YOLO

    loader_cls, basis = YOLO, "no train_args readable -- YOLO default"
    try:
        ck = torch.load(str(weights), map_location="cpu", weights_only=False)
        ta = ck.get("train_args", {}) if isinstance(ck, dict) else {}
        mname = str(ta.get("model", ""))
        if mname:
            basis = f"checkpoint train_args model={mname!r}"
            if "rtdetr" in mname.lower():
                loader_cls = RTDETR
        del ck
    except Exception as e:  # noqa: BLE001
        basis = f"train_args unreadable ({type(e).__name__}) -- YOLO default"
    return loader_cls, basis


def export_one(fmt: str, weights: Path, imgsz: int, out_dir: Path):
    """Export `weights` to `fmt` on CPU; move artifact into out_dir.
    Returns dict with measured integrity fields. Raises on failure."""
    import ultralytics

    loader_cls, basis = pick_loader(weights)
    model = loader_cls(str(weights))
    t0 = time.time()
    produced = model.export(format=fmt, imgsz=imgsz, device="cpu",
                            half=False, dynamic=False, nms=False, verbose=True)
    elapsed = time.time() - t0
    src = Path(str(produced))
    if not src.is_file():
        raise RuntimeError(f"ultralytics export returned non-file {src!r}")
    dst = out_dir / src.name
    shutil.move(str(src), str(dst))
    return {
        "format": fmt,
        "path": str(dst.relative_to(C5_ROOT)),
        "sha256": sha256_file(dst),
        "size_bytes": dst.stat().st_size,
        "elapsed_s": round(elapsed, 3),
        "loader_basis": basis,
        "ultralytics": ultralytics.__version__,
    }


def measure_onnx(onnx_path: Path, warmup: int, iters: int):
    import onnxruntime as ort

    sess = ort.InferenceSession(str(onnx_path), providers=["CPUExecutionProvider"])
    inp = sess.get_inputs()[0]
    if inp.type not in ORT_DTYPE_MAP:
        raise RuntimeError(f"unmapped ONNX input dtype {inp.type!r} -- refusing to guess (spec 46)")
    shape = [d if isinstance(d, int) and d > 0 else 1 for d in inp.shape]
    x = np.random.default_rng(0).standard_normal(shape).astype(ORT_DTYPE_MAP[inp.type])
    outs = sess.run(None, {inp.name: x})  # sanity forward
    times = []
    for _ in range(warmup):
        sess.run(None, {inp.name: x})
    for _ in range(iters):
        t0 = time.perf_counter()
        sess.run(None, {inp.name: x})
        times.append((time.perf_counter() - t0) * 1000.0)
    arr = np.asarray(times)
    return {
        "runtime": "onnxruntime-cpu",
        "providers": list(sess.get_providers()),
        "input": {"name": inp.name, "shape": [int(d) for d in shape], "dtype": str(ORT_DTYPE_MAP[inp.type].__name__)},
        "outputs": [{"name": o.name, "shape": [d if isinstance(d, int) else str(d) for d in o.shape]}
                    for o in sess.get_outputs()],
        "forward_ok": True,
        "sanity_output_shapes": [[d if isinstance(d, int) else str(d) for d in o.shape] for o in outs],
        "dummy_seed": 0,
        "warmup": warmup,
        "iters": iters,
        "p50_ms": round(float(np.percentile(arr, 50)), 3),
        "p95_ms": round(float(np.percentile(arr, 95)), 3),
        "mean_ms": round(float(arr.mean()), 3),
        "imgs_per_s": round(1000.0 / float(arr.mean()), 2),
    }


def measure_torchscript(ts_path: Path, like: dict, warmup: int, iters: int):
    import torch

    ts = torch.jit.load(str(ts_path), map_location="cpu")
    ts.eval()
    torch.manual_seed(0)
    x = torch.from_numpy(
        np.random.default_rng(0).standard_normal(like["input"]["shape"])
        .astype(ORT_DTYPE_MAP["tensor(float)"]))
    with torch.inference_mode():
        ts(x)  # sanity forward
        for _ in range(warmup):
            ts(x)
        times = []
        for _ in range(iters):
            t0 = time.perf_counter()
            ts(x)
            times.append((time.perf_counter() - t0) * 1000.0)
    arr = np.asarray(times)
    return {
        "runtime": "torchscript-cpu",
        "forward_ok": True,
        "warmup": warmup,
        "iters": iters,
        "p50_ms": round(float(np.percentile(arr, 50)), 3),
        "p95_ms": round(float(np.percentile(arr, 95)), 3),
        "mean_ms": round(float(arr.mean()), 3),
        "imgs_per_s": round(1000.0 / float(arr.mean()), 2),
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--weights", required=True)
    ap.add_argument("--experiment-id", required=True)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--formats", default="onnx,torchscript",
                    help="csv subset of: onnx,torchscript,engine")
    ap.add_argument("--warmup", type=int, default=10)
    ap.add_argument("--iters", type=int, default=50)
    ap.add_argument("--force", action="store_true",
                    help="overwrite an existing report for this experiment_id")
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

    weights = Path(args.weights).resolve()
    if not weights.is_file():
        LOG.error("weights not found: %s", weights)
        return 2
    fmts = [f.strip() for f in args.formats.split(",") if f.strip()]
    if not fmts or any(f not in ALLOWED_FORMATS for f in fmts):
        LOG.error("--formats must be a csv subset of %s (got %r)", ALLOWED_FORMATS, fmts)
        return 2

    alive, detail = training_alive()
    contention = alive is True
    LOG.info("training_alive probe -> %s (detail=%r)", alive, detail)

    if "engine" in fmts and (alive is True or alive is None):
        LOG.error("REFUSING engine export: GPU is training (alive=%s) or probe failed "
                  "(%r) -- a TensorRT build on the 4 GB WDDM GPU would contend with "
                  "training. Re-run after the chain finishes (spec 46: no silent fallback).",
                  alive, detail)
        return 3
    fmts = [f for f in fmts if f != "engine"]
    deferrals = ["engine: TensorRT build + engine latency DEFERRED until the GPU "
                 "is free of training duty; not measured, not assumed (spec 43)."]

    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORTS_DIR / f"{args.experiment_id}_export.json"
    if report_path.is_file() and not args.force:
        LOG.error("report exists: %s (pass --force to overwrite)", report_path)
        return 4
    out_dir = EXPORTS_DIR / args.experiment_id
    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        import onnxslim  # noqa: F401 -- export dep; fail loud before any work
        import onnx
        import onnxruntime
        import torch
        import ultralytics
    except ImportError as e:
        LOG.error("missing export dependency: %s -- install it explicitly (spec 46)", e)
        return 5

    export_results, latencies = [], {}
    try:
        for f in fmts:
            LOG.info("export %s (imgsz=%d, cpu)...", f, args.imgsz)
            export_results.append(export_one(f, weights, args.imgsz, out_dir))
    except Exception as e:  # noqa: BLE001
        LOG.error("export failed: %s -- see ultralytics output above; artifacts so far: %s",
                  e, [r["path"] for r in export_results])
        return 5

    onnx_res = next((r for r in export_results if r["format"] == "onnx"), None)
    if onnx_res:
        LOG.info("measuring onnxruntime-cpu latency (%d warmup / %d iters)...",
                 args.warmup, args.iters)
        latencies["onnx"] = measure_onnx(C5_ROOT / onnx_res["path"], args.warmup, args.iters)
    ts_res = next((r for r in export_results if r["format"] == "torchscript"), None)
    if ts_res and "onnx" in latencies:
        latencies["torchscript"] = measure_torchscript(
            C5_ROOT / ts_res["path"], latencies["onnx"], args.warmup, args.iters)

    try:
        git_rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=str(C5_ROOT),
                                 capture_output=True, text=True, timeout=30).stdout.strip() or None
    except Exception:  # noqa: BLE001
        git_rev = None

    try:
        import psutil
        rss_mb = round(psutil.Process().memory_info().rss / (1 << 20), 1)
        mem = {"peak_observed_rss_mb": rss_mb,
               "note": "this python process RSS after measurement (Windows; not a hard cap)"}
    except ImportError:
        mem = {"peak_observed_rss_mb": None,
               "note": "psutil unavailable -- process memory NOT measured, null not zero (spec 62)"}

    report = {
        "schema": "c5_export_benchmark_v1",
        "experiment_id": args.experiment_id,
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "source_weights": {"path": str(weights.relative_to(C5_ROOT)),
                           "sha256": sha256_file(weights),
                           "size_bytes": weights.stat().st_size},
        "export": {"imgsz": args.imgsz, "batch": 1, "dynamic": False, "half": False,
                   "device": "cpu", "formats_requested": fmts, "results": export_results},
        "latency": {"device": "cpu", **latencies},
        "memory": mem,
        "environment": {"python": platform.python_version(), "torch": torch.__version__,
                        "ultralytics": ultralytics.__version__, "onnx": onnx.__version__,
                        "onnxslim": getattr(onnxslim, "__version__", "unknown"),
                        "onnxruntime": onnxruntime.__version__, "git_commit": git_rev},
        "contention": {"training_alive": alive, "probe_detail": detail,
                       "measured_under_training_contention": contention,
                       "note": ("latency measured while train_detector.py was RUNNING on "
                                "this machine -- re-measure on an idle machine before any "
                                "deployment decision (spec 61/62)" if contention
                                else "measured on an idle machine (no train_detector process)")},
        "deferrals": deferrals,
    }
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lat_line = " | ".join(f"{k}: p50 {v['p50_ms']} ms / p95 {v['p95_ms']} ms / {v['imgs_per_s']} img/s"
                          for k, v in latencies.items())
    LOG.info("report written: %s", report_path.relative_to(C5_ROOT))
    LOG.info("exports: %s", ", ".join(f"{r['format']}={r['size_bytes']:,} B sha256 {r['sha256'][:12]}..."
                                      for r in export_results))
    LOG.info("latency (cpu%s): %s",
             ", TRAINING-CONTENDED" if contention else "", lat_line or "none")
    return 0


if __name__ == "__main__":
    sys.exit(main())
