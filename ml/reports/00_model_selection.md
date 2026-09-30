# 00 — Model Selection Report (Phase 1)

**Project:** PRHAAR — SSB AI-Powered Border Surveillance & Command Platform
**Scope:** Global AI/ML layer, components C1–C7 (master phase spec §4, §5, §131)
**Status:** Phase 1 deliverable — **selection deferred to measured benchmarks** (per §5: no selection from marketing statements, no subjective ranking)
**Date:** 2026-09-29
**Related:** `00_dataset_plan.md`, `00_license_audit.md`, `PRHAAR_AI_MODEL_PLAN.md`

---

## 1. Purpose and ground rules

This report inventories and pre-scores model candidates for C5 (detection), C6 (tracking), C7 (ANPR: plate detection + OCR), and documents why C1–C4 deliberately use **no neural model** at this stage (§67–§74).

Ground rules applied throughout:

1. Candidates are described with **verifiable facts** (local package inspection, license text, published benchmark tables clearly labelled as external and *not* project-verified).
2. A candidate is **not** declared a winner in this phase. The decision table (§6) is completed only with measurements from Phase 2–5 benchmarks on PRHAAR data.
3. Every deployment dependency carries a license column (§4, §8). No Ultralytics production dependency decision is final until the AGPL/Enterprise question is resolved (§1 of `00_license_audit.md`).
4. The hard-case test set is frozen from day one (§83); nothing in this plan is trained, tuned, or augmented on it.

## 2. Evaluation environment (measured, not assumed)

| Property | Value | How verified |
|---|---|---|
| CPU | Intel Core i5-13420H, 8 cores / 12 threads | PowerShell `Get-CimInstance Win32_Processor` |
| System RAM | 8.29 GB | PowerShell `Get-CimInstance Win32_ComputerSystem` |
| GPU | NVIDIA RTX 2050, **4 GB VRAM** | CUDA functional with torch 2.5.1+cu121 |
| Free disk | ~307 GB on C: | filesystem check |
| Python | 3.11 | interpreter path |

**Consequences for training (§79 compute-aware training):**

- Primary training resolution **640**; 960 as a measured experiment; 1280 only if measured feasible on 4 GB VRAM.
- AMP enabled; small batch sizes; gradient accumulation where needed.
- YOLO26**m** is the practical upper bound for full-resolution training on this machine; **l** and **x** are to be *measured*, not assumed — if a scale cannot be trained on this hardware, that is documented as evidence, not hidden.
- All training feasibility claims in later reports must cite measured VRAM/time, not spec-sheet estimates.

## 3. C5 — Detection candidates

### 3.1 Primary candidate: YOLO26 (verified locally)

Local ultralytics package contains the full YOLO26 family:

```
cfg/models/26/yolo26.yaml        (scales n/s/m/l/x)
cfg/models/26/yolo26-p2.yaml     (small-object variant, P2 head)
cfg/models/26/yolo26-p6.yaml     (large-object variant, P6 head)
```

Verified architecture facts from the local YAML:

- `end2end: True` — NMS-free end-to-end inference option.
- `reg_max: 1` — no DFL branch.
- Scales (local YAML comments, exact parameter counts):
  n: 2,572,280 · s: 10,009,784 · m: 21,896,248 · l: 26,299,704 · x: 58,993,368
- P2/P6 variants are **YAML-only** (no scale-specific pretrained weights) — matches §45 note; parent-COCO checkpoint init + fine-tune is the documented path.

Published COCO reference (Ultralytics HF model card, retrieved 2026-09-29 — **externally published, NOT project-verified**; note param counts differ slightly from local YAML revision):

| Variant | mAP50-95 | mAP50-95 (e2e) | CPU ONNX ms | T4 TensorRT10 ms | Params (M, card) |
|---|---|---|---|---|---|
| YOLO26n | 40.9 | 40.1 | 38.9 | 1.7 | 2.4 |
| YOLO26s | 48.6 | 47.8 | 87.2 | 2.5 | 9.5 |
| YOLO26m | 53.1 | 52.5 | 220.0 | 4.7 | 20.4 |
| YOLO26l | 55.0 | 54.4 | 286.2 | 6.2 | 24.8 |
| YOLO26x | 57.5 | 56.9 | 525.8 | 11.8 | 55.7 |

