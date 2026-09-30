# C1 — Risk Engine AI/ML Report

`C1_RISK_AI_ML_REPORT.md` — PRHAAR Global AI/ML Phase, §106 deliverable
Component: C1 (Virtual Fence + Risk Engine) — spec lines 2099–2171
Benchmark executed: 2026-09-29, backend venv (Python 3.11), working tree at engine hashes below
Engine code modified: **NO** (§125 respected — benchmark is a read-only consumer)

---

## 1. No ML used (§71)

No AI/ML model was trained or introduced for C1. The existing risk engine remains:

- **deterministic** — pure function of its inputs, no state, no randomness (verified, §4 below)
- **explainable** — every point originates from a named factor with a human-readable evidence string
- **configurable** — all point values come from `app/core/config.py` settings (snapshot in §2)
- **auditable** — factor catalog is static and reviewable (`risk_factors.py`)

§74 (C3 evidence stays purely cryptographic, no AI/ML) is unaffected by this report.

---

## 2. Deterministic rules benchmark

### Engine interface (verified by direct read)

```python
calculate_risk(*, object_type, zone_crossed, is_night, multi_camera_confirmed,
               confidence, reliability, evidence=None) -> RiskResult
```

Sole production caller: `app/domain/incidents/incident_service.py:305-313` — invoked only on the
ENTRY path after `"rule_passed": True`, always with `zone_crossed=True`.

### Factor catalog and live configuration snapshot (2026-09-29)

| Factor code | Points | Condition |
|---|---|---|
| `RESTRICTED_ZONE_CROSSING` | +25 (non-animal) / +4 (animal) | always appended by the engine |
| `NIGHT_TIME` | +20 | `is_night` |
| `MULTI_CAMERA_CONFIRMATION` | +15 | `multi_camera_confirmed` |
| `OBJECT_HUMAN` / `OBJECT_VEHICLE` / `OBJECT_ANIMAL` | +15 / +10 / 0 | object type (animal counted via crossing) |
| `DETECTION_CONFIDENCE` | `round(confidence × 20)` | always |
| `LOW_RELIABILITY` | −15 | `reliability == "LOW"` |

Clamp: `final = max(0, min(100, raw))`. Severity bands: `<40` LOW, `40–64` MEDIUM, `65–84` HIGH,
`85–100` CRITICAL. `RISK_SCORE_MIN/MAX = 0/100` (no `.env` present; defaults active — recorded in
results `config_matches_generation: true`).

### Method — independent rule-arithmetic oracle

The benchmark (`ml/c1_risk/benchmarks/run_c1_benchmark.py`) re-implements the documented factor
math **independently** (labels, order, evidence string templates read from the catalog, point
values from the live config snapshot) and compares full engine output against it for every event.

**This oracle validates conformance to documented rules. It is not ground truth and does not
measure real-world correctness (§73/§105).**

### Result

- **Oracle conformance: 3,660 / 3,660 events = 100.0%** — score, severity, raw score, factor
  codes, factor order, factor points and evidence strings all exact-match.
- **Mismatches recorded in results JSON: 0**

---

## 3. Scenario dataset — PRHAAR-C1-RISK-SCENARIOS v1

File: `ml/c1_risk/scenarios/c1_scenarios_v1.json`
SHA-256: `e3b1bdcadaeb4bdeafb5c0666751be2c851c587949ced9d993a080495977fe0d`
Generator: `ml/c1_risk/scenarios/generate_c1_scenarios.py` (no randomness; inputs only; no labels)

| | Count |
|---|---|
| Scenarios | **3,649** |
| Events (risk-engine inputs) | **3,660** |
| `rule_coverage_grid` (exhaustive cartesian) | 3,636 |
| Scripted families | 13 scenarios / 24 events |

Grid axes: `object_type {HUMAN,VEHICLE,ANIMAL} × is_night {F,T} × multi_camera {F,T} ×
reliability {HIGH,MEDIUM,LOW} × confidence {0.00…1.00 step 0.01}` — 3,636 combinations,
exhaustive, no sampling.

§72 coverage mapping (scripted families):

