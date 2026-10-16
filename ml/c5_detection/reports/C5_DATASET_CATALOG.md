# C5 DATASET CATALOG

**Project:** PRHAAR — SSB AI-Powered Border Surveillance & Command Platform
**Component:** C5 — Production Object Detection
**Spec reference:** C5 spec §8 (public dataset research), §9 (layers A/B/C/D), §10 (PRHAAR-C5-DETECTION), §11–14 (diversity / small-object / animal / metadata), §58 (this catalog)
**Catalog date:** 2026-10-04 (IST)
**Status:** LIVE — updated after each acquisition event. License freeze happens at the §6 gate (before final training). No cell in this catalog is an estimate; every count is either "source-claimed" (as published by the source) or "measured" (from our own acquisition manifest).

---

## 0. Reading guide

Status legend:

| Status | Meaning |
|---|---|
| ACQUIRED | Downloaded + hashed; measured counts in our manifest |
| ACQUIRING | Download in progress right now (or queued) |
| PENDING-USER-ACTION | Legal/download step requires Harsh (form, registration, API key) |
| PENDING-LICENSE | License text not yet obtained/verified — **no download until resolved** (per §4 protocol: ambiguity → do not download) |
| RESEARCH-CAVEAT | Downloadable, but provenance/license has an unresolved caveat — usable only with explicit caveat in reports, never in final training without resolution |
| BLOCKED | License does not permit our use |
| REJECTED | Failed license audit for free use (e.g., paid-only) |
| CANDIDATE | Audited, not yet needed; may be pulled in by the §23 improvement loop |

Counts policy (§61/§62): a number is written only when (a) the source itself publishes it — then it is labeled *source-claimed, unverified by us* — or (b) our own acquisition measured it — then it is labeled *measured* and traceable to a manifest with SHA-256.

Layer roles (§9) — never mixed:

- **Layer A** — generic pretrained knowledge / generic in-the-wild imagery
- **Layer B** — Indian domain adaptation
- **Layer C** — PRHAAR custom surveillance domain
- **Layer D** — hard-case frozen evaluation (never trained on, never tuned against)

---

## 1. Summary table

| # | Dataset | Source | License | Images | Classes we take | Role | Status |
|---|---|---|---|---|---|---|---|
| 1 | Open Images V7 (subset) | Google / Open Images | Annotations CC BY 4.0; per-image Flickr licenses captured per image | **measured 16,372** (train 11,898 / val 1,989 / test 2,485; 0 failed) | PERSON, MOTORCYCLE, BICYCLE, CAR, LIGHT_VEHICLE, TRUCK, BUS, ANIMAL | A (supplemental) | ACQUIRED + CONVERTED (→ `staging/oi_yolo`, QA pass) |
| 2 | TiHAN Camera Dataset ("DriveIndia") | TiHAN, IIT Hyderabad | TiHAN Research EULA — non-commercial, no redistribution, derivative *models* explicitly permitted | source-claimed 66,986 (paper; site states no count) | Indian road domain incl. TRACTOR / AUTO_RICKSHAW references | B (key) | PENDING-USER-ACTION |
| 3 | IDD-AW (IDD adverse weather) | IIT Hyderabad (IDD team) | unresolved — portal terms; site footer shows CC BY-SA 4.0 (not confirmed as data license) | source-claimed (IDD split 46,588 base images per spec §8; AW counts TBD) | B (adverse weather) | PENDING-LICENSE |
| 4 | MIO-TCD | Université de Sherbrooke / McGill | CC BY-NC-SA 4.0 (verified) | source-claimed 786,702 | fixed-camera traffic views (supplemental) | A/B candidate | CANDIDATE |
| 5 | Poribohon-BD | Kaggle (Hridoy Yahmed) → Roboflow export | CC0 (Kaggle page JSON-LD) vs CC BY 4.0 (Roboflow export files) — discrepancy recorded; stricter (CC BY 4.0) assumed | **measured 5,205** (train 3,643 / valid 1,044 / test 518; 13,346 source boxes) | bicycle→BICYCLE, bike→MOTORCYCLE, bus→BUS, car→CAR, cng+easybike→AUTO_RICKSHAW (declared grouping), leguna+van→LIGHT_VEHICLE, truck→TRUCK; rickshaw (cycle) **excluded** (no canonical class) | B (supplemental, BD ≠ India caveat) | ACQUIRED (converted → staging/poribohon_yolo) |
| 6 | Auto-Rickshaw Detection | Kaggle (uzairahmad1434) → Roboflow export | Apache 2.0 (Kaggle page JSON-LD; Roboflow export files say "Public Domain" — stricter assumed) | **measured 663** (train 465 / val 132 / test 66; 808 boxes) | AUTO_RICKSHAW | B (supplemental) | ACQUIRED (converted → staging/autorickshaw_yolo) |
| 7 | Kaggle IDD re-releases (idd20kii; IDD-Detections YOLOv11) | third parties | re-licensed by uploader; **original IDD license unresolved** | source-claimed ~5.9 GB / subset | IDD 30-class domain | RESEARCH-CAVEAT | RESEARCH-CAVEAT |
| 8 | Original IDD distribution | IIT Hyderabad | unresolved at primary source | — | — | BLOCKED (until primary license verified) | BLOCKED |
| 9 | Roboflow Universe livestock sets | Roboflow users | CC BY 4.0 (per set, to re-verify at key availability) | source-claimed 28,295 (goat/sheep/cow) + 1,747 (cow+buffalo) | ANIMAL subclasses incl. buffalo gap | B (supplemental) | PENDING-USER-ACTION (API key) |
| 10 | VisDrone | Tianjin Univ. et al. | not yet audited | source-claimed (aerial) | small-object *research only* — per §8 never represented as SSB-like fixed-camera data | research only | CANDIDATE |
| 11 | DataCluster "Indian Vehicle Dataset" | DataCluster Labs | "Data files © Original Authors"; license must be **purchased** for research or commercial use | — | — | REJECTED (paid) |
| 12 | DataCluster "Construction Vehicle Images" | DataCluster Labs | CC BY-NC-ND 4.0 | — | — | BLOCKED (NC-ND: NoDerivatives ambiguity for training/augmentation; free portion is a sample only) |
| 13 | PRHAAR-C5-DETECTION (composite, Layer C+D) | PRHAAR capture + curated above | composite — per-source attribution retained | **measured 20,722** (3 license-clean public sources); target 40,000–80,000+ remains until Layer B/C lands | full §7 taxonomy (TRACTOR presented as empty, 0 boxes) | C (+ D frozen) | **BUILT 2026-10-14** — 20,722 img / 13,020 groups / 59,972 boxes; leakage pass true; dataset hash `7fa08e2bf23baefc…` |

