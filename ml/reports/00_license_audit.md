# 00 — License Audit (Phase 1)

**Project:** PRHAAR — SSB AI-Powered Border Surveillance & Command Platform
**Scope:** Every external dataset and software dependency referenced by the AI/ML phase (spec §8, §4)
**Date:** 2026-09-29
**Rule (§8):** *Never silently download and incorporate data with unknown or incompatible rights.*

> This audit records publicly documented license information and its verification state. It is not legal advice.

---

## 1. Dataset audit table (spec §8 field format)

Status legend: **USABLE** (verified, may be used with conditions) · **VERIFY-AT-ACQUISITION** (license must be re-confirmed on the download page before download) · **BLOCKED** (license unresolved — do not download) · **NOT USED** (rejected or unnecessary) · **LINEAGE** (used only as pretrained-weight lineage, not redistributed).

| # | dataset_name | source_url | license | commercial restriction | research-only | redistribution | attribution required | download status | used/not-used | reason |
|---|---|---|---|---|---|---|---|---|---|---|
| 1 | COCO (via pretrained checkpoints) | cocodataset.org | Annotations CC-BY-4.0; images per-Flickr-source | per image | no | we never redistribute images | yes (lineage noted in model card) | not downloaded | **LINEAGE** | Transfer-learning initialization only; no COCO image ships with PRHAAR |
| 2 | Open Images V7 (candidate) | storage.googleapis.com/openimages | CC-BY-4.0 (images + annotations, per provider docs) | no (verify) | no | per license | yes | not downloaded; loader bundled in ultralytics | VERIFY-AT-ACQUISITION | Candidate Layer-B animal/person diversity |
| 3 | India Driving Dataset (IDD) | idd.insaan.iiit.ac.in / india-data.org | **UNRESOLVED** — license page (india-data.org/licenses/idd-crs-license) returned no content during audit | unknown | unknown | unknown | unknown | **not downloaded** | **BLOCKED** | Cannot confirm terms → no download, no use, until resolved |
| 4 | VisDrone (DET/MOT) | github.com/VisDrone | Researc/scholarly use (terms not explicit on page) | likely restricted | likely yes | restricted | yes | not downloaded; auto-downloadable via ultralytics | VERIFY-AT-ACQUISITION | Small-object + tracking research only; never presented as border-camera evidence |
| 5 | MOT17 / MOT20 (C6 secondary) | motchallenge.net | Research/academic agreement (non-commercial) | restricted | yes | restricted | yes | not downloaded | VERIFY-AT-ACQUISITION | Secondary tracking benchmark if terms confirmed |
| 6 | **Zenodo 13954136 "Number Plate Number Identification Dataset"** | zenodo.org/records/13954136 | **CC-BY-4.0 (verified on record page 2026-09-29)** | no | no | permitted with attribution | yes | not downloaded yet | **USABLE** | 1,700 images, Bapatla (AP), India — plate detection base |
| 7 | DataCluster "Indian Licence Plate Image Dataset" (6,000+, 20+ states) | datacluster.ai | **NOASSERTION / access-controlled (contact sales)** | unknown | unknown | unknown | unknown | not accessible | **NOT USED** | No license asserted + access-controlled → excluded |
| 8 | DataCluster "Indian number-plate dataset" (20,000+, 700+ areas) | datacluster.ai | **NOASSERTION / access-controlled (contact sales)** | unknown | unknown | unknown | unknown | not accessible | **NOT USED** | Same as #7 |
| 9 | Kaggle Indian plate datasets (various) | kaggle.com (per dataset) | varies per dataset page | varies | varies | varies | varies | requires Kaggle auth | VERIFY-AT-ACQUISITION | Per-dataset license check recorded in this table before any download |
| 10 | african-wildlife (bundled loader) | ultralytics bundled `african-wildlife.yaml` | verify at download | verify | verify | verify | verify | not downloaded | VERIFY-AT-ACQUISITION | Optional animal-silhouette diversity; no claims beyond its labels |
| 11 | xView | bundled `xView.yaml` | CC-BY-NC-4.0 (per provider) | non-commercial | yes | restricted | yes | not downloaded | **NOT USED** | Satellite domain mismatch for border-CCTV; not needed |
| 12 | BDD100K | bdd-data.berkeley.edu | UIUC custom, non-commercial | restricted | yes | restricted | yes | not downloaded | **NOT USED** | Driving domain mismatch; insufficient marginal value |
| 13 | PRHAAR-C5/C6/C7 custom collections | project-captured | project-owned | n/a | n/a | project policy | n/a | not yet collected | PLANNED | Layer C — the real target domain |

