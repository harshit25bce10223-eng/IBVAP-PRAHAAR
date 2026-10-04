# C5 §4 — Repository Audit Report

**Project:** PRHAAR (प्रहार) — C5 Production Object Detection
**Spec refs:** C5 spec §3 (current architecture), §4 (first task — repository audit), §67 step 1
**Date:** 2026-10-03
**Method:** full-file reads of every C5 surface listed in §4 + targeted greps for cross-domain consumers. Every statement below cites the file that proves it. Nothing is inferred from memory of an older revision.

Files inspected (complete list):

| Surface (spec §4) | File(s) |
|---|---|
| Provider interface | `ibvap-backend/app/domain/detection/inference_provider.py` |
| Providers implemented | `ibvap-backend/app/domain/detection/providers/demo.py` (only file in `providers/`) |
| Normalizer | `ibvap-backend/app/domain/detection/normalizer.py` |
| Domain service | `ibvap-backend/app/domain/detection/service.py` |
| Schemas | `ibvap-backend/app/schemas/detection/schemas.py` |
| Persistence | `ibvap-backend/app/models/detection.py`, `app/repositories/detection/detection_repository.py`, `app/repositories/detection/config_repository.py` |
| API routes | `ibvap-backend/app/api/routes/detection/routes.py` |
| Settings | `ibvap-backend/app/core/config.py` |
| Frontend service | `ibvap-frontend/src/services/detection/{index.ts, IDetectionService.ts, RealDetectionService.ts, mapDetection.ts}` |
| Frontend types (DTO) | `ibvap-frontend/src/types/detection.ts` |
| Tests | `tests/unit/test_detection_{normalizer,provider,service,api}.py`, `tests/integration/test_detection_edge_sync.py` |
| Downstream consumers | grep across `app/domain/tracking`, `app/domain/risk`, `app/domain/correlation`, all `class_name` references repo-wide |

---

## 1. Verified pipeline (what exists today)

The architecture matches spec §3 exactly. Confirmed flow:

```
Frame
 ↓ provider.infer(frame, frame_id, camera_id)
DetectionInferenceProvider (ABC)
 ↓ normalizer.normalize_result(...)
NormalizedDetection (canonical, DET-* ids)
 ↓ DetectionService.process_frame
DetectionRepository → Detection table (+ events via adapter)
 ↓
C6 Tracking (DetectionInput; objects/class opaque)
 ↓
C1 / C4 / C3 downstream
```

No component bypasses the provider or normalizer boundary. The production detector plugs in as a new provider module; nothing upstream or downstream of the provider slot needs redesign.

## 2. Provider interface — exact contract

From `inference_provider.py` (verified, verbatim structure):

Abstract methods every provider must implement:

| Method | Signature | Required behavior |
|---|---|---|
| `load()` | `async def load() -> None` | Load model; must be called before inference |
| `warmup()` | `async def warmup() -> None` | Dummy inference after load |
| `infer(frame, frame_id, camera_id)` | `async def → InferenceResult`; frame is `np.ndarray` (H,W,C) BGR or RGB | Single-frame inference |
| `infer_batch(frames, frame_ids, camera_id)` | `async def → list[InferenceResult]` | Batch; one result per frame |
| `health()` | `async def → ProviderHealth` | Current state |
| `metadata()` | `async def → dict` | model name/version, supported classes, input format, batch limits |
| `shutdown()` | `async def → None` | Release resources |

`ProviderHealth` dataclass states in use: `UNAVAILABLE` (default) · `READY` · `LOADING` · `WARMING` · `DEGRADED` · `FAILED` · `UNKNOWN`, plus `last_successful_inference`, `recent_failures`, `queue_depth`, `avg_latency_ms`, `model_name`, `model_version`, `device`, `details`.

`create_provider(provider_type, config)` factory (`inference_provider.py:142-175`) references seven types: `local_cpu`, `local_gpu`, `onnx`, `tensorrt`, `remote`, `edge`, `demo`. **Only `demo` can actually construct** — `providers/` contains only `demo.py`; the other six branches import modules that do not exist (ImportError at call time). Unknown type raises `ValueError` (test-locked).

## 3. Exact required output contract (normative for the production detector)

Per spec §4: "Confirm the exact required output contract. Do NOT invent a new detection schema." The contract a production provider must satisfy — no new fields, no new tables:

**`infer()` must return `InferenceResult`:**

