# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 6 — TrackingProvider Abstract Interface
#
# This is the model-agnostic boundary between the tracking domain and any
# actual tracker implementation (future: ByteTrack, BoT-SORT, DeepSORT, etc.).
#
# The domain never depends on tracker-specific output.
# Provider output flows through an adapter/normalizer into canonical
# Track + TrackObservation records.
#
# Interface contract:
#   initialize()    — prepare provider state (load weights, warm up, etc.)
#   ready()         — returns True if provider can accept updates
#   update()        — process a list of DetectionInput objects for one camera
#   flush()         — force output of any buffered state
#   health()        — return ProviderHealthInfo (no fake values)
#   metadata()      — return ProviderMetadata (version info, null if unknown)
#   shutdown()      — clean up resources
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.domain.tracking.constants import (
    PROVIDER_READY,
    PROVIDER_UNAVAILABLE,
    PROVIDER_UNKNOWN,
    AssociationResult,
)


# ─────────────────────────────────────────────────────────────────────────────
# Data transfer objects (provider input / output)
# These are pure Python dataclasses — no ORM, no Pydantic.
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class DetectionInput:
    """
    Minimal detection payload consumed by the tracking provider.
    Derived from Component 5 Detection — never duplicates the Detection table.
    """
    detection_id: str
    camera_id: str
    observed_at: datetime
    bbox_x: float
    bbox_y: float
    bbox_width: float
    bbox_height: float
    object_class: str
    confidence: float | None
    quality: str | None
    occlusion: str | None
    source: str
    frame_id: str | None = None
    frame_number: int | None = None
    region_profile: str | None = None
    sector_id: str | None = None
    # Provider may use health context for camera-motion compensation
    camera_health_state: str | None = None
    camera_health_reliability: str | None = None
    camera_viewpoint_shift: bool | None = None


@dataclass
class TrackAssignment:
    """
    Provider output: how one detection was associated.

    result: MATCHED_TO_TRACK | NEW_TRACK | UNMATCHED | REJECTED
    track_id: existing track (if MATCHED) or newly allocated (if NEW_TRACK)
    is_new_track: True when the provider created a new track identity
    sequence: observation sequence within the track
    continuity_quality: STRONG | MODERATE | WEAK | UNKNOWN (provider-assessed)
    confidence: provider confidence in this assignment (nullable — never fabricated)
    velocity: m/s if provider supplies it (nullable)
    speed: m/s scalar if provider supplies it (nullable)
    direction: text label if provider supplies it (nullable)
    provider_track_id: internal provider ID (may differ from canonical track_id)
    """
    detection_id: str
    result: str  # AssociationResult literal
    track_id: str | None = None
    is_new_track: bool = False
    sequence: int | None = None
    continuity_quality: str | None = None
    confidence: float | None = None
    velocity: float | None = None
    speed: float | None = None
    direction: str | None = None
    provider_track_id: str | None = None
    reason: str | None = None


@dataclass
class ProviderUpdateResult:
    """
    Output of a single provider.update() call for one camera frame/batch.
    """
    camera_id: str
    processed_at: datetime
    assignments: list[TrackAssignment] = field(default_factory=list)
    tracks_ended: list[str] = field(default_factory=list)   # track_ids provider ended
    tracks_lost: list[str] = field(default_factory=list)    # track_ids provider marked lost
    tracks_reacquired: list[str] = field(default_factory=list)
    provider_name: str | None = None
    provider_version: str | None = None
    configuration_version: str | None = None
    processing_latency_ms: int | None = None


@dataclass(frozen=True)
class ProviderHealthInfo:
    """
    Provider health snapshot — no fake metrics.
    Only values the provider can actually observe.
    """
    state: str              # ProviderHealthState literal
    provider_name: str
    provider_version: str | None
    last_successful_update: datetime | None
    failure_count: int
    queue_depth: int
    processing_latency_ms: float | None  # last observed, not a fabricated average
    cameras_active: int
    note: str | None = None


@dataclass(frozen=True)
class ProviderMetadata:
    """
    Version and configuration provenance for reproducibility.
    All fields nullable — never fabricate if unavailable.
    """
    provider_name: str
    tracker_name: str | None = None
    tracker_version: str | None = None
    algorithm_version: str | None = None
    configuration_version: str | None = None
    description: str | None = None


@dataclass
class CameraContext:
    """
    Contextual signals for one camera passed into provider.update().
    Contains Camera Health snapshot from Component 2 (never calculated here).
    """
    camera_id: str
    health_state: str | None = None
    health_reliability: str | None = None
    viewpoint_shift: bool = False
    region_profile: str | None = None
    sector_id: str | None = None


# ─────────────────────────────────────────────────────────────────────────────
# Abstract interface
# ─────────────────────────────────────────────────────────────────────────────

class TrackingProvider(ABC):
    """
    Model-agnostic tracking provider interface.

    Future implementations may wrap:
      · ByteTrack  (§3 research-informed: uses lower-score detections)
      · BoT-SORT   (§3 research-informed: camera-motion compensation)
      · DeepSORT   (§3 research-informed: appearance Re-ID)
      · Any custom SSB-specific tracker

    NONE of those are implemented here. This interface is the boundary.
    The domain layer (TrackAssociationService) calls this interface only.
    """

    @abstractmethod
    async def initialize(self) -> None:
        """Prepare provider (warm up, load state, etc.)."""

    @abstractmethod
    def ready(self) -> bool:
        """Returns True if the provider can accept update() calls."""

    @abstractmethod
    async def update(
        self,
        detections: list[DetectionInput],
        context: CameraContext,
    ) -> ProviderUpdateResult:
        """
        Process a batch of detections for one camera.
        Returns association results + lifecycle events.
        Must be idempotent for same (detection_id, camera_id, observed_at).
        """

    @abstractmethod
    async def flush(self, camera_id: str) -> ProviderUpdateResult:
        """Force output of any buffered/pending state for one camera."""

    @abstractmethod
    def health(self) -> ProviderHealthInfo:
        """Return current provider health. No fake values."""

    @abstractmethod
    def metadata(self) -> ProviderMetadata:
        """Return version/configuration provenance."""

    @abstractmethod
    async def shutdown(self) -> None:
        """Release resources cleanly."""


# ─────────────────────────────────────────────────────────────────────────────
# Global provider registry
# ─────────────────────────────────────────────────────────────────────────────

_tracking_provider: TrackingProvider | None = None


def get_tracking_provider() -> TrackingProvider | None:
    return _tracking_provider


def set_tracking_provider(provider: TrackingProvider) -> None:
    global _tracking_provider
    _tracking_provider = provider


def require_tracking_provider() -> TrackingProvider:
    p = _tracking_provider
    if p is None:
        raise RuntimeError(
            "No TrackingProvider registered. "
            "Call set_tracking_provider() during application startup."
        )
    return p
