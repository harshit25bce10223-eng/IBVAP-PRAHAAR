# PRHAAR Component 6 — Tracking Engine

```
Component 5 Detection → Component 6 Tracking → Component 4 Correlation → Component 1 Risk → Incident → Component 3 Evidence
```

This document describes the model-agnostic tracking engine backend for PRHAAR (Sashastra Seema Bal).

## Architecture Overview

Component 6 owns **temporal continuity** — answering the question:

> *Which observations may represent the same moving object over time?*

Component 6 explicitly does **NOT** own:

- Identity recognition (no Re-ID, no face embeddings)
- Correlation (no relationship calculation)
- Risk assessment (no threat scores)
- Incident creation
- Evidence ledger

These remain authoritative in their respective components.

---

## Model Overview

### Track (TrackV2)

Represents a **hypothesis of continuity** — not an identity.

| Field | Type | Description |
|-------|------|-------------|
| `track_id` | string | Unique ID, `TRK-<hex10>` |
| `camera_id` | string | Camera that produced this track |
| `status` | enum | TENTATIVE, ACTIVE, LOST, REACQUIRED, ENDED, STALE, INVALID, UNKNOWN |
| `object_class` | string | PERSON, VEHICLE, ANIMAL, OBJECT, UNKNOWN |
| `first_seen_at` | datetime | First observation timestamp |
| `last_seen_at` | datetime | Latest observation timestamp |
| `current_detection_id` | string | Reference to latest Detection |
| `observation_count` | int | Total observations in this track |
| `continuity_quality` | string | STRONG, MODERATE, WEAK, UNKNOWN (provider-supplied) |
| `confidence` | float | Provider confidence (nullable — never fabricated) |
| `provider` | string | Provider name (e.g., "DEMO") |
| `tracker_name` | string | Tracker model name (nullable) |
| `tracker_version` | string | Tracker version (nullable) |
| `source` | string | LIVE, EDGE, CENTRAL, DEMO, UNKNOWN |
| `sector_id` | string | Operational sector (nullable) |
| `region_profile` | string | Region context (nullable) |
| `health_context_json` | JSON | Camera health snapshot (nullable) |
| `revision` | int | Optimistic locking token |
| `schema_version` | string | Schema version |
| `sync_state` | string | LOCAL_ONLY, SYNC_PENDING, SYNCED, SYNC_FAILED |
| `created_at` | datetime | Record creation time |
| `updated_at` | datetime | Last update time |

**Key invariant:** `LOST ≠ ENDED`. A LOST track may be reacquired. An ENDED track must not continue without explicit backend semantics.

### TrackObservation

Links one detection to one track. Uniqueness constraint: `(track_id, detection_id)`.

| Field | Type | Description |
|-------|------|-------------|
| `observation_id` | string | `OBS-<hex10>` |
| `track_id` | string | Reference to Track |
| `detection_id` | string | Reference to Detection (soft FK) |
| `camera_id` | string | Camera ID |
| `observed_at` | datetime | Sensor time (original) |
| `received_at` | datetime | Ingestion time (auto-set) |
| `sequence` | int | Provider-assigned sequence (nullable) |
| `bbox_*` | float | Normalized bounding box |
| `confidence` | float | Detector confidence (nullable) |
| `quality` | string | Quality state (nullable) |
| `velocity/speed/direction` | nullable | Motion data only if provider supplies |
| `object_class` | string | Class at this observation |
| `provider` | string | Provider name |

### TrackHistory

Audit log of every status transition.

| Field | Type | Description |
|-------|------|-------------|
| `history_id` | string | `THIST-<hex8>` |
| `track_id` | string | |
| `revision` | int | Track revision at transition |
| `old_status` | string | |
| `new_status` | string | |
| `reason` | string | e.g., DETECTION_RECEIVED, NO_OBSERVATIONS, TIMEOUT |
| `trigger_detection_id` | string | Detection that triggered transition |
| `provider`, `provider_version`, `configuration_version` | strings | Context |

### TrackCandidate

Cross-camera continuation hypothesis — **never** implies identity.

| Field | Type | Description |
|-------|------|-------------|
| `candidate_id` | string | `TCAND-<hex8>` |
| `source_track_id` | string | Track on source camera |
| `target_camera_id` | string | Target camera |
| `candidate_track_id` | string | Candidate track on target (nullable) |
| `relation_type` | string | `POSSIBLE_CONTINUATION`, `POSSIBLE_SAME_ENTITY` |
| `strength` | float | Confidence [0,1] (nullable) |
| `status` | string | OPEN, ACCEPTED, REJECTED, EXPIRED |

### TrackingConfig

Per-camera configuration (extensible JSON).

---

## Provider Abstraction

Component 6 is **model-agnostic**. The boundary is `TrackingProvider`:

```python
class TrackingProvider(ABC):
    async def initialize() -> None
    def ready() -> bool
    async def update(detections, context) -> ProviderUpdateResult
    async def flush(camera_id) -> ProviderUpdateResult
    def health() -> ProviderHealthInfo
    def metadata() -> ProviderMetadata
    async def shutdown() -> None
```

