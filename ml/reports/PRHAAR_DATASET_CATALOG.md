# PRHAAR Dataset Catalog

**Master catalog of every dataset used or planned for the PRHAAR AI/ML layer** (spec §114)
**Status:** Phase 1 — initialized 2026-09-29. Counts are recorded only from verified sources; nothing is fabricated. `Hash` is filled at acquisition time (SHA-256 manifest).
**Related:** `00_dataset_plan.md`, `00_license_audit.md`

Status legend: `PLANNED` (not yet collected) · `READY` (verified + available to use) · `BLOCKED` · `NOT USED`

---

## 1. PRHAAR custom datasets (Layer C — the real target domain)

### 1.1 PRHAAR-C5-DETECTION

| Field | Value |
|---|---|
| Name | PRHAAR-C5-DETECTION |
| Purpose | C5 production detector training/validation/test (border CCTV scenes) |
| Source | Project field collection (SSB-context imagery, drones where authorized, fixed-camera captures) |
| License | Project-owned |
| Images | **Not yet collected** — goals: MVP 20,000+ curated · production-candidate 40,000–80,000+ (§9) |
| Videos | Source clips retained for C6 extraction |
| Classes | PERSON, MOTORCYCLE, BICYCLE, CAR, LIGHT_VEHICLE, TRUCK, BUS, TRACTOR, ANIMAL (+AUTO_RICKSHAW only if data supports) |
| Annotations | BBox + class + attributes (occlusion/truncation); YOLO txt + JSON manifest |
| Conditions | Tagged per §11 matrix (environment/lighting/weather/visibility/distance/camera/object_context) |
| Split | Scene/camera-grouped train/val/test; frozen hard-case test (§83, §84) |
| Version | v0.0-planned |
| Hash | at acquisition |
| Used for | C5 training, C5 evaluation, C6 sequence source, C7 vehicle/plate crop source |
| Known limitations | Does not exist yet — critical path; inter-annotator agreement QA must precede mass labeling |

### 1.2 PRHAAR-C5-SMALL-OBJECT (subset)

| Field | Value |
|---|---|
| Purpose | Tiny-object performance measurement (tiny person/motorcycle/car/truck, far animal) |
| Images | Subset of PRHAAR-C5 by **measured** bbox-area bins (very_small/small/medium/large — no arbitrary thresholds) |
| Used for | §12 per-bin recall reporting; YOLO26-p2 decision evidence |
| Version / Hash | v0.0-planned / at acquisition |

### 1.3 PRHAAR-C5-ANIMAL-HUMAN (subset)

| Field | Value |
|---|---|
| Purpose | Human↔animal confusion measurement (critical PRHAAR requirement §13) |
| Classes | cow, buffalo, goat, dog, (legally sourced deer/wildlife/livestock), PERSON |
| Hard cases | person beside animal, animal in vegetation, animal at night/far, human crouching/bending/carrying, dark clothing, animal-like silhouette |
| Used for | PERSON recall, ANIMAL recall, human-on-animal FP rate, animal-on-human FP rate (separately reported) |
| Version / Hash | v0.0-planned / at acquisition |

### 1.4 PRHAAR-C6-TRACKING

| Field | Value |
|---|---|
| Purpose | ByteTrack vs BoT-SORT benchmark + tracker tuning evidence (§33–§38) |
| Source | Video sequences from C5 collection trips + authorized captures |
| Videos | Not yet collected; required scenarios per §35 (occlusion/re-entry, crossing, night, fog/rain, animal co-presence, motorcycle+person, dense, long-duration) |
| Annotations | Per-frame boxes, stable track IDs, occlusion/visibility flags, lifecycle events |
| Metrics target | HOTA / IDF1 / MOTA / ID-switch rate / fragmentation (§37) |
| Version / Hash | v0.0-planned / at acquisition |

### 1.5 PRHAAR-C7-PLATES (detection)

| Field | Value |
|---|---|
| Purpose | Plate detector training/eval (C7 Model B, §45–§47) |
| Source | Zenodo 13954136 crops + PRHAAR field plate imagery + verified Kaggle sets |
| Images | Zenodo base: **1,700 verified**; project expansion: not yet collected |
| Conditions | day/night, blur, angle, occlusion, dirt, glare, rain — labelled |
| Version / Hash | v0.0-planned / at acquisition |

