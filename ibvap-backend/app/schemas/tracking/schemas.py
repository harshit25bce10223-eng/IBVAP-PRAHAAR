# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 6 — Tracking Engine Pydantic Schemas
#
# These schemas are aligned EXACTLY with the locked TypeScript contract in:
#   src/types/tracking.ts   (Track, TrackObservation, TrackingFeed, etc.)
#   src/services/tracking/ITrackingService.ts
#
# Field names use camelCase in responses (alias_generator or explicit aliases)
# to match the frontend. Internal service methods use snake_case.
#
# Nullability: any field that is Optional in the TS contract is Optional here.
# Extra fields are allowed in responses (forward compatibility).
# Extra fields are FORBIDDEN in request bodies (strict validation).
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


def _iso_utc(dt: datetime | None) -> str | None:
    """Serialize a datetime as ISO-8601 with an explicit UTC offset.

    SQLite returns naive datetimes for DateTime(timezone=True) columns. A naive
    string like "2026-09-28T14:55:01" is parsed by browsers as LOCAL time,
    which shifted every displayed timestamp by the local offset. Found in §27
    browser QA: Track Detail showed firstSeenAt converted to IST but
    updatedAt/observations/history rendered as raw UTC (5.5h apart).
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


# ─────────────────────────────────────────────────────────────────────────────
# Re-exported literal types (mirror TS)
# ─────────────────────────────────────────────────────────────────────────────

TrackStatus = str          # TENTATIVE|ACTIVE|LOST|REACQUIRED|ENDED|STALE|INVALID|UNKNOWN
TrackSource = str          # LIVE|EDGE|CENTRAL|DEMO|UNKNOWN
TrackContinuityQuality = str   # STRONG|MODERATE|WEAK|UNKNOWN
TrackingFeedState = str    # READY|PROCESSING|DEGRADED|UNAVAILABLE|STALE|OFFLINE|UNKNOWN
DetectionClass = str       # PERSON|VEHICLE|ANIMAL|OBJECT|UNKNOWN


# ─────────────────────────────────────────────────────────────────────────────
# Sub-objects
# ─────────────────────────────────────────────────────────────────────────────

class BoundingBox(BaseModel):
    """Normalized bounding box [0,1] — matches DetectionBBox in TS."""
    model_config = ConfigDict(extra="allow", from_attributes=True)
    x: float
    y: float
    width: float
    height: float


class TrackPoint(BaseModel):
    """Single 2D trajectory point. Matches TrackPoint in TS."""
    model_config = ConfigDict(extra="allow", from_attributes=True, populate_by_name=True)
    x: float
    y: float
    timestamp: Optional[str] = None
    observationId: Optional[str] = Field(None, validation_alias="observation_id")
    sequence: Optional[int] = None
    speed: Optional[float] = None


class TrackCameraHealthContext(BaseModel):
    """Camera health snapshot attached to a track. Matches TrackCameraHealthContext in TS."""
    model_config = ConfigDict(extra="allow", from_attributes=True)
    status: str = "UNKNOWN"        # ONLINE|DEGRADED|OFFLINE|UNKNOWN
    reliability: str = "UNKNOWN"   # HIGH|MEDIUM|LOW|UNKNOWN
    viewpointShiftDetected: Optional[bool] = None
    note: Optional[str] = None


class CrossCameraCandidate(BaseModel):
    """Cross-camera continuation hypothesis. Matches CrossCameraCandidate in TS."""
    model_config = ConfigDict(extra="allow", from_attributes=True)
    targetCameraId: str
    candidateTrackId: str
    continuityConfidence: Optional[float] = None
    gapDurationSec: Optional[float] = None
    sequenceNumber: Optional[int] = None
    note: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# TrackObservationResponse — matches TrackObservation in TS
# ─────────────────────────────────────────────────────────────────────────────

class TrackObservationResponse(BaseModel):
    """Single observation linking a detection to a track."""
    model_config = ConfigDict(extra="allow", from_attributes=True, populate_by_name=True)

    observationId: str = Field(validation_alias="observation_id")
    trackId: str = Field(validation_alias="track_id")
    detectionId: Optional[str] = Field(None, validation_alias="detection_id")
    cameraId: str = Field(validation_alias="camera_id")
    observedAt: str = Field(validation_alias="observed_at_iso")   # ISO string
    receivedAt: Optional[str] = Field(None, validation_alias="received_at_iso")
    bbox: Optional[BoundingBox] = None
    velocity: Optional[float] = None
    speed: Optional[float] = None
    direction: Optional[str] = None
    quality: Optional[str] = None
    confidence: Optional[float] = None
    sequence: Optional[int] = None
    source: str = "UNKNOWN"
    frameNumber: Optional[int] = Field(None, validation_alias="frame_number")
    frameId: Optional[str] = Field(None, validation_alias="frame_id")
    evidenceId: Optional[str] = Field(None, validation_alias="evidence_id")

    @classmethod
    def from_orm(cls, obs: Any) -> "TrackObservationResponse":
        """Build from a TrackObservation ORM instance."""
        bbox = None
        if obs.bbox_x is not None:
            bbox = BoundingBox(
                x=obs.bbox_x, y=obs.bbox_y,
                width=obs.bbox_width, height=obs.bbox_height,
            )
        return cls(
            observation_id=obs.observation_id,
            track_id=obs.track_id,
            detection_id=obs.detection_id,
            camera_id=obs.camera_id,
            observed_at_iso=_iso_utc(obs.observed_at) or "",
            received_at_iso=_iso_utc(obs.received_at),
            bbox=bbox,
            velocity=obs.velocity,
            speed=obs.speed,
            direction=obs.direction,
            quality=obs.quality,
            confidence=obs.confidence,
            sequence=obs.sequence,
            source=obs.source or "UNKNOWN",
            frame_number=obs.frame_number,
            frame_id=obs.frame_id,
            evidence_id=obs.evidence_id,
        )


# ─────────────────────────────────────────────────────────────────────────────
# TrackResponse — matches Track in TS
# ─────────────────────────────────────────────────────────────────────────────

class TrackResponse(BaseModel):
    """
    Canonical track entity response.
    Aligns exactly with the locked Track interface in tracking.ts.
    """
    model_config = ConfigDict(extra="allow", from_attributes=True, populate_by_name=True)

    trackId: str = Field(validation_alias="track_id")
    cameraId: str = Field(validation_alias="camera_id")
    status: str
    objectClass: str = Field(validation_alias="object_class")

    firstSeenAt: str = Field(validation_alias="first_seen_at_iso")
    lastSeenAt: str = Field(validation_alias="last_seen_at_iso")
    observedAt: str = Field(validation_alias="observed_at_iso")
    updatedAt: Optional[str] = Field(None, validation_alias="updated_at_iso")

    ageMs: Optional[int] = Field(None, validation_alias="age_ms")
    durationSec: Optional[float] = Field(None, validation_alias="duration_sec")
    detectionCount: int = Field(validation_alias="observation_count")

    currentDetectionId: Optional[str] = Field(None, validation_alias="current_detection_id")
    currentBoundingBox: Optional[BoundingBox] = None
    trajectory: Optional[list[TrackPoint]] = None

    speed: Optional[float] = None
    velocity: Optional[float] = None
    direction: Optional[str] = None
    confidence: Optional[float] = None
    continuityQuality: Optional[str] = Field(None, validation_alias="continuity_quality")

    source: str = "UNKNOWN"
    dataSource: str = Field(validation_alias="data_source")
    provider: Optional[str] = None
    trackerName: Optional[str] = Field(None, validation_alias="tracker_name")
    trackerVersion: Optional[str] = Field(None, validation_alias="tracker_version")

    eventId: Optional[str] = Field(None, validation_alias="event_id")
    correlationId: Optional[str] = Field(None, validation_alias="correlation_id")
    incidentId: Optional[str] = Field(None, validation_alias="incident_id")
    evidenceId: Optional[str] = Field(None, validation_alias="evidence_id")
    candidateEntityId: Optional[str] = Field(None, validation_alias="entity_candidate_id")

    crossCameraCandidate: Optional[CrossCameraCandidate] = None
    cameraHealthContext: Optional[TrackCameraHealthContext] = None

    regionProfile: Optional[str] = Field(None, validation_alias="region_profile")
    sectorId: Optional[str] = Field(None, validation_alias="sector_id")

    revision: Optional[int] = None
    schemaVersion: Optional[str] = Field(None, validation_alias="schema_version")

    previousClass: Optional[str] = Field(None, validation_alias="previous_class")
    classRevisionReason: Optional[str] = Field(None, validation_alias="class_revision_reason")
    classRevisedAt: Optional[str] = Field(None, validation_alias="class_revised_at_iso")

    dataCompleteness: Optional[str] = Field(None, validation_alias="data_completeness")
    missingObservationsNote: Optional[str] = Field(None, validation_alias="missing_observations_note")

    @classmethod
    def from_orm(cls, track: Any, *, trajectory: list[Any] | None = None) -> "TrackResponse":
        """Build from a TrackV2 ORM instance."""
        import json as _json
        from datetime import timezone as _tz

        # Health context snapshot
        health_ctx = None
        if track.health_context_json:
            try:
                hd = _json.loads(track.health_context_json)
                health_ctx = TrackCameraHealthContext(
                    status=hd.get("state", "UNKNOWN") or "UNKNOWN",
                    reliability=hd.get("reliability", "UNKNOWN") or "UNKNOWN",
                    viewpointShiftDetected=hd.get("viewpoint_shift"),
                    note=None,
                )
            except Exception:
                pass

        # Current bbox
        cur_bbox = None
        if track.current_bbox_x is not None:
            cur_bbox = BoundingBox(
                x=track.current_bbox_x, y=track.current_bbox_y,
                width=track.current_bbox_width, height=track.current_bbox_height,
            )

        # Trajectory from observations
        traj_points = None
        if trajectory:
            traj_points = [
                TrackPoint(
                    x=obs.bbox_x + obs.bbox_width / 2.0 if obs.bbox_x is not None else 0.0,
                    y=obs.bbox_y + obs.bbox_height / 2.0 if obs.bbox_y is not None else 0.0,
                    timestamp=_iso_utc(obs.observed_at),
                    observation_id=obs.observation_id,
                    sequence=obs.sequence,
                    speed=obs.speed,
                )
                for obs in trajectory
                if obs.bbox_x is not None
            ]

        first_seen = track.first_seen_at or track.first_seen
        last_seen = track.last_seen_at or track.last_seen

        # Ensure timezone-aware datetimes for arithmetic
        from datetime import timezone as _tz
        if first_seen is not None and first_seen.tzinfo is None:
            first_seen = first_seen.replace(tzinfo=_tz.utc)
        if last_seen is not None and last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=_tz.utc)

        # Duration
        duration_sec = None
        if first_seen and last_seen:
            duration_sec = round((last_seen - first_seen).total_seconds(), 1)

        now = datetime.now(_tz.utc)
        age_ms = None
        if last_seen:
            age_ms = int((now - last_seen).total_seconds() * 1000)

        observed_at_iso = last_seen.isoformat() if last_seen else ""
        updated_at_iso = _iso_utc(track.updated_at)
        class_revised_at_iso = _iso_utc(track.class_revised_at)

        return cls(
            track_id=track.track_id,
            camera_id=track.camera_id,
            status=track.status or "UNKNOWN",
            object_class=track.object_class or "UNKNOWN",
            first_seen_at_iso=first_seen.isoformat() if first_seen else observed_at_iso,
            last_seen_at_iso=last_seen.isoformat() if last_seen else observed_at_iso,
            observed_at_iso=observed_at_iso,
            updated_at_iso=updated_at_iso,
            age_ms=age_ms,
            duration_sec=duration_sec,
            observation_count=track.observation_count or 0,
            current_detection_id=track.current_detection_id,
            currentBoundingBox=cur_bbox,
            trajectory=traj_points,
            confidence=track.confidence,
            continuity_quality=track.continuity_quality,
            source=track.source or "UNKNOWN",
            data_source=track.source or "UNKNOWN",
            provider=track.provider,
            tracker_name=track.tracker_name,
            tracker_version=track.tracker_version,
            event_id=track.event_id,
            correlation_id=track.correlation_id,
            incident_id=track.incident_id,
            evidence_id=track.evidence_id,
            entity_candidate_id=track.entity_candidate_id,
            cameraHealthContext=health_ctx,
            region_profile=track.region_profile,
            sector_id=track.sector_id,
            revision=track.revision,
            schema_version=track.schema_version,
            previous_class=track.previous_class,
            class_revision_reason=track.class_revision_reason,
            class_revised_at_iso=class_revised_at_iso,
            data_completeness=track.data_completeness,
            missing_observations_note=track.missing_observations_note,
        )


# ─────────────────────────────────────────────────────────────────────────────
# TrackingFeed — matches TrackingFeed in TS
# ─────────────────────────────────────────────────────────────────────────────

class TrackingFeedResponse(BaseModel):
    """Camera feed response including all active tracks."""
    model_config = ConfigDict(extra="allow")

    cameraId: str
    state: str                          # TrackingFeedState
    lastUpdatedAt: Optional[str] = None
    tracks: list[TrackResponse]
    providerHealth: Optional[str] = None  # READY|DEGRADED|UNAVAILABLE|OFFLINE|UNKNOWN


# ─────────────────────────────────────────────────────────────────────────────
# TrackSummary — matches TrackSummary in TS
# ─────────────────────────────────────────────────────────────────────────────

class TrackSummaryResponse(BaseModel):
    """Structural summary counts. No threat counts (spec §77)."""
    model_config = ConfigDict(extra="allow")

    cameraId: str
    totalActive: int
    totalTracks: int
    byClass: dict[str, int]
    byStatus: dict[str, int]
    lastUpdatedAt: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# TrackResultPage — matches TrackResultPage in TS
# ─────────────────────────────────────────────────────────────────────────────

class TrackResultPageResponse(BaseModel):
    """Paginated track list response."""
    model_config = ConfigDict(extra="allow")

    tracks: list[TrackResponse]
    total: int
    page: int
    pageSize: int


# ─────────────────────────────────────────────────────────────────────────────
# Track history response
# ─────────────────────────────────────────────────────────────────────────────

class TrackHistoryEntryResponse(BaseModel):
    """Single lifecycle transition record."""
    model_config = ConfigDict(extra="allow", from_attributes=True, populate_by_name=True)

    historyId: str = Field(validation_alias="history_id")
    trackId: str = Field(validation_alias="track_id")
    revision: int
    oldStatus: Optional[str] = Field(None, validation_alias="old_status")
    newStatus: str = Field(validation_alias="new_status")
    reason: Optional[str] = None
    triggerDetectionId: Optional[str] = Field(None, validation_alias="trigger_detection_id")
    provider: Optional[str] = None
    providerVersion: Optional[str] = Field(None, validation_alias="provider_version")
    configurationVersion: Optional[str] = Field(None, validation_alias="configuration_version")
    timestamp: str = ""

    @classmethod
    def from_orm(cls, h: Any) -> "TrackHistoryEntryResponse":
        return cls(
            history_id=h.history_id,
            track_id=h.track_id,
            revision=h.revision,
            old_status=h.old_status,
            new_status=h.new_status,
            reason=h.reason,
            trigger_detection_id=h.trigger_detection_id,
            provider=h.provider,
            provider_version=h.provider_version,
            configuration_version=h.configuration_version,
            timestamp=_iso_utc(h.timestamp) or "",
        )


class TrackHistoryPageResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    history: list[TrackHistoryEntryResponse]
    total: int
    page: int
    pageSize: int


# ─────────────────────────────────────────────────────────────────────────────
# Cross-camera candidate response
# ─────────────────────────────────────────────────────────────────────────────

class TrackCandidateResponse(BaseModel):
    """Cross-camera continuation hypothesis."""
    model_config = ConfigDict(extra="allow", from_attributes=True, populate_by_name=True)

    candidateId: str = Field(validation_alias="candidate_id")
    sourceTrackId: str = Field(validation_alias="source_track_id")
    targetCameraId: str = Field(validation_alias="target_camera_id")
    candidateTrackId: Optional[str] = Field(None, validation_alias="candidate_track_id")
    relationType: str = Field(validation_alias="relation_type")
    strength: Optional[float] = None
    reason: Optional[str] = None
    status: str = "OPEN"
    provider: Optional[str] = None
    gapDurationSec: Optional[float] = Field(None, validation_alias="gap_duration_sec")
    createdAt: str = ""
    expiresAt: Optional[str] = None

    @classmethod
    def from_orm(cls, c: Any) -> "TrackCandidateResponse":
        return cls(
            candidate_id=c.candidate_id,
            source_track_id=c.source_track_id,
            target_camera_id=c.target_camera_id,
            candidate_track_id=c.candidate_track_id,
            relation_type=c.relation_type,
            strength=c.strength,
            reason=c.reason,
            status=c.status,
            provider=c.provider,
            gap_duration_sec=c.gap_duration_sec,
            createdAt=_iso_utc(c.created_at) or "",
            expiresAt=_iso_utc(c.expires_at),
        )


# ─────────────────────────────────────────────────────────────────────────────
# Provider health response
# ─────────────────────────────────────────────────────────────────────────────

class TrackingProviderHealthResponse(BaseModel):
    """Provider health. No fake metrics."""
    model_config = ConfigDict(extra="allow")

    state: str
    provider: str
    providerVersion: Optional[str] = None
    trackerName: Optional[str] = None
    trackerVersion: Optional[str] = None
    lastSuccessfulUpdate: Optional[str] = None
    failureCount: int = 0
    queueDepth: int = 0
    processingLatencyMs: Optional[float] = None
    camerasActive: int = 0
    note: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Ingestion request (internal — POST /internal/tracking/update)
# ─────────────────────────────────────────────────────────────────────────────

class TrackingIngestDetectionItem(BaseModel):
    """One detection entry in the ingestion payload."""
    model_config = ConfigDict(extra="forbid")

    detectionId: str
    cameraId: str
    observedAt: str                 # ISO 8601 with timezone
    bboxX: float = Field(ge=0.0, le=1.0)
    bboxY: float = Field(ge=0.0, le=1.0)
    bboxWidth: float = Field(gt=0.0, le=1.0)
    bboxHeight: float = Field(gt=0.0, le=1.0)
    objectClass: str = "UNKNOWN"
    confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    quality: Optional[str] = None
    occlusion: Optional[str] = None
    source: str = "UNKNOWN"
    frameId: Optional[str] = None
    frameNumber: Optional[int] = None
    regionProfile: Optional[str] = None
    sectorId: Optional[str] = None
    cameraHealthState: Optional[str] = None
    cameraHealthReliability: Optional[str] = None
    cameraViewpointShift: Optional[bool] = None

    @field_validator("detectionId", "cameraId")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must be a non-empty string")
        return v.strip()


class TrackingIngestRequest(BaseModel):
    """Batch ingestion request for the internal tracking update endpoint."""
    model_config = ConfigDict(extra="forbid")

    cameraId: str
    source: str = "LIVE"
    sectorId: Optional[str] = None
    regionProfile: Optional[str] = None
    detections: list[TrackingIngestDetectionItem] = Field(max_length=500)

    @field_validator("cameraId")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must be a non-empty string")
        return v.strip()


class TrackingIngestResponse(BaseModel):
    """Result of a tracking ingestion batch."""
    model_config = ConfigDict(extra="allow")

    cameraId: str
    processedAt: str
    totalDetections: int
    matched: int
    newTracks: int
    unmatched: int
    rejected: int
    duplicateRejected: int
    errors: int
    providerName: Optional[str] = None
    providerVersion: Optional[str] = None
    processingLatencyMs: Optional[int] = None


# ─────────────────────────────────────────────────────────────────────────────
# Observation page response
# ─────────────────────────────────────────────────────────────────────────────

class TrackObservationPageResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    observations: list[TrackObservationResponse]
    total: int
    page: int
    pageSize: int


# ─────────────────────────────────────────────────────────────────────────────
# Tracking config schemas
# ─────────────────────────────────────────────────────────────────────────────

class TrackingConfigResponse(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True, populate_by_name=True)

    configId: str = Field(validation_alias="config_id")
    cameraId: str = Field(validation_alias="camera_id")
    provider: str
    trackerName: Optional[str] = Field(None, validation_alias="tracker_name")
    trackerVersion: Optional[str] = Field(None, validation_alias="tracker_version")
    associationProfile: Optional[str] = Field(None, validation_alias="association_profile")
    maxTrackAgeSec: Optional[int] = Field(None, validation_alias="max_track_age_sec")
    sampleRate: float = Field(validation_alias="sample_rate")
    minFrameIntervalMs: int = Field(validation_alias="min_frame_interval_ms")
    regionProfile: Optional[str] = Field(None, validation_alias="region_profile")
    active: bool
    revision: int
    configurationVersion: str = Field(validation_alias="configuration_version")
    createdAt: str = ""
    updatedAt: str = ""

    @classmethod
    def from_orm(cls, cfg: Any) -> "TrackingConfigResponse":
        return cls(
            config_id=cfg.config_id,
            camera_id=cfg.camera_id,
            provider=cfg.provider,
            tracker_name=cfg.tracker_name,
            tracker_version=cfg.tracker_version,
            association_profile=cfg.association_profile,
            max_track_age_sec=cfg.max_track_age_sec,
            sample_rate=cfg.sample_rate,
            min_frame_interval_ms=cfg.min_frame_interval_ms,
            region_profile=cfg.region_profile,
            active=cfg.active,
            revision=cfg.revision,
            configuration_version=cfg.configuration_version,
            createdAt=_iso_utc(cfg.created_at) or "",
            updatedAt=_iso_utc(cfg.updated_at) or "",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Error codes (spec §158)
# ─────────────────────────────────────────────────────────────────────────────

TRACKING_ERROR_CODES = frozenset({
    "TRACK_NOT_FOUND",
    "TRACKING_UNAVAILABLE",
    "PROVIDER_TIMEOUT",
    "PROVIDER_ERROR",
    "CAMERA_NOT_FOUND",
    "INVALID_QUERY",
    "INVALID_TRACK",
    "REVISION_CONFLICT",
    "FORBIDDEN",
})
