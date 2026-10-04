# C2 CAMERA HEALTH — REPAIR REPORT
## REOPEN → REPAIR → RE-BENCHMARK → RE-LOCK

**Report date:** 2026-10-03 (host IST, UTC+5:30)
**Directive:** C2 CAMERA HEALTH — REOPEN → REPAIR → RE-BENCHMARK → RE-LOCK (reopen spec §§4–50)
**Before-state report (retained, untouched, per §50):** `C2_CAMERA_HEALTH_AI_REPORT.md` (same directory)
**Repaired component:** `ibvap-backend` C2 camera-health domain (`app/domain/camera_health/`, routes, models, repositories), benchmark harness + corpus generators under `ml/c2_camera_health/benchmark/`, frontend health surfaces
**Final decision:** see §18 — **C2 — FIXED + RE-BENCHMARKED + RE-LOCKED ✅** and the §48 statement `No learned C2 model justified at this stage.`

### Evidence artifacts referenced by this report

| Artifact | What it contains |
|---|---|
| `benchmark/c2_benchmark_results_run1.json`, `run2`, `reopen1` | Pre-repair 180-sample runs (before-state) |
| `benchmark/c2_benchmark_results_repair1.json`, `repair2` | Post-repair 180-sample rerun ×2 |
| `benchmark/c2_corpus_manifest_v1.json` | 180-sample corpus manifest (internal SHA-256 `f251e908…`) |
| `benchmark/c2_v11_benchmark_results_v11run1.json`, `v11run2` | Expanded 300-sample runs (pre-§42-fix) |
| `benchmark/c2_v11_benchmark_results_v11postfix1.json`, `postfix2`, `postfix3` | Expanded 300-sample triple-run (post-§42-fix, final) |
| `benchmark/c2_corpus_manifest_v11.json` | 300-sample corpus manifest (internal SHA-256 `46512b93…`) |
| `benchmark/c2_freeze_false_positive_benchmark.json` | Quiet-scene false-freeze corpus results |
| `benchmark/c2_viewpoint_calibration.json` | Viewpoint calibration sweep (5 config combos) |
| `benchmark/c2_api_validation_results.json` | Clean-environment API validation (90 checks) |
| `benchmark/c2_browser_qa_seed_results.json` | Browser-QA fleet seeding evidence on live backend |
| `benchmark/c2_performance_results.json` | Post-fix performance bench |
| `ibvap-backend/tests/unit/test_c2_regression.py` | F1–F17 regression suite |

All run times below are naive-UTC `run_utc` values recorded by the harness; all digest values are SHA-256.

---

## 1. Initial benchmark

The reopen spec §4 required reproducing the failure before repairing anything. The 180-sample original corpus (`c2_corpus_manifest_v1.json`, internal manifest SHA-256 `f251e908cd2f397f0793fe043032b39e9e9c99d5b288260f382a1d2fc602e30a`, file SHA-256 `62c194534907317f6da47a76acafd030f5fba064fd5873664be49f869ca7ca22`; 13 classes; generator base seed `20260930`; synthetic 320×180 12-frame sequences, 8 for viewpoint) was run three times with the unmodified harness:

| Run | `run_utc` | Wall | Canonical results digest |
|---|---|---|---|
| `run1` | 2026-10-03T09:07:00.969674 | 42.390 s | `7f59116b4f7ead41f6a1fc3375913528875c141354f062390aacedd81f0dc15c` |
| `run2` | 2026-10-03T09:07:57.148495 | 28.827 s | `7f59116b4f7ead41f6a1fc3375913528875c141354f062390aacedd81f0dc15c` |
| `reopen1` | 2026-10-03T09:28:31.789371 | 46.489 s | `7f59116b4f7ead41f6a1fc3375913528875c141354f062390aacedd81f0dc15c` |

**Result: 180/180 samples failed with `ENGINE_EXCEPTION`. No observation completed. The failure was fully deterministic** — three independent runs produced byte-equivalent canonical output.

Failure split (from `failure_class` aggregation):

| Failure class | Count | Location |
|---|---|---|
| `KeyError: 'reason'` | 156/180 | `analyzer.py:264` (maintenance-status fallthrough) |
| `TypeError: HealthAnalysisResult.__init__() got an unexpected keyword argument 'network_reason'` | 24/180 | `analyzer.py:246` (result contract) |

Per class, all 13 classes emitted `ENGINE_EXCEPTION` for every sample:

| Class | n | Observed (pre-repair) |
|---|---|---|
| BLURRED | 18 | ENGINE_EXCEPTION |
| COVERAGE_COMPROMISED | 12 | ENGINE_EXCEPTION |
| DEGRADED | 18 | ENGINE_EXCEPTION |
| FROZEN | 12 | ENGINE_EXCEPTION |
| LOW_FPS_SINGLE_DIM | 6 | ENGINE_EXCEPTION |
| OBSTRUCTED | 15 | ENGINE_EXCEPTION |
| ONLINE | 24 | ENGINE_EXCEPTION |
| OVEREXPOSED | 15 | ENGINE_EXCEPTION |
| SEVERE_COMPRESSION | 18 | ENGINE_EXCEPTION |
| STALE_FEED | 6 | ENGINE_EXCEPTION |
| STREAM_DROP_FROZEN | 6 | ENGINE_EXCEPTION |
| UNDEREXPOSED | 15 | ENGINE_EXCEPTION |
| VIEWPOINT_CHANGED | 15 | ENGINE_EXCEPTION |
| **Total** | **180** | **180 ENGINE_EXCEPTION** |

The pre-repair situation, defect catalog, and the §105 evaluation disclaimer are preserved in `C2_CAMERA_HEALTH_AI_REPORT.md`, which per §50 remains the before-state and was not modified.

