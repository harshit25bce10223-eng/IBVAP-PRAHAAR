# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 7 — ANPR Pydantic Schemas
#
# Aligned with frontend types/anpr.ts and IANPRService
#
# Wire format note: response schemas declare camelCase FIELD names with
# snake_case value aliases. ANPR routes are declared with
# response_model_by_alias=False so FastAPI serializes by FIELD NAME → the wire
# format is camelCase (what the frontend contract expects).
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


def _iso_utc(dt: datetime | None) -> str | None:
    """Serialize a datetime as ISO-8601 with an explicit UTC offset.

    SQLite returns naive datetimes for DateTime(timezone=True) columns. A naive
    string like "2026-09-28T14:55:01" is parsed by browsers as LOCAL time,
    which shifts every displayed timestamp by the local offset. Same fix as C6
    (app/schemas/tracking/schemas.py).
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _parse_char_conf(raw: Any) -> list[float] | None:
    """Parse a character-confidence JSON text column into a list of floats."""
    if not raw:
        return None
    try:
        val = json.loads(raw) if isinstance(raw, str) else raw
        if isinstance(val, list):
            return [float(x) for x in val]
    except (ValueError, TypeError):
        return None
    return None


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
        return cls(
            rank=cand.rank,
            raw_read=cand.raw_read,
            normalized_read=cand.normalized_read,
            confidence=cand.confidence,
            character_confidence=_parse_char_conf(cand.character_confidence),
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
    candidates: list[PlateCandidateResponse] = Field(default_factory=list)

    @classmethod
    def from_orm(cls, pr: Any) -> "PlateReadResponse":
        return cls(
            raw_read=pr.raw_read,
            normalized_read=pr.normalized_read,
            display_read=pr.display_read,
            confidence=pr.confidence,
            character_confidence=_parse_char_conf(pr.character_confidence),
            format_status=pr.format_status,
            quality=pr.quality,
            crop_reference=pr.crop_reference,
            observed_at=_iso_utc(pr.observed_at) or "",
            source_frame_ref=pr.source_frame_ref,
            candidates=[],
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
    plateCandidates: list[PlateCandidateResponse] = Field(default_factory=list, alias="plate_candidates")
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
        candidates = [
            PlateCandidateResponse.from_orm(c) for c in (sighting.candidates or [])
        ]

        plate_read = None
        if sighting.plate_read:
            plate_read = PlateReadResponse.from_orm(sighting.plate_read)
            plate_read.candidates = candidates

        return cls(
            sighting_id=sighting.sighting_id,
            vehicle_id=sighting.vehicle_id,
            vehicle_track_id=sighting.track_id,
            camera_id=sighting.camera_id,
            observed_at=_iso_utc(sighting.observed_at) or "",
            received_at=_iso_utc(sighting.received_at),
            vehicle_class=sighting.vehicle_class,
            vehicle_color=sighting.vehicle_color,
            vehicle_direction=sighting.vehicle_direction,
            plate_read=plate_read,
            plate_candidates=candidates,
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
    sightings: list[VehicleSightingResponse] = Field(default_factory=list)
    firstSeen: Optional[str] = Field(None, alias="first_seen")
    lastSeen: Optional[str] = Field(None, alias="last_seen")
    totalSightings: int = Field(alias="total_sightings")

    @classmethod
    def from_sightings(cls, vehicle_id: str, sightings: list[VehicleSightingResponse]) -> "VehicleHistoryResponse":
        if not sightings:
            return cls(vehicle_id=vehicle_id, sightings=[], first_seen=None, last_seen=None, total_sightings=0)

        # All observedAt values are ISO-8601 UTC (fixed offset) so lexicographic
        # ordering is chronological ordering.
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
    """ANPR summary — matches ANPRSummary in frontend types.

    Counts are plate observations, not OCR accuracy metrics. This platform does
    not compute OCR accuracy/precision/recall (no evaluation backend exists).
    """
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    totalReads: int = Field(alias="total_reads")
    readablePlates: int = Field(alias="readable_plates")
    partialReads: int = Field(alias="partial_reads")
    unreadablePlates: int = Field(alias="unreadable_plates")
    uniqueTrackedSightings: int = Field(alias="unique_tracked_sightings")
    camerasReporting: int = Field(alias="cameras_reporting")
    lastUpdated: Optional[str] = Field(None, alias="last_updated")


class SightingPageResponse(BaseModel):
    """Paginated sighting response — matches SightingPage in frontend service."""
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    sightings: list[VehicleSightingResponse] = Field(default_factory=list)
    hasMore: bool = Field(alias="has_more")
    nextCursor: Optional[str] = Field(None, alias="next_cursor")


class ANPRSearchResultResponse(BaseModel):
    """One plate-search hit with its spec §24 classification label.

    matchType is one of EXACT_NORMALIZED_MATCH | RAW_READ_MATCH |
    PARTIAL_MATCH | CANDIDATE_MATCH | RELATED_SIGHTING. Partial text
    matches are never reported as exact identity.
    """
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    sighting: VehicleSightingResponse
    matchType: str = Field(alias="match_type")


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
# Ingestion request (internal — POST /api/v1/anpr/internal/observe)
#
# These models are the INBOUND contract for edge sync / component ingestion.
# They historically accepted snake_case keys (name = camelCase, alias =
# snake_case, populate_by_name NOT enabled → validation accepts the snake_case
# alias only). Both e2e scripts and C5/C6 payloads send snake_case here, so the
# contract is preserved.
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

    sightingId: Optional[str] = Field(default=None, alias="sighting_id")
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
    candidates: list[ANPRIngestPlateCandidate] = Field(default_factory=list)


class ANPRIngestSighting(BaseModel):
    """One vehicle sighting in ingestion payload."""
    model_config = ConfigDict(extra="forbid")

    cameraId: str = Field(alias="camera_id")
    observedAt: str = Field(alias="observed_at")
    receivedAt: Optional[str] = Field(default=None, alias="received_at")
    # Optional caller-supplied sighting ID. Precedence when both are present:
    # sighting-level > plateRead-level > provider-fabricated.
    sightingId: Optional[str] = Field(default=None, alias="sighting_id")
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
            createdAt=_iso_utc(cfg.created_at) or "",
            updatedAt=_iso_utc(cfg.updated_at) or "",
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

ANPR_ERROR_CODES = frozenset({
    "SIGHTING_NOT_FOUND",
    "VEHICLE_NOT_FOUND",
    "ANPR_UNAVAILABLE",
    "PROVIDER_TIMEOUT",
    "PROVIDER_ERROR",
    "CAMERA_NOT_FOUND",
    "INVALID_QUERY",
    "INVALID_CURSOR",
    "INVALID_SIGHTING",
    "DUPLICATE_SIGHTING",
    "REVISION_CONFLICT",
    "FORBIDDEN",
})
