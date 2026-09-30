# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 7 — ANPR Provider Interface
#
# Model-agnostic interface for ANPR/OCR providers.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field
from typing import Optional

from app.domain.anpr.constants import (
    ANPRProviderHealthState,
    ANPRSource,
    PlateQuality,
    VehicleClass,
    VehicleColor,
    VehicleDirection,
    WatchlistStatus,
)


class ANPRProviderUnavailableError(Exception):
    """Raised when ANPR provider is not available."""

    def __init__(self, reason: str = "ANPR Provider is not ready.") -> None:
        super().__init__(reason)


# ─────────────────────────────────────────────────────────────────────────────
# Input: Plate Candidate from provider
# ─────────────────────────────────────────────────────────────────────────────

class PlateCandidateInput(BaseModel):
    """One OCR candidate from provider."""
    model_config = {"extra": "allow"}

    rank: int
    raw_read: str
    normalized_read: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    character_confidence: list[float] | None = None
    format_status: str = "UNKNOWN_FORMAT"


# ─────────────────────────────────────────────────────────────────────────────
# Input: Plate Read from provider
# ─────────────────────────────────────────────────────────────────────────────

class PlateReadInput(BaseModel):
    """Single plate read from provider."""
    model_config = {"extra": "allow"}

    raw_read: str
    normalized_read: str | None = None
    display_read: str
    confidence: float = Field(ge=0.0, le=1.0)
    character_confidence: list[float] | None = None
    format_status: str = "UNKNOWN_FORMAT"
    quality: str = "UNKNOWN"
    crop_reference: str | None = None
    source_frame_ref: str | None = None
    observed_at: datetime
    candidates: list[PlateCandidateInput] = []


# ─────────────────────────────────────────────────────────────────────────────
# Input: Vehicle Sighting for ingestion
# ─────────────────────────────────────────────────────────────────────────────

class VehicleSightingInput(BaseModel):
    """Vehicle sighting input from provider / detection pipeline."""
    model_config = {"extra": "allow"}

    # If the caller (edge sync / internal ingest) already assigned a
    # sighting ID, the provider must reuse it instead of fabricating one.
    sighting_id: str | None = None
    camera_id: str
    observed_at: datetime
    received_at: datetime | None = None
    vehicle_class: str = "UNKNOWN"
    vehicle_color: str | None = None
    vehicle_direction: str = "UNKNOWN"
    track_id: str | None = None
    detection_id: str | None = None
    vehicle_id: str | None = None
    plate_read: PlateReadInput | None = None
    confidence: float | None = None
    detection_quality: str | None = None
    camera_health_state: str | None = None
    camera_health_context_json: str | None = None
    location_context: str | None = None
    sector_id: str | None = None
    zone_id: str | None = None
    watchlist_status: str = "NOT_CHECKED"
    evidence_id: str | None = None
    event_id: str | None = None
    correlation_id: str | None = None
    incident_id: str | None = None
    thumbnail_url: str | None = None
    plate_crop_url: str | None = None
    source_provider: str | None = None
    sync_payload_hash: str | None = None
    edge_device_id: str | None = None


# ─────────────────────────────────────────────────────────────────────────────
# Provider output / result
# ─────────────────────────────────────────────────────────────────────────────

class ANPRObservationResult(BaseModel):
    """Result of a single sighting ingestion."""
    model_config = {"extra": "allow"}

    sighting_id: str
    vehicle_id: str | None = None
    status: Literal["CREATED", "DUPLICATE", "ERROR"] = "CREATED"
    error: str | None = None
    # Final plate observation produced by the provider for this sighting.
    # The service persists this payload; it is never overwritten on re-ingest.
    plate_read: PlateReadInput | None = None


class ANPRBatchResult(BaseModel):
    """Result of batch sighting ingestion."""
    model_config = {"extra": "allow"}

    camera_id: str
    processed_at: datetime
    total_sightings: int
    created: int
    duplicates: int
    errors: int
    results: list[ANPRObservationResult] = []
    provider_name: str | None = None
    provider_version: str | None = None
    processing_latency_ms: int | None = None