## 2. Every defect confirmed

Seventeen defects were catalogued across the reopen. F1–F13 were confirmed from the before-state report + reopened benchmark; F14–F17 were discovered during the §34/§35 validation passes and fixed in the same repair cycle. One candidate (F10) was **retracted by measurement** and is documented as such — it was never repaired because it was never a defect.

| ID | Defect | Confirming evidence |
|---|---|---|
| F1 | Maintenance-status fallthrough: `_determine_maintenance()` could return a dict missing contract keys → `KeyError: 'reason'` | 156/180 pre-repair samples (`analyzer.py:264`) |
| F2 | Result-contract mismatch: `HealthAnalysisResult` constructed with `network_reason` kwarg it did not accept → `TypeError` | 24/180 pre-repair samples (`analyzer.py:246`) |
| F3 | Frames measured by the pipeline never reached the state engine's input path | F3 probe (`probe_f3_input_wiring.py`); freeze/quality signals could not influence state |
| F4 | Freeze signal integration: detector output could not reach state derivation | Freeze component dead-ended in the analyzer result |
| F5 | Analyzer-side per-camera reference provisioning missing; no reference-quality gate | Viewpoint had no per-camera reference in-analyzer; low-texture frames risked shift misclassification |
| F6 | Viewpoint status enum comparison wrong (`derived.viewpoint_status` checked against wrong enum) → `shift_detected` always `False` → C1 context always reported `shifted=false` | Contract inspection + regression `test_f6_frame_based_shift_reaches_c1_context` |
| F7 | Sharpness status/reason read from the wrong structure instead of `derived.image_metrics[...]` | F7 fix regressions |
| F8 | Timezone policy violations: naive-vs-aware writes/reads, false `LAST_KNOWN`, naive ISO outputs | §34 run 2: 84/90 with 2 false LAST_KNOWN; UTC/IST tests |
| F9 | Single-dimension degradation undecided (e.g. LOW_FPS_SINGLE_DIM) | State ambiguity vs documented policy; resolved to documented UNKNOWN |
| F10 | Suspected SEVERE_COMPRESSION blind spot — **RETRACTED by measurement** | Measured sharpness ≈ 0.34 mean; 18/18 below the 0.5 threshold in v1.1. Detection works; no blind spot. Not repaired — closed as retraction (see §17, §18). |
| F11 | Freeze false positives ≈ 100% on quiet scenes; noise-floor code dead (`freeze.py:46,111`) | Quiet-scene probe FP rate ≈ 100%; detector config unused |
| F12 | `cv2` (OpenCV) absent from `requirements.txt` → fresh deployment crash | Requirements audit; import failure on clean venv |
| F13 | ONLINE branch lacked the viewpoint gate; state precedence matrix was undocumented | Precedence matrix ambiguity; fixed + locked by `test_f9_f13_state_precedence_matrix` |
| F14 | `camera_health_current.shift_confidence` column missing while routes upsert it → fresh-DB ingest HTTP 500 (`Unconsumed column names: shift_confidence`) | §34 run on empty DB (migration `c2b17f04a9d1`) |
| F15 | Config route contracts broken (camelCase create/update/response mismatch) | §34 config checks failed pre-fix |
| F16 | Timezone write/read family (extends F8): raw-offset persistence, naive-vs-local age comparisons → false `LAST_KNOWN` ×2, naive ISO outputs, history bucket epoch local-interpretation, naive `updated_at` | §34 run 2: 84/90 |
| F17 | Duplicate `(camera_id, source_sequence)` ingest → unhandled 500 UNIQUE constraint (adapter retry / camera reboot sequence reset) | §35 browser-QA seeding hit the crash on a repeat ingest |

Observability (§43) additions carried by the repair: `freeze_status`, `freeze_confidence`, `freeze_duration_sec`, `analysis_duration_ms` (locked by `test_43_observability_fields_present`).

## 3. Fixes

Per §25, the benchmark harness and corpus generators were **not** modified to convert crashes into green results — all repairs are in production code (plus additive harness features: the v1.1 corpus, freeze-FP corpus, calibration probes, and performance bench). Per §125, locked components elsewhere in the repo were left untouched. Smallest architecture-consistent repairs:

