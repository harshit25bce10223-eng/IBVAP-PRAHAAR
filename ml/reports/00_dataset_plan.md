# 00 — Dataset Plan (Phase 1)

**Project:** PRHAAR — SSB AI-Powered Border Surveillance & Command Platform
**Scope:** AI/ML datasets for C1–C7 (master phase spec §6–§18, §34, §46–§48, §64, §76, §83–§86)
**Status:** Phase 1 deliverable — plan only; **no dataset is downloaded by this document**
**Date:** 2026-09-29
**Related:** `00_model_selection.md`, `00_license_audit.md`, `PRHAAR_DATASET_CATALOG.md`

---

## 1. Dataset philosophy — three layers (§6)

```
LAYER A — GENERIC PRETRAINING      COCO-lineage checkpoint weights (transfer learning, no redistribution)
LAYER B — INDIA DOMAIN ADAPTATION  IDD / VisDrone / open imagery (license-gated, see audit)
LAYER C — PRHAAR CUSTOM DOMAIN     PRHAAR-C5 / C6 / C7 collected + annotated under project control
```

Rules:

- Transfer learning, never training from scratch (§6).
- Public benchmark performance is **not** PRHAAR performance (§6).
- Drone imagery (VisDrone) must never be presented as equivalent to fixed border-camera imagery (§7).
- Layer-B data is used only if its license permits; no silent download of unknown-rights data (§8).
- If a dataset count is smaller than planned, the real number is reported and the gap documented — counts are never fabricated (§9).

## 2. Layer A — Generic pretraining (weights lineage only)

| Item | Detail |
|---|---|
| Source | COCO-pretrained YOLO26 / RT-DETR checkpoints from the official model release |
| Use | Initialization only; we do not redistribute COCO images or annotations |
| License note | Checkpoint lineage recorded in model cards; COCO annotation license is CC-BY-4.0, images vary by Flickr source — audit entry recorded for completeness |
| Status | Available (checkpoints downloadable) — used in Phase 3/5 fine-tuning |

## 3. Layer B — India domain adaptation (license-gated candidates)

| Dataset | Verified facts | Intended role | Gate |
|---|---|---|---|
| **India Driving Dataset (IDD)** | 46,588 images, train/val/test splits; Indian road/unstructured environments | Domain adaptation toward Indian scenes | **BLOCKED** — license page unreachable during audit; do not download until terms are confirmed (see `00_license_audit.md`) |
| **VisDrone** | 288 video clips, 261,908 frames, 10,209 static images, 2.6M+ boxes; drone imagery | Small-object and tracking research benchmark | Research-use terms must be verified at acquisition; never presented as border-camera evidence |
| **Open Images V7** | Bundled loader present in local ultralytics package (`open-images-v7.yaml`) | Additional animal/person diversity (Layer B augmentation) | License verification at download time |
| **african-wildlife** | Bundled loader present locally; 4 large-mammal classes | Partial wild-animal silhouette diversity | License verification at download time; do not map to Indian species claims |
| **Kaggle Indian plate sets** | Various, license varies per dataset page | C7 plate detection/OCR candidates | Blocked until per-dataset license verified at download time (KAGGLE_AUTH needed) |

No Layer-B download proceeds until its row in `00_license_audit.md` shows `license_verified = YES`.

## 4. Layer C — PRHAAR custom datasets (the real target)

### 4.1 PRHAAR-C5-DETECTION (§9–§18)

| Property | Target |
|---|---|
| Scale | MVP **20,000+** curated images; production-candidate **40,000–80,000+** — only real counts reported (§9) |
| Diversity requirement | High diversity and hard-case coverage is the target, not raw count (§9) |
| Taxonomy (§10) | PERSON, MOTORCYCLE, BICYCLE, CAR, LIGHT_VEHICLE, TRUCK, BUS, TRACTOR, ANIMAL (+ AUTO_RICKSHAW only if sufficient data) |
| Scenario tags (§11) | environment (plains/foothills/forest/hill/agriculture/settlement/road/fence), lighting (day/dawn/dusk/night), weather (clear/haze/fog/rain), visibility (normal/partial/heavy occlusion), distance (near/medium/far/very_far), camera (high_quality/low_resolution/compression/shake/degraded), object_context (person_near_animal, person_near_vehicle, motorcycle_near_person, crowded, vegetation_overlap) |
| Annotation (§14) | Per image/object: bounding box + class + attributes per spec (occlusion, truncation where applicable); YOLO-format labels + JSON sidecar manifest; annotation guidelines document before labeling starts |
| QA (§15) | Multi-stage: annotation guideline pass → 100% automated validation (geometry, class sanity, duplicates) → % human spot-check with acceptance threshold → inter-annotator agreement sample. Exact acceptance thresholds fixed in the QA config before labeling |
| Leakage prevention (§16) | Scene/camera-grouped splits; near-duplicate detection; video-frame temporal split (no frame from a test video in train) |
| Splits (§17) | train/val/test by scene-group; test slice frozen; hard-case test set **frozen from day one** (§83) — never trained/tuned/augmented on |
| Versioning (§76) | `PRHAAR-C5 vMAJOR.MINOR`; manifest JSON with per-file SHA-256 recorded at acquisition |