# ─────────────────────────────────────────────────────────────────────────────
# Provider Health / Metadata
# ─────────────────────────────────────────────────────────────────────────────

class ANPRProviderHealthInfo(BaseModel):
    """Provider health status."""
    model_config = {"extra": "allow"}

    state: ANPRProviderHealthState
    provider_name: str
    provider_version: str | None = None
    tracker_name: str | None = None
    tracker_version: str | None = None
    last_successful_update: datetime | None = None
    failure_count: int = 0
    queue_depth: int = 0
    processing_latency_ms: float | None = None
    cameras_active: int = 0
    note: str | None = None


class ANPRProviderMetadata(BaseModel):
    """Provider metadata / capabilities."""
    model_config = {"extra": "allow"}

    provider_name: str
    tracker_name: str | None = None
    tracker_version: str | None = None
    algorithm_version: str | None = None
    configuration_version: str | None = None
    description: str = ""
    supported_vehicle_classes: list[str] = []
    supported_plate_formats: list[str] = []
    max_batch_size: int = 50
    supports_multi_frame: bool = False
    supports_character_confidence: bool = False
    supports_quality_assessment: bool = True


# ─────────────────────────────────────────────────────────────────────────────
# Provider Interface
# ─────────────────────────────────────────────────────────────────────────────

class ANPRProvider:
    """
    Base interface for ANPR providers.

    Implementations must be model-agnostic — the backend does not
    embed any specific OCR model logic.
    """

    _PROVIDER_NAME: str = "UNKNOWN"
    _PROVIDER_VERSION: str = "0.0.0"

    async def initialize(self) -> None:
        """Initialize provider (load model, warm up, etc.)."""
        raise NotImplementedError

    def ready(self) -> bool:
        """Whether the provider is ready to accept work. Default: not ready."""
        return False

    async def recognize(
        self,
        sightings: list[VehicleSightingInput],
        camera_context: "ANPRCameraContext",
    ) -> ANPRBatchResult:
        """
        Process a batch of vehicle sightings through ANPR recognition.

        Args:
            sightings: Vehicle sightings from detection/tracking pipeline
            camera_context: Camera-specific context (health, config, etc.)

        Returns:
            Batch result with created/duplicate/error counts
        """
        raise NotImplementedError

    async def flush(self, camera_id: str) -> ANPRBatchResult:
        """Flush any pending observations for a camera."""
        raise NotImplementedError

    def health(self) -> ANPRProviderHealthInfo:
        """Get provider health status."""
        raise NotImplementedError

    def metadata(self) -> ANPRProviderMetadata:
        """Get provider metadata / capabilities."""
        raise NotImplementedError

    async def shutdown(self) -> None:
        """Graceful shutdown."""
        raise NotImplementedError


# ─────────────────────────────────────────────────────────────────────────────
# Camera Context (passed to provider)
# ─────────────────────────────────────────────────────────────────────────────

class ANPRCameraContext(BaseModel):
    """Camera context passed to provider."""
    model_config = {"extra": "allow"}

    camera_id: str
    config_id: str | None = None
    health_state: str | None = None
    health_reliability: str | None = None
    viewpoint_shift: bool = False
    region_profile: str | None = None
    sector_id: str | None = None
    zone_id: str | None = None


# ─────────────────────────────────────────────────────────────────────────────
# Provider Registry
# ─────────────────────────────────────────────────────────────────────────────

_anpr_provider: ANPRProvider | None = None


def get_anpr_provider() -> ANPRProvider | None:
    """Get the globally registered ANPR provider."""
    return _anpr_provider


def set_anpr_provider(provider: ANPRProvider) -> None:
    """Register the global ANPR provider."""
    global _anpr_provider
    _anpr_provider = provider