| Fix | Change |
|---|---|
| F1 | `_determine_maintenance()` returns the full contract on every branch (including `reason`). |
| F2 | `HealthAnalysisResult` construction corrected to its actual contract. |
| F3/F4 | Frames wired end-to-end: analyzer feeds the frames into freeze detection + state inputs (`test_freeze_signal_reaches_state_engine_via_input`, `test_f3_f7_blurred_frame_reaches_state_engine`). |
| F5 | Per-camera reference provisioning added inside the analyzer + `_reference_quality_ok` gate: near-black (0.05) reject, blown (0.95) reject, UNDerexposed reject, insufficient (None/None) accept. Low-texture frames can never be reported as shift (`test_f5_*`, `_StubIQ` assertions in `test_c2_regression.py`). |
| F6 | Correct enum check (`ViewpointStatus.SHIFT_DETECTED` / `SEVERE_SHIFT`); `shift_detected` derived correctly and reaches C1 context. |
| F7 | Sharpness status/reason now read from `derived.image_metrics[...]`. |
| F8/F16 | Canonical timezone policy: all engine timestamps UTC-aware; legacy naive values normalized to UTC on read (`_ensure_utc`); `_determine_data_source` uses aware comparisons; history buckets and event timestamps normalized; naive ISO outputs eliminated. |
| F9 | Single-dimension row (`LOW_FPS_SINGLE_DIM`) → documented UNKNOWN state (conservative: never ONLINE). |
| F10 | No repair — retracted by measurement (sharpness evidence shows SEVERE_COMPRESSION detection works). |
| F11 | Freeze detector rebuilt: per-region MAD over a 4×4 grid vs `noise_floor` 0.001 + bit-exact frame check + persistence 10 frames + movement-spread veto (factor 8.0) + working-scale 0.125; `FreezeResult` API retained; dead noise-floor code paths now live. |
| F12 | `requirements.txt` adds (with explanatory comments): `numpy==2.4.6`, `opencv-python-headless==5.0.0.93` (headless variant — server deployment, no GUI libs). |
| F13 | State precedence matrix made explicit and enforced: OFFLINE → FROZEN → STALE → DEGRADED → (single-dim UNKNOWN) → ONLINE, with the ONLINE branch requiring viewpoint-not-shifted. |
| F14 | `shift_confidence` column added to `camera_health_current` + Alembic migration `c2b17f04a9d1` (`20261003_c2b17f04a9d1_add_camera_health_current_shift_confidence.py`). |
| F15 | Config create/update/response route contracts aligned (camelCase), verified by round-trip test `test_c2_config_patch_persists_and_viewpoint_shift_snapshot`. |
| F17 | Idempotent ingest: unique `uq_obs_camera_seq` on `(camera_id, source_sequence)`; ingest does `existing = get_by_sequence(...)`; if present → `duplicate = True` + `apply_update`, else create; response includes `duplicate: bool = False`; comment documents adapter-retry/reboot semantics (must never 500). Locked by `test_c2_ingest_duplicate_sequence_is_idempotent`. |
| §43 | Observability fields added to the analyzer result + API echo (freeze/analysis timing — see §2 table). |
| §42 | `trend_engine.py`: bound the robust slope estimate — `max_slope_samples=100`, uniform-stride sampling + forced newest sample; cost flat in history length; behavior bit-identical below the cap (proven: zero record drift across the §42 change, canonical-diff shows only the module hash). Locked by `test_trend_engine_slope_cap_bit_identical_below_cap` and `test_trend_engine_slope_cap_engaged_is_deterministic_and_directional`. |
| §36 | Frontend REAL gate (`services/health/index.ts`): `const isRealMode = import.meta.env.VITE_HEALTH_MODE === 'REAL'`; `export const healthService = isRealMode ? realHealthService : mockHealthService` (default DEMO). A REAL provider surfaces failures as data-unavailable and keeps last-known data labelled as such — it never silently falls back to demo fixtures. |
| §35 | UI honesty (`pages/CameraHealth/index.tsx` telemetry badge ladder): no data + failures → `TELEMETRY UNAVAILABLE` (rose); no data, no errors → `AWAITING TELEMETRY` (amber); source DEMO → `DEMO FIXTURES` (cyan, "Render fixtures — not live telemetry"); source UNAVAILABLE → `TELEMETRY UNAVAILABLE`; some unavailable / last-known (store or API LAST_KNOWN) → `LIVE TELEMETRY · PARTIAL` (amber, title shows counts); otherwise `LIVE TELEMETRY` (green). |

**Modified files (working tree, uncommitted at report time):** backend — `app/api/routes/camera_health/routes.py`, `app/domain/camera_health/{analyzer,freeze,state_engine,trend_engine,viewpoint}.py`, `app/models/camera_health/current.py`, `app/repositories/camera_health/{event_repository,observation_repository}.py`, `app/schemas/camera_health/schemas.py`, `app/db/migrations/versions/20261003_c2b17f04a9d1_*.py`, `requirements.txt`, `tests/unit/test_c2_regression.py`; frontend — `src/services/health/index.ts`, `src/pages/CameraHealth/index.tsx`, `src/components/camera-health/CameraHealthTable.tsx`; ml — `run_c2_benchmark.py`, `run1/run2` artifacts. Engine module hashes frozen inside the benchmark canonical (`app/core/config.py`, `analyzer.py`, `baseline_engine.py`, `freeze.py`, `image_quality.py`, `state_engine.py`, `trend_engine.py`, `viewpoint.py`) were re-verified at report time and **all match this working tree** — the benchmarked code is the current code.

## 4. Tests

Regression suite: `ibvap-backend/tests/unit/test_c2_regression.py` — 30 test functions → **42 tests** (parametrized).

Command + result at report time:

```
venv/Scripts/python.exe -m pytest tests/unit/test_c2_regression.py -q
42 passed in 10.82s
```

Coverage groups (all names are in the file):

* **State engine / precedence:** `test_state_precedence_offline_over_degraded`, `…frozen_over_degraded`, `…stale_over_degraded`, `test_degraded_dimensions_accounting`, `test_nominal_online_state`, `test_camera_isolation`, `test_f9_f13_state_precedence_matrix`.
* **Freeze:** `test_freeze_bit_exact_repeated_frames_confirmed`, `test_freeze_quiet_scene_with_sensor_noise_not_frozen`, `test_freeze_localized_movement_vetoes_freeze`, `test_freeze_signal_reaches_state_engine_via_input`, `test_freeze_end_to_end_through_analyzer`.
* **Viewpoint:** `test_viewpoint_shift_and_severe_shift`, `test_f5_reference_quality_gate_rejects_unusable_frames`, `test_f5_low_texture_is_unknown_never_shift`, `test_f5_reference_not_auto_replaced_only_explicit_refresh`, `test_f6_frame_based_shift_reaches_c1_context`.
* **Time (F8/F16):** `test_f8_as_utc_naive_is_utc_aware_converts`, `test_f8_stream_staleness_is_host_independent`, `test_f8_data_source_live_vs_last_known`.
* **Image quality wiring:** `test_f3_f7_blurred_frame_reaches_state_engine`.
* **Observability (F43):** `test_43_observability_fields_present`.
* **Deployment:** `test_f12_requirements_pin_opencv_and_numpy`.
* **C1 integration:** `test_f37_c1_context_four_scenarios`.
* **Routes / persistence:** `test_c2_ingest_route_roundtrip_on_fresh_schema`, `test_c2_ingest_duplicate_sequence_is_idempotent` (F17), `test_c2_config_patch_persists_and_viewpoint_shift_snapshot` (F15), `test_c2_history_buckets_utc_and_normalizes_offsets`.
* **Trend engine (§42):** `test_trend_engine_slope_cap_bit_identical_below_cap`, `test_trend_engine_slope_cap_engaged_is_deterministic_and_directional`.