Evidence snapshots for the license claims above: `ml/c5_detection/reports/evidence/` (raw HTML/PDF captures with capture dates in filenames).

---

## 2. Source records (§58 field order)

### 2.1 Open Images V7 — supplemental generic (Layer A)

- **dataset:** Open Images V7 (target-class subset, 12 OI classes)
- **source:** Google Open Images — download page `https://storage.googleapis.com/openimages/web/download_v7.html` (evidence: `evidence/oi_v7_download_page_2026-10-03.html`)
- **license:** box annotations CC BY 4.0; image copyrights remain with Flickr authors — **per-image license is captured in our manifest** (`license`, `author`, `original_url`, `landing_url` per image) from the official images-with-rotation CSVs. Acquisition policy: image dropped if no license row found (counted + sampled in summary). **Full run: 0 drops — 16,372/16,372 license rows resolved from the v6 info CSVs; the 1.3 GB v4 fallback CSV was never needed (lazy path).** License histogram 16,372/16,372 = CC BY 2.0 — measured to be the official CSVs' own content (validation 41,620/41,620 full-file; train sampled 1,000,000/1,000,000), faithfully mirrored, not our inference.
- **images:** cap ≤17,200 across the 12 classes (union with multi-class images); 70/15/15 split target. **Measured (full run completed 2026-10-14 00:58 IST): 16,372 images — train 11,898 / validation 1,989 / test 2,485** (5,530,210,738 B total, 0 failed, elapsed 12,965.1 s @ 8 workers) → `datasets/sources/openimages_v7/acquisition_summary.json` (sha256 `5343a2a53c1cd2c57d8146b5e7bfa124a55aa129e7c31e6bdb8085d5f358967d`)
- **classes:** OI→canonical map: Person→PERSON; Bicycle→BICYCLE; Car→CAR; Motorcycle→MOTORCYCLE; Bus→BUS; Truck→TRUCK; Van→LIGHT_VEHICLE; Dog/Cattle/Sheep/Goat/Horse→ANIMAL
- **conditions:** in-the-wild Flickr photography; mixed but unquantified day/night/weather; `IsOccluded` (0/1) preserved as occlusion signal — NOT a §11-compliant condition matrix; not surveillance imagery
- **annotation:** OI bbox CSV (XMin/XMax/YMin/YMax normalized); flags `IsOccluded/IsTruncated/IsGroupOf/IsDepiction/IsInside` preserved in raw records; raw JSONL: `datasets/sources/openimages_v7/annotations/annotations_raw.jsonl`. **Coordinate-frame finding (measured 2026-10-04, `evidence/oi_rotation_probe/probe_report.json`):** OI boxes are in the **raw stored-image frame** — Person boxes on 90°/270°-rotation images are 80.0–86.2% wide (lying) vs 10.1% wide on 0° controls (n=104); Car 270° flips to tall vs its wide control; the aspect-preserving 180° group matches the control. Consequence: raw bytes + raw normalized boxes are frame-consistent; the `Rotation` field (Flickr-intended display orientation) is display metadata only, recorded per image in the manifest, never applied to pixels or boxes. Downloaded bytes are NOT the original Flickr files — OI redistributes resized (max 1024 px) images, so `OriginalMD5`/`OriginalSize` in the info CSVs refer to the original upload and never match (100/100 measured, expected, not an integrity issue; our integrity anchor is the per-image SHA-256 in the manifest).
- **version:** OI V7 page distribution = bbox CSVs `v6/oidv6-train-annotations-bbox.csv` (train), `v5/validation-annotations-bbox.csv`, `v5/test-annotations-bbox.csv`; class list `v7/oidv7-class-descriptions-boxable.csv`
- **hash:** metadata file SHA-256s → `datasets/sources/openimages_v7/_metadata/file_hashes.json`; per-image SHA-256 → `acquisition_manifest.jsonl`; summary artifact hash → `acquisition_summary.json`
- **purpose:** Layer A **supplemental** only — adds class breadth (esp. LIGHT_VEHICLE via Van, dog/goat/sheep/cattle/horse) and volume; explicitly NOT Indian-domain; NOT fixed-camera; NEVER part of the frozen hard-case eval
- **limitations:** no TRACTOR class; no buffalo; western/global image distribution; staging filter policy: `IsDepiction=1` boxes always dropped at conversion (non-photographic), `IsGroupOf=1` boxes dropped for the real build (`--drop-group-of`, counted in conversion_report.json — a single box spanning many instances is not a valid instance box for detection training; `IsOccluded`/`IsTruncated` boxes KEPT by design for occlusion diversity); occlusion granularity coarse (binary); sampling deterministic (seed `prahaar-c5-v1` + SHA-1) so the subset is reproducible, not exhaustive