These numbers are COCO-generic. Per §6, **COCO performance is not PRHAAR performance** — Indian border scenes, night/fog, tiny objects, and animal/human confusion must be measured on project data.

License: **AGPL-3.0 or Ultralytics Enterprise License** (verified from Ultralytics legal documentation). Decision item carried into `00_license_audit.md` §2 — the production-dependency choice (AGPL vs Enterprise) must be made explicitly before any C5 deployment claim.

### 3.2 Alternative candidate: RT-DETR (verified locally)

```
cfg/models/rt-detr/rtdetr-l.yaml, rtdetr-x.yaml          (available)
cfg/models/rt-detr/rtdetr-resnet50.yaml, resnet101.yaml  (YAML-only)
```

Published reference (Ultralytics docs, retrieved 2026-09 — **externally published, NOT project-verified**): RT-DETR-L ≈ 53.0 AP @ 114 FPS on T4; RT-DETR-X ≈ 54.8 AP @ 74 FPS. Transformer detector; distinct failure modes from YOLO26 (different small-object behavior, different latency profile on 4 GB VRAM).

The spec explicitly says **do not assume YOLO26 wins** (§4). The Phase 3 benchmark will run both families on the same PRHAAR-C5 splits.

### 3.3 C5 decision protocol (§5 decision table — filled in Phase 2–3)

| Field | Status |
|---|---|
| Models to benchmark | YOLO26s / YOLO26m / YOLO26l; RT-DETR-l (if trainable on 4 GB VRAM); YOLO26-p2 variant if small-object recall is insufficient |
| Dataset | PRHAAR-C5 v1 splits + frozen hard-case set (§83), scene/camera-grouped (§84) |
| Metrics required | Precision, Recall, mAP50, mAP50-95, per-class AP, small-object recall, night/fog/rain recall, occlusion recall, animal↔human confusion rates, FP/image |
| Deployment metrics | CPU latency, GPU latency, VRAM, RAM, model size, startup cost, ONNX export stability |
| Operating modes | HIGH_RECALL / BALANCED / HIGH_PRECISION evaluated separately (§90) |
| Decision | **PENDING — no winner declared in Phase 1** |

## 4. C6 — Tracker candidates (no training initially, §32)

All six trackers ship with the local ultralytics package (verified):

```
bytetrack.yaml  botsort.yaml  ocsort.yaml  deepocsort.yaml  fasttrack.yaml  tracktrack.yaml
```

Verified defaults (local config text, ByteTrack & BoT-SORT): `track_high_thresh: 0.25`, `track_low_thresh: 0.1`, `new_track_thresh: 0.25`, `track_buffer: 30`, `match_thresh: 0.8`, `fuse_score: True`. BoT-SORT adds `gmc_method: sparseOptFlow` (global motion compensation) and optional ReID (`with_reid: False` default; not enabled initially — §132 excludes Re-ID workstreams).

Primary comparison per §32: **ByteTrack vs BoT-SORT**, benchmarked on PRHAAR-C6 sequences with HOTA / IDF1 / MOTA / ID-switch rate / fragmentation (§37). OSCsort/DeepOCSORT/FastTracker/TrackTrack are bonus candidates if the primary two underperform on the project's occlusion patterns. Multi-camera identity is explicitly **out of scope** (§41).

Decision: **PENDING — Phase 4 benchmark.**

## 5. C7 — ANPR candidates

### 5.1 Plate detector

| Candidate | Rationale | Status |
|---|---|---|
| YOLO26n / YOLO26s fine-tuned on PRHAAR-C7 plate set | Small object class; fastest inference; consistent toolchain with C5 | Primary |
| YOLO26-p2 (small-object head) | Tiny/distant plates | Pursue only if measured recall on small plates is insufficient |
| RT-DETR-l | Alternative family per §45/§66 area | Only if measured P/R beats YOLO26 on the same plate split |

Targets (§120): plate detection **Precision ≥ 97%, Recall ≥ 97%** — targets, never to be presented as achieved until measured. Plate conditions matrix (§47): day/night, motion blur, angle, partial occlusion, dirt, glare, rain — each reported separately.

### 5.2 OCR

