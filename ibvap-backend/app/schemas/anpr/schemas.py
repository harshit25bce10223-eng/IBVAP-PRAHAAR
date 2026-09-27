# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 7 — ANPR Pydantic Schemas
#
# Aligned with frontend types/anpr.ts and IANPRService
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


# ─────────────────────────────────────────────────────────────────────────────
# Sub-objects matching frontend types
# ─────────────────────────────────────────────────────────────────────────────

class PlateCandidateResponse(BaseModel):
    """Plate candidate — matches PlateCandidate in frontend types."""
    model_config = ConfigDict(extra="allow", from_attributes=True, populate_by_name=True)

    rank: int
    rawRead: str = Field(alias="raw_read")
    normalizedRead: Optional[str] = Field(None, alias="normalized_read")
    confidence: float
    characterConfidence: Optional[list[float]] = Field(None, alias="character_confidence")
    formatStatus: str = Field(alias="format_status")

    @classmethod
    def from_orm(cls, cand: Any) -> "PlateCandidateResponse":
        # Parse character_confidence JSON if present
        char_conf = None
        if cand.character_confidence:
            try:
                import json
                char_conf = json.loads(cand.character_confidence)
            except Exception:
                pass
        return cls(
            rank=cand.rank,
            raw_read=cand.raw_read,
            normalized_read=cand.normalized_read,
            confidence=cand.confidence,
            character_confidence=char_conf,
            format_status=cand.format_status,
        )


class PlateReadResponse(BaseModel):
    """Single plate read — matches PlateRead in frontend types."""
    model_config = ConfigDict(extra="allow", from_attributes=True, populate_by_name=True)

    rawRead: str = Field(alias="raw_read")
    normalizedRead: Optional[str] = Field(None, alias="normalized_read")
    displayRead: str = Field(alias="display_read")
    confidence: float
    characterConfidence: Optional[list[float]] = Field(None, alias="character_confidence")
    formatStatus: str = Field(alias="format_status")
    quality: str
    cropReference: Optional[str] = Field(None, alias="crop_reference")
    observedAt: str = Field(alias="observed_at")
    sourceFrameRef: Optional[str] = Field(None, alias="source_frame_ref")
    candidates: list[PlateCandidateResponse] = []

    @classmethod
    def from_orm(cls, pr: Any) -> "PlateReadResponse":
        return cls(
            raw_read=pr.raw_read,
            normalized_read=pr.normalized_read,
            display_read=pr.display_read,
            confidence=pr.confidence,
            character_confidence=None,  # TODO: parse JSON if needed
            format_status=pr.format_status,
            quality=pr.quality,
            crop_reference=pr.crop_reference,
            observed_at=pr.observed_at.isoformat() if pr.observed_at else "",
            source_frame_ref=pr.source_frame_ref,
            candidates=[],  # Will be populated separately if needed
        )


