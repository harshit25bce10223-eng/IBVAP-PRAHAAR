# C2 — Camera Health AI/ML Report

`C2_CAMERA_HEALTH_AI_REPORT.md` — PRHAAR Global AI/ML Phase, §107 deliverable
Component: C2 (Camera Health Monitoring) — spec §68 classes, §67 classical-first mandate
Benchmark executed: 2026-10-03, backend venv (Python 3.11, cv2 5.0.0, numpy 2.4.6), IST host (UTC+5:30)
Engine code modified: **NO** (§125 respected — benchmark is a read-only consumer; the two harness
adaptations to locked-code behaviour are documented in §3.4)

---

## 0. Verdict (read first)

**The wired C2 pipeline cannot complete a single observation.** Across the full 180-sample corpus,
`CameraHealthAnalyzer.analyze_observation()` raised an exception on **180/180 samples** —
156 × `KeyError: 'reason'` (analyzer.py:264) and 24 ×
`TypeError: HealthAnalysisResult.__init__() got an unexpected keyword argument 'network_reason'`
(analyzer.py:246). The live API route `app/api/routes/camera_health/routes.py:513` calls exactly
this entry point, so the camera-health observation endpoint fails on essentially every real
observation today.

Consequences, stated plainly per §117/§118:

- **No accuracy percentage is claimed.** Per-state precision/recall/F1 are 0 or undefined because
  the orchestrator never produces a state (§5). Forcing a 95% figure here would be fabrication.
- The classical CV components underneath (image quality, freeze, viewpoint) are individually
  functional and, where measurable, respond correctly to their target degradations (§6).
  The dominant failure class is **integration/wiring defects in locked orchestrator code**, not
  algorithmic incapacity — therefore §67's learned-model escalation is **not triggered** (§8).
- All 13 defects are catalogued with file:line evidence in §7. Fixes require touching locked
  C2 components; per §125 that decision is escalated, not taken silently.

**Field-validation disclaimer (§105, verbatim):** *Model was evaluated on public and/or
project-specific non-operational data and has not been field-validated by SSB.* No model was
trained for this component at all (§67 classical-first); the benchmark corpus is fully synthetic,
deterministically generated in-repo, and contains no operational or SSB data of any kind.

---

## 1. Scope and spec compliance

| Spec clause | Status | Where |
|---|---|---|
| §67 classical-CV benchmark first | Done | §2, §4, §5, §6 — classical components benchmarked end-to-end and per-component; no neural camera-health model trained |
| §68 ten health classes | Done | All ten benchmarked: ONLINE, DEGRADED, FROZEN, BLURRED, OBSTRUCTED, UNDEREXPOSED, OVEREXPOSED, SEVERE_COMPRESSION, VIEWPOINT_CHANGED, COVERAGE_COMPROMISED |
| §107 report sections | Done | Classical benchmark §4–§6; learned-model justification §8; per-state P/R/F1 §5; false-ONLINE §5.3; camera degradation analysis §6 |
| §105 field-validation disclaimer | Done | Verbatim in §0 |
| §117/§118 no forced 95% | Done | §0, §5.4 — impossibility documented, not hidden |
| §125 locked components untouched | Done | Zero edits under `app/`; harness adaptations documented §3.4 |
| §9/§83 corpus integrity | Done | Deterministic seeded generator; manifest SHA-256 §2.3; frozen corpus; double-run canonical hash match §3.3 |

Supplementary state rows (not §68 classes, added by the corpus for coverage): STALE_FEED,
STREAM_DROP_FROZEN, LOW_FPS_SINGLE_DIM — counted separately where relevant (§5).

---

## 2. Corpus

### 2.1 Generator