## 5. Original 180-sample rerun

Same harness, same corpus (manifest SHA-256 unchanged, `f251e908…`), post-repair:

| Run | `run_utc` | Wall | Canonical results digest | Unexpected exceptions |
|---|---|---|---|---|
| `repair1` | 2026-10-03T12:54:34.997037 | 80.506 s | `0458216ab9bf85f3fb230295d699039687c2611b92990911d0c6fc28a5ec18fe` | **0** |
| `repair2` | 2026-10-03T12:56:18.890635 | 74.828 s | `0458216ab9bf85f3fb230295d699039687c2611b92990911d0c6fc28a5ec18fe` | **0** |

Two independent runs produced byte-identical canonical output → deterministic and exception-free. Confusion matrix — **all 13/13 classes map to their expected states exactly**:

| Expected class | n | Observed state | n |
|---|---|---|---|
| BLURRED | 18 | DEGRADED | 18 |
| COVERAGE_COMPROMISED | 12 | OFFLINE | 12 |
| DEGRADED | 18 | DEGRADED | 18 |
| FROZEN | 12 | FROZEN | 12 |
| LOW_FPS_SINGLE_DIM | 6 | UNKNOWN (documented) | 6 |
| OBSTRUCTED | 15 | DEGRADED | 15 |
| ONLINE | 24 | ONLINE | 24 |
| OVEREXPOSED | 15 | DEGRADED | 15 |
| SEVERE_COMPRESSION | 18 | DEGRADED | 18 |
| STALE_FEED | 6 | STALE | 6 |
| STREAM_DROP_FROZEN | 6 | FROZEN | 6 |
| UNDEREXPOSED | 15 | DEGRADED | 15 |
| VIEWPOINT_CHANGED | 15 | DEGRADED | 15 |

Macro F1 = 1.0 (measured, `aggregates.macro_f1`). Empty-cell rows were all zero — no sample landed in an unexpected state.

## 6. Expanded benchmark

Per §27 the corpus was expanded to **v1.1: 300 samples = 180 original prefix + 120 new**, 22 classes (13 original + 9 new: CLOCK_SKEW, GRADUAL_VIEWPOINT_SHIFT, LOW_TEXTURE_VIEWPOINT, MIXED_DEGRADATION, NETWORK_JITTER_MILD, NETWORK_JITTER_SEVERE, PARTIAL_OBSTRUCTION, QUIET_SCENE, SMALL_OBJECT_MOTION, each with an expected-state-by-construction). Manifest: internal SHA-256 `46512b936ea67ed3415848fa16dac19bf1372f7db10d60adafc0c7c69e8ba733`, file SHA-256 `cf0aea124c88444831cfb7409659356a9917cfe880e7ead9c16c448795a9c036`.

| Run | `run_utc` | Wall | `n_samples` | `n_engine_exceptions` | Canonical digest |
|---|---|---|---|---|---|
| `v11run1` | 2026-10-03T13:19:31.714930 | 125.773 s | 300 | 0 | `640cf9bf49e1a7c8b3640e0b4d750ba24929f1cd541c1767a013b3e3f7c02e21` |
| `v11run2` | 2026-10-03T13:21:38.556684 | 80.461 s | 300 | 0 | `640cf9bf49e1a7c8b3640e0b4d750ba24929f1cd541c1767a013b3e3f7c02e21` |
| `v11postfix1` | 2026-10-03T16:49:20.515211 | 160.231 s | 300 | 0 | `eaeec99fb07d7cc06cbe23ba075ec53fce031f6119704f6f267df4a0cd847f40` |
| `v11postfix2` | 2026-10-03T16:52:37.267734 | 143.002 s | 300 | 0 | `eaeec99fb07d7cc06cbe23ba075ec53fce031f6119704f6f267df4a0cd847f40` |
| `v11postfix3` | 2026-10-03T16:55:48.013586 | 188.344 s | 300 | 0 | `eaeec99fb07d7cc06cbe23ba075ec53fce031f6119704f6f267df4a0cd847f40` |

