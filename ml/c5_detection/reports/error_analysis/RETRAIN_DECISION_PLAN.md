# PRHAAR C5 — Error-analysis interpretation + final-retrain decision plan

Working doc (#33 prep, written 2026-10-15 night while exp001 trains to its
epoch-50 cap). Purpose: the moment the chain's measured rows land, the
decision is execution-only — no morning deliberation. Every projection here
is LABELED as a projection; only §63 log rows are measured truth (§62).

## What lands automatically tonight (no manual work)

Chain (run_sweep_302.sh) after the cap manifest appears (~02:00-02:45):
1. `eval_detector.py` val@640 → `evaluation/exp001_yolo26s_640_val_eval.json`
2. `eval_detector.py` test@640 → `evaluation/exp001_yolo26s_640_test_eval.json` + §63 row
3. `analyze_errors.py` test@640 → `reports/error_analysis/exp001_yolo26s_640_test_errors.json`
   (per-class P/R/AP50, size-bucketed recall small<32²/medium<96²/large px,
   occlusion slice on OI subset, multi-conf-floor recall from one conf-0.001 pass)
4. Then exp004 rtdetr-l 640 b4 50ep starts (overnight; cap decision for it is
   separate — watcher is generic: `epoch_cap_watcher.sh exp004_rtdetr_l_640 N rtdetr-l.pt`)

## Interpretation playbook (driver → lever)

| Measured driver (from errors.json) | Lever for final retrain | Expected magnitude* |
|---|---|---|
| small-object recall << medium/large | imgsz 960 (or 1280), batch halved for VRAM | +1-3 mAP50 |
| ANIMAL class AP50 lowest of the 10 | more animal sources (Roboflow key — user item), or accept (grouped class, hard) | data-bound |
| occlusion slice recall << overall | nothing free — occlusion-heavy sources scarce; note in report | small |
| recall@conf-0.1 ≥0.85 while mAP stuck | operating-point headroom exists; document conf recommendation for integration | deployment lever, not mAP |
| all classes uniformly ~0.7x, no outlier | model capacity is the binding constraint → bigger model | +2-5 mAP50 |
| TRACTOR remains empty | cannot fix with training; stays a declared gap (needs SSB/PRHAAR footage) | — |

\* expectations from typical detection practice, NOT measurements; each retrain
row in the log is measured before any claim (§2/§29).

## Final-retrain recommendation (single strong config, NOT a new sweep)

§23's sweep purpose (family decision + baseline) is served by exp001+exp004.
The retrain after #33 is ONE hero run, config chosen by the measured driver:

- **Default pick (if error analysis shows no single dominant class outlier):**
  `yolo26m.pt @ imgsz 960, batch 4 (VRAM), epochs 80, patience 20, cos_lr,
  seed 0, workers 2, --no-pin-memory` — capacity + resolution together are
  the two largest honest levers; running them in one run matches the GPU-time
  budget (m @960 b4 ≈ est. 35-45 min/ep → cap consideration needed; see below).
- **If license gate (Ultralytics AGPL/RUP §4.2) still OPEN at retrain time:**
  the hero becomes `rtdetr-l @ 960` instead — same capacity class, Apache-2.0
  lineage (model_license_audit.md). yolo26m/l remain eval-only until cleared.
- **If small recall is THE dominant gap:** prefer 1280 over a bigger model
  (resolution beats capacity for small objects), batch 2.
- exp002 (yolo26m) / exp003 (yolo26l) from the trimmed sweep fold into this:
  the retrain IS their slot (deferred ≠ cancelled — chain header record).

Time honesty: 80 epochs of m@960 will NOT fit a night on this RTX 2050
(est. 35-45 min/ep → 40-55 h). Expect to cap it the same way as exp001
(watcher) at a chosen epoch and treat that as the measured retrain row;
state the cap in the manifest (same labeled-deviation protocol).

## Pre-registered decision rule (avoid post-hoc bias)

1. Read errors.json + the two eval JSONs.
2. Pick the dominant measured driver per the playbook table (top row that applies).
3. Launch the matching config same morning; cap epoch chosen from measured
   pace so it lands in the available window.
4. Whatever the result: it goes into the §63 log measured, and the acceptance
   table (§36) compares it against §29 targets as PASS/GAP — no re-framing.