`ml/c2_camera_health/benchmark/gen_c2_corpus.py` — deterministic, seeded
(`BASE_SEED = 20260930`), no external assets, no network access. Frames are synthetic border-watch
scenes rendered at 320×180 (sky/ground gradient, fence posts, wires, bushes, guard hut, speckle),
then per-class degradations are applied: Gaussian blur (odd kernels), near-black occluding
rectangle (cover fraction 0.82–0.90), exposure scaling, JPEG re-encode (quality 3/5/8),
viewpoint warp (rotation-matrix + `warpAffine` `BORDER_CONSTANT`), bit-exact frame copies for
frozen, and Gaussian sensor noise (σ). Telemetry recipes (latency, packet loss, FPS, frame-drop,
heartbeat age, source age) accompany every sample. `cv2.setRNGSeed` is pinned per sample in the
harness for RANSAC reproducibility.

### 2.2 Composition (180 samples, sequence length 12; viewpoint sequences 8)

| Class | n | Sub-variants | Expected state |
|---|---|---|---|
| ONLINE | 24 | sensor σ2 / σ3 | ONLINE |
| DEGRADED | 18 | blur+net / low-FPS+underexposed / viewpoint-injected+net | DEGRADED |
| FROZEN | 12 | bit-exact frame copies | FROZEN |
| BLURRED | 18 | mild (k 11–19) / heavy (k 21–41) | DEGRADED |
| OBSTRUCTED | 15 | cover 0.82–0.90, shade 8–25 | DEGRADED |
| UNDEREXPOSED | 15 | factor 0.03–0.08 | DEGRADED |
| OVEREXPOSED | 15 | factor 7–11 | DEGRADED |
| SEVERE_COMPRESSION | 18 | JPEG q 3 / 5 / 8 | DEGRADED |
| VIEWPOINT_CHANGED | 15 | moderate (tx 55–95 px, rot 0.5–3°, zoom 1.0–1.06) / severe (tx 110–160 px, rot 4–8°, zoom 1.12–1.25); frame 0 unwarped as reference | DEGRADED |
| COVERAGE_COMPROMISED | 12 | disconnected (9) / disconnected + stale heartbeat (3) | OFFLINE |
| STALE_FEED (suppl.) | 6 | source age 40–55.9 s | STALE |
| STREAM_DROP_FROZEN (suppl.) | 6 | frame-drop rate 0.55–0.90 | FROZEN |
| LOW_FPS_SINGLE_DIM (suppl.) | 6 | observed FPS 8–11.5 | UNKNOWN |

### 2.3 Integrity

- Manifest: `benchmark/c2_corpus_manifest_v1.json`
- **manifest_sha256 = `f251e908cd2f397f0793fe043032b39e9e9c99d5b288260f382a1d2fc602e30a`**
- Corpus is frozen for this benchmark round (§83). No dataset counts beyond these are claimed (§9).

---

## 3. Method and determinism

### 3.1 Evaluation layers

1. **Component level** — each locked detector (`ImageQualityAnalyzer`, `FreezeDetector`,
   `ViewpointDetector`) fed corpus frames directly through its public interface.
2. **Orchestrator level** — `CameraHealthAnalyzer.analyze_observation()` (the production entry
   point used by routes.py:513) fed the same frames plus telemetry.
3. **Determinism check** — two cross-process runs; canonical SHA-256 over the deterministic
   record subset must match.

### 3.2 Locked engine files hashed into the results

| SHA-256 (prefix) | File |
|---|---|
| `bef246a2f72dd767` | `app/core/config.py` |
| `bf6429ce48af29a3` | `app/domain/camera_health/analyzer.py` |
| `09c2efe87fa273e0` | `app/domain/camera_health/baseline_engine.py` |
| `832da9e18ab54f9f` | `app/domain/camera_health/freeze.py` |
| `5dff8afbbdc16fe0` | `app/domain/camera_health/image_quality.py` |
| `c34c74c1451b4b6c` | `app/domain/camera_health/state_engine.py` |
| `a9c305cb61e08c22` | `app/domain/camera_health/trend_engine.py` |
| `c05a4953c0a3fd08` | `app/domain/camera_health/viewpoint.py` |

### 3.3 Double-run canonical verification — PASS