class VehicleSightingResponse(BaseModel):
    """Vehicle sighting — matches VehicleSighting in frontend types."""
    model_config = ConfigDict(extra="allow", from_attributes=True, populate_by_name=True)

    sightingId: str = Field(alias="sighting_id")
    vehicleId: Optional[str] = Field(None, alias="vehicle_id")
    vehicleTrackId: Optional[str] = Field(None, alias="vehicle_track_id")
    cameraId: str = Field(alias="camera_id")
    observedAt: str = Field(alias="observed_at")
    receivedAt: Optional[str] = Field(None, alias="received_at")
    vehicleClass: str = Field(alias="vehicle_class")
    vehicleColor: Optional[str] = Field(None, alias="vehicle_color")
    vehicleDirection: str = Field(alias="vehicle_direction")
    plateRead: Optional[PlateReadResponse] = Field(None, alias="plate_read")
    plateCandidates: list[PlateCandidateResponse] = Field(default=[], alias="plate_candidates")
    confidence: Optional[float] = None
    detectionQuality: Optional[str] = Field(None, alias="detection_quality")
    cameraHealthState: Optional[str] = Field(None, alias="camera_health_state")
    locationContext: Optional[str] = Field(None, alias="location_context")
    watchlistStatus: str = Field(default="NOT_CHECKED", alias="watchlist_status")
    evidenceRef: Optional[str] = Field(None, alias="evidence_ref")
    eventRef: Optional[str] = Field(None, alias="event_ref")
    correlationRef: Optional[str] = Field(None, alias="correlation_ref")
    incidentRef: Optional[str] = Field(None, alias="incident_ref")
    thumbnailUrl: Optional[str] = Field(None, alias="thumbnail_url")
    plateCropUrl: Optional[str] = Field(None, alias="plate_crop_url")
    sourceProvider: Optional[str] = Field(None, alias="source_provider")

    @classmethod
    def from_orm(cls, sighting: Any) -> "VehicleSightingResponse":
        plate_read = None
        if sighting.plate_read:
            plate_read = PlateReadResponse.from_orm(sighting.plate_read)
            # Add candidates
            if sighting.candidates:
                plate_read.candidates = [
                    PlateCandidateResponse.from_orm(c) for c in sighting.candidates
                ]

        return cls(
            sighting_id=sighting.sighting_id,
            vehicle_id=sighting.vehicle_id,
            vehicle_track_id=sighting.track_id,
            camera_id=sighting.camera_id,
            observed_at=sighting.observed_at.isoformat() if sighting.observed_at else "",
            received_at=sighting.received_at.isoformat() if sighting.received_at else None,
            vehicle_class=sighting.vehicle_class,
            vehicle_color=sighting.vehicle_color,
            vehicle_direction=sighting.vehicle_direction,
            plate_read=plate_read,
            plate_candidates=[PlateCandidateResponse.from_orm(c) for c in sighting.candidates] if sighting.candidates else [],
            confidence=sighting.confidence,
            detection_quality=sighting.detection_quality,
            camera_health_state=sighting.camera_health_state,
            location_context=sighting.location_context,
            watchlist_status=sighting.watchlist_status,
            evidence_ref=sighting.evidence_id,
            event_ref=sighting.event_id,
            correlation_ref=sighting.correlation_id,
            incident_ref=sighting.incident_id,
            thumbnail_url=sighting.thumbnail_url,
            plate_crop_url=sighting.plate_crop_url,
            source_provider=sighting.provider,
        )


class VehicleHistoryResponse(BaseModel):
    """Vehicle history — matches VehicleHistory in frontend types."""
    model_config = ConfigDict(extra="allow")

    vehicleId: str = Field(alias="vehicle_id")
    sightings: list[VehicleSightingResponse] = []
    firstSeen: Optional[str] = Field(None, alias="first_seen")
    lastSeen: Optional[str] = Field(None, alias="last_seen")
    totalSightings: int = Field(alias="total_sightings")

    @classmethod
    def from_sightings(cls, vehicle_id: str, sightings: list[VehicleSightingResponse]) -> "VehicleHistoryResponse":
        if not sightings:
            return cls(vehicle_id=vehicle_id, sightings=[], first_seen=None, last_seen=None, total_sightings=0)

        first = min(s.observedAt for s in sightings)
        last = max(s.observedAt for s in sightings)
        return cls(
            vehicle_id=vehicle_id,
            sightings=sightings,
            first_seen=first,
            last_seen=last,
            total_sightings=len(sightings),
        )


class ANPRSummaryResponse(BaseModel):
    """ANPR summary — matches ANPRSummary in frontend types."""
    model_config = ConfigDict(extra="allow")

    totalReads: int = Field(alias="total_reads")
    readablePlates: int = Field(alias="readable_plates")
    partialReads: int = Field(alias="partial_reads")
    unreadablePlates: int = Field(alias="unreadable_plates")
    uniqueTrackedSightings: int = Field(alias="unique_tracked_sightings")
    camerasReporting: int = Field(alias="cameras_reporting")
    lastUpdated: Optional[str] = Field(None, alias="last_updated")


class SightingPageResponse(BaseModel):
    """Paginated sighting response — matches SightingPage in frontend service."""
    model_config = ConfigDict(extra="allow")

    sightings: list[VehicleSightingResponse]
    hasMore: bool = Field(alias="has_more")
    nextCursor: Optional[str] = Field(None, alias="next_cursor")


# ─────────────────────────────────────────────────────────────────────────────
# Request/Query schemas
# ─────────────────────────────────────────────────────────────────────────────

class ANPRFilter(BaseModel):
    """Query filter — matches ANPRFilter in frontend types."""
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    search: str = ""
    cameraId: str = Field(default="", alias="camera_id")
    vehicleClass: str = Field(default="", alias="vehicle_class")
    quality: str = ""
    confidenceMin: float = Field(default=0.0, alias="confidence_min")
    confidenceMax: float = Field(default=1.0, alias="confidence_max")
    direction: str = ""
    watchlistStatus: str = Field(default="", alias="watchlist_status")
    from_: Optional[str] = Field(default=None, alias="from")
    to: Optional[str] = Field(default=None, alias="to")
    cursor: Optional[str] = None
    limit: int = 50
    sort: str = "observed_at"
    order: str = "desc"

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        return min(max(v, 1), 500)


