# PRHAAR AI/ML Model Plan

**PRHAAR — SSB AI-Powered Border Surveillance & Command Platform — Global AI/ML Layer (C1–C7)**
**Document type:** Living master plan (spec §131 order of execution)
**Created:** 2026-09-29 (Phase 1)
**Companions:** `00_model_selection.md` · `00_dataset_plan.md` · `00_license_audit.md` · `PRHAAR_DATASET_CATALOG.md`

---

## 1. Objective and the meaning of "95%"

Non-negotiable objective (§0): build the C1–C7 AI/ML intelligence layer to a **measurable, honest** standard — achieve 95%+ where the problem is observable and measurable — while **explicitly refusing to fabricate accuracy where the pixels do not contain enough information**.

Never report "PRHAAR accuracy = 95%". Report per-model, per-condition metrics with dataset/split definitions (§87), e.g.:

```
C5 detection:   Precision 96.2% · Recall 95.4% · mAP50 97.1% (on PRHAAR-C5 vX test, frozen hard-case reported separately)
C6 tracking:    IDF1 93.6% · HOTA 91.8%
C7:             Plate detection recall 97.4% · OCR character accuracy 98.6% · Track-level exact plate 95.8%
```

An aggregate metric never implies production readiness (§88, §116). If a component reaches 88%, it is reported as 88% with the gap and cause identified — thresholds are not forced down to fit claims (§117). Where the data physically cannot support a rate, that impossibility is documented instead of patched with a guess (§118).

## 2. Component plan (method per component)

| Comp. | Method | Trained? | Phase | Deliverable report | Acceptance target (§120) — targets, never pre-claimed |
|---|---|---|---|---|---|
| C1 | Deterministic risk engine (existing) + scenario benchmark | No | 2 | `C1_RISK_AI_ML_REPORT.md` | Deterministic consistency = 100% on defined scenarios |
| C2 | Classical CV / statistical health analyzers + frozen health benchmark | No (learned model only if evidence justifies, §67–68) | 2 | `C2_CAMERA_HEALTH_AI_REPORT.md` | Health-state macro-F1 ≥ 95% held-out; false ONLINE rate explicitly reported |
| C3 | Cryptographic evidence pipeline benchmark (SHA-256 / ledger / verification) | No — **never AI/ML** | 2 | `C3_EVIDENCE_CRYPTO_REPORT.md` | Expected-outcome correctness = 100% |
| C4 | Deterministic temporal/spatial/entity correlation + held-out scenarios | No neural initially (§69) | 2 | `C4_CORRELATION_AI_REPORT.md` | P/R ≥ 95% held-out; false-correlation rate reported |
| C5 | Deep detector: YOLO26 s/m/l primary vs RT-DETR-l alternative (measured) | Yes | 3 | `C5_DETECTION_MODEL_REPORT.md` | P ≥ 95% · R ≥ 95% · mAP50 ≥ 95%; hard-case subsets separate |
| C6 | ByteTrack vs BoT-SORT (+4 bundled backends) | No initial training | 4 | `C6_TRACKING_MODEL_REPORT.md` | 90–95%+ tracking quality depending on benchmark; IDF1/HOTA/MOTA + ID-switch reported |
| C7a | Plate detector (YOLO26 n/s, p2 variant if needed) | Yes | 5 | `C7_ANPR_MODEL_REPORT.md` (with C7b) | Plate P ≥ 97% · R ≥ 97% |
| C7b | OCR: PP-OCRv6 fine-tune (t/s/m; PP-OCRv5 baseline) | Yes/fine-tuned | 5 | same | Char acc ≥ 98% on readable crops; exact ≥ 95% on quality-gated readable tracks |
| C7c | Temporal fusion + Indian format validator (§56–§58) | No (logic layer) | 5 | same | Read-confidence separation (§59) reported; raw reads immutable (§54) |

Detailed selection evidence: `00_model_selection.md`. Dataset construction: `00_dataset_plan.md`.

## 3. Integration architecture (drop-in providers, §124)

Production models integrate at the **provider boundary only**:

```
AI model (YOLO26 fine-tune)  →  C5 DetectionInferenceProvider (app/domain/detection/inference_provider.py)
                             →  DetectionNormalizer (app/domain/detection/normalizer.py)
                             →  existing detection service / persistence / APIs / frontend
AI model (plate detect + OCR) →  C7 ANPRProvider (app/domain/anpr/provider.py)
                             →  existing ANPR service / persistence / APIs
```

Hard rules:

- No model-specific field ever leaks past the normalizer into C6/C4/C1 domain services.
- The factory `create_provider()` gains real implementations (`local_gpu`, `onnx`, …) alongside the existing demo provider; **REAL mode never silently falls back to DEMO** — an explicit unavailable state is raised instead (§30).
- C5 model taxonomy (PERSON, MOTORCYCLE, BICYCLE, CAR, LIGHT_VEHICLE, TRUCK, BUS, TRACTOR, ANIMAL) maps to the app canonical taxonomy (PERSON / VEHICLE / ANIMAL / OBJECT / UNKNOWN) inside the provider adapter, preserving the fine-grained class in metadata only.
- If integration exposes an actual schema mismatch in a locked component: identify → document → minimal fix → regression test (§125). No rewrites for architectural preference.

## 4. Metadata, versioning, traceability