- run1 `canonical_results_sha256` = **`7f59116b4f7ead41f6a1fc3375913528875c141354f062390aacedd81f0dc15c`**
- run2 `canonical_results_sha256` = **`7f59116b4f7ead41f6a1fc3375913528875c141354f062390aacedd81f0dc15c`**
- Identical across independent processes; per-sample outcome mix stable at 156 KeyError + 24
  TypeError. The canonical subset excludes `status_reason` (embeds wall-clock-derived seconds);
  the full payload retains it.

### 3.4 Harness adaptations to locked-code behaviour (§125 — harness adapts, engine untouched)

1. **Naive-UTC per-sample wall clock.** The locked `trend_engine` compares sample timestamps
   against naive `datetime.now()` (it is not tz-aware; aware timestamps crash it), while the
   state engine normalizes naive source timestamps to UTC and compares against
   `datetime.now(timezone.utc)`. On this IST host that means the harness must feed the naive
   representation of the *current UTC* wall clock, freshly per sample
   (`datetime.now(timezone.utc).replace(tzinfo=None)`). A single global base timestamp was
   measured to flip 16/180 borderline samples across STALE thresholds (run-position-dependent
   frame age) and broke cross-run determinism — the per-sample fix restored an exact canonical
   match. This is a harness-side accommodation of locked tz-naive code, recorded as finding F8.
2. **Exceptions recorded as outcomes.** Locked-code crashes are caught at the harness boundary and
   recorded as `ENGINE_EXCEPTION` results (with the exception class and message) rather than
   silently dropped or retried. Crash sites were additionally verified by direct reproduction
   with full tracebacks (§7).

---

## 4. Classical CV benchmark — end-to-end result

### 4.1 What the orchestrator did on every sample

`analyze_observation` builds `CameraHealthInput` at analyzer.py:152 **before** the frame path,
runs the frame path (image quality / viewpoint / freeze on the local variables), then calls
`derive_state(input_data)` at analyzer.py:203 with the **original** input object. Runtime probe
(`benchmark/probe_f3_input_wiring.py`, monkeypatch capture at the state-engine boundary): after
feeding 12 real ONLINE frames through the public path, `derive_state` still received
`image=None, viewpoint=None`. The frame-derived metrics therefore never reach the state engine
(finding F3). Downstream, `_build_issues`/`_determine_operational_impact` run off
telemetry-only derived state and the result construction crashes:

- analyzer.py:246 passes `network_reason=...` to `HealthAnalysisResult`, whose dataclass has no
  such field → `TypeError`. Reached on every path where the maintenance dict has a `"reason"`
  key, i.e. whenever `overall_status ∈ {OFFLINE, FROZEN, STALE}` or the trend engine recommends
  maintenance.
- Otherwise evaluation reaches analyzer.py:264 `maintenance["reason"]` while the locked
  `_determine_maintenance` fallthrough returns `{"recommended": False}` → `KeyError: 'reason'`.

### 4.2 Outcome counts (run1 = run2)

| Outcome | Samples | Classes affected |
|---|---|---|
| `KeyError: 'reason'` (analyzer.py:264) | 156 | all except the three below |
| `TypeError: network_reason` (analyzer.py:246) | 24 | COVERAGE_COMPROMISED (12), STREAM_DROP_FROZEN (6), STALE_FEED (6) |
| Any completed observation | **0** | — |

### 4.3 Timing

Full 180-sample double evaluation (components + orchestrator + noise sweep): run1 wall ≈ 29 s,
run2 wall ≈ 29 s, single process each. Corpus materialization included.

---

## 5. Per-state precision / recall / F1 and false-ONLINE (§107)

### 5.1 Per-class table

Expected state → what the orchestrator actually produced. Every cell reads `ENGINE_EXCEPTION`;
no valid state was emitted for any sample.