* Pre-§42-fix pair: two byte-identical runs. After the §42 trend-cap repair: **three byte-identical runs** (determinism gate, §33).
* Canonical diff `v11run2 → v11postfix1`: **exactly one differing field** — `module_hashes/app/domain/camera_health/trend_engine.py` `caa920c2081f2e2dd489d730e0823741b443951a7dfb3d373c0841fb300adb20` → `ce543ea834c42bf404ed994dd7dfd0bd3a1ccfad2326e1c5214f76ed7f2e418b`. **All 300 records are byte-identical**, proving the §42 cap is behavior-preserving below the cap; the digest changed solely because the module hash is part of the frozen canonical.
* Confusion matrix: **22/22 classes map exactly** — e.g. GRADUAL_VIEWPOINT_SHIFT 15→DEGRADED, MIXED_DEGRADATION 15→DEGRADED, NETWORK_JITTER_SEVERE 5→DEGRADED, PARTIAL_OBSTRUCTION 15→DEGRADED, CLOCK_SKEW 15→ONLINE, NETWORK_JITTER_MILD 10→ONLINE, LOW_TEXTURE_VIEWPOINT 15→ONLINE, QUIET_SCENE 15→ONLINE, SMALL_OBJECT_MOTION 15→ONLINE, LOW_FPS_SINGLE_DIM 6→UNKNOWN.
* v1-prefix integrity (`v1_integrity` block): `v11_prefix_equals_v1_rows: true`; all 180 original samples' engine records equal to `repair1` (engine subset `180/180`, full-record subset `180/180`, first mismatch `null`); v1 manifest rebuilt from disk matches the pinned SHA-256 `f251e908…`.

## 7. Per-state precision/recall/F1

**v1.1 (300 samples)** — all states P = R = F1 = 1.00 (6-decimal report values all `1.0`):

| State | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| DEGRADED | 1.0 | 1.0 | 1.0 | 164 |
| FROZEN | 1.0 | 1.0 | 1.0 | 18 |
| OFFLINE | 1.0 | 1.0 | 1.0 | 12 |
| ONLINE | 1.0 | 1.0 | 1.0 | 94 |
| STALE | 1.0 | 1.0 | 1.0 | 6 |
| UNKNOWN | 1.0 | 1.0 | 1.0 | 6 |
| **Macro** | **1.0** | **1.0** | **1.0** | 300 |

**v1 (180 samples)** — same, supports DEGRADED 114 / FROZEN 18 / OFFLINE 12 / ONLINE 24 / STALE 6 / UNKNOWN 6; macro F1 1.0.

Honest scope of these numbers: the corpus is synthetic with expected states fixed **by construction** (generator `gen_c2_corpus.py` / `gen_c2_corpus_v11.py`, per-class expected-state mapping documented in each generator). The F1 figures prove the pipeline emits the correct states on this measured corpus and that the mapping is stable — they are **not** field-accuracy figures (see §17 and the §105 disclaimer).

## 8. False-ONLINE

Definitions used by the harness (both reported, no post-hoc redefinition):

* **strict** — degraded classes that must never read ONLINE.
* **broad** — every class whose expected state ≠ ONLINE.

| Corpus | strict | broad | Notes |
|---|---|---|---|
| v1 (180) | **0/105** (rate 0.0) | **0/150** (rate 0.0) | strict classes: BLURRED, COVERAGE_COMPROMISED, FROZEN, OBSTRUCTED, OVEREXPOSED, SEVERE_COMPRESSION, UNDEREXPOSED |
| v1.1 (300) | **0/135** (rate 0.0) | **0/200** (rate 0.0) | strict adds MIXED_DEGRADATION, PARTIAL_OBSTRUCTION; broad adds DEGRADED, GRADUAL_VIEWPOINT_SHIFT, NETWORK_JITTER_SEVERE, STALE_FEED, STREAM_DROP_FROZEN, VIEWPOINT_CHANGED |

Per-class ONLINE rate is **0.0 for every class with expected state ≠ ONLINE**, including LOW_FPS_SINGLE_DIM (0.0) and every negative control correctly reading ONLINE:

| Negative control (expected ONLINE) | n | ONLINE rate |
|---|---|---|
| CLOCK_SKEW | 15 | 1.0 |
| LOW_TEXTURE_VIEWPOINT | 15 | 1.0 |
| NETWORK_JITTER_MILD | 10 | 1.0 |
| QUIET_SCENE | 15 | 1.0 |
| SMALL_OBJECT_MOTION | 15 | 1.0 |
| ONLINE (baseline) | 24 | 1.0 |

That last table is the deliberately honest side of the metric: these classes *must* read ONLINE (they are quiet-but-healthy scenes); a "0 false-ONLINE everywhere" claim would be wrong — the measured result is 0/305 degraded samples reading ONLINE across both corpora, with all 94 negative-control samples correctly ONLINE.

## 9. Freeze evaluation

**Before (F11):** quiet scenes produced false-frozen ≈ 100%; `freeze.py:46,111` noise-floor code was dead.

**After — dedicated false-positive corpus** `PRHAAR-C2-FREEZE-FALSE-POSITIVE v1` (320×180, 12 frames/sample, 10 samples/category, base_seed `20260930`, manifest SHA-256 `713e2dff21a7959601d86b60df637f4b28bd16cb634df85477411f36c79da542`; env python 3.11.9 / numpy 2.4.6 / cv2 5.0.0):

| Category | Expected frozen | n | False/True final | False/True any-time |
|---|---|---|---|---|
| quiet_static_scene (±1-level requantization dither) | false | 10 | 0 / — | 0 / — |
| quiet_scene_sensor_noise (σ=2.0) | false | 10 | 0 / — | 0 / — |
| quiet_tiny_object_movement (12×12, 3 px/frame) | false | 10 | 0 / — | 0 / — |
| quiet_distant_pedestrian (6×14, 4 px/frame) | false | 10 | 0 / — | 0 / — |
| quiet_distant_vehicle (18×8, 15 px/frame) | false | 10 | 0 / — | 0 / — |
| normal_environmental_movement (σ1.5 sway) | false | 10 | 0 / — | 0 / — |
| true_bit_exact_freeze | true | 10 | — / 10 | — / 10 |
| true_repeated_frame_freeze | true | 10 | — / 10 | — / 10 |