| Field | Type | Notes |
|---|---|---|
| `frame_id` | str | Echo of the input frame id |
| `camera_id` | str | Echo |
| `detections` | `list[RawDetection]` | May be empty (healthy zero-object result) |
| `inference_latency_ms` | int | Measured, not estimated |
| `model_name` | str | e.g. `prahaar-c5-detector` |
| `model_version` | str | e.g. `1.0` (mapped from §48 versioned identifier) |
| `provider` | str | Provider token (source of truth for `Detection.provider`) |
| `device` | str \| None | e.g. `cuda:0`, `cpu` |
| `runtime_version` | str \| None | e.g. torch/onnxruntime version |
| `timestamp` | str \| None | ISO when inference completed |

**Each `RawDetection`:**

| Field | Type | Notes |
|---|---|---|
| `class_id` | int | Model-native index — preserved end-to-end |
| `class_name` | str | Model-native class token; normalizer canonicalizes (unknown → UNKNOWN, never fabricated) |
| `confidence` | float | Strictly validated to [0,1]; NaN/Inf/out-of-range raise (normalizer) |
| `bbox` | list[float] (4) | Finite; format declared in `bbox_format` |
| `bbox_format` | str | One of `xyxy`, `xywh`, `xyxy_norm`, `xywh_norm`; pixel formats require frame dims |
| `occlusion` | float \| None | Numeric 0–1 or string (LOW/MEDIUM/HIGH; SEVERE/HEAVY→HIGH) |
| `quality` | str \| None | GOOD/LIMITED/POOR (+ variants; unknown→UNKNOWN) |
| `metadata` | dict \| None | Optional; must not carry identity claims (§55) |

**Behavioral requirements** (already enforced/expected by the existing pipeline):

- Normalizer generates the `DET-{10-hex}` id; persisted fields fill the existing `Detection` columns — the adapter must not write the DB directly.
- Service-level `asyncio.wait_for(..., timeout)` (default 10.0 s) wraps `infer`; a timeout surfaces as an explicit inference error, not a silent empty result.
- Confidence thresholding, `max_detections` trim, edge-dedup and idempotency happen **in the service** — the provider returns raw model output only.
- Failure contract (spec §46/§47): provider failures raise; the feed endpoint maps them to `UNAVAILABLE` + `FAILED`/actual state. **No path in the current code turns a failed provider into demo rows** — verified in `routes.py` feed implementation and tests (`test_feed_provider_unavailable_no_demo_fallback`).
- §55: the provider must emit object classes only — never `person`-identity, suspect/criminal/owner labels.

## 4. Normalizer contract (what the adapter must feed)

`normalizer.py` (verified):

- **Class**: `CANONICAL_CLASSES` (v1.0) = PERSON · VEHICLE · ANIMAL · OBJECT · UNKNOWN. Aliases map case-insensitively; unknown token → `UNKNOWN`. Raw token preserved in `provider_class`; `class_id` preserved; `taxonomy_version` ("1.0") stamped on each row.
- **BBox**: validated finite; pixel formats **require** frame dims (raise otherwise); normalized to xywh 0–1; clipping policy = `clip_bbox`.
- **Confidence**: [0,1] enforced; NaN/Inf raise; rounded to 4 dp; `None` preserved.
- **Quality/Occlusion**: mapped to canonical enums; unknown → UNKNOWN.
- **State derivation** (`normalize_state`): `None` confidence → UNKNOWN; `<0.3` → LOW_CONFIDENCE; quality POOR/LIMITED → LOW_CONFIDENCE; occlusion HIGH/MEDIUM → OCCLUDED; else DETECTED.
- **Timestamps**: ISO enforced; naive → UTC; `None` → now (observation time); unparseable raises (never silently replaced).
- **Payload hash**: SHA-256 over canonical fields (camera, frame, class, bbox, confidence, observed_at) — idempotency key for edge sync.
- Per-detection failures skip the row and continue (no fabricated detection).

## 5. Persistence contract

`Detection` (SQLite via SQLAlchemy 2.x) — production-relevant columns all present, no migration needed:

- `detection_id` PK · `camera_id` idx · `frame_id` · `event_id`/`track_id`/`incident_id`/`evidence_id` (soft FKs)
- `class_name` `String(32)` (**not** SQL enum → fine-class strings fit) · `class_id` int · `taxonomy_version` String(16) · `provider_class` String(64)
- `confidence` float · `quality_state`/`occlusion_state`/`detection_state` String(16)
- `bbox_x/y/width/height` floats NOT NULL (normalized 0–1) · `frame_width`/`frame_height`
- `source` String(16) (EDGE/CENTRAL/REMOTE/DEMO/UNKNOWN) · `provider` String(64) · `model_name/model_version/runtime_version/device/inference_mode/postprocess_version`
- `schema_version` "1.0" · `region_profile` · `sector_id`
- camera-health snapshot: `camera_health_state/reliability/viewpoint_shift/captured_at`
- sync: `sync_state/payload_hash/edge_device_id/source_event_id/source_sequence`
- `observed_at` NOT NULL idx · `received_at` · `processed_at` · `inference_latency_ms`/`queue_latency_ms` · `payload_json`