class ANPRSearchRequest(BaseModel):
    """Plate search request."""
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    query: str
    cameraId: Optional[str] = Field(default=None, alias="camera_id")
    matchType: Optional[str] = Field(default=None, alias="match_type")  # exact | partial | raw | candidate
    limit: int = 50

    @field_validator("limit")
    @classmethod
    def validate_limit(cls, v: int) -> int:
        return min(max(v, 1), 500)


# ─────────────────────────────────────────────────────────────────────────────
# Ingestion request (internal)
# ─────────────────────────────────────────────────────────────────────────────

class ANPRIngestPlateCandidate(BaseModel):
    """One plate candidate in ingestion payload."""
    model_config = ConfigDict(extra="forbid")

    rank: int
    rawRead: str = Field(alias="raw_read")
    normalizedRead: Optional[str] = Field(default=None, alias="normalized_read")
    confidence: float
    characterConfidence: Optional[list[float]] = Field(default=None, alias="character_confidence")
    formatStatus: str = Field(default="UNKNOWN_FORMAT", alias="format_status")


class ANPRIngestPlateRead(BaseModel):
    """One plate read in ingestion payload."""
    model_config = ConfigDict(extra="forbid")

    sightingId: str = Field(alias="sighting_id")
    rawRead: str = Field(alias="raw_read")
    normalizedRead: Optional[str] = Field(default=None, alias="normalized_read")
    displayRead: str = Field(alias="display_read")
    confidence: float
    characterConfidence: Optional[list[float]] = Field(default=None, alias="character_confidence")
    formatStatus: str = Field(default="UNKNOWN_FORMAT", alias="format_status")
    quality: str
    cropReference: Optional[str] = Field(default=None, alias="crop_reference")
    sourceFrameRef: Optional[str] = Field(default=None, alias="source_frame_ref")
    observedAt: str = Field(alias="observed_at")
    candidates: list[ANPRIngestPlateCandidate] = Field(default=[])


class ANPRIngestSighting(BaseModel):
    """One vehicle sighting in ingestion payload."""
    model_config = ConfigDict(extra="forbid")

    cameraId: str = Field(alias="camera_id")
    observedAt: str = Field(alias="observed_at")
    receivedAt: Optional[str] = Field(default=None, alias="received_at")
    vehicleClass: str = Field(default="UNKNOWN", alias="vehicle_class")
    vehicleColor: Optional[str] = Field(default=None, alias="vehicle_color")
    vehicleDirection: str = Field(default="UNKNOWN", alias="vehicle_direction")
    trackId: Optional[str] = Field(default=None, alias="track_id")
    detectionId: Optional[str] = Field(default=None, alias="detection_id")
    vehicleId: Optional[str] = Field(default=None, alias="vehicle_id")
    plateRead: Optional[ANPRIngestPlateRead] = None
    confidence: Optional[float] = None
    detectionQuality: Optional[str] = Field(default=None, alias="detection_quality")
    cameraHealthState: Optional[str] = Field(default=None, alias="camera_health_state")
    cameraHealthContextJson: Optional[str] = Field(default=None, alias="camera_health_context_json")
    locationContext: Optional[str] = Field(default=None, alias="location_context")
    sectorId: Optional[str] = Field(default=None, alias="sector_id")
    zoneId: Optional[str] = Field(default=None, alias="zone_id")
    watchlistStatus: str = Field(default="NOT_CHECKED", alias="watchlist_status")
    evidenceId: Optional[str] = Field(default=None, alias="evidence_id")
    eventId: Optional[str] = Field(default=None, alias="event_id")
    correlationId: Optional[str] = Field(default=None, alias="correlation_id")
    incidentId: Optional[str] = Field(default=None, alias="incident_id")
    thumbnailUrl: Optional[str] = Field(default=None, alias="thumbnail_url")
    plateCropUrl: Optional[str] = Field(default=None, alias="plate_crop_url")
    sourceProvider: Optional[str] = Field(default=None, alias="source_provider")
    syncPayloadHash: Optional[str] = Field(default=None, alias="sync_payload_hash")
    edgeDeviceId: Optional[str] = Field(default=None, alias="edge_device_id")