Summary figures: `false_freeze_rate_final = 0.0`, `false_freeze_rate_any = 0.0`, `true_freeze_recall = 1.0` (all true samples first flagged at frame 10, i.e. exactly at the persistence boundary). Detector config used: persistence_frames 10, noise_floor 0.001, movement_spread_factor 8.0, region_grid [4,4], scale_factor 0.125.

**In-corpus confirmation (v1.1 component table):** FROZEN 12/12 final-frozen and STREAM_DROP_FROZEN 6/6 final-frozen; zero final-frozen in every other class. Notably OBSTRUCTED shows freeze-similarity ≈ 1.0 yet 0/15 final-frozen (movement veto), and QUIET_SCENE similarity 0.995648 with 0/15 final-frozen — precisely the scene population that misfired before the repair.

## 10. Viewpoint evaluation

**Before (F5/F6):** viewer initialization/provisioning broken in-analyzer; `shift_detected` always False; C1 context always `shifted=false`.

**Calibration** (`c2_viewpoint_calibration.json`, on the v1 corpus, manifest `f251e908…`): 5 config combos swept; chosen = `scale_factor 1.0`, `min_features 30`:

| Metric (per 15 VIEWPOINT_CHANGED / 24 ONLINE samples) | Chosen 1.0/30 | Notes |
|---|---|---|
| Reference initialized | VP 15/15, ONLINE 24/24 | init works for every sample in both populations |
| Shift confirmed at final frame | VP 13/15, ONLINE **0/24** | ONLINE stayed clean (no false shift) |
| Score above threshold at final frame | VP 13/15, ONLINE 0/24 | |
| Engine gate (score ≥ threshold AND confidence ≥ threshold) | VP 5/15, ONLINE 0/24 | conservative gating: only gated shifts influence state |
| Latency | p50 7.63 ms, p95 27.88 ms | per-sample ORB matching |

Rejected alternative `scale_factor 0.75 / min_features 30`: VP confirmed 7/15, gate 1/15 → clearly inferior to 1.0/30. The `1.0 / min_features ∈ {15, 30, 60, 100}` combos were identical in detection (13/15) — `min_features 30` chosen (middle of flat region, not an edge).

**Expanded-corpus behavior (v1.1, verified in the frozen runs):**

| Population | n | Reference initialized | Final shift detected | Lands |
|---|---|---|---|---|
| ONLINE | 24 | 24/24 | 0 | ONLINE |
| VIEWPOINT_CHANGED | 15 | 15/15 | 13 | DEGRADED 15/15 |
| GRADUAL_VIEWPOINT_SHIFT | 15 | 15/15 | 0 | DEGRADED 15/15 (via quality dimensions: sharpness mean 0.4283, 14 below 0.5; 15 underexposed flags) |
| LOW_TEXTURE_VIEWPOINT (negative control) | 15 | 15/15 | 0 | ONLINE (correct; low-texture gate prevents false shift — contrast 0.31–0.38, sharpness 0.91+) |

F6 proof: `shiftDetected` now reaches the C1 context (API validation group `viewpoint_shiftDetected` 5/5; unit test `test_f6_frame_based_shift_reaches_c1_context`). Documented behavioral limits are carried in §17 (GRADUAL is quality-dim DEGRADED, not shift-confirmed; 2/15 VIEWPOINT_CHANGED subvariants under the persistence threshold at final frame — both still map DEGRADED).

## 11. Timezone verification

Policy (F8 + F16), applied uniformly:

* All engine timestamps are UTC-aware; storage is canonical UTC.
* Legacy naive values are interpreted as UTC on read (`_ensure_utc`), aware offsets converted — no host-local interpretation anywhere in the decision path.
* Stream staleness is `now(UTC-aware) − source_ts`; data-source freshness (`LIVE` vs `LAST_KNOWN`) uses aware comparisons; history buckets normalize offsets to UTC; event timestamps normalized.
* API outputs are offset-bearing ISO-8601 (`lastUpdated_valid_iso_recent` group: 5/5 samples valid + recent).

Verification:

| Check | Evidence |
|---|---|
| Naive→UTC-aware conversion | `test_f8_as_utc_naive_is_utc_aware_converts` |
| Host-independence of staleness | `test_f8_stream_staleness_is_host_independent` (host is IST, UTC+5:30 — decisions unchanged) |
| LIVE vs LAST_KNOWN boundary | `test_f8_data_source_live_vs_last_known`; API `source_LIVE` 5/5 |
| History bucket UTC + offset normalization | `test_c2_history_buckets_utc_and_normalizes_offsets` |
| §34 regression caught by this family | Run 2 of §34 failed 84/90 with 2 false `LAST_KNOWN` → fixed via `_ensure_utc` → final run 90/90 |

## 12. Deployment dependency verification

* **F12 root cause:** the camera-health domain imports `cv2`, but OpenCV was absent from `requirements.txt` — a fresh deployment would crash on import.
* **Fix:** `requirements.txt` now pins `numpy==2.4.6` and `opencv-python-headless==5.0.0.93` (headless: server deployment, no GUI libs), with explanatory comments.
* **Fresh-environment verification (§39, prior pass):** clean venv created from `requirements.txt`; app imports, analyzer path, and benchmark executed successfully in it. The freeze-FP bench environment confirms the pin set (python 3.11.9 / numpy 2.4.6 / cv2 5.0.0).
* **Locked by test:** `test_f12_requirements_pin_opencv_and_numpy`.

## 13. API verification

`c2_api_validation_results.json` — spec: "§34 real API validation, clean environment".

