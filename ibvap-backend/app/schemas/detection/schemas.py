# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 5 — Detection Schemas
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Enums ─────────────────────────────────────────────────────────────────────

DetectionClass = Literal["PERSON", "VEHICLE", "ANIMAL", "OBJECT", "UNKNOWN"]

DetectionQuality = Literal["GOOD", "LIMITED", "POOR", "UNKNOWN"]

DetectionOcclusion = Literal["LOW", "MEDIUM", "HIGH", "UNKNOWN"]

DetectionState = Literal[
    "DETECTED",
    "LOW_CONFIDENCE",
    "PARTIAL",
    "OCCLUDED",
    "UNKNOWN",
    "INVALID",
    "UNAVAILABLE",
    "STALE",
]

DetectionSource = Literal["EDGE", "CENTRAL", "REMOTE", "DEMO", "UNKNOWN"]

DetectionFeedState = Literal[
    "READY",
    "NO_OBJECTS",
    "UNCONFIGURED",
    "PROCESSING",
    "DEGRADED",
    "UNAVAILABLE",
    "OFFLINE",
    "STALE",
    "UNKNOWN",
]

InferenceState = Literal["READY", "LOADING", "WARMING", "PROCESSING", "DEGRADED", "FAILED", "UNAVAILABLE", "UNKNOWN"]

DetectionSyncState = Literal["LOCAL_ONLY", "SYNC_PENDING", "SYNCED", "SYNC_FAILED", "UNKNOWN"]


# ── Core Models ───────────────────────────────────────────────────────────────

class BoundingBox(BaseModel):
    """Normalized bounding box (0-1)."""
    model_config = ConfigDict(extra="forbid")
    x: float = Field(ge=0.0, le=1.0)
    y: float = Field(ge=0.0, le=1.0)
    width: float = Field(ge=0.0, le=1.0)
    height: float = Field(ge=0.0, le=1.0)


class CameraHealthContext(BaseModel):
    """Camera health snapshot at detection time."""
    model_config = ConfigDict(extra="allow", from_attributes=True)
    state: Optional[str] = None
    reliability: Optional[str] = None
    viewpoint_shift: Optional[bool] = None
    captured_at: Optional[str] = None


class ProviderMetadata(BaseModel):
    """Inference provider metadata."""
    model_config = ConfigDict(extra="allow", from_attributes=True)
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    runtime_version: Optional[str] = None
    device: Optional[str] = None
    inference_mode: Optional[str] = None
    postprocess_version: Optional[str] = None


class EdgeSyncInfo(BaseModel):
    """Edge synchronization information."""
    model_config = ConfigDict(extra="allow", from_attributes=True)
    sync_state: Optional[str] = None
    payload_hash: Optional[str] = None
    edge_device_id: Optional[str] = None
    source_event_id: Optional[str] = None
    source_sequence: Optional[int] = None


class LatencyInfo(BaseModel):
    """Latency breakdown."""
    model_config = ConfigDict(extra="allow", from_attributes=True)
    inference_ms: Optional[int] = None
    queue_ms: Optional[int] = None
    total_ms: Optional[int] = None


# ── Summary / List Models ─────────────────────────────────────────────────────

class DetectionSummary(BaseModel):
    """Lightweight detection for lists."""
    model_config = ConfigDict(extra="allow", from_attributes=True)
    
    detection_id: str
    camera_id: str
    frame_id: Optional[str] = None
    event_id: Optional[str] = None
    track_id: Optional[str] = None
    incident_id: Optional[str] = None
    evidence_id: Optional[str] = None
    
    class_name: str
    class_id: Optional[int] = None
    confidence: Optional[float] = None
    
    bbox: BoundingBox
    frame_width: Optional[int] = None
    frame_height: Optional[int] = None
    
    quality_state: str
    occlusion_state: str
    detection_state: str
    
    source: str
    provider: Optional[str] = None
    
    observed_at: str
    received_at: str
    processed_at: Optional[str] = None
    
    camera_health_context: Optional[CameraHealthContext] = None
    provider_metadata: Optional[ProviderMetadata] = None
    edge_sync: Optional[EdgeSyncInfo] = None
    latency: Optional[LatencyInfo] = None


class DetectionPage(BaseModel):
    """Paginated detection list."""
    model_config = ConfigDict(extra="allow")
    detections: list[DetectionSummary]
    total: int
    page: int
    page_size: int