| Class | n | Expected | Predicted distribution | Recall vs expected | Online rate |
|---|---|---|---|---|---|
| ONLINE | 24 | ONLINE | ENGINE_EXCEPTION ×24 | 0.00 | 0.00 |
| DEGRADED | 18 | DEGRADED | ENGINE_EXCEPTION ×18 | 0.00 | 0.00 |
| FROZEN | 12 | FROZEN | ENGINE_EXCEPTION ×12 | 0.00 | 0.00 |
| BLURRED | 18 | DEGRADED | ENGINE_EXCEPTION ×18 | 0.00 | 0.00 |
| OBSTRUCTED | 15 | DEGRADED | ENGINE_EXCEPTION ×15 | 0.00 | 0.00 |
| UNDEREXPOSED | 15 | DEGRADED | ENGINE_EXCEPTION ×15 | 0.00 | 0.00 |
| OVEREXPOSED | 15 | DEGRADED | ENGINE_EXCEPTION ×15 | 0.00 | 0.00 |
| SEVERE_COMPRESSION | 18 | DEGRADED | ENGINE_EXCEPTION ×18 | 0.00 | 0.00 |
| VIEWPOINT_CHANGED | 15 | DEGRADED | ENGINE_EXCEPTION ×15 | 0.00 | 0.00 |
| COVERAGE_COMPROMISED | 12 | OFFLINE | ENGINE_EXCEPTION ×12 | 0.00 | 0.00 |
| STALE_FEED (suppl.) | 6 | STALE | ENGINE_EXCEPTION ×6 | 0.00 | 0.00 |
| STREAM_DROP_FROZEN (suppl.) | 6 | FROZEN | ENGINE_EXCEPTION ×6 | 0.00 | 0.00 |
| LOW_FPS_SINGLE_DIM (suppl.) | 6 | UNKNOWN | ENGINE_EXCEPTION ×6 | 0.00 | 0.00 |

**Macro F1 = 0.0. Macro precision/recall = 0.0 / 0.00.** Per-state precision is undefined (zero
predictions emitted in any valid state).

### 5.2 Why these zeros are not "the model is wrong"

The zeros measure *orchestrator crash on every sample*, not classification error. The state
engine itself was probed directly (telemetry passed explicitly, bypassing the broken frame
wiring): e.g. a blur+degraded-network input derives `image_status=DEGRADED,
overall_status=DEGRADED` exactly as designed. The end-to-end number cannot be computed until
findings F1–F3 are fixed in the locked component (§7, §9).

### 5.3 False-ONLINE rate

- **Strict set** (the 7 gross-degradation classes: BLURRED, OBSTRUCTED, UNDEREXPOSED,
  OVEREXPOSED, SEVERE_COMPRESSION, FROZEN, COVERAGE_COMPROMISED): **0/105 = 0.0**
- **Broad set** (all classes except ONLINE and LOW_FPS_SINGLE_DIM): **0/150 = 0.0**

**Caveat (stated, not hidden):** 0% here is an artifact of 100% crash rate — the endpoint errors
instead of returning a state. It does **not** evidence correct rejection. A healthy camera that
crashes the route is not "safe"; it is unavailable. False-ONLINE after the F1/F2 fixes is
unmeasurable from this run and must be re-benchmarked.

### 5.4 §117/§118 statement

The 95% target is **not achievable in this benchmark round and the reason is documented, not
papered over**: the production orchestrator raises on 180/180 samples due to four locked-code
defects (F1–F3, F7). Component-level capability (§6) shows the classical CV underneath is sound
for most classes; what is missing is a working integration. Claiming any accuracy figure for the
wired pipeline today would violate the no-fabrication rules.

---

## 6. Camera degradation analysis (§107) — component-level capability

Component evaluation bypasses the orchestrator wiring and feeds corpus frames directly to the
locked detectors. This is where the classical-CV capability actually lives (§67 evidence).

### 6.1 Image quality analyzer (`image_quality.py`) — functional, thresholds marginal on obstruction

Normalized metrics per class (means over all frames of all samples in the class):