| §72 item | Family | Measured outputs |
|---|---|---|
| zone crossing | `zone_crossing` | MEDIUM (59) |
| multiple crossings | `multiple_crossings` | 3× identical: HIGH (75,75,75) |
| repeated visit | `repeated_visit` | 2× identical: MEDIUM (52,52) |
| camera degraded | `camera_degraded` | LOW (score 0 w/ penalty) / MEDIUM |
| correlated events | `correlated_events` | CRITICAL (93,93), multi-camera factor present |
| long duration | `long_duration` (900 s) | MEDIUM (54) |
| short duration | `short_duration` (5 s) | MEDIUM (54) — identical to long |
| normal civilian activity | `normal_civilian_activity` | MEDIUM (59, 54) — see §6/§7 |
| animal movement | `animal_movement` | LOW, MEDIUM, LOW — see §7 |
| vehicle movement | `vehicle_movement` | MEDIUM / CRITICAL |
| (extra) night intrusion | `night_intrusion` | HIGH (77) |
| (extra) input case normalization | `input_case_normalization` | identical outputs for `human`/`HUMAN` |
| (extra) clamp boundary | `clamp_boundary` | floor clamp exact (raw −11 → 0); measured max raw 95 |

---

## 4. Repeatability test (§72 — "same input → same output every time")

Three independent evaluations per event, all deep-compared on risk score, severity, raw score,
full factor list (code/label/points/evidence, exact order) and `to_dict()`:

| Check | Passed |
|---|---|
| Same-process re-invocation (call A == call B) | 3,660 / 3,660 |
| JSON serialize → deserialize → re-invoke (A == C) | 3,660 / 3,660 |
| Independent oracle arithmetic (A == oracle) | 3,660 / 3,660 |
| **Determinism consistency (§120 C1)** | **100.0%** |

**Cross-process proof:** two separate interpreter processes (`run1`, `run2`) produced
**identical canonical SHA-256 over all inputs+outputs**:

```
results_sha256 = f5136456a4990fe45044a4f8e64ec584b27dc4a3ade15372d42c123ab1242412
```

per-run wall time 621.7 ms / 734.7 ms. The `events` sections of both results files are
byte-identical (verified). §120 C1 target — deterministic consistency 100% on defined
scenarios — **MET on this benchmark** (`tests/test_dbs`-style artifacts:
`c1_benchmark_results_run1.json`, `c1_benchmark_results_run2.json`).

---

## 5. Human-review benchmark (§73) — NOT AVAILABLE

No human reviewers were available for this phase, therefore **no agreement, disagreement,
false-positive or miss numbers are reported**. No fabricated reviewer numbers appear anywhere in
this report.

Prepared protocol for when reviewers exist (per §73):

1. Sample scenarios from `c1_scenarios_v1.json` (stratified by severity band, not uniform).
2. Reviewers see the factor breakdown + evidence strings, not the numeric score.
3. Independent label: `agree / disagree` with the recommended severity band.
4. Report: agreement rate, disagreement rate, high-risk false-positive rate, high-risk miss rate.
5. Labeling rules: this is **decision-support rule validation against a defined scenario-review
   protocol — not "accuracy of truth"** (verbatim §73 caution).

---

## 6. False-high-risk analysis

Definition used (internal, stated explicitly because §73 labels do not exist): a *high-risk call*
is severity ≥ HIGH; two weak-evidence qualifiers were measured over the grid.

| Measure | Count | Rate |
|---|---|---|
| HIGH/CRITICAL events (all) | 970 / 3,660 | 26.5% |
| …with `reliability == LOW` | 134 / 970 | **13.8%** |
| …with `confidence ≤ 0.5` | 303 / 970 | 31.2% |

Severity × reliability crosstab (grid + scripted):

| severity ↓ / reliability → | HIGH | MEDIUM | LOW |
|---|---|---|---|
| LOW | 307 | 306 | 578 |
| MEDIUM | 503 | 492 | 504 |
| HIGH | 334 | 336 | **134** |
| CRITICAL | 85 | 81 | 0 |

Observed interpretations (measured, not fixed — §125):

- 134 HIGH calls carry the LOW-reliability penalty, e.g. `C1-SCN-G00909-E0`
  (HUMAN, night, multi-camera, conf 1.0, LOW reliability → raw 65 → HIGH). The −15 penalty is
  applied but does not demote multi-factor scenarios below the HIGH band. This is a **candidate
  policy review item** for a future phase; the locked engine was not modified.
- CRITICAL never occurs with LOW reliability in this input space (0 of 166), because the maximum
  raw with the penalty applied is 80 (human, night, multicam = 95 − 15).
- 303 HIGH calls at confidence ≤ 0.5 concentrate in night + multi-camera combinations where the
  +60 of rule-based factors dominate the low confidence term.

---

## 7. False-low-risk analysis