class ANPRIngestRequest(BaseModel):
    """Batch ingestion request for internal ANPR observe endpoint."""
    model_config = ConfigDict(extra="forbid")

    cameraId: str = Field(alias="camera_id")
    source: str = "LIVE"
    sectorId: Optional[str] = Field(default=None, alias="sector_id")
    zoneId: Optional[str] = Field(default=None, alias="zone_id")
    sightings: list[ANPRIngestSighting] = Field(max_length=200)

    @field_validator("cameraId")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must be a non-empty string")
        return v.strip()


class ANPRIngestResponse(BaseModel):
    """Result of ANPR ingestion batch."""
    model_config = ConfigDict(extra="allow")

    cameraId: str = Field(alias="camera_id")
    processedAt: str = Field(alias="processed_at")
    totalSightings: int = Field(alias="total_sightings")
    created: int
    duplicates: int
    errors: int
    providerName: Optional[str] = Field(default=None, alias="provider_name")
    providerVersion: Optional[str] = Field(default=None, alias="provider_version")
    processingLatencyMs: Optional[int] = Field(default=None, alias="processing_latency_ms")


# ─────────────────────────────────────────────────────────────────────────────
# Config schemas
# ─────────────────────────────────────────────────────────────────────────────

class ANPRConfigResponse(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True, populate_by_name=True)

    configId: str = Field(alias="config_id")
    cameraId: str = Field(alias="camera_id")
    provider: str
    trackerName: Optional[str] = Field(None, alias="tracker_name")
    trackerVersion: Optional[str] = Field(None, alias="tracker_version")
    associationProfile: Optional[str] = Field(None, alias="association_profile")
    maxSightingAgeSec: Optional[int] = Field(None, alias="max_sighting_age_sec")
    sampleRate: float = Field(alias="sample_rate")
    minFrameIntervalMs: int = Field(alias="min_frame_interval_ms")
    regionProfile: Optional[str] = Field(None, alias="region_profile")
    active: bool
    revision: int
    configurationVersion: str = Field(alias="configuration_version")
    createdAt: str = ""
    updatedAt: str = ""

    @classmethod
    def from_orm(cls, cfg: Any) -> "ANPRConfigResponse":
        return cls(
            config_id=cfg.config_id,
            camera_id=cfg.camera_id,
            provider=cfg.provider,
            tracker_name=cfg.tracker_name,
            tracker_version=cfg.tracker_version,
            association_profile=cfg.association_profile,
            max_sighting_age_sec=cfg.max_sighting_age_sec,
            sample_rate=cfg.sample_rate,
            min_frame_interval_ms=cfg.min_frame_interval_ms,
            region_profile=cfg.region_profile,
            active=cfg.active,
            revision=cfg.revision,
            configuration_version=cfg.configuration_version,
            createdAt=cfg.created_at.isoformat() if cfg.created_at else "",
            updatedAt=cfg.updated_at.isoformat() if cfg.updated_at else "",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Provider health
# ─────────────────────────────────────────────────────────────────────────────

class ANPRProviderHealthResponse(BaseModel):
    """Provider health."""
    model_config = ConfigDict(extra="allow")

    state: str  # READY|DEGRADED|UNAVAILABLE|OFFLINE|UNKNOWN
    provider: str
    providerVersion: Optional[str] = None
    lastSuccessfulUpdate: Optional[str] = None
    failureCount: int = 0
    queueDepth: int = 0
    processingLatencyMs: Optional[float] = None
    camerasActive: int = 0
    note: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Error codes
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# Ingestion request (internal — POST /internal/anpr/observe)
# ─────────────────────────────────────────────────────────────────────────────

class ANPRIngestPlateCandidate(BaseModel):
    """One plate candidate in ingestion payload."""
    model_config = ConfigDict(extra="forbid")

    rank: int
    rawRead: str = Field(alias="raw_read")
    normalizedRead: Optional[str] = Field(default=None, alias="normalized_read")
    confidence: float
    characterConfidence: Optional[list[float]] = Field(default=None, alias="character_confidence")
    formatStatus: str = Field(default="UNKNOWN_FORMAT", alias="format_status")


class ANPRIngestPlateRead(BaseModel):
    """One plate read in ingestion payload."""
    model_config = ConfigDict(extra="forbid")

    sightingId: str = Field(alias="sighting_id")
    rawRead: str = Field(alias="raw_read")
    normalizedRead: Optional[str] = Field(default=None, alias="normalized_read")
    displayRead: str = Field(alias="display_read")
    confidence: float
    characterConfidence: Optional[list[float]] = Field(default=None, alias="character_confidence")
    formatStatus: str = Field(default="UNKNOWN_FORMAT", alias="format_status")
    quality: str
    cropReference: Optional[str] = Field(default=None, alias="crop_reference")
    sourceFrameRef: Optional[str] = Field(default=None, alias="source_frame_ref")
    observedAt: str = Field(alias="observed_at")
    candidates: list[ANPRIngestPlateCandidate] = Field(default=[])


class ANPRIngestSighting(BaseModel):
    """One vehicle sighting in ingestion payload."""
    model_config = ConfigDict(extra="forbid")

    cameraId: str = Field(alias="camera_id")
    observedAt: str = Field(alias="observed_at")
    receivedAt: Optional[str] = Field(default=None, alias="received_at")
    vehicleClass: str = Field(default="UNKNOWN", alias="vehicle_class")
    vehicleColor: Optional[str] = Field(default=None, alias="vehicle_color")
    vehicleDirection: str = Field(default="UNKNOWN", alias="vehicle_direction")
    trackId: Optional[str] = Field(default=None, alias="track_id")
    detectionId: Optional[str] = Field(default=None, alias="detection_id")
    vehicleId: Optional[str] = Field(default=None, alias="vehicle_id")
    plateRead: Optional[ANPRIngestPlateRead] = None
    confidence: Optional[float] = None
    detectionQuality: Optional[str] = Field(default=None, alias="detection_quality")
    cameraHealthState: Optional[str] = Field(default=None, alias="camera_health_state")
    cameraHealthContextJson: Optional[str] = Field(default=None, alias="camera_health_context_json")
    locationContext: Optional[str] = Field(default=None, alias="location_context")
    sectorId: Optional[str] = Field(default=None, alias="sector_id")
    zoneId: Optional[str] = Field(default=None, alias="zone_id")
    watchlistStatus: str = Field(default="NOT_CHECKED", alias="watchlist_status")
    evidenceId: Optional[str] = Field(default=None, alias="evidence_id")
    eventId: Optional[str] = Field(default=None, alias="event_id")
    correlationId: Optional[str] = Field(default=None, alias="correlation_id")
    incidentId: Optional[str] = Field(default=None, alias="incident_id")
    thumbnailUrl: Optional[str] = Field(default=None, alias="thumbnail_url")
    plateCropUrl: Optional[str] = Field(default=None, alias="plate_crop_url")
    sourceProvider: Optional[str] = Field(default=None, alias="source_provider")
    syncPayloadHash: Optional[str] = Field(default=None, alias="sync_payload_hash")
    edgeDeviceId: Optional[str] = Field(default=None, alias="edge_device_id")


class ANPRIngestRequest(BaseModel):
    """Batch ingestion request for internal ANPR observe endpoint."""
    model_config = ConfigDict(extra="forbid")

    cameraId: str = Field(alias="camera_id")
    source: str = "LIVE"
    sectorId: Optional[str] = Field(default=None, alias="sector_id")
    zoneId: Optional[str] = Field(default=None, alias="zone_id")
    sightings: list[ANPRIngestSighting] = Field(max_length=200)

    @field_validator("cameraId")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must be a non-empty string")
        return v.strip()


class ANPRIngestResponse(BaseModel):
    """Result of ANPR ingestion batch."""
    model_config = ConfigDict(extra="allow")

    cameraId: str = Field(alias="camera_id")
    processedAt: str = Field(alias="processed_at")
    totalSightings: int = Field(alias="total_sightings")
    created: int
    duplicates: int
    errors: int
    providerName: Optional[str] = Field(default=None, alias="provider_name")
    providerVersion: Optional[str] = Field(default=None, alias="provider_version")
    processingLatencyMs: Optional[int] = Field(default=None, alias="processing_latency_ms")


# ─────────────────────────────────────────────────────────────────────────────
# Error codes
# ─────────────────────────────────────────────────────────────────────────────

ANPR_ERROR_CODES = frozenset({
    "SIGHTING_NOT_FOUND",
    "ANPR_UNAVAILABLE",
    "PROVIDER_TIMEOUT",
    "PROVIDER_ERROR",
    "CAMERA_NOT_FOUND",
    "INVALID_QUERY",
    "INVALID_SIGHTING",
    "DUPLICATE_SIGHTING",
    "REVISION_CONFLICT",
    "FORBIDDEN",
})