| Class | Sharpness (mean) | Sharpness < 0.5 | Brightness (mean) | < 0.1 | > 0.9 | Exposure verdicts |
|---|---|---|---|---|---|---|
| ONLINE (n=24) | 0.784 | 0/24 | 0.538 | 0 | 0 | NORMAL 24/24 |
| BLURRED (n=18) | 0.200 | 18/18 | 0.538 | 0 | 0 | NORMAL 18/18 |
| SEVERE_COMPRESSION (n=18) | 0.341 | 18/18 | 0.543 | 0 | 0 | NORMAL 18/18 |
| UNDEREXPOSED (n=15) | 0.181 | 15/15 | 0.025 | 15/15 | 0 | UNDEREXPOSED 15/15 |
| OVEREXPOSED (n=15) | 0.174 | 15/15 | 0.996 | 0 | 15/15 | OVEREXPOSED 15/15 |
| OBSTRUCTED (n=15) | 0.274 | 15/15 | 0.127 | **2/15** | 0 | NORMAL 15/15 |
| VIEWPOINT_CHANGED (n=15) | 0.386 | 14/15 | 0.412 | 0 | 0 | UNDEREXPOSED 15/15 |
| FROZEN (n=12) | 0.757 | 0/12 | 0.538 | 0 | 0 | NORMAL 12/12 |

Reading:

- **Blur and compression are captured** by the Laplacian-variance sharpness signal with a wide
  margin (0.20 / 0.34 vs ONLINE 0.78, threshold 0.5). The earlier blind-spot hypothesis for
  SEVERE_COMPRESSION (compression artefacts boosting high-frequency energy) was **retracted by
  measurement**: 18/18 samples sit below threshold.
- **Exposure classes are captured decisively** (brightness 0.025 vs 0.996, thresholds 0.1/0.9,
  and the clipping-based exposure label agrees 15/15 in both directions).
- **OBSTRUCTED is only partially captured at the engine's brightness threshold**: the occluding
  rectangle (cover 0.82–0.90 at shade 8–25/255) leaves mean brightness at 0.127 — only 2/15
  frames fall below the 0.1 DEGRADED threshold. What saves detection is sharpness (15/15 below
  0.5: the flat occluder collapses Laplacian variance). If a future fix routes only brightness
  to the state logic, obstruction becomes a blind spot; sharpness must stay in the path.
- **VIEWPOINT_CHANGED produces a secondary IQ signature** (sharpness 14/15 low; black
  `BORDER_CONSTANT` fill reads as UNDEREXPOSED 15/15). This is a side effect of the warping
  recipe, not viewpoint detection.

### 6.2 Freeze detector (`freeze.py`) — exact on frozen, near-total false-freeze on quiet scenes

- FROZEN class: **12/12** sequences reach `frozen=True` (similarity 1.0).
- ONLINE class: **0/24** false freezes (mean similarity 0.956 vs 0.995 threshold) **when a motion
  blob traverses the scene**.
- Noise sweep (quiet border scene, ONLINE content, sensor σ 1.5–6, 8 sequences per cell,
  static and with motion):

| σ | Static false-freeze | Motion false-freeze |
|---|---|---|
| 1.5 | 8/8 (1.0) | 8/8 (1.0) |
| 2.0 | 8/8 (1.0) | 8/8 (1.0) |
| 3.0 | 8/8 (1.0) | 8/8 (1.0) |
| 4.0 | 8/8 (1.0) | 8/8 (1.0) |
| 6.0 | 8/8 (1.0) | 7/8 (0.875) |

  Whole-frame normalized cross-correlation on a 40×22 thumbnail is insensitive to small moving
  objects: sensor noise alone stays under the 0.995 similarity bar almost never. At realistic
  quiet-scene noise the detector reports frozen ~100% of the time. The `noise_floor` parameter
  and `_compute_noise_level()` (freeze.py:46, freeze.py:111) that might have guarded this are
  dead code — never read anywhere in the locked tree.

  **Risk note:** this defect is latent today only because the orchestrator discards
  `freeze_result` (F4). Any fix that wires freeze detection naively converts a quiet camera
  into a permanently-"frozen" camera.

### 6.3 Viewpoint detector (`viewpoint.py`) — inoperable at locked calibration