**Strong-signal misses** — "strong signal" defined as HUMAN + night + multi-camera + HIGH
reliability + confidence ≥ 0.8 (24 grid events). Expected band by rule arithmetic: ≥ HIGH.

- Measured: **0 / 24 misses** (all 24 are CRITICAL, 95).

**Band straddle under uncertainty** — HUMAN + night, single camera, LOW reliability (101 events):
scores span **45–65**; 100 of 101 land MEDIUM, and only confidence 1.0 reaches exactly 65 (HIGH).
Documented as: the LOW-reliability penalty can sit the score just below the HIGH threshold on
genuinely uncertain night intrusions — an operational review flag, not a correctness claim.

**Object-type policy bounds** — measured vs config-derived (identical for all three):

| object_type | min raw (measured = theory) | max raw (measured = theory) | max possible severity |
|---|---|---|---|
| HUMAN | 25 | 95 | CRITICAL |
| VEHICLE | 20 | 90 | CRITICAL |
| ANIMAL | −11 (clamped to 0, 55 activations) | **59** | **MEDIUM** |

Animal ceiling is a config consequence of the +4 animal crossing policy: an animal can never
exceed MEDIUM severity even at night with multi-camera confirmation and confidence 1.0. Recorded
as an explicit policy limitation of the locked configuration; not changed.

Clamp usage: floor active 55 times (raw < 0 → 0); ceiling never active (max raw 95 < 100).

---

## 8. Documented observations (engine untouched, §125)

1. `zone_crossed` is accepted by `calculate_risk` but not consulted in scoring; the sole caller
   (`incident_service.py:305`) passes `True` only on the ENTRY path after rule evaluation. The
   guard is caller-side. Recorded for future schema review, not modified.
2. Duration is not an input of the risk engine; long (900 s) and short (5 s) events with identical
   vectors produce identical scores (verified). Duration-based escalation would be a policy change.
3. Maximum observable raw score with current config is 95 — the RISK_SCORE_MAX ceiling clamp is
   unreachable.
4. Multiplicity semantics: multiple crossings / repeated visits are scored per event; state and
   deduplication live in `incident_service` (`dedup_key`, `count_entries`), not the risk engine.

## 9. Non-claims (§105)

**Model was evaluated on public and/or project-specific non-operational data and has not been
field-validated by SSB.** (C1 uses no model at all; the statement applies to this benchmark
result as well.) This benchmark validates determinism and documented-rule conformance on a
synthetic input space; it does **not** validate real-world risk correctness, and it is not
"accuracy of truth". No SSB field validation is claimed.

## 10. Artifacts and provenance

| Artifact | Path | SHA-256 |
|---|---|---|
| Scenario dataset v1 | `ml/c1_risk/scenarios/c1_scenarios_v1.json` | `e3b1bdcadaeb4bdeafb5c0666751be2c851c587949ced9d993a080495977fe0d` |
| Generator | `ml/c1_risk/scenarios/generate_c1_scenarios.py` | (in git working tree) |
| Benchmark runner | `ml/c1_risk/benchmarks/run_c1_benchmark.py` | (in git working tree) |
| Results run1 | `ml/c1_risk/benchmarks/c1_benchmark_results_run1.json` | contains full per-event evidence |
| Results run2 | `ml/c1_risk/benchmarks/c1_benchmark_results_run2.json` | identical canonical hash |
| Canonical results hash | both runs | `f5136456a4990fe45044a4f8e64ec584b27dc4a3ade15372d42c123ab1242412` |

Engine source hashes at benchmark time (recorded in results `meta`):

```
app/domain/risk/risk_engine.py   f65d6fdc6ff4d93c8524a5a40a4ea24055c32c22710524bb6f0a3f40a8f696e6
app/domain/risk/risk_factors.py  ba1cbc1356efd8476c3d354517c75d8e73554a6a212ba23c59985dc46d714356
app/domain/risk/severity.py      53adeaa60437e41c2a208c407516b7af1bf35beb5b3e7985692fb3c1598dbd3b
app/core/config.py               bef246a2f72dd7675d0b5297f7443cb8ca518c337d095b9cf7b40bc358ff0253
```

## 11. Status

- §71 no neural risk model — respected.
- §72 deterministic scenario benchmark — **COMPLETE**, 100% determinism + 100% rule conformance.
- §73 human-review — **NOT AVAILABLE** (protocol prepared, no numbers fabricated).
- §106 report sections — all present; false-high-risk and false-low-risk analyses included.
