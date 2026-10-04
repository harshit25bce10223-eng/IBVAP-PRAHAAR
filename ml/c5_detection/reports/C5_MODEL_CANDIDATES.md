# C5 — Detector Candidate Set (spec §5)

**Project:** PRHAAR — SSB AI-Powered Border Surveillance & Command Platform
**Component:** C5 — Production Object Detection
**Spec traceability:** §5 (benchmark candidates), §67 execution order step 2
**Date:** 2026-10-03
**Status:** Candidate set frozen for benchmarking — **no winner declared** (spec §5: "Do not declare a model winner before measured evaluation")

> This document defines *what will be trained and evaluated* in the C5 benchmark (task #32).
> It contains no accuracy, latency, or suitability claims — those arrive only as measured
> results in `C5_EXPERIMENT_LOG.csv` and the final report.

---

## 1. Required benchmark set (spec §5)

| # | Candidate | Scale | Family | Requirement |
|---|-----------|-------|--------|-------------|
| 1 | YOLO26s | small | CNN single-stage, end-to-end | required (s/m/l) |
| 2 | YOLO26m | medium | CNN single-stage, end-to-end | required (s/m/l) |
| 3 | YOLO26l | large | CNN single-stage, end-to-end | required (s/m/l) |
| 4 | RT-DETR-l | large | Transformer (DETR family) | the "meaningfully different family" |

RT-DETR is the suggested different family in §5 and is included as **rtdetr-l**
(the large scale — the transformer family's compute cost does not allow a fair
like-for-like scale sweep on the available hardware; this asymmetry is itself
recorded as a benchmark condition).

## 2. Measured candidate metadata (verified locally, 2026-10-03)

Configs shipped in the installed `ultralytics 8.4.118` package; counts measured by
building each model from its YAML on this machine (no weights downloaded, no network):

| Candidate | YAML | Layers | Parameters | GFLOPs | Measured via |
|---|---|---|---|---|---|
| yolo26s | `cfg/models/26/yolo26.yaml` (scale s) | 260 | 10,009,784 | 22.8 | local model build + `info()` |
| yolo26m | `cfg/models/26/yolo26.yaml` (scale m) | 280 | 21,896,248 | 75.4 | local model build + `info()` |
| yolo26l | `cfg/models/26/yolo26.yaml` (scale l) | 392 | 26,299,704 | 93.8 | local model build + `info()` |
| rtdetr-l | `cfg/models/rt-detr/rtdetr-l.yaml` | 470 | 32,970,476 | 110.2 | local model build + `info()` |

Reproduction command (working ML Python 3.11 with torch 2.5.1+cu121):

```python
from ultralytics import YOLO, RTDETR
for s in ("s", "m", "l"):
    YOLO(f"yolo26{s}.yaml").model.info()
RTDETR("rtdetr-l.yaml").model.info()
```

## 3. Why this set is "meaningfully different" (§5 intent)

- YOLO26 (s/m/l) — CNN single-stage detector; YAML facts (read from the installed
  config, 2026-10-03): `end2end: True` (end-to-end mode) and `reg_max: 1` (DFL bins).
  Same architecture family across three compute scales → tests the accuracy/cost
  trade-off on the target hardware.
- RT-DETR-l — set-based transformer detector (HGNetv2 stem/backbone + hybrid encoder +
  decoder). No NMS post-processing by architecture; qualitatively different failure
  modes from the CNN family (e.g., handling of dense small objects and occlusion).
  A different family is required precisely so the final decision is not an
  all-in-one-architecture assumption.

The comparison answers: *does the transformer decoder earn its ~x GFLOPs cost on
PRHAAR's target classes (person/vehicle/animal at border-camera viewing angles)?*
— answer only from measured results in #32.

## 4. Hardware / training feasibility context (measured environment)

Verified machine constraints (recon, carried forward):

| Resource | Value |
|---|---|
| GPU | RTX 2050, 4 GB VRAM, driver 576.88 |
| RAM | 8.29 GB |
| CPU | i5-13420H (8C/12T) |
| Disk free | ~288 GB on C: |
| CUDA stack | torch 2.5.1+cu121, CUDA available = True |

Consequences recorded as *risks to be resolved by measurement in #32* — not assumed away:

- **rtdetr-l fine-tuning on 4 GB VRAM** is the highest-risk item of the benchmark
  (110.2 GFLOPs, 33.0 M params). Mitigation space under measurement: reduced batch
  size, AMP, frozen backbone stages, smaller image size — each mitigation is recorded
  per experiment row if used. If rtdetr-l cannot be trained to a valid state on this
  hardware, that is reported as a hardware-limited finding, not silently dropped.
- **YOLO26m/l** are the practical upper-bound scales for this VRAM class (from #1–#3);
  confirmed by measured batch tests in #32, not assumed.
- **Image size:** primary 640; 960 and 1280 only as measured experiments if feasible
  (spec §25 — 1280 is never auto-selected).

## 5. License dimension (cross-ref §6 audit)

All four candidates as implemented in the installed ultralytics package share the
same AGPL-3.0 / Enterprise licensing surface — including the YAML configs, whose first
line carries the AGPL-3.0 notice. The RT-DETR family additionally exists as an
Apache-2.0 original implementation (lyuwenyu/RT-DETR) that could replace the
ultralytics implementation if a no-AGPL constraint becomes binding.

Full record: [`model_license_audit.md`](./model_license_audit.md) (§6).

## 6. Open items handed to #32 (training/benchmark)

1. Per-candidate training recipe (pretrained-init source, epochs, augmentation, seed) —
   identical across candidates wherever fair, differences documented.
2. Measured VRAM batch feasibility per candidate on the RTX 2050.
3. Measured latency at 640 (and 960/1280 experiments where feasible).
4. Whether rtdetr-l trains to a valid state on this hardware (see §4 risk).
5. COCO-pretrained initialization checkpoints for each candidate — recorded with
   SHA-256 in the experiment log at download time.

## 7. Non-claims

- No model is declared a winner here; no accuracy, recall, or latency statement is made.
- Param/GFLOP counts are architecture facts, not performance predictions.
- No SSB validation, field-readiness, or production-candidate status is implied by
  anything in this document.
