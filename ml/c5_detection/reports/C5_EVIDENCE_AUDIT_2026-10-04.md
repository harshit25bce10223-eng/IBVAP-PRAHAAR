# C5 evidence and reporting audit

Date: 2026-10-04 (Asia/Calcutta)

## Scope and decision

This is a non-operational review of existing dataset manifests, QA reports and experiment evidence. It does not train, improve, integrate or validate an operational detector. No production-readiness or 95% performance claim is supported by the reviewed evidence.

Existing reports and code were left unchanged. No dataset acquisition, re-splitting, model training, inference or deployment was performed. Dataset images were not manually reviewed or independently decoded in this audit. Reported historical QA results are distinguished below from checks performed today.

## Findings

1. **Dataset assembly and model evaluation are different artifacts.** `datasets/PRHAAR-C5-DETECTION-smoke/split_report.json` reports 5,603 images, 11,825 boxes and 5,530 groups. Independently counting its manifest today confirms 3,923 train / 840 validation / 840 test entries. These are dataset inventory counts, not evidence of detection accuracy.

2. **Source splits contain reported overlap.** The stored Poribohon QA report records 6 exact-duplicate groups and 19 near-duplicate/burst clusters crossing source splits. The autorickshaw QA report records 8 near-duplicate/burst clusters crossing source splits. These historical counts were read from reports, not regenerated from image pixels today. They must not be added together as unique affected-image counts.

3. **Composite leakage claims have a limited scope.** The composite report records zero cross-split exact-hash groups and zero cross-split declared groups. Manifest-level checks were performed separately today. This only concerns recorded hashes and group identifiers: absent camera/video/session metadata prevents a claim that all scenes or capture sessions are independent. The report itself discloses proxy-based grouping and retention of exact duplicates within a split.

4. **The available evaluation is a plumbing smoke test.** `evaluation/dryrun_plumbing_val_eval.json` identifies `_synthetic_smoke`, validation split, 6 images and a one-epoch experiment. It records precision, recall, mAP50 and mAP50-95 as 0.0. These values neither demonstrate practical performance nor estimate performance on real imagery. Several class metrics have no ground-truth support; condition-wise metrics are null, not passing results.

5. **Experiment accounting is incomplete.** `C5_EXPERIMENT_LOG.csv` contains a header only, while the evaluation JSON contains an `experiment_log_row`. Therefore an empty CSV does not prove that no training ever ran. The previous conversational statement should be read as “no established practical performance,” not “no experiment exists.” The smoke checkpoint exists and its SHA-256 was checked against the evaluation record.

6. **Reproducibility evidence is partial.** The smoke evaluation stores a checkpoint digest and data-YAML digest, but `dataset.split_hash` is null. A configuration-file digest alone is not a complete fingerprint of image content, annotations and split membership. The composite builder's `dataset_hash` is defined over image identifiers and image hashes; its name should not be interpreted as covering every annotation or evaluation setting.

7. **Rights are not independently cleared by this audit.** Local source records contain license statements, including differing upstream labels. This review records their existence; it does not verify current external terms or provide legal clearance. No external license assertions were adopted as independently verified conclusions.

8. **C2's report is not real-world certification.** `../c2_camera_health/reports/C2_CAMERA_HEALTH_REPAIR_REPORT.md` explicitly limits its benchmark conclusions to synthetic corpora and local development timings. Its re-lock statement is a historical engineering decision. C2 benchmarks, API tests and browser checks were not rerun in this audit.

## Permissible reporting language

“Dataset assembly and synthetic plumbing checks are documented. Practical detection performance, condition-wise reliability and operational readiness remain unverified.”

Do not describe missing metrics as zero errors, manifest grouping as proof of unseen-camera independence, a synthetic smoke test as a real-world benchmark, or an existing report's PASS as an independently repeated result.

## Evidence reviewed

- `datasets/PRHAAR-C5-DETECTION-smoke/{manifest.jsonl,split_report.json}`
- `datasets/staging/poribohon_yolo/dataset_quality_report.json`
- `datasets/staging/autorickshaw_yolo/dataset_quality_report.json`
- `evaluation/dryrun_plumbing_val_eval.json`
- `training/runs/dryrun_plumbing/weights/best.pt` (digest only)
- `C5_EXPERIMENT_LOG.csv`
- `scripts/qa_dataset.py` and `scripts/build_composite.py` (reporting semantics only)
- `reports/C5_DATASET_CATALOG.md`
- `../c2_camera_health/reports/C2_CAMERA_HEALTH_REPAIR_REPORT.md`

This document is an evidence audit, not a completed fresh dataset QA run or a production approval.