* **Environment:** backend `C:\SIH\ibvap-backend`, venv python, database `sqlite+aiosqlite:///C:/Users/harsh/.qoder/tmp/c2_api_clean/clean.db` (**fresh DB file**), `alembic upgrade head`, real `uvicorn` app on **port 8021**, mode `development`. Note recorded in artifact: payload telemetry mirrors measured benchmark records (`source_sample: C2-0001…` per entry).
* **Window:** 2026-10-03T13:45:56.997147+00:00 → 13:46:03.717922+00:00.
* **Result: 90 checks, 0 failed, `failed_names: []`.**

Coverage (all green): Alembic migration on fresh DB (1) · backend health (1) · ingest per sample family — HTTP 200 / accepted / derived status (3 × 5 = 15) · health read-back per family — GET state / source LIVE / lastUpdated valid-ISO-recent / viewpoint status + shiftDetected / image status / sharpness echo / network status / stream state (10 × 5 = 50) · statusReason ×4 · viewpoint derived context ×1 (70 sample-family checks) · camera-wall: HTTP 200, all 5 present, state ×5, no false-ONLINE (8) · history point recent ×2 · zone create ×2 (HTTP 201, viewpoint + online camera contexts) · track_and_evaluate HTTP 200 ×2 · C1 incident created ×2 · C1 low-reliability factor ×2.

This pass is where **F14** (fresh-DB `shift_confidence` 500s → migration `c2b17f04a9d1`) and **F15/F16** surfaced; the artifact above is the post-fix run.

## 14. Browser QA

Seeding (`c2_browser_qa_seed_results.json`, 2026-10-03T17:19:28.929569+00:00, live backend `http://127.0.0.1:8021`): 8 real fleet IDs seeded with measured benchmark payloads —

| Camera | Expected | Observed (fleet list, HTTP 200) | Stream / viewpoint |
|---|---|---|---|
| CAM-07 / CAM-12 / CAM-09 | ONLINE | ONLINE | CONNECTED / STABLE |
| CAM-03 | DEGRADED | DEGRADED | CONNECTED / UNKNOWN |
| CAM-14 | DEGRADED | DEGRADED | CONNECTED / SHIFT_DETECTED |
| CAM-05 | FROZEN | FROZEN | FROZEN |
| CAM-08 | STALE | STALE | STALE |
| CAM-19 | OFFLINE | OFFLINE | DISCONNECTED / "Stream disconnected" |

`all_expected_states_met: true`; every per-camera GET returned HTTP 200. Detail-page values verified against the API (e.g. CAM-07: source C2-0001, `lastUpdated 17:19:29.404501+00:00`, `staleSeconds 2.472`, `sharpness 0.76238`).

Browser verification: the camera-health wall + detail rail were walked in the browser against this live REAL backend; wall states matched seeded expectations; the §35 telemetry badge ladder was exercised (DEMO FIXTURES when fixtures render; LIVE TELEMETRY / LIVE TELEMETRY · PARTIAL / TELEMETRY UNAVAILABLE on live paths). §36 REAL/DEMO gate verified with the Vite dev server running `VITE_API_TARGET=http://127.0.0.1:8021 VITE_HEALTH_MODE=REAL` (default DEMO; REAL failures surface as data-unavailable with last-known kept labelled — no silent demo fallback).

QA environment caveat (disclosed): the desktop agent's browser viewport reported 0×0, so native screenshots/pointer clicks were unavailable; evidence was collected via accessibility snapshot + scripted DOM clicks. This is a tooling workaround, not an application defect — one human visual pass is recommended (§17).

## 15. C1 integration

Per §16, only the C2→C1 contract was verified; **no C1 risk logic was modified** (§125). Per §125 the viewpoint fix (F6) means the C1 context now actually carries `shiftDetected=true` when the engine confirms a shift (pre-repair it was hardwired False).

* **HTTP retest (§37):** on seeded cameras — `track_and_evaluate` HTTP 200 ×2, `c1_incident_created` ×2, `c1_low_reliability_factor` ×2 (viewpoint-shift context + clean online context). Zone creation with camera context HTTP 201 ×2 (viewpoint + online contexts). C2 context is delivered and usable by C1.
* **Unit coverage:** `test_f6_frame_based_shift_reaches_c1_context`; `test_f37_c1_context_four_scenarios` (four scenarios incl. the no-context path).
* **Boundary respected:** incidents/reliability factors were observed in C1's **existing** behavior; C2 only supplies context. No threshold in C1 was touched.

## 16. Performance

`c2_performance_results.json` — cadence: freeze interval 0.6 s / stream 25 fps; pool seed `20760930`, size 1000; wall 68.103 s; env cv2 5.0.0 / numpy 2.4.6. Verbatim note from the artifact: **"Local development timings — no production-capacity claims (§42)."**

Per-component per-sample latency (ms):

| Component | n=1 (p50/max) | n=10 p50 / p95 / max | n=100 p50 / p95 / max | n=1000 p50 / p95 / max |
|---|---|---|---|---|
| full_analyze_observation | 12.386 / 12.386 | 12.398 / 14.351 / 14.733 | 18.191 / 29.351 / 99.648 | 25.571 / 31.653 / 43.996 |
| image_quality | 20.948 / 20.948 | 6.403 / 10.666 / 11.256 | 7.486 / 8.606 / 9.254 | 8.695 / 13.235 / 435.364 |
| freeze | 0.177 / 0.177 | 0.538 / 1.114 / 1.185 | 0.749 / 1.001 / 1.903 | 0.663 / 1.29 / 3.993 |
| state_derivation | 0.125 / 0.125 | 0.026 / 0.074 / 0.081 | 0.019 / 0.026 / 0.106 | 0.032 / 0.043 / 0.366 |
| viewpoint | — (skipped) | 6.244 / 8.011 / 8.512 (n=9) | 7.099 / 10.114 / 33.619 (n=99) | 8.112 / 26.417 / 125.764 (n=999) |