### 2.2 TiHAN Camera Dataset ("DriveIndia") — Layer B key source

- **dataset:** TiHAN Camera Dataset (page section branding includes "DriveIndia"); street-level images captured on Indian roads
- **source:** TiHAN, IIT Hyderabad — `https://tihan.iith.ac.in/TiAND.html` (evidence: `evidence/` — page HTML saved 2026-10-03; EULA PDF downloaded from the official Google Drive link and archived as `evidence/tihan_eula_2026-10-03.pdf` + text extract)
- **license:** TiHAN Dataset Research EULA (read in full, archived). Key verified terms: free for academic and non-academic **non-commercial** purposes; **do not distribute** the dataset or modified versions; distribution of **derivative works as abstract representations (e.g., trained models) is explicitly permitted**; citation required; no faces/license plates reproduced in publications; **face identification, vehicle identification, or similar recognition activities strictly prohibited** (aligned with PRHAAR §55 no-identity-outputs constraint); requires signed EULA (Name/Designation/Institution/Place/Date/Signature) uploaded in the request form → confirmation email with access link.
- **images:** source-claimed **66,986** (from the dataset paper); the TiHAN site itself states no count → treat 66,986 as *paper-claimed, unverified by us* until delivery; measured count will be recorded at acquisition
- **classes:** Indian driving/traffic domain (includes auto-rickshaw, tractor categories in the paper's taxonomy — re-verify at delivery; do NOT map classes from the paper alone)
- **conditions:** Indian roads; per paper includes rural/urban; exact condition matrix to be measured at delivery
- **annotation:** per delivery (paper describes detection/tracking annotations; re-verify format at delivery)
- **version:** to be recorded from the delivered archive (dated release)
- **hash:** to be computed at delivery (archive SHA-256) + per-file manifest
- **purpose:** Layer B (Indian domain adaptation) — the highest-value licensable Indian source found so far, once the EULA flow completes
- **limitations:** **user action required** (see §4); non-commercial; no redistribution (fine — we redistribute models, not data, which the EULA permits); no identity recognition (fine — §55); delivery timing not in our control

### 2.3 IDD-AW — adverse-weather Indian domain (Layer B) — PENDING-LICENSE

- **dataset:** Indian Driving Dataset — Adverse Weather (and base IDD split; spec §8: base IDD = 46,588 documented images)
- **source:** IIT Hyderabad IDD team — IDD portal (registration + 24 h token flow per IDDAW_kit README); competition mirror `iddawlabels` (Google Drive) is alive but license-unstated; `iddawtest` mirror link is dead (404 at review)
- **license:** **unresolved.** The website footer's CC BY-SA 4.0 is the *site's* license, not confirmed as the *data* license. Official flow = portal registration → per the IDD terms shown at registration. Per §4 protocol: ambiguity → **no download** (evidence: `evidence/iddaw_page_2026-10-03.html`)
- **images:** base IDD 46,588 (spec §8); IDD-AW counts to be measured after licensed access
- **classes:** IDD taxonomy (Indian roads; per-class verification at access — note: verify TRACTOR/AUTO_RICKSHAW presence against primary label files, not secondary claims)
- **conditions:** IDD-AW adds fog/rain/night adverse conditions — exactly the §11 axes; base IDD covers day/settlement/road
- **annotation:** IDD detection labels (format per portal delivery)
- **version:** to be recorded at access
- **hash:** at access
- **purpose:** Layer B (adverse-weather + Indian domain) — pending until license resolved by user registration
- **limitations:** portal registration needed (user action); license terms must be **read and archived at registration** before any download; secondary Kaggle re-releases carry a provenance caveat (see 2.7)

### 2.4 MIO-TCD — fixed-camera traffic (Layer A/B candidate)

- **dataset:** MIO-TCD (traffic classification + localization)
- **source:** Université de Sherbrooke / McGill University — `http://podoce.dinf.usherbrooke.ca/` (verified earlier this phase; direct archive links alive)
- **license:** CC BY-NC-SA 4.0 — verified on source page (research/non-commercial OK for SIH; ShareAlike)
- **images:** source-claimed 786,702 (classification) + localization subset; **not yet downloaded** (large)
- **classes:** 11 traffic classes (car, truck, bus, motorcycle, bike, pedestrian, etc. — fixed-camera Canadian traffic)
- **conditions:** **fixed traffic cameras** — viewpoint-relevant; day/night variation; Canadian domain (not Indian)
- **annotation:** classification labels + localization boxes (per source format)
- **version:** per source release archived; hash at download
- **purpose:** candidate supplemental for fixed-camera viewpoint diversity — pull in only if the §23 error loop identifies viewpoint/domain gaps it can fill
- **limitations:** NC + SA; Canadian roads; classification-heavy (bbox subset smaller); no tractor/animals

### 2.5 Poribohon-BD — Bangladesh vehicle scenes (Layer B supplemental) — ACQUIRED + CONVERTED

- **dataset:** Poribohon-BD (Bangladeshi vehicle scenes; Kaggle page title says "15 vehicle types" but the **as-downloaded Roboflow export contains 10 classes with boxes** — measured)
- **source:** Kaggle `hridoyyahmed/poribohon-bd` (evidence: `evidence/kaggle_poribohon_bd_license_2026-10-04.html`); archive is a **Roboflow YOLO export** (dataset source `academic-bafvt/poribohon-bd-cblos` v1) with `train/valid/test` splits and per-image `.rf.<hash>.jpg` filenames — **not** VOC XML as earlier recorded
- **license:** **discrepancy:** Kaggle page JSON-LD says **CC0 1.0 Public Domain**; the Roboflow export's own files say **CC BY 4.0**. Both permissive; we treat it as **CC BY 4.0 (stricter)** and keep attribution + provenance per image. Note: some sample images observed during class-semantics verification are **TV broadcast frames** (e.g. Jamuna TV logo in a leguna image) → provenance limitation, flagged for #31 QA.
- **images:** **measured 5,205** (train 3,643 / valid 1,044 / test 518); zip SHA-256 `04996c240062364e9d5bbbf4b518fca892af8ac44e6e0c3dd4de12e563e375a1` (353,841,206 bytes, measured 2026-10-04)
- **classes:** measured source boxes: bicycle 103, bike 1,550, bus 1,117, car 2,145, cng 1,439, easybike 1,257, leguna 622, rickshaw 2,329, truck 1,329, van 1,455 (**13,346 total**). Mapping (declared; class semantics **visually verified on sample images** before writing the map): bicycle→BICYCLE, bike→MOTORCYCLE, bus/car/truck exact, **cng→AUTO_RICKSHAW** (verified classic CNG auto-rickshaw), **easybike→AUTO_RICKSHAW** (BD battery 3-wheeler taxi = India e-rickshaw analog — declared grouping decision, documented in conversion report), leguna→LIGHT_VEHICLE, van→LIGHT_VEHICLE, **rickshaw (cycle rickshaw) EXCLUDED** — no canonical class (2,329 boxes dropped). **No tractor class in this dataset** (earlier "TRACTOR coverage path" claim was wrong — see §3).
- **conditions:** BD road scenes; day/night mix unquantified until measured in #31 QA
- **annotation:** Roboflow YOLO txt (as-downloaded); 5,205/5,205 label files lack trailing newlines (recounts must use per-file parsing — the `cat|wc` trap caught 2026-10-04)
- **version:** Roboflow export `academic-bafvt/poribohon-bd-cblos` v1, fetched 2026-10-04
- **hash:** zip SHA-256 above → §5 acquisition record; converted artifacts: `datasets/staging/poribohon_yolo/` (index.jsonl + conversion_report.json, index SHA-256 recorded there)
- **purpose:** Layer B supplemental — South-Asian vehicle mix; AUTO_RICKSHAW box-volume contributor (2,696 canonical boxes kept)
- **limitations:** **Bangladesh ≠ India** — usable as adjacent-domain data, never described as Indian; 265 images had no boxes and were skipped (counted); 2,329 rickshaw boxes unmapped (counted); TV-frame provenance noted above

### 2.6 Auto-Rickshaw Detection (Kaggle, uzairahmad1434) — ACQUIRED + CONVERTED

- **dataset:** AUTO-RICKSHAW-DETECTION (single class)
- **source:** Kaggle `uzairahmad1434/auto-rickshaw-detection` (evidence: `evidence/kaggle_uzairah_auto_rickshaw_license_2026-10-04.html`); archive is a **Roboflow YOLO export** (dataset source `uzair-ahmad-khan/richshaw-detection` v1)
- **license:** **Apache 2.0** per Kaggle page JSON-LD (permissive, includes patent grant); Roboflow export files say "Public Domain" — discrepancy noted, stricter (Apache 2.0) assumed
- **images:** **measured 663** (train 465 / val 132 / test 66); **808 boxes**
- **classes:** Auto Rickshaw (1 class) → AUTO_RICKSHAW
- **conditions:** road scenes (as exported); day/night mix to be quantified in #31 QA
- **annotation:** YOLO txt (Roboflow export) — direct fit for our pipeline
- **version:** Roboflow export `uzair-ahmad-khan/richshaw-detection` v1, fetched 2026-10-04
- **hash:** zip SHA-256 `4f62a62e012329c5c2963c830c35af40ac47611ac5eb988d1b1afd83c8da1406` (measured 2026-10-04); converted artifacts: `datasets/staging/autorickshaw_yolo/` (663 labels, index SHA-256 `e181e3049045a51c…` in conversion report)
- **purpose:** Layer B supplemental seed for AUTO_RICKSHAW — §7 allows AUTO_RICKSHAW only with sufficient data; combined seed now **3,504 boxes** (this + Poribohon 2,696) before any IDD-AW/PRHAAR contributions; sufficiency decided at taxonomy-freeze time
- **limitations:** small (663 measured); single-class; image sourcing by uploader; quality/duplicates checked in #31 QA

### 2.7 Kaggle IDD re-releases (idd20kii; IDD-Detections YOLOv11) — RESEARCH-CAVEAT

- **dataset:** third-party re-uploads of IDD as YOLO detections
- **source:** Kaggle `sehaj1104/idd20kii`; Kaggle IDD-Detections YOLOv11
- **license:** uploader-declared CC BY-NC-SA 4.0; **a third party re-licensing IDD does not cure the original IDD license being unresolved** → RESEARCH-CAVEAT only
- **images:** source-claimed (5.9 GB / subset)
- **classes:** IDD 30-class set
- **conditions:** Indian roads (derived)
- **annotation:** converted YOLO
- **version:** upload dates; hash at any use
- **purpose:** fallback *research reference* only unless the primary IDD license is resolved via the portal; never silently substituted for licensed IDD data
- **limitations:** provenance unresolved; conversions unverified against primary labels

### 2.8 Original IDD distribution — BLOCKED

- Original IDD / IDD detection data at primary source: no explicit data license confirmed at review; blocked until the portal terms are captured at registration. (The registration needed for IDD-AW in 2.3 also resolves this.)

### 2.9 Roboflow Universe livestock sets — PENDING-USER-ACTION

- **dataset:** livestock detection sets (goat/sheep/cow 28,295 images CC BY 4.0; separate cow+buffalo set 1,747) — source-claimed sizes from discovery review
- **source:** Roboflow Universe workspaces (exact sets pinned at download time)
- **license:** CC BY 4.0 per set (source page; re-verify per set at fetch)
- **images:** not yet downloaded — **requires Roboflow API key (user action)**; no key present in environment at review time
- **classes:** ANIMAL subclasses — notably **buffalo**, which OI and Poribohon do not cover
- **conditions:** farm/livestock scenes; not surveillance
- **annotation:** Roboflow-export formats (COCO/VOC available per set)
- **version:** per set revision id at download; hash then
- **purpose:** Layer B supplemental for §13 animal realism (cow/buffalo/goat/dog + person-beside-animal where present)
- **limitations:** many small community sets (quality varies — QA in #31); attribution required (CC BY)

### 2.10 VisDrone — CANDIDATE (research only)

- Per §8: supplemental small-object research (and optionally tracking evaluation later); **aerial** — must never be represented as SSB-like fixed-camera data. License audit still to be done before any download (not yet audited → no download per §4 protocol).

### 2.11 DataCluster "Indian Vehicle Dataset" — REJECTED (paid)

- Kaggle `dataclusterlabs/indian-vehicle-dataset`. Page states free portion excludes the useful volume: **"A license must be purchased for research or commercial purposes to access a larger portion of the training dataset."** License field: "Data files © Original Authors" (no explicit grant). → Fails free-use audit. Recorded so we never silently re-consider it without purchase.

### 2.12 DataCluster "Construction Vehicle Images" — BLOCKED (CC BY-NC-ND)

- Kaggle `dataclusterlabs/construction-vehicle-images` — **CC BY-NC-ND 4.0**. NoDerivatives makes training + augmentation legally ambiguous (and the free portion is explicitly a sample). Despite containing tractor boxes, it is **not** used. (This removes one of the few tractor-bearing public sources — combined with Poribohon-BD having no tractor class, **TRACTOR currently has zero license-clean public sources** — see §3.)

### 2.13 PRHAAR-C5-DETECTION (composite target dataset, §10) — BUILT 2026-10-14 (public-data base)

- **dataset:** PRHAAR-C5-DETECTION — the curated training dataset, assembled from Layer A (generic: OI subset), Layer B (Indian/adjacent domain: TiHAN, IDD-AW, Poribohon-BD, auto-rickshaw set, Roboflow livestock) and **Layer C (PRHAAR custom surveillance — requires real PRHAAR/SSB footage from the user; no internet substitute exists for fixed-border-camera domain)**. **Layer D** = PRHAAR-HARD-TEST frozen set — built once, hashed, never trained on, never tuned against (§20–21).
- **source:** composite; per-source provenance retained in per-source manifests; class-wise source attribution kept (per §6 license verification at freeze)
- **license:** composite — each image keeps its source license; derivative-model distribution permitted by each used source (TiHAN clause verified; OI per-image CC + CC BY 4.0 annotations; Poribohon CC BY 4.0 assumed (stricter of CC0/CC BY conflict); auto-rickshaw Apache 2.0; Roboflow CC BY attribution)
- **images:** **Measured: 20,722 images / 13,020 leakage groups / 59,972 boxes** from the 3 license-clean sources available so far (OI 15,119 + Poribohon-BD 4,940 + auto-rickshaw 663). Group-wise split: train 14,506 / val 3,108 / test 3,108 (69.99/14.99/14.99 % images; 9,112/1,954/1,954 groups); every image hardlinked, 0 fallbacks. Target 40,000–80,000+ (§10) still stands — the remainder (Layer B TiHAN/IDD-AW + Roboflow livestock + **Layer C PRHAAR footage**) lands when acquired, then the composite is rebuilt and re-hashed.
- **classes:** §7 canonical taxonomy — PERSON, MOTORCYCLE, BICYCLE, CAR, LIGHT_VEHICLE, TRUCK, BUS, TRACTOR, ANIMAL (+AUTO_RICKSHAW only if sufficient data at freeze; public seed so far: **3,504 measured boxes** = Poribohon 2,696 + auto-rickshaw set 808, before IDD-AW/PRHAAR). **Measured per-class boxes in the built composite:** PERSON 15,314 / MOTORCYCLE 4,193 / BICYCLE 3,502 / CAR 12,354 / LIGHT_VEHICLE 4,130 / TRUCK 4,245 / BUS 3,286 / **TRACTOR 0** / ANIMAL 9,444 / AUTO_RICKSHAW 3,504.
- **conditions:** §11 axes (PLAIN/FOOTHILL/FOREST/HILL/AGRICULTURE/SETTLEMENT/ROAD/FENCE-ADJACENT/LONG-RANGE × DAY/DAWN/DUSK/NIGHT × CLEAR/HAZE/FOG/RAIN × occlusion). Realistically: public data covers part; the surveillance/fence-adjacent/long-range cells depend on Layer C captures.
- **annotation:** YOLO txt + §15 metadata; converted by our own #31 converters (`convert_openimages_to_yolo.py`, `convert_roboflow_yolo.py`, `convert_voc_to_yolo.py` — all three sources converted; each staging dir QA-passed with `qa_dataset.py`, structural pass true, 0 corrupt/missing/orphan)
- **version:** `prahaar-c5-publicbase-v1` (this public-data build); content-hashed; rebuilt + re-versioned when Layer B/C sources land
- **hash:** **dataset hash `7fa08e2bf23baefc6ac1fd47e6d5a7885df2f7d8f53dc8e38b08441c01afef3b`** (sha256 over sorted `(image_id, image_sha256)`); manifest sha256 `62494a95e470015d18a2d5c2597a8112e8c7722a1853bd97aac1ff1df4bff4eb`; independently re-verified by `scripts/verify_composite.py` (ALL CHECKS PASS: file existence, label line counts, 40/40 sampled image hashes, per-class reconciliation vs staging reports, 0 cross-split groups, reproducible dataset hash)
- **purpose:** the actual training/validation corpus for C5
- **limitations:** Layer C/D coverage depends on PRHAAR capture availability (user dependency); public sources do not fill surveillance-specific cells; §11 matrix will be reported honestly as coverage, not aspiration

---

## 3. Taxonomy coverage map (as of this catalog date)

| §7 class | Current license-clean sources | Gap / action |
|---|---|---|
| PERSON | OI (2,000 cap) | Volume + long-range/occlusion from Layer C (user footage) |
| MOTORCYCLE | OI, Poribohon-BD | long-range from Layer C |
| BICYCLE | OI, Poribohon-BD | minor |
| CAR | OI (2,500 cap), Poribohon-BD | long-range from Layer C |
| LIGHT_VEHICLE | OI (Van), Poribohon-BD (Van) | pickup-type coverage still thin → TiHAN/IDD-AW |
| TRUCK | OI, Poribohon-BD | heavy-truck Indian forms → TiHAN |
| BUS | OI | Indian forms → TiHAN/IDD-AW |
| TRACTOR | **NONE currently** — OI lacks the class; Poribohon-BD measured to have **no tractor class** (earlier claim corrected 2026-10-04); DataCluster sets blocked (ND 4.0 / paid) | **zero-source gap** — Roboflow Universe tractor search via API key; TiHAN if present at delivery; PRHAAR footage if tractors appear at deployment sites |
| ANIMAL (cow/goat/dog/sheep/cattle/horse) | OI, Roboflow (pending key) | **buffalo missing** → Roboflow cow+buffalo set (API key); dark/crouched/animal-at-night → Layer C |
| AUTO_RICKSHAW (§7 conditional) | auto-rickshaw set (663 img / 808 boxes measured) + Poribohon-BD (cng+easybike → 2,696 boxes measured) | public seed **3,504 boxes**; sufficiency decided at taxonomy freeze (IDD-AW may add) |

---

## 4. User action items (blocking or high-value)

1. **TiHAN Camera Dataset access** (Layer B key source): download "EULA Form" from the TiHAN datasets page, sign it (Name/Designation/Institution/Place/Date/Signature), upload it in the "Request Access" form on the same page → confirmation email with data link. Page: `https://tihan.iith.ac.in/TiAND.html`. EULA copy archived at `ml/c5_detection/reports/evidence/tihan_eula_2026-10-03.pdf`.
2. **IDD-AW portal registration** (Layer B adverse weather): register on the IDD portal per IDDAW_kit README flow; the token arrives ~24 h later. **At registration, save the license/terms text** — it resolves both IDD-AW and the original-IDD BLOCKED status.
3. **Roboflow API key** (livestock + possibly tractor sets): create a free Roboflow account → Settings → API key, and place it in the environment. Without it the livestock (incl. buffalo) gap cannot be filled from those CC BY 4.0 sets.
4. **PRHAAR/SSB custom footage** (Layer C + Layer D — the critical one): fixed-camera border surveillance footage (day/night/weather, fence-adjacent, long-range, animal zones). No public dataset substitutes for this domain; it is required for the §10 custom layer and the §20 frozen hard test. Even a small curated set (hundreds of clips) materially changes ceiling quality.
5. *(Optional)* MIO-TCD download decision — large fixed-camera traffic corpus; pull only if the §23 error loop shows viewpoint/domain gaps it can fill.

---

## 5. Acquisition record (measured artifacts)

| Artifact | SHA-256 | Date | Notes |
|---|---|---|---|
| `datasets/sources/kaggle/auto_rickshaw_apache2/auto-rickshaw-detection.zip` | `4f62a62e012329c5c2963c830c35af40ac47611ac5eb988d1b1afd83c8da1406` | 2026-10-04 | measured 663 img / 808 boxes; converted → `datasets/staging/autorickshaw_yolo/` (index SHA-256 `e181e3049045a51c…`) |
| `datasets/sources/kaggle/poribohon_bd/poribohon-bd.zip` | `04996c240062364e9d5bbbf4b518fca892af8ac44e6e0c3dd4de12e563e375a1` | 2026-10-04 | measured 5,205 img / 13,346 boxes; converted → `datasets/staging/poribohon_yolo/` (4,940 img out, 11,017 boxes kept, 2,329 rickshaw unmapped, 265 no-box skipped; index SHA-256 in conversion_report.json) |
| QA: `datasets/staging/poribohon_yolo/dataset_quality_report.json` | index sha256 `eb758eaa69ab78ff…` | 2026-10-04 | §17 structural pass; 0 corrupt/missing; 8 exact-dup groups (6 cross-split) + 43 near-dup/burst clusters (19 cross-split) → **source's own split is leaky; #31 must re-split by cluster** |
| QA: `datasets/staging/autorickshaw_yolo/dataset_quality_report.json` | index sha256 `e181e3049045a51e…` | 2026-10-04 | §17 structural pass; 0 corrupt/missing; 0 exact dups; 17 near-dup/burst clusters (8 cross-split) |
| Composite builder smoke: `datasets/PRHAAR-C5-DETECTION-smoke/` | dataset hash `ea8e260fe60f9bb0…` | 2026-10-04 | tooling validation on the 2 available sources: 5,603 img → 5,530 groups (8 exact + 84 near pairs deduped), split 3,923/840/840 (70.0/15.0/15.0, by group), **leakage pass true (0 cross-split groups)**, 11,825 boxes (= 11,017 + 808), all hardlinked; smoke artifact only — the real `PRHAAR-C5-DETECTION` build runs after OI lands |
| OI metadata CSVs (8 files) | see `datasets/sources/openimages_v7/_metadata/file_hashes.json` | 2026-10-03/04 | recorded automatically by `scripts/acquire_openimages.py`; all 8 complete (train bbox 2,258,447,590 B; train info v6 2,684,720,962 B; train info v4 NOT downloaded — lazy fallback, unneeded so far) |
| OI smoke run: `datasets/sources/openimages_v7/acquisition_summary.json` | manifest sha256 `0e061798baa48df5…`; annotations_raw sha256 `0084fe78488969dd…` | 2026-10-04 | **smoke verified end-to-end**: 100 union images (28 train / 36 val / 36 test), 100/100 downloaded ok (0 failed, 32.9 MB, 36 s @ 8 workers, 100% `https-s3-pathstyle`), 0 dropped for missing license, license histogram 100× CC BY 2.0; artifacts `annotations_raw.jsonl` + `acquisition_manifest.jsonl` (100 lines each) schema-verified |
| OI FULL run: `datasets/sources/openimages_v7/acquisition_summary.json` | summary sha256 `5343a2a53c1cd2c5…`; manifest sha256 `7c882f696cf797a3…`; annotations_raw sha256 `85ef0c0d1a4614cd…` | 2026-10-13/14 | **COMPLETED 2026-10-14 00:58 IST**: 16,372 images (train 11,898 / val 1,989 / test 2,485), **16,372 ok / 0 failed**, 5,530,210,738 B, elapsed 12,965.1 s @ 8 workers (ISP-level shaping caused bimodal throughput; retry/cached design lost nothing); 0 license drops (v4 fallback never needed); license histogram 16,372× CC BY 2.0 (official CSV content, measured); 53,497 raw boxes |
| OI conversion: `datasets/staging/oi_yolo/conversion_report.json` | index sha256 `c47ce8f114fe6211…` | 2026-10-14 | 16,372 img → 15,119 (1,253 no-box skipped); boxes 53,497 → **48,147 kept** (dropped 2,743 depiction + 2,607 group-of, all counted); per-class boxes: PERSON 15,314 / MOTORCYCLE 2,643 / BICYCLE 3,399 / CAR 10,209 / LIGHT_VEHICLE 2,053 / TRUCK 2,916 / BUS 2,169 / ANIMAL 9,444 / TRACTOR 0 / AUTO_RICKSHAW 0 |
| QA: `datasets/staging/oi_yolo/dataset_quality_report.json` | index sha256 `c47ce8f114fe6211…` | 2026-10-14 | §17 structural **pass true**: 15,119/15,119 images ok (0 missing/corrupt), labels ok 15,119 / bad 0 / **orphans 0**, 48,147 boxes (0 malformed/class-invalid/degenerate/out-of-bounds), 0 exact dups, 2 near-dup/burst clusters (0 cross-split) |
| **Composite build: `datasets/PRHAAR-C5-DETECTION/`** | **dataset hash `7fa08e2bf23baefc…`**; manifest sha256 `62494a95e470015d…`; split_report in dir | 2026-10-14 | **REAL BUILD (not smoke)**: 20,722 img (OI 15,119 + Poribohon 4,940 + auto-rickshaw 663) → 13,020 groups (8 exact + 88 near pairs + 7,625 author pairs, 7 authors capped at 64) → group-wise 70/15/15 (14,506/3,108/3,108 img; 9,112/1,954/1,954 groups); **leakage pass true, 0 problems**; 59,972 boxes (= 48,147 + 11,017 + 808 exactly); all 20,722 hardlinked, 0 copy-fallbacks; **independently re-verified** by `scripts/verify_composite.py` → ALL CHECKS PASS (files, label line counts, 40/40 sampled sha256, per-class reconciliation, 0 cross-split groups incl. exact-dups, reproducible hash) |
| OI rotation/frame probe | `reports/evidence/oi_rotation_probe/probe_report.json` (+ 4 montages + contact sheet) | 2026-10-04 | boxes = raw stored-image frame (aspect-stat proof); rotation = display metadata only; downloads are max-1024px redistributions, not original Flickr bytes |

Acquisition + conversion tooling:
- `ml/c5_detection/scripts/acquire_openimages.py` — deterministic (seed `prahaar-c5-v1`, SHA-1 sampling), occlusion-flag preserving, per-image license capture, SHA-256 manifests, `--smoke` validation mode.
- `ml/c5_detection/scripts/c5_taxonomy.py` — canonical taxonomy v1.0 single source of truth (all converters import it).
- `ml/c5_detection/scripts/convert_roboflow_yolo.py` — Roboflow YOLO export → canonical YOLO (class-remap, unmapped-abort unless `--allow-skip`; per-source-class box counts recorded).
- `ml/c5_detection/scripts/convert_openimages_to_yolo.py` — OI JSONL → canonical YOLO (depiction rows dropped, occluded/truncated kept, group-of configurable).
- `ml/c5_detection/scripts/convert_voc_to_yolo.py` — VOC XML → canonical YOLO (generic; ready for XML-based sources).
- `ml/c5_detection/scripts/qa_dataset.py` — §17 automated validation + §18 duplicate detection (SHA-256 exact + dHash-64 near-dup/burst via PIL; `imagehash` unavailable) + §12 bbox area distribution → `<staging>/dataset_quality_report.json`.
- `ml/c5_detection/scripts/build_composite.py` — assembles `datasets/PRHAAR-C5-DETECTION/` from QA-passed staging dirs: self-contained re-hash, union-find leakage groups (§19: exact + near-dup + capped OI-author union), group-wise ~70/15/15 split (§20), hardlink materialization (fallbacks counted, never silent), `manifest.jsonl` + `data.yaml` + `dataset_hash.txt` + `split_report.json` with post-build leakage verification.
- `ml/c5_detection/scripts/verify_composite.py` — independent second-source-of-truth verifier for the built composite (does not reuse builder internals): manifest file existence + label line counts + sampled SHA-256 (40 images), per-class reconciliation vs staging conversion reports, leakage re-check from the manifest itself, stem uniqueness, dataset-hash reproducibility.
- Kaggle sources fetched with the official `kaggle` CLI 2.2.4 (authenticated); archives hashed before extraction.

---

## 6. Dataset gap statement (honest accounting per §10)

As of this catalog date, the license-clean pipeline covers: generic classes broadly (**OI acquired + converted: 16,372 img down → 15,119 staged / 48,147 canonical boxes**), South-Asian vehicle mixes (**Poribohon-BD measured 5,205 img / 11,017 canonical boxes**, converted; its `cng`+`easybike` classes → AUTO_RICKSHAW 2,696 boxes, hand-pulled `rickshaw` 2,329 boxes excluded), an auto-rickshaw seed (663 img / 808 boxes, converted), and — pending user actions — Indian driving domain (TiHAN), adverse weather (IDD-AW), buffalo/livestock (Roboflow). **The public-data composite `PRHAAR-C5-DETECTION` is BUILT (2026-10-14): 20,722 img / 13,020 groups / 59,972 boxes, leakage pass true, dataset hash `7fa08e2bf23baefc…`** — this is the base for #32 training experiments; it will be rebuilt when Layer B/C sources land. Known gaps: **TRACTOR has zero license-clean public sources** (OI lacks it; Poribohon has no tractor class; DataCluster sets blocked) — the composite ships with TRACTOR as an empty class, declared, not hidden; **buffalo** still uncovered; and the **surveillance-domain axis (Layer C: fixed cameras, fence-adjacent, long-range, night/thermal-like conditions) plus the frozen hard-case layer (Layer D) have no public substitute and depend on PRHAAR footage.** §11 condition matrix and §12 long-range targets will be reported as partial coverage — actual numbers only.

---

*This catalog is updated after each acquisition. Counts are never estimated; "pending" means pending, not approximated.*