Component evaluation called `set_reference(frames[0])` exactly as production wiring should:
**reference accepted on 0/39 sequences** (24 ONLINE + 15 VIEWPOINT_CHANGED); every `analyze()`
returned `"Detector not initialized or OpenCV unavailable"`. Root cause measured, not guessed:

| Preprocessing scale | Frame size | ORB keypoints | Required (`min_features`) |
|---|---|---|---|
| 1.0 (full) | 320×180 | 219 | 100 |
| 0.5 | 160×90 | 20–32 | 100 |
| **0.25 (locked default)** | 80×45 | **0** | 100 |

At the locked `scale_factor=0.25` the scene yields **zero** ORB keypoints; even at 4× the
resolution (0.5) the yield stays far below the locked `min_features=100`. The detector can
never initialize on low-texture border scenes at its shipped calibration — doubly broken in
production, where `set_reference` is additionally never called (F5). VIEWPOINT_CHANGED recall
at component level is therefore **unmeasurable with locked defaults**, stated as a gap rather
than scored.

---

## 7. Findings register (file:line evidence, locked tree unmodified)

| # | Finding | Evidence | Production impact |
|---|---|---|---|
| F1 | `_determine_maintenance` fallthrough returns `{"recommended": False}` without `reason`/`duration`/`impact_note`; analyzer.py:264 unconditionally subscripts `maintenance["reason"]` → `KeyError: 'reason'` | analyzer.py:264, 414; reproduced with full traceback; 156/180 samples | **Live:** observation route raises on the nominal path |
| F2 | `HealthAnalysisResult` has no `network_reason` field; analyzer.py:246 passes it → `TypeError` on every path that reaches result construction | analyzer.py:246 vs dataclass analyzer.py:30-101; 24/180 samples | **Live:** any path where maintenance dict is complete |
| F3 | `CameraHealthInput` built at analyzer.py:152 before the frame path; frame path mutates only local `image`/`viewpoint` variables; `derive_state(input_data)` at analyzer.py:203 sees `image=None, viewpoint=None` forever → engine image/viewpoint status always UNKNOWN | analyzer.py:152-203; runtime probe `probe_f3_input_wiring.py` (12 ONLINE frames → captured `image=None, viewpoint=None`) | **Critical:** even with F1/F2 fixed, classical CV output never influences health state |
| F4 | `freeze_result = self.freeze_detector.analyze(...)` at analyzer.py:193 is never consumed | analyzer.py:193 | Freeze detection is dead code end-to-end; latent false-freeze risk (§6.2) |
| F5 | `ViewpointDetector.set_reference()` is never called anywhere in `app/` | grep over `app/`; component eval 0/39 reference_set | Viewpoint detection permanently uninitialized |
| F6 | `shift_detected=...CameraHealthState.VIEWPOINT_SHIFT_DETECTED...` — that enum lives on `ViewpointStatus`, not `CameraHealthState`; `hasattr` guard makes the field **always False** | analyzer.py:254; state_engine.py enums | `get_health_context_for_component1()` permanently reports `viewpoint_shift_detected=False`, `fence_confidence_override=None`, `geometry_confidence="HIGH"` to Component 1 — even during a real shift |
| F7 | `_build_issues` reads `derived.sharpness_status` / `derived.sharpness_reason`, which do not exist on `CameraHealthDerived` → `AttributeError` | analyzer.py:320, 322 vs state_engine.py dataclass; reproduced by direct call with an image-DEGRADED derived object | Latent today only because F3 keeps image_status UNKNOWN; fires the moment F3 is fixed |
| F8 | `trend_engine` is tz-naive (crashes on aware timestamps); state engine treats naive source timestamps as UTC — on non-UTC hosts naive-local timestamps produce negative frame ages | trend_engine.py; state_engine.py `_derive_stream_health` | On this IST host, real observations built from naive-local clocks compute wrong staleness; benchmark harness feeds naive-UTC (§3.4) |
| F9 | State engine DEGRADED requires ≥2 degraded dimensions (or viewpoint SEVERE_SHIFT); single-dimension degradation collapses to UNKNOWN/ONLINE design tension | state_engine.py `_determine_overall_state` | LOW_FPS_SINGLE_DIM expected UNKNOWN — by design, but worth an explicit product decision |
| F10 | SEVERE_COMPRESSION blind spot — **retracted by measurement** (§6.1: sharpness 0.34, 18/18 below threshold) | component table §6.1 | none; documented retraction |
| F11 | Freeze detector false-freeze ≈100% on quiet scenes at σ1.5–4; `noise_floor`/`_compute_noise_level` dead code | freeze.py:46, 111; sweep §6.2 | Dangerous once F4 is fixed without recalibration |
| F12 | `cv2` absent from `requirements.txt`; only present as `opencv-python-headless 5.0.0.93` in the dev venv | requirements.txt grep (no match) | **Deployment blocker:** a fresh production install silently loses all CV health checks (every detector degrades to "OpenCV unavailable" no-ops) |
| F13 | ONLINE branch ignores viewpoint status (`stream CONNECTED and image GOOD and network STABLE` → ONLINE) | state_engine.py `_determine_overall_state` | A shifted camera with clean telemetry reports ONLINE |