| Candidate | Published facts (external, not project-verified) | License (verified locally today) |
|---|---|---|
| **PP-OCRv6** tiny / small / medium — primary | 1.5M / 7.7M / 34.5M params; 73.5% / 81.3% / 83.2% reported accuracy; 50 languages; LCNetV4 backbone (paper) | PaddleOCR repository: **Apache-2.0** (LICENSE fetched from repo, 2026-09-29) |
| PP-OCRv5 — regression baseline | Prior generation; baseline for fine-tuning delta | Same repository license |
| TrOCR / PARSeq fine-tune — fallback | Only if PP-OCRv6 fails measured targets on Indian plates; document before attempting | Verify before use |

Fine-tuning strategy per §51: fine-tune on PRHAAR-C7 OCR crops (Indian plates, state-wise formats), keep **raw_read immutable** (§54), character confusions (O↔0, I↔1, B↔8, S↔5, Z↔2, G↔6) handled at the candidate layer as evidence only (§55). OCR metrics (§52): character accuracy ≥ 98% target on readable/accepted crops; exact plate ≥ 95% target on quality-gated readable tracks (§53, §120) — report per quality gate, not as one global number.

Decision: **PENDING — Phase 5 fine-tune + end-to-end evaluation.**

## 6. C1–C4 — no deep model in this phase

| Component | Method | Spec ref | Reason |
|---|---|---|---|
| C1 Risk | Deterministic scoring (existing engine) | §71–73 | Reproducibility = 100% on defined scenarios; neural risk model not justified without measured evidence of gaps |
| C2 Camera health | Classical CV / statistical (existing analyzers) | §67–68 | Learned model only if classical benchmark shows a measurable, documented deficit |
| C3 Evidence | SHA-256 / ledger / verification (existing) | §74 | Cryptographic correctness is deterministic; **no AI/ML** |
| C4 Correlation | Deterministic temporal/spatial/entity rules | §69–70 | No neural correlation model initially; decision revisited only with measured gap evidence |

Benchmarks for these are scenario/corpus-based (Phase 2), not training-based.

## 7. Summary decision table (to be completed with measurements)

| Component | Candidate(s) | Weights source | License | Measured P/R/mAP | Latency (CPU/GPU) | Decision |
|---|---|---|---|---|---|---|
| C5 detection | YOLO26 s/m/l; RT-DETR-l | COCO checkpoints → PRHAAR-C5 fine-tune | AGPL-3.0 / Enterprise | TBD Phase 3 | TBD Phase 3 | PENDING |
| C6 tracking | ByteTrack, BoT-SORT (+4) | none (algorithmic) | AGPL-3.0 (bundled toolchain) | HOTA/IDF1 TBD Phase 4 | TBD Phase 4 | PENDING |
| C7 plate det. | YOLO26 n/s (+p2 if needed) | COCO → PRHAAR-C7 fine-tune | AGPL-3.0 / Enterprise | TBD Phase 5 | TBD Phase 5 | PENDING |
| C7 OCR | PP-OCRv6 t/s/m | Official pretrained → PRHAAR-C7 fine-tune | Apache-2.0 | char/exact TBD Phase 5 | TBD Phase 5 | PENDING |
| C1 risk | deterministic | — | in-repo | reproducibility TBD Phase 2 | — | PENDING |
| C2 health | classical CV | — | in-repo | macro-F1 TBD Phase 2 | — | PENDING |
| C3 evidence | cryptography | — | in-repo | 100% expected-outcome TBD Phase 2 | — | PENDING |
| C4 correlation | deterministic rules | — | in-repo | P/R TBD Phase 2 | — | PENDING |

## 8. Explicit non-claims

- No model in this report is "selected", "production-ready", or "95%+". Every row says PENDING until its benchmark report exists (Phase 2–5).
- Published COCO/reported numbers above are external references, clearly not PRHAAR evidence.
- Per §105, any future evaluation of these models on public/project data must carry: *"Model was evaluated on public and/or project-specific non-operational data and has not been field-validated by SSB."*

## 9. Open items / verification gaps

1. **AGPL vs Enterprise** decision for the Ultralytics dependency — carried in `00_license_audit.md` §2; must be resolved before C5/C6/C7 deployment is called a production candidate.
2. YOLO26 param-count discrepancy between local YAML comments and HF card — resolved naturally when weights are hashed and measured in Phase 3.
3. RT-DETR trainability on 4 GB VRAM — to be measured (batch 1–2, AMP), not assumed.
4. PP-OCRv6 fine-tuning toolchain (PaddlePaddle) on this machine — feasibility check scheduled at the start of Phase 5.