- **Model metadata in every output (§29):** `model_name`, `model_version`, `weights_hash`, `taxonomy_version`, `preprocessing_version`, runtime/device — the existing `NormalizedDetection` dataclass already carries these fields; providers must populate them (no silent UNKNOWNs for real models).
- **Dataset versioning (§76):** `PRHAAR-C5 vMAJOR.MINOR` etc., manifest JSON + per-file SHA-256 recorded at acquisition.
- **Model versioning (§77):** model id + weights SHA-256 + training config hash + dataset version + eval report id.
- **Reproducibility (§78):** every training run emits a run manifest (config, seed, environment, dataset version, metrics).
- **E2E traceability (§122):** camera_id → detection_id → track_id → event_id → correlation_id → incident_id → evidence_id (+ sighting_id/vehicle_id for C7) resolvable; model_version + weights_hash attached where applicable.

## 5. Compute-aware training (§79)

Machine (measured): i5-13420H 8C/12T · 8.29 GB RAM · RTX 2050 **4 GB VRAM** · ~307 GB free disk · Python 3.11.

- Batch/AMP tuned by measurement; training feasibility of each model scale is an **experiment result**, recorded (VRAM peak, s/epoch), not an assumption.
- yolo26m is the practical ceiling for full-res training here; l/x only if measured feasible (likely reduced imgsz); p2 variants are YAML-only (parent checkpoint init, must be documented).
- No "realtime" claims without measured pipeline latency across acquisition → preprocess → inference → postprocess → tracking → ANPR → persistence (§91–§92).

## 6. Safety, ethics, and claims policy (§80, §83, §101–§105, §129)

- **Never** claim: `100% accuracy` · `100% real-world accuracy` · `guaranteed 95% everywhere` · `zero false positives` · `SSB field validated` · `production certified` — without real evidence.
- C3 evidence chain stays cryptographic and deterministic; **no AI/ML** added (§74).
- **Frozen hard-case test set** (§83): created once, never trained/tuned/augmented on; its metrics always reported separately, per split definition.
- **No autonomous enforcement** (§103): AI output never directly triggers enforcement; a human decision layer is required, and identity/plate outputs are never treated as legal truth (§54, §104).
- A model confidence is not legal truth; a Track ID is not a human identity; an OCR output is not a legally confirmed vehicle identity.
- Required evaluation disclaimer (§105): *"Model was evaluated on public and/or project-specific non-operational data and has not been field-validated by SSB."*
- No hidden failures: gaps, blocked datasets, infeasible scales, and degraded conditions are reported in the open (§31, §129).

## 7. Execution order (spec §131) and current status

| Phase | Content | Status |
|---|---|---|
| 1 | Research + license audit → `ml/reports/00_*.md` + catalog + this plan + `ml/` scaffold (§75) | **IN PROGRESS — deliverables written 2026-09-29** |
| 2 | C1 scenario benchmark · C2 classical-CV benchmark · C3 cryptographic corpus · C4 correlation benchmark | Pending |
| 3 | C5 dataset construction → annotation QA → training → evaluation → hard-case → deployment (REAL provider) | Pending |
| 4 | C6 tracker benchmark → custom MOT dataset → evaluation → selection → integration | Pending |
| 5 | C7 plate dataset → plate detector training → OCR dataset → OCR fine-tuning → temporal fusion → e2e evaluation | Pending |
| 6 | Full C1–C7 integration | Pending |
| 7 | Shadow mode (real chain observed, not trusted) | Pending |
| 8 | Production-candidate decisions (§116 gate) + master reports (`PRHAAR_AI_MODEL_CATALOG.md`, `PRHAAR_AI_BENCHMARK.md`, `PRHAAR_AI_ML_MASTER_FINAL_REPORT.md`) | Pending |

## 8. Artifact strategy (§123)

- Weights (`best.pt`, `exported.onnx`, OCR artifacts) are **not committed to git**; they live under module `checkpoints/`/`export/` dirs (gitignored), with SHA-256 hashes + training configs + dataset manifests recorded in reports.
- At completion the artifact set includes: best checkpoint, ONNX export, TensorRT engine if supported on this hardware, OCR model artifact, plate detector artifact, model metadata, SHA-256 hashes, training configs, dataset manifests, evaluation reports.

## 9. Explicit non-goals this phase (§132)

Not started and will not be started here: Face recognition · Person Re-ID · Suspicious behaviour · Fight detection · Weapon detection · Night enhancement models · Specialist human-vs-animal classifier · Audio anomaly · Surface/ground anomaly · Pose-crawling · Camouflage · NL investigation assistants. (C6 uses tracker algorithms only; ReID features stay disabled in BoT-SORT initially.)

## 10. Open decisions and verification gaps

1. **Ultralytics AGPL vs Enterprise** — blocks any production-candidate label for C5/C6/C7 until decided (see `00_license_audit.md` §3).
2. **IDD license unresolved** → Layer-B currently limited to verify-at-acquisition sources.
3. **Layer C data does not exist yet** — collection is the critical path; counts will be reported as collected, never fabricated.
4. **RT-DETR / yolo26-l trainability on 4 GB VRAM** — to be measured in Phase 3.
5. **PaddleOCR toolchain feasibility** on this machine — measured at Phase 5 start.
6. **Indian plate public data scarcity** — mitigated by CC-BY-4.0 Zenodo base (1,700 verified) + project collection + synthetic augmentation only where clearly labelled.