**Demo implementation:** `DemoTrackingProvider` (deterministic, no real algorithm).

**Production implementation:** Future implementations may wrap ByteTrack, BoT-SORT, DeepSORT, or SSB-specific trackers.

**Never:** Fabricate velocity, direction, confidence, or accuracy metrics.

---

## Lifecycle State Machine

```
         (new) ──► TENTATIVE ──► ACTIVE ──► LOST ──► REACQUIRED ──► ACTIVE
                         └───────────────────────────────────────────► ENDED
                                               └────────────────────► STALE
           Any state ───────────────────────────────────────────────► INVALID
```

Transitions are performed by `TrackLifecycleService` and recorded in `TrackHistory`.

---

## Database Schema

### New Tables

- `tracks` (extended from legacy table with ALTER TABLE)
- `track_observations`
- `track_history`
- `track_candidates`
- `tracking_configs`

### Indexes

`camera_id`, `status`, `object_class`, `first_seen_at`, `last_seen_at`, `current_detection_id`, `event_id`, `incident_id`, `correlation_id`, `evidence_id`, `sector_id`, `region_profile`, `source`, `provider`, `sync_state`, `observation_count`, `revision`, `gap_count`, `reacquisition_count`.

---

## API Endpoints

### Public

- `GET /api/v1/tracks` — paginated, filtered track list
- `GET /api/v1/tracks/recent` — all active tracks (dashboard)
- `GET /api/v1/tracks/{track_id}` — track detail
- `GET /api/v1/tracks/{track_id}/observations` — observation history (paged)
- `GET /api/v1/tracks/{track_id}/history` — lifecycle history (paged)
- `GET /api/v1/tracks/{track_id}/candidates` — cross-camera continuation candidates
- `GET /api/v1/cameras/{camera_id}/tracks` — tracks for one camera
- `GET /api/v1/cameras/{camera_id}/tracks/feed` — TrackingFeed (active tracks + provider state)
- `GET /api/v1/cameras/{camera_id}/tracks/summary` — camera count summary (no threat scores)
- `GET /api/v1/tracking/health` — provider health (no fake metrics)
- `GET /api/v1/tracking/config/{camera_id}` — tracking config for camera

### Internal (service-to-service)

- `POST /api/v1/internal/tracking/update` — ingest detection batch (requires `X-Internal-Service` header)

---

## Integration Points

### Component 5 (Detection)

Consumes `Detection` records via `DetectionInput`.

**Never duplicates detection data** — only references `detection_id`.

### Component 4 (Event Correlation)

Tracks may reference `event_id`, `correlation_id` but do **NOT** create events.

### Component 1 (Risk)

No direct risk score. Risk remains Component 1's responsibility.

### Component 3 (Evidence)

Tracks may reference `evidence_id` but do **NOT** create evidence.

### Component 2 (Camera Health)

Read-only health context via `CameraHealthProvider`. Never queries Component 2 tables directly.

---

## Idempotency

- Same `(detection_id, camera_id, observed_at)` → one observation (DB constraint)
- Same batch replayed → same logical outcome
- Concurrency: optimistic locking via `revision` field

---

## Concurrency & Edge Sync

- Revision-based optimistic locking
- Sync states: `LOCAL_ONLY`, `SYNC_PENDING`, `SYNCED`, `SYNC_FAILED`
- Idempotent edge sync (same `track_id` + `revision` = no-op)

---

## Testing

Unit tests: `tests/unit/test_tracking_*.py`

- Lifecycle transitions
- Provider initialization and health
- New track creation
- Duplicate handling
- Out-of-order detections
- Late detection handling
- Concurrency protection

---

## Future Tracker Integration Contract

A future tracker implementation must:

1. Implement `TrackingProvider` interface
2. Return `ProviderUpdateResult` with `TrackAssignment` per detection
3. Supply **only** observed values (no fabricated metrics)
4. Preserve `provider_name`, `tracker_version`, `configuration_version`

No database schema changes required.

---

## Security

- Reuses existing CORS and no-auth pattern (consistent with rest of PRHAAR)
- Internal endpoint requires `X-Internal-Service` header

---

## Performance Considerations

- Bounded result sets (no unbounded history queries)
- Pagination enforced (page_size max 200 for tracks, 500 for observations)
- Track history capped at 200 records per query
- Trajectory points capped at 500

---

## Limitations (Current Release)

- No production tracker algorithm (Demo mode only)
- No cross-camera identity confirmation
- No velocity/direction fabrication
- No benchmark metrics exposed

---

## References

- Component 6 TypeScript types: `ibvap-frontend/src/types/tracking.ts`
- Component 5 Detection schema: `app/models/detection.py`
- Component 2 Camera Health: `app/domain/camera_health/provider.py`
- Component 4 Event Correlation: `app/models/event_correlation/`
- Component 1 Risk Engine: `app/domain/risk/`

---

**No production tracking algorithm or Re-ID model was trained or selected as part of this backend architecture task. The tracking backend is model-agnostic and exposes a TrackingProvider integration boundary. The actual tracker selection, tuning, dataset, benchmark, and Re-ID integration will be handled as a separate AI/ML task.**
