# PRHAAR C5 — ANNOTATION GUIDE

**Component:** C5 — Production Object Detection
**Spec reference:** C5 spec §7 (taxonomy), §11–14 (diversity / small objects / animals / metadata), §15 (format), §16 (this guide), §17 (QC), §18 (duplicates)
**Version:** 1.0 — 2026-10-04
**Applies to:** (a) PRHAAR/Layer C footage annotated in-house; (b) reviewer QA of converted public datasets (Layer A/B); (c) any future annotator or tool adding labels to PRHAAR-C5-DETECTION.

Namespace: the ONLY classes allowed are the canonical taxonomy below (`ml/c5_detection/scripts/c5_taxonomy.py`, v1.0). **Annotators must never invent classes, subclasses, or attributes as classes.** An object that does not fit the taxonomy is skipped and counted, never renamed into it.

---

## 1. Canonical taxonomy (do not renumber, do not extend)

| idx | class | notes |
|---|---|---|
| 0 | PERSON | any human, any posture (standing/walking/crouched/bent) |
| 1 | MOTORCYCLE | two-wheeler motorized (incl. scooters, mopeds); rider is NOT a separate box |
| 2 | BICYCLE | human-powered two-wheeler; rider is NOT a separate box |
| 3 | CAR | sedan/hatchback/SUV-class passenger car |
| 4 | LIGHT_VEHICLE | van, pickup, jeep-type, tempo, small utility & goods vehicles that are not TRUCK/BUS |
| 5 | TRUCK | goods truck (incl. heavy, container, tipper) |
| 6 | BUS | passenger bus / minibus |
| 7 | TRACTOR | agricultural tractor (+ trailer if tractor-drawn — one box with tractor) |
| 8 | ANIMAL | cow, buffalo, goat, sheep, dog, horse, other livestock; wildlife only if legally sourced |
| 9 | AUTO_RICKSHAW | **conditional** (§7) — only present if included at taxonomy freeze; annotate normally if in scope |

Decision notes:

- **CAR vs LIGHT_VEHICLE:** if it has a distinct goods bed → LIGHT_VEHICLE or TRUCK by size/axle count; when uncertain between LIGHT_VEHICLE and TRUCK, prefer the class the reviewer confirms; never silently relabel.
- **TRACTOR / AUTO_RICKSHAW are conditional:** annotation is recorded normally, but their inclusion in a training run is a dataset-freeze decision (§7), logged — not an annotator decision.
- A trailer under a truck: annotate truck + trailer as separate TRUCK boxes only if the trailer is clearly distinct and separable; otherwise one TRUCK box around the articulated unit is acceptable — be consistent per dataset version and note the choice.

## 2. Box drawing rules

- One tight bounding box per object instance, in **YOLO format**: `class_id x_center y_center width height`, normalized to [0,1], written to `<stem>.txt` (UTF-8, one object per line).
- Box the **visible extent** of the object. Do not pad boxes; do not draw boxes around empty space to "include" hidden parts.
- Minimum box: **width AND height ≥ 2 px** at native resolution. Below 2 px the information is not learnable; skip and count.
- Objects smaller than ~16 px that are not class-identifiable: skip and count as `unannotated_unidentifiable`.
- Boxes must be fully inside [0,1] bounds (clipping artifacts are a §17 hard failure).

### 2.1 Partial object

An object partially outside the frame (cut by image border):

- Annotate if **≥ ~30% of the object is visible** and the class is identifiable; otherwise skip + count.
- The box covers only the visible part; do not extrapolate the hidden part.
- Set object metadata `truncated=true`, `visibility=partial`.

### 2.2 Truncated object

Same case as 2.1 seen from the frame-edge perspective: object cut by the image boundary. Rule identical — annotate visible part, `truncated=true`. Consistency matters more than theory: apply the ~30% rule uniformly.

### 2.3 Severe occlusion

Object mostly behind another object (fence post, pole, vegetation, vehicle):

- **PARTIALLY OCCLUDED** (≈30–70% hidden): annotate; box the visible extent; `occlusion=partial`.
- **HEAVILY OCCLUDED** (> ~70% hidden): annotate ONLY if the class is unambiguous (e.g. clear truck cab profile behind a pole); `occlusion=heavy`. If not identifiable → skip + count.
- Never mark an occlusion guess as a class guess; occlusion is metadata, not a class.

### 2.4 Tiny object

§12 targets very_far PERSON/MOTORCYCLE/CAR/TRUCK and forbids a dataset dominated by large close objects — tiny objects are **wanted**, not avoided:

- Annotate every class-identifiable object down to the 2 px minimum (see §2).
- Record distance metadata per §4 (`very_far` for tiny objects).
- Borderline call: if a reviewer cannot tell PERSON vs fence post at 6 px, skip + count as `unidentifiable_tiny`. False PERSON detections cost downstream risk logic (§13) — do not inflate tiny PERSON labels.

### 2.5 Uncertain class

- If the object is between two taxonomy classes → **skip and log** (`class_uncertain` hit list with image, approximate location, the two candidates).
- The uncertain list informs taxonomy guidance updates and QA sampling — it is never resolved by guessing.
- Exception: animal/human ambiguity has a forced procedure (§2.8).

### 2.6 Overlapping objects

- Annotate each instance with its own box, even if boxes overlap heavily.
- Person riding motorcycle/bicycle: label the vehicle only (rider not a separate PERSON box) — consistent with §7 vehicle classes and public-dataset mappings.
- Person in/on a car/truck/bus: driver/cargo persons inside vehicles are NOT annotated as separate PERSON boxes.
- Crowd: annotate each clearly visible person where feasible; when density makes instance separation impossible, annotate all persons whose extents are separable and count the remainder as `crowd_unseparated_count` (image-level note). Never draw one box around a crowd.

### 2.7 Group boxes

Never annotate "group of X" boxes in PRHAAR data. (Open Images `IsGroupOf` rows are a different provenance and are handled by the conversion layer, not by PRHAAR annotators.)

### 2.8 Animal/human ambiguity (forced procedure)

False human detections directly affect downstream risk/event logic (§13), so ambiguity is never resolved toward PERSON by default:

1. Quadruped body plan → **ANIMAL** (even if it "looks like" a crouched person).
2. Bipedal, upright, walking/standing gait → **PERSON**.
3. Human with livestock proximity (§13 `person beside animal`) → annotate BOTH boxes when both are identifiable.
4. Still ambiguous after 1–2 → skip + log (`animal_human_ambiguous`); annotate the scene-level note.
5. **Never** label an animal as PERSON and never label a PERSON as ANIMAL to "clear" a scene.

## 3. Metadata (spec §14/§15 — "where possible", never invented)

Per image and/or per object where obtainable. Public-dataset conversions fill what exists (e.g. OI occlusion flags); unknown cells stay `null` — unknown is a legitimate value, a guess is not.

| field | values | scope |
|---|---|---|
| visibility | `full` / `partial` / `heavy_occlusion` | object |
| occlusion | `none` / `partial` / `heavy` | object |
| distance | `near` / `mid` / `far` / `very_far` | object (very_far ≈ §12 tiny threshold) |
| lighting | `day` / `dawn` / `dusk` / `night` | image |
| weather | `clear` / `haze` / `fog` / `rain` | image |
| environment | `plain` / `foothill` / `forest` / `hill` / `agriculture` / `settlement` / `road` / `fence_adjacent` / `long_range` | image (§11 axes) |

For PRHAAR/Layer C footage these fields come from the capture log and are mandatory. For Layer A/B they are partially derivable; conversions document exactly which fields were set by tooling and which remain null.

## 4. Original annotation QA (reviewer process, §17)

- Every annotated batch gets automated validation first: `scripts/qa_dataset.py` (image/label presence, class validity, bbox validity/bounds/size, malformed files, corrupt images) → `dataset_quality_report.json`.
- Reviewer QA sample: **all** objects flagged `class_uncertain` / `animal_human_ambiguous` / edge cases, plus a **≥10% stratified sample** per class per batch (stratified by size bucket: tiny/small/medium/large).
- Reviewer issues are logged with image id + object index; corrections are edits, not deletions, where possible (traceability).
- Reviewer sign-off is recorded per batch in the QA report; unresolved disagreements escalate to the dataset owner before freeze.

## 5. Consistency with converted public data

- Public-dataset conversions follow their own documented policies (e.g. OI: `depiction` rows dropped; occluded/truncated kept; clip to [0,1]; degenerate dropped) and record counts in `conversion_report.json`.
- Converted boxes are NOT re-annotated by hand except in reviewer-QA sampling; policy mismatches found in QA sampling are fixed in the conversion script + re-conversion (not by patching labels), so the transformation stays reproducible.
- The canonical taxonomy version used by every conversion and annotation set is recorded in each artifact (`c5_taxonomy.py` v1.0 or successor).

## 6. What never happens

- No invented classes, no class renames to "fit" an object, no silent merges (e.g. easy-bike→AUTO_RICKSHAW happens ONLY as a declared, counted mapping in conversion code — never by an annotator).
- No attribute-as-class tricks (no "person_night", no "dark_clothed_person" labels; those are metadata).
- No guessed metadata; null is allowed, "probably" is not.
- No edits to the frozen PRHAAR-HARD-TEST set (§20/§21) — ever, for any reason.