`DetectionConfig`: `provider` free string · `confidence_threshold` (default 0.3) · `iou_threshold` (0.5) · `max_detections` (100) · `sample_rate` · `min_frame_interval_ms` · `nms_enabled` · `clip_bbox` · `class_remap_json` (see F3) · queue/rate limits · edge-sync flags · `active` · `revision`. CRUD via API, 409 on duplicate camera config.

9 indexes cover camera×time, camera×class×time, event/track/incident/sector/region/state/received.

## 6. API contract

`/detections` router (verified):

| Endpoint | Contract |
|---|---|
| `GET /` | Filters: camera_id, class_name, source, state, quality, search, region_profile, sector_id, event/track/incident id, from/to time (422 if inverted), min_confidence; sort whitelist {observed_at, received_at, created_at, confidence, class_name, camera_id}; pagination. `class_name=OTHER` expands server-side to `["OBJECT","UNKNOWN"]` |
| `GET /recent`, `/cameras/{id}`, `/cameras/{id}/summary` | Summary 404s when the camera has no active config |
| `GET /cameras/{id}/feed` | `{state, inference, last_updated_at, detections}`; state mapping: UNCONFIGURED (no active config) · UNAVAILABLE (+FAILED) when provider cannot load/answer · STALE for LOADING/WARMING/DEGRADED/unknown · NO_OBJECTS when provider answered READY with zero rows · READY with detections. Docstring states: "A failed provider request never reads as 'no objects detected'" |
| `GET /{detection_id}` | Full detail + read-only `anpr_ref` (C7 soft reference; C5 never interprets) |
| `GET /inference/health` | Per-camera provider health; lazily initializes the provider to answer (see F7); 404 when no provider and no config; UNAVAILABLE record when config exists but provider cannot load |
| `GET /inference/metrics` | Counts by camera/class from stored rows |
| `POST /internal/ingest` | **501 Not implemented** (see F2) |
| `POST/GET/PATCH/DELETE /config[/{camera_id}]` | Config CRUD (validated by pydantic, 409 duplicate, PATCH bumps revision) |

Detail/summary builders surface missing stored values as `UNKNOWN` — never upgraded to positive states.

## 7. Frontend contract

- Gate: `VITE_DETECTION_MODE === 'REAL'` selects `realDetectionService`, else mock (`services/detection/index.ts`). REPAIR comment: a REAL provider must surface failures as DETECTION DATA UNAVAILABLE — never silently fall back to fixtures.
- `RealDetectionService`: axios against `/api/v1`; typed failure `DETECTION DATA UNAVAILABLE: backend unreachable` when no response; HTTP errors surfaced with status+detail.
- `mapDetection.ts`: defensive, total mappers. Field-name contract verified against `schemas.py` (comment in file names the fields). Class tokens narrowed to `DETECTION_CLASSES` (coarse); unknown → UNKNOWN; a row without detection_id is dropped, never fabricated.
- `types/detection.ts`: `DetectionClass = PERSON|VEHICLE|ANIMAL|OBJECT|UNKNOWN`; `DetectionResult.subclass: string | null` — **already populated from backend `provider_class`** (the designed extension point for the model-native class); feed states READY/NO_OBJECTS/UNCONFIGURED/UNAVAILABLE/STALE/OFFLINE; `mapFeedState` maps malformed/unknown → UNAVAILABLE, never READY.
- Query DTO passes `class_name` (coarse) or `OTHER` through to the API.

## 8. Tests locking the contract (inventory)

| File | Coverage |
|---|---|
| `test_detection_normalizer.py` | bbox conversions (4 formats, resolutions, deterministic), rejection (negative, oversize, NaN/±Inf), class normalization incl. **`car/truck/bus/motorcycle/bicycle/vehicle/auto → VEHICLE`** (v1.0 taxonomy), confidence bounds, quality/occlusion mappings, state derivation matrix, timestamps, taxonomy version |
| `test_detection_provider.py` | ProviderHealth defaults/updates, RawDetection/InferenceResult fields, demo provider lifecycle (load/warmup/infer/health/metadata/shutdown/failure simulation), factory (demo constructs; unknown raises) |
| `test_detection_service.py` | provider init/caching/shutdown, process_frame (no config → error, inactive → error, inference+normalize, timeout, confidence filtering, sampling, max trim, idempotency duplicate/payload-mismatch), list/get/summary/recent/refs, sync marking, health, metrics |
| `test_detection_api.py` | config CRUD flow, list filters (incl. OTHER expansion + exact class filter), pagination, feed states (UNCONFIGURED/inactive/NO_OBJECTS/READY/unavailable-no-fallback), detail + event/track/incident lookups, ref lookups |
| `test_detection_edge_sync.py` (integration) | edge sync flow with stored detections |