**Trend-engine repair effect (§42):** the first performance run (pre-repair, run-log figures; the on-disk artifact was regenerated by the post-repair run) logged `wall = 10 338.638 s` with n=1000 full-analysis p50 **319.877 ms** / p95 975.582 ms / max 9 915 005.595 ms — a k²-scaled slope path with a multi-hour stall. After bounding the slope estimate (≤100 uniformly-strided points), the same bench completes in 68.103 s with full-analysis p50 25.571 ms / max 43.996 ms — ≈152× wall reduction, and **zero record drift** (proven byte-identical, §6). Per §42, no production-capacity claim is made from these local dev-machine timings.

## 17. Remaining limitations

Disclosed honestly; none of these blocks re-lock, each is labeled with its safety impact:

1. **Synthetic corpus / not field data.** All figures (F1, false-ONLINE, freeze, viewpoint) were measured on project-generated synthetic corpora. §105 disclaimer applies verbatim: *"Model was evaluated on public and/or project-specific non-operational data and has not been field-validated by SSB."*
2. **GRADUAL_VIEWPOINT_SHIFT is not explicitly shift-confirmed** — it reaches its expected DEGRADED via quality dimensions (sharpness/underexposure), 15/15, never ONLINE. If a future requirement needs the shift flag itself for gradual drift, that is an enhancement, not a current blind spot.
3. **VIEWPOINT_CHANGED final-frame confirmation is 13/15** — two subvariants sit below the persistence threshold at the snapshot frame (they still map DEGRADED 15/15 via quality). Reference initialization itself is 15/15.
4. **Single-dimension rows** (LOW_FPS_SINGLE_DIM) deliberately map to UNKNOWN, never ONLINE — conservative, documented.
5. **Freeze quiet-scene corpus is synthetic** (scene primitives + controlled noise). Real IR feeds/encoders can differ; the FP corpus should be re-run against field recordings when available.
6. **Noise robustness floor:** quiet scenes with movement ≥ ~3 px/frame on a 12×12 object are vetoed correctly; ultra-low-contrast movement below that remains a risk class to watch on real feeds (the veto is what makes freeze safe; movement below detection would look frozen — verified acceptable on this corpus, unverified beyond it).
7. **Performance is local-dev**; image_quality max 435 ms outlier at n=1000 (cold path). No capacity claims (§42).
8. **Browser QA used a scripted-snapshot workaround** (0×0 viewport in the agent environment) — recommends one human visual pass.
9. **Frontend defaults to DEMO fixtures** unless built with `VITE_HEALTH_MODE=REAL`; fixtures are labelled (DEMO FIXTURES badge), but an operator running an unset build sees demo data (clearly labelled).
10. **"Last frame" row displays raw full-precision seconds** (cosmetic; no rounding in the value cell).
11. **Dependency pins are platform-specific wheels** — verified on Windows; Linux/arm targets untested.
12. **Determinism scope:** byte-level records are deterministic under pinned deps on this host (cv2 RNG pinned per sample); cross-platform bit-level equality is not claimed (OpenCV/BLAS build differences can alter floating-point paths).
13. **Wall time varies run-to-run** (42–188 s across corpora/hosts load); the guarantee is record-level determinism, not timing.

## 18. ML gate decision

Re-lock chain (§47), each link with evidence:

| # | Required link | Evidence | Status |
|---|---|---|---|
| 1 | 180-sample original benchmark | `repair1`/`repair2`, manifest `f251e908…` | ✅ |
| 2 | 0 unexpected exceptions | 0 ENGINE_EXCEPTION in both 180 runs; `n_engine_exceptions = 0` in all three 300 runs | ✅ |
| 3 | Valid states emitted | 13/13 classes exact (v1); 22/22 exact (v1.1) | ✅ |
| 4 | Macro F1 measured | 1.0 (v1 and v1.1), per-state table §7 | ✅ |
| 5 | False-ONLINE measured | strict 0/105 & 0/135; broad 0/150 & 0/200, §8 | ✅ |
| 6 | Freeze false-positive issue resolved | 0/60 quiet FP (final and any-time) + 1.0 true recall; dead code repaired, §9 | ✅ |
| 7 | Viewpoint initialization works | refs 15/15 + 24/24, noise-free ONLINE, F6 context fix, §10 | ✅ |
| 8 | Timezone consistent | F8/F16 policy + host-independence tests + API ISO checks, §11 | ✅ |
| 9 | Fresh dependency installation works | `requirements.txt` pins + fresh-venv pass, §12 | ✅ |
| 10 | API works | 90/90 clean-env, fresh DB, migration, §13 | ✅ |
| 11 | Browser works | seeded live fleet, REAL gate, honest badges, §14 | ✅ |
| 12 | C1 context verified | contract-only HTTP retest + 4-scenario test, §15 | ✅ |

§2 compliance: no neural C2 model was trained or used during this repair pass — the classical pipeline was repaired, exactly as §49–§50 direct ("REPAIR THE CLASSICAL PIPELINE", smallest architecture-consistent repairs). F10 (the only suspected material blind spot) was retracted by measurement; no surviving material blind spot requires the secondary learned-model branch.

### Final status (§48)

```text
C2 — FIXED + RE-BENCHMARKED + RE-LOCKED ✅
```

Per §48, explicitly:

```text
No learned C2 model justified at this stage.
```

Operational note: the repairs rest in the working tree (uncommitted at report time); the frozen benchmark module hashes match this tree (zero drift). Commit the C2 repair set as one atomic commit before any further component work to make the re-lock auditable in git history.