### 4.2 C5-SMALL-OBJECT subset (§12)

Dedicated subset for tiny person / tiny motorcycle / tiny car / tiny truck / far animal.
**Rule:** "small" is defined by measured bounding-box-area distribution (normalized area bins: very_small / small / medium / large), not arbitrarily. Phase 3 reports per-bin performance.

### 4.3 C5-ANIMAL-HUMAN subset (§13) — critical requirement

Classes: cow, buffalo, goat, dog + legally sourced deer/wildlife/other livestock, together with humans in similar scenes.
Hard cases required: person beside animal, animal partially hidden by vegetation, animal at night, animal far away, human crouching, human bending, human carrying object, person wearing dark clothing, animal resembling human silhouette.
Measures (reported separately): PERSON recall, ANIMAL recall, human-on-animal FP rate, animal-on-human FP rate. No "human-vs-animal solved" claim from aggregate mAP (§13).

### 4.4 PRHAAR-C6-TRACKING (§34, §35)

| Property | Plan |
|---|---|
| Source | Video sequences from PRHAAR collection (same field trips as C5 where possible) + curated public MOT sequences as secondary |
| Required scenarios (§35) | occlusion/re-entry, crossing paths, night, fog/rain, person+animal co-presence, motorcycle+person, dense scene, static long-duration |
| Annotation | Per-frame boxes + stable track IDs + occlusion/visibility flags; track lifecycle events marked |
| Public secondary benchmarks | MOT17/MOT20 sequences (research license — verify), VisDrone-MOT — documented as non-border-domain evidence |
| Versioning | `PRHAAR-C6 vMAJOR.MINOR` + manifest + hashes |

### 4.5 PRHAAR-C7-PLATES + OCR (§46–§48, §64)

| Dataset | Plan |
|---|---|
| Plate detection base | **Zenodo 13954136 "Number Plate Number Identification Dataset"** — 1,700 images, Bapatla (Andhra Pradesh, India), license **CC-BY-4.0 verified** — usable with attribution |
| Plate detection expansion | Crops from PRHAAR field video + any verified Kaggle Indian-plate sets (per-dataset license check) |
| OCR crops | Cropped plate images with character-level labels; raw text preserved verbatim (§54) |
| Charset | Indian plate charset per §50 (Latin A–Z, digits, plus state/format symbols as validated); format validator per §56 handles state series / BH series / standard formats |
| Conditions matrix (§47) | day/night, blur, angle, partial occlusion, dirt, glare, rain — each labelled and reported separately |
| End-to-end set (§64) | Video snippets with vehicle + plate + expected fused read; used for track-level exact-match metrics (§65) |
| Versioning | `PRHAAR-C7-PLATES vMAJOR.MINOR`, `PRHAAR-C7-OCR vMAJOR.MINOR` + manifests + hashes |

## 5. Download & storage plan

| Step | Action | Gate |
|---|---|---|
| 1 | Download only datasets whose `00_license_audit.md` row = `license_verified: YES` | License audit |
| 2 | Record per-file SHA-256 + manifest JSON + acquisition date + source URL in `PRHAAR_DATASET_CATALOG.md` | Reproducibility (§78) |
| 3 | Store images/videos under `ml/c5_detection/datasets/` (etc.); **never commit dataset binaries or weights to git** (§123) | `.gitignore` per module |
| 4 | Keep raw downloads immutable; all preprocessing writes to separate `processed/` | Traceability |

Storage budget on this machine: ~307 GB free (measured). Dataset sizes are recorded **when actually downloaded** — never estimated as facts.

## 6. What this plan will NOT do

- No fabricated image counts; MVP/target numbers are goals, not claims (§9).
- No training, tuning, or augmentation on the frozen hard-case test set (§83).
- No drone-image results presented as border-camera performance (§7).
- No download of DataCluster datasets (no license asserted, access-controlled — see audit).
- No use of any dataset with unresolved license, including IDD until its terms are verified.

## 7. Open gaps (honest status)

1. **No project-specific border-scene imagery exists yet** — Layer C is the critical path; everything else is adaptation material.
2. IDD license unresolved → Layer B currently rests on VisDrone + open-image loaders (each still gate-verified).
3. Indian plate public data is scarce and mostly license-ambiguous; the verified CC-BY-4.0 Zenodo set (1,700 images) plus project collection is the realistic base.
4. Inter-annotator agreement tooling to be built in `ml/common/dataset_tools/` before mass annotation.