### 1.6 PRHAAR-C7-OCR (recognition)

| Field | Value |
|---|---|
| Purpose | PP-OCRv6 fine-tuning + character-level evaluation (§48–§53) |
| Source | Cropped plates with character-level labels (raw reads preserved verbatim §54) |
| Charset | Indian plate charset per §50; format classes handled by validator (§56) |
| Metrics | character accuracy, exact-plate match on quality-gated readable tracks |
| Version / Hash | v0.0-planned / at acquisition |

### 1.7 PRHAAR-C7-E2E (end-to-end)

| Field | Value |
|---|---|
| Purpose | Track-level fused-read evaluation (§64–§65) |
| Source | Video snippets with vehicle→plate→OCR→fusion expected outcomes |
| Metrics | track-level exact plate match, false-exact-read rate |
| Version / Hash | v0.0-planned / at acquisition |

---

## 2. External datasets

### 2.1 Zenodo 13954136 — "Number Plate Number Identification Dataset"

| Field | Value |
|---|---|
| Purpose | Indian plate detection base (C7 Model B) |
| Source | zenodo.org/records/13954136 (Bapatla Engineering College / Bapatla town, Andhra Pradesh, India) |
| License | **CC-BY-4.0 (verified 2026-09-29)** — attribution required |
| Images | 1,700 (verified count on record page) |
| Classes | Number plates (Indian) |
| Conditions | Campus + town scenes, varied viewpoints/illumination (per record description) |
| Split | To be defined scene-aware after acquisition |
| Version / Hash | v1.0 on acquisition / at acquisition |
| Used for | Plate detector fine-tuning + plate-condition eval |
| Known limitations | Single-geography (AP); no night/heavy-weather guarantees — expansion needed |

### 2.2 VisDrone (DET + MOT)

| Field | Value |
|---|---|
| Purpose | Small-object detection + tracking research benchmark (secondary) |
| Source | github.com/VisDrone; auto-downloadable via bundled ultralytics loader |
| License | Research-use; terms must be verified at acquisition |
| Images/Videos | 10,209 images; 288 clips / 261,908 frames; 2.6M+ boxes |
| Classes | person, vehicle categories, etc. |
| Used for | Secondary small-object/tracker comparison **only** |
| Known limitations | Drone imagery ≠ fixed border CCTV (§7); never quoted as border-camera evidence |

### 2.3 India Driving Dataset (IDD)

| Field | Value |
|---|---|
| Purpose | Candidate Indian-domain adaptation (Layer B) |
| Source | idd.insaan.iiit.ac.in |
| License | **UNRESOLVED — BLOCKED** (license page returned no content during audit) |
| Images | 46,588 (train/val/test per project docs) |
| Status | **Do not download until license terms confirmed** |

### 2.4 Open Images V7 (candidate)

| Field | Value |
|---|---|
| Purpose | Layer-B diversity (animals/persons) |
| License | CC-BY-4.0 (per provider docs) — verify at acquisition |
| Status | VERIFY-AT-ACQUISITION; loader bundled locally |

### 2.5 MOT17 / MOT20 (C6 secondary)

| Field | Value |
|---|---|
| Purpose | Secondary tracker benchmark |
| License | Research/academic (non-commercial) — verify at acquisition |
| Status | VERIFY-AT-ACQUISITION |

### 2.6 COCO (lineage only)

| Field | Value |
|---|---|
| Purpose | Pretraining lineage of YOLO26/RT-DETR checkpoints |
| License | Annotations CC-BY-4.0; images vary (Flickr) |
| Status | LINEAGE — no image/annotation redistribution by PRHAAR |

### 2.7 Rejected / not used

| Dataset | Reason |
|---|---|
| DataCluster Indian plate sets (6k+ / 20k+) | No license asserted; access-controlled → excluded (§8) |
| xView | Satellite domain mismatch; CC-BY-NC |
| BDD100K | Driving-domain mismatch; non-commercial |

---

## 3. Catalog maintenance rules

1. A dataset row is updated **only with verified numbers** (counts, hashes, license) — no placeholders silently filled with guesses.
2. Any dataset entering use gets: version tag, SHA-256 manifest, license row in `00_license_audit.md`, and attribution entry.
3. Blocked datasets stay blocked until their audit row changes to verified.