# ── Detail Models ─────────────────────────────────────────────────────────────

class DetectionDetailResponse(BaseModel):
    """Full detection detail."""
    model_config = ConfigDict(extra="allow", from_attributes=True)
    
    detection_id: str
    camera_id: str
    frame_id: Optional[str] = None
    event_id: Optional[str] = None
    track_id: Optional[str] = None
    incident_id: Optional[str] = None
    evidence_id: Optional[str] = None
    
    class_name: str
    class_id: Optional[int] = None
    taxonomy_version: Optional[str] = None
    provider_class: Optional[str] = None
    confidence: Optional[float] = None
    
    bbox: BoundingBox
    frame_width: Optional[int] = None
    frame_height: Optional[int] = None
    
    quality_state: str
    occlusion_state: str
    detection_state: str
    
    source: str
    provider: Optional[str] = None
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    runtime_version: Optional[str] = None
    device: Optional[str] = None
    inference_mode: Optional[str] = None
    postprocess_version: Optional[str] = None
    
    schema_version: str
    taxonomy_version: Optional[str] = None
    region_profile: Optional[str] = None
    sector_id: Optional[str] = None
    
    camera_health_context: Optional[CameraHealthContext] = None
    provider_metadata: Optional[ProviderMetadata] = None
    edge_sync: Optional[EdgeSyncInfo] = None
    latency: Optional[LatencyInfo] = None
    
    # Read-only soft reference to a Component 7 ANPR sighting that cites this
    # detection (e.g. SIGHT-...). Never implies plate identity — C7 remains
    # authoritative for that record.
    anpr_ref: Optional[str] = None
    
    observed_at: str
    received_at: str
    processed_at: Optional[str] = None
    
    inference_latency_ms: Optional[int] = None
    queue_latency_ms: Optional[int] = None
    payload_json: Optional[str] = None


# ── Camera Summary Models ─────────────────────────────────────────────────────

class CameraDetectionSummary(BaseModel):
    """Detection summary for a camera."""
    model_config = ConfigDict(extra="allow")
    
    camera_id: str
    total_detections: int
    by_class: dict[str, int]
    low_confidence_count: int
    quality_summary: dict[str, int]
    last_observed_at: Optional[str] = None
    from_time: Optional[str] = None
    to_time: Optional[str] = None


class InferenceHealthResponse(BaseModel):
    """Inference provider health."""
    model_config = ConfigDict(extra="allow")
    camera_id: str
    state: str
    last_successful_inference: Optional[str] = None
    recent_failures: int = 0
    queue_depth: int = 0
    avg_latency_ms: float = 0.0
    model_name: Optional[str] = None
    model_version: Optional[str] = None


class DetectionFeedResponse(BaseModel):
    """
    Composed camera detection feed: pipeline availability + recent detections.

    Availability is deliberately separated from object presence:
    - UNCONFIGURED / UNAVAILABLE / OFFLINE / STALE never mean "no objects"
    - NO_OBJECTS means the provider answered with zero detections
    - READY means the provider answered and at least one detection is shown
    All values are derived from stored state and the actual provider health —
    never fabricated and never silently replaced by demo data.
    """
    model_config = ConfigDict(extra="allow")

    camera_id: str
    state: DetectionFeedState
    inference: InferenceState
    # Newest observed_at among the returned detections; None when none exist.
    last_updated_at: Optional[str] = None
    detections: list[DetectionSummary] = []


# ── Config Models ─────────────────────────────────────────────────────────────

class DetectionConfigBase(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True)
    config_id: str
    camera_id: str
    provider: str
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    source: str
    confidence_threshold: float
    iou_threshold: float
    max_detections: int
    sample_rate: float
    min_frame_interval_ms: int
    nms_enabled: bool
    clip_bbox: bool
    class_remap_json: Optional[dict] = None
    max_inference_rate_per_sec: Optional[int] = None
    queue_size_limit: int
    enable_edge_sync: bool
    sync_interval_sec: int
    active: bool
    revision: int
    created_at: datetime
    updated_at: datetime
    activated_at: Optional[datetime] = None


class DetectionConfigCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    camera_id: str
    provider: str = "edge"
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    source: str = "EDGE"
    confidence_threshold: float = Field(default=0.3, ge=0.0, le=1.0)
    iou_threshold: float = Field(default=0.5, ge=0.0, le=1.0)
    max_detections: int = Field(default=100, ge=1, le=1000)
    sample_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    min_frame_interval_ms: int = Field(default=0, ge=0)
    nms_enabled: bool = True
    clip_bbox: bool = True
    class_remap_json: Optional[dict] = None
    max_inference_rate_per_sec: Optional[int] = None
    queue_size_limit: int = Field(default=50, ge=1, le=500)
    enable_edge_sync: bool = False
    sync_interval_sec: int = Field(default=60, ge=1)


class DetectionConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="allow")
    provider: Optional[str] = None
    model_name: Optional[str] = None
    model_version: Optional[str] = None
    source: Optional[str] = None
    confidence_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    iou_threshold: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    max_detections: Optional[int] = Field(default=None, ge=1, le=1000)
    sample_rate: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    min_frame_interval_ms: Optional[int] = Field(default=None, ge=0)
    nms_enabled: Optional[bool] = None
    clip_bbox: Optional[bool] = None
    class_remap_json: Optional[dict] = None
    max_inference_rate_per_sec: Optional[int] = None
    queue_size_limit: Optional[int] = Field(default=None, ge=1, le=500)
    enable_edge_sync: Optional[bool] = None
    sync_interval_sec: Optional[int] = Field(default=None, ge=1)
    active: Optional[bool] = None


class DetectionConfigResponse(DetectionConfigBase):
    pass


# ── Ingestion Models ──────────────────────────────────────────────────────────

class RawDetection(BaseModel):
    """Raw detection from inference provider (before normalization)."""
    model_config = ConfigDict(extra="allow")
    class_id: int
    class_name: str
    confidence: float
    bbox: list[float]
    bbox_format: str = "xyxy_norm"
    occlusion: Optional[float] = None
    quality: Optional[str] = None
    metadata: Optional[dict] = None


class InferenceResult(BaseModel):
    """Raw inference result from provider."""
    model_config = ConfigDict(extra="allow")
    frame_id: str
    camera_id: str
    detections: list[RawDetection]
    inference_latency_ms: int
    model_name: str
    model_version: str
    provider: str
    device: Optional[str] = None
    runtime_version: Optional[str] = None
    timestamp: Optional[str] = None


class EdgeConfig(BaseModel):
    """Edge ingestion configuration."""
    model_config = ConfigDict(extra="allow")
    sync_state: str = "LOCAL_ONLY"
    payload_hash: Optional[str] = None
    edge_device_id: Optional[str] = None
    source_event_id: Optional[str] = None
    source_sequence: Optional[int] = None


class CameraHealthContextRequest(BaseModel):
    """Camera health context for ingestion."""
    model_config = ConfigDict(extra="allow")
    state: Optional[str] = None
    reliability: Optional[str] = None
    viewpoint_shift: Optional[bool] = None
    captured_at: Optional[str] = None


class DetectionIngestRequest(BaseModel):
    """Internal detection ingestion request."""
    model_config = ConfigDict(extra="allow")
    camera_id: str
    frame_id: str
    frame_width: int
    frame_height: int
    observed_at: str
    detections: list[RawDetection]
    provider: str = "EDGE"
    model_name: str
    model_version: str
    runtime_version: Optional[str] = None
    device: Optional[str] = None
    inference_latency_ms: int
    edge_config: Optional[EdgeConfig] = None
    camera_health_context: Optional[CameraHealthContextRequest] = None


class DetectionIngestResponse(BaseModel):
    """Response for detection ingestion."""
    model_config = ConfigDict(extra="allow")
    created: int = 0
    skipped: int = 0
    errors: list[str] = []
    detection_ids: list[str] = []


# ── Export Models ─────────────────────────────────────────────────────────────

class DetectionExportRequest(BaseModel):
    """Export detection data."""
    model_config = ConfigDict(extra="allow")
    camera_id: Optional[str] = None
    from_time: Optional[str] = None
    to_time: Optional[str] = None
    class_name: Optional[str] = None
    format: str = "json"  # json, csv, parquet
    include_images: bool = False


class DetectionExportResponse(BaseModel):
    """Export response."""
    model_config = ConfigDict(extra="allow")
    export_id: str
    state: str  # REQUESTED, READY, FAILED
    download_url: Optional[str] = None
    expires_at: Optional[str] = None