## 8. Learned-model experiment — not justified (§67)

§67 permits a learned camera-health model only if "classical approach has material blind spots
AND learned approach improves the target metric". This benchmark found the opposite: where the
classical components could be measured, they separated classes with wide margins (§6.1, §6.2
frozen-detection exact). The failures are wiring and calibration defects (F1–F6, F11) that a
neural model would inherit at its interface and could not fix. **No learned experiment was run;
no model weights exist for C2.** If F1–F7 are repaired and a genuine blind spot then surfaces,
this decision can be revisited with a targeted experiment.

---

## 9. Recommendations (decisions for the maintainers — not executed, §125)

1. **Fix F1/F2** (two-line-level changes in `analyzer.py`) — unblocks the observation route;
   without this the component is down in production.
2. **Fix F3** (write frame-derived metrics back into `input_data` before `derive_state`) —
   otherwise classical CV stays invisible to health states.
3. **Re-benchmark after 1+2** — per-state P/R/F1 and false-ONLINE from this report are
   placeholders measuring crash rate; a real accuracy number requires a completed observation.
4. **Recalibrate or gate the freeze detector before wiring it (F4/F11)** — ROI-aware or
   edge-aware similarity, and activate the existing `noise_floor` machinery.
5. **Rework viewpoint initialization (F5/F6)**: call `set_reference` at provisioning and on
   officer-confirmed stable frames; revisit `scale_factor`/`min_features` (measured: 0 keypoints
   at locked 0.25 downscale); fix the `shift_detected` enum reference.
6. **Add `opencv-python-headless` to `requirements.txt` (F12)** and add the tz-naive handling
   decision for non-UTC deployments (F8).

## 10. Artifacts

| Artifact | Path | Hash / note |
|---|---|---|
| Corpus generator | `ml/c2_camera_health/benchmark/gen_c2_corpus.py` | rewritten this round after file loss; interfaces re-verified against locked tree |
| Benchmark harness | `ml/c2_camera_health/benchmark/run_c2_benchmark.py` | two documented adaptations (§3.4) |
| F3 wiring probe | `ml/c2_camera_health/benchmark/probe_f3_input_wiring.py` | runtime evidence for F3 |
| Corpus manifest | `ml/c2_camera_health/benchmark/c2_corpus_manifest_v1.json` | sha256 `f251e908…c602e30a` |
| Results run1 | `ml/c2_camera_health/benchmark/c2_benchmark_results_run1.json` | canonical sha256 `7f59116b…f0dc15c` |
| Results run2 | `ml/c2_camera_health/benchmark/c2_benchmark_results_run2.json` | canonical sha256 `7f59116b…f0dc15c` (match) |

*Benchmark environment: Windows, Python 3.11, opencv-python-headless 5.0.0.93, numpy 2.4.6,
backend venv. Benchmark wall ≈29 s per full run.*