## 2. Software / model dependency audit

| # | software/model | version | license (verification) | production implication |
|---|---|---|---|---|
| 1 | Ultralytics (YOLO26, trackers) | local package present | **AGPL-3.0** or **Enterprise** (verified from Ultralytics legal page) | **Decision item**: if PRHAAR ships Ultralytics-derived inference as part of a distributed/network service, AGPL obligations must be evaluated; Enterprise license is the alternative. Must be resolved before any C5/C6/C7 production-candidate status |
| 2 | PaddleOCR / PP-OCR family | to install at Phase 5 | **Apache-2.0** (LICENSE fetched directly from PaddlePaddle/PaddleOCR repo, 2026-09-29) | Permissive; fine for backend deployment with attribution/notice files |
| 3 | PyTorch + torchvision | 2.5.1+cu121 (present) | BSD-3-Clause (verify at install) | Permissive |
| 4 | ONNX / ONNX Runtime | to install at Phase 3 | Apache-2.0 / MIT (verify at install) | Permissive; export path |
| 5 | NumPy / OpenCV / SciPy | present/to install | BSD-style / Apache-2.0 (verify at install) | Permissive |
| 6 | CC-BY-4.0 datasets (Zenodo #6, Open Images #2) | — | attribution + license reference in repo docs | Add to `ATTRIBUTIONS` section of final report |

## 3. AGPL decision record (open item)

- **What:** Ultralytics code/weights are AGPL-3.0. The PRHAAR backend serves detection/tracking results over a network API.
- **Why it matters:** AGPL's network-use clause can impose source-availability obligations on services built on the software.
- **Options:** (a) comply with AGPL for the AI service boundary, (b) Ultralytics Enterprise License, (c) alternative detector family with permissive license *only if* Phase 3 measured results favor it.
- **Status:** OPEN — carried in `PRHAAR_AI_MODEL_PLAN.md` §Open decisions. No production-candidate claim for C5/C6/C7 until resolved.

## 4. Acquisition-time verification protocol (mandatory)

For every dataset marked VERIFY-AT-ACQUISITION, before the first byte is written to disk:

1. Capture the license text/URL and date of review.
2. Record: commercial restriction, research-only restriction, redistribution restriction, attribution requirement.
3. Update the dataset's row in this file + `PRHAAR_DATASET_CATALOG.md` (version, count, SHA-256 manifest).
4. If anything remains ambiguous → **do not download** (blocked, documented).

## 5. Attribution ledger (to carry into final reports)

- Zenodo 13954136 dataset authors (CC-BY-4.0) — cite record + authors when used.
- Ultralytics (AGPL-3.0 license text + copyright notice) in any distribution complying with the chosen option.
- PaddleOCR (Apache-2.0) notice.
- Any future Layer-B datasets added per §4 protocol.

## 6. Status summary

| Bucket | Datasets |
|---|---|
| Usable now | Zenodo 13954136 (CC-BY-4.0, attribution) |
| Verify at acquisition | Open Images V7, VisDrone, MOT17/20, Kaggle candidates, african-wildlife |
| Blocked | IDD (license unreachable/unresolved) |
| Not used | DataCluster ×2 (no license asserted, access-controlled); xView, BDD100K (domain mismatch) |
| Lineage only | COCO (checkpoint initialization; no redistribution) |