## 9. Findings (verified constraints for the integration phase)

**F1 — Six factory branches are placeholders.** `providers/` contains only `demo.py`. The production detector must be added as a new module under one of the existing reserved type names (`local_cpu` / `local_gpu` / `onnx` / `tensorrt`) — the name describes the runtime, so no new vocabulary is invented and `DetectionConfig.provider` stays a free string. Decision deferred to the export/integration phase (§42–§43 evidence will pick the runtime).

**F2 — No runtime frame feeder exists.** `process_frame` is called only from tests and `scripts/e2e_c6_traceability.py` / `e2e_c7_traceability.py`; `POST /internal/ingest` returns 501. The §39 REAL-mode test will drive the pipeline through the service boundary exactly as the e2e scripts do. Building a live camera feeder is NOT part of C5 scope.

**F3 — `class_remap_json` is inert.** It is stored in the model/schema/migration but **no code path reads it**. The model-class → PRHAAR-class remap (spec §7) will therefore live in the adapter/normalizer mapping, not in this column — or the column gets wired deliberately at integration. Recorded so no one assumes it currently does anything.

**F4 — Taxonomy gap (§7 fine classes vs v1.0 coarse canonical).** Current canonical output is PERSON/VEHICLE/ANIMAL/OBJECT/UNKNOWN, and the normalizer tests lock `car→VEHICLE` etc. Spec §7 requires the fine classes (PERSON, MOTORCYCLE, BICYCLE, CAR, LIGHT_VEHICLE, TRUCK, BUS, TRACTOR, ANIMAL) with an explicit model-class → PRHAAR-class mapping. No schema migration is needed to carry fine classes (String(32) column, `provider_class`, `class_id`, `taxonomy_version` all exist). Recommended: taxonomy v2.0 — fine classes as canonical `class_name` values for the production model; keep VEHICLE as a grouping/compat value for demo/edge/legacy sources; bump `taxonomy_version`; extend the frontend class union additively at integration (F6). Implementation point: integration phase (task §36–39), with the normalizer tests updated to the v2.0 contract at that time. Recorded now so dataset class design and training targets follow §7 from day one.

**F5 — Device selection is settings-driven.** `settings.USE_GPU` (default `False`) → provider config `device`. `DetectionConfig` has no device column. The production provider must honor the config dict it receives.

**F6 — Frontend narrows class tokens.** `mapDetectionClass` and `mapCameraDetectionSummary` drop any token outside the coarse set (fine classes would collapse to UNKNOWN / be dropped from `byClass`). `subclass` (from `provider_class`) already renders the raw model class. Union extension happens with F4 at integration — additive, no redesign.

**F7 — Provider lifecycle is per-request.** `get_detection_service` builds a new `DetectionService` per request; `_providers` cache and inference queues are per-instance. `get_provider_health`/feed lazily call `initialize_provider` (load + warmup) to answer. With the demo provider this is cheap; **with a torch/ONNX production provider this would load weights on every request**. Integration must introduce a process-scoped provider lifecycle (e.g., app-lifespan registry) without changing the provider boundary. This is the single largest integration constraint found by the audit.

**F8 — Downstream class consumers: none.** Repo-wide grep: `class_name` is referenced only by the detection repository/route/schema layer; C6 receives `DetectionInput.object_class: str` (opaque — no value branching in association/lifecycle code); C1/C4/C3 domains contain no `class_name` branches; `Detection` model imports outside C5 are relationship-only (`models/event.py`, `incident.py`, `evidence/record.py`). Fine taxonomy therefore has no downstream logic dependency — only display/filter/aggregation surfaces (F6).

## 10. Non-claims

- This audit validates interfaces and code paths only. It makes **no** statement about detection accuracy, dataset sufficiency, or model readiness — those are measured in §8–§44.
- No metric in this document is a model metric; every number is a code fact (counts of branches, files, tests, columns).

## 11. Conclusion

The C5 output contract is confirmed and fully implementable without inventing any new detection schema: `infer() → InferenceResult(RawDetection[])` with model-native class tokens, validated/normalized by the existing normalizer into the existing columns, surfaced by the existing API, gated by the existing REAL-mode frontend switch. Required work for integration is bounded to: (1) implement the production provider module under an existing factory type, (2) process-scoped provider lifecycle (F7), (3) taxonomy v2.0 activation with the §7 fine classes (F4/F6), (4) wire the class remap deliberately (F3). Everything else — normalizer, persistence, API, frontend DTOs, tests — is already in place and locked by tests.

**Next:** §5–§6 — candidate research (YOLO26s/m/l + at least one different family) and `model_license_audit.md`.
