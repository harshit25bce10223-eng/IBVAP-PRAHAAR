# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 5 — SQLAlchemy 2.x ORM Model: Detection
# ─────────────────────────────────────────────────────────────────────────────
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Float,
    Boolean,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.event import Event
    from app.models.incident import Incident
    from app.models.evidence import EvidenceRecord


def _detection_id() -> str:
    return f"DET-{uuid.uuid4().hex[:10].upper()}"


class DetectionClass(str):
    PERSON = "PERSON"
    VEHICLE = "VEHICLE"
    ANIMAL = "ANIMAL"
    OBJECT = "OBJECT"
    UNKNOWN = "UNKNOWN"


class DetectionQuality(str):
    GOOD = "GOOD"
    LIMITED = "LIMITED"
    POOR = "POOR"
    UNKNOWN = "UNKNOWN"


class DetectionOcclusion(str):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    UNKNOWN = "UNKNOWN"


class DetectionState(str):
    DETECTED = "DETECTED"
    LOW_CONFIDENCE = "LOW_CONFIDENCE"
    PARTIAL = "PARTIAL"
    OCCLUDED = "OCCLUDED"
    UNKNOWN = "UNKNOWN"
    INVALID = "INVALID"
    UNAVAILABLE = "UNAVAILABLE"
    STALE = "STALE"


class DetectionSource(str):
    EDGE = "EDGE"
    CENTRAL = "CENTRAL"
    REMOTE = "REMOTE"
    DEMO = "DEMO"
    UNKNOWN = "UNKNOWN"


class DetectionFeedState(str):
    READY = "READY"
    PROCESSING = "PROCESSING"
    DEGRADED = "DEGRADED"
    UNAVAILABLE = "UNAVAILABLE"
    OFFLINE = "OFFLINE"
    STALE = "STALE"
    UNKNOWN = "UNKNOWN"
    # Feed-level availability, kept distinct from object presence:
    # NO_OBJECTS = detector answered with zero boxes (NOT unavailable)
    # UNCONFIGURED = detection not configured on this camera
    NO_OBJECTS = "NO_OBJECTS"
    UNCONFIGURED = "UNCONFIGURED"


class InferenceState(str):
    READY = "READY"
    LOADING = "LOADING"
    WARMING = "WARMING"
    PROCESSING = "PROCESSING"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    UNAVAILABLE = "UNAVAILABLE"
    UNKNOWN = "UNKNOWN"


class DetectionSyncState(str):
    LOCAL_ONLY = "LOCAL_ONLY"
    SYNC_PENDING = "SYNC_PENDING"
    SYNCED = "SYNCED"
    SYNC_FAILED = "SYNC_FAILED"
    UNKNOWN = "UNKNOWN"


class Detection(Base):
    __tablename__ = "detections"
    __table_args__ = (
        Index("ix_detections_camera_time", "camera_id", "observed_at"),
        Index("ix_detections_camera_class_time", "camera_id", "class_name", "observed_at"),
        Index("ix_detections_event", "event_id"),
        Index("ix_detections_track", "track_id"),
        Index("ix_detections_incident", "incident_id"),
        Index("ix_detections_sector", "sector_id"),
        Index("ix_detections_region", "region_profile"),
        Index("ix_detections_state", "detection_state"),
        Index("ix_detections_received", "received_at"),
    )

    detection_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=_detection_id
    )

    # Core references
    camera_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    frame_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("events.event_id"), index=True, nullable=True
    )
    track_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    incident_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("incidents.incident_id"), index=True, nullable=True
    )
    evidence_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("evidence_records.evidence_id"), index=True, nullable=True
    )

    # Classification
    class_name: Mapped[str] = mapped_column(String(32), nullable=False)
    class_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    taxonomy_version: Mapped[str | None] = mapped_column(String(16), nullable=True)
    provider_class: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Confidence & Quality
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_state: Mapped[str] = mapped_column(
        String(16), default=DetectionQuality.UNKNOWN, nullable=False
    )
    occlusion_state: Mapped[str] = mapped_column(
        String(16), default=DetectionOcclusion.UNKNOWN, nullable=False
    )
    detection_state: Mapped[str] = mapped_column(
        String(16), default=DetectionState.DETECTED, nullable=False
    )

    # Bounding box (normalized 0-1)
    bbox_x: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_y: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_width: Mapped[float] = mapped_column(Float, nullable=False)
    bbox_height: Mapped[float] = mapped_column(Float, nullable=False)

    # Frame dimensions for reconstruction
    frame_width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    frame_height: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Source & Provider
    source: Mapped[str] = mapped_column(
        String(16), default=DetectionSource.UNKNOWN, nullable=False
    )
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    runtime_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    device: Mapped[str | None] = mapped_column(String(64), nullable=True)
    inference_mode: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Post-processing
    postprocess_version: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Schema versioning
    schema_version: Mapped[str] = mapped_column(String(16), default="1.0", nullable=False)
    # (taxonomy_version is declared once, in the Classification block above)

    # Context
    region_profile: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sector_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)

    # Camera health context (nullable snapshot)
    camera_health_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    camera_health_reliability: Mapped[str | None] = mapped_column(String(16), nullable=True)
    camera_viewpoint_shift: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    camera_health_captured_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Sync (for edge)
    sync_state: Mapped[str] = mapped_column(
        String(16), default=DetectionSyncState.UNKNOWN, nullable=False
    )
    sync_payload_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    edge_device_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_event_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_sequence: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Timestamps
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Latency tracking
    inference_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    queue_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Extended payload
    payload_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    event: Mapped["Event | None"] = relationship(
        "Event", back_populates="detections"
    )
    incident: Mapped["Incident | None"] = relationship(
        "Incident", back_populates="detections"
    )
    evidence: Mapped["EvidenceRecord | None"] = relationship(
        "EvidenceRecord", back_populates="detections"
    )


class DetectionConfig(Base):
    __tablename__ = "detection_configs"
    __table_args__ = (
        Index("ix_detection_configs_camera", "camera_id"),
        Index("ix_detection_configs_active", "active"),
    )

    config_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"DETCFG-{uuid.uuid4().hex[:10].upper()}"
    )
    camera_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    model_version: Mapped[str | None] = mapped_column(String(64), nullable=True)

    source: Mapped[str] = mapped_column(String(16), default=DetectionSource.EDGE, nullable=False)

    # Inference config
    confidence_threshold: Mapped[float] = mapped_column(Float, default=0.3, nullable=False)
    iou_threshold: Mapped[float] = mapped_column(Float, default=0.5, nullable=False)
    max_detections: Mapped[int] = mapped_column(Integer, default=100, nullable=False)

    # Sampling
    sample_rate: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    min_frame_interval_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Post-processing
    nms_enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    clip_bbox: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    class_remap_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Throttling
    max_inference_rate_per_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    queue_size_limit: Mapped[int] = mapped_column(Integer, default=50, nullable=False)

    # Edge sync
    enable_edge_sync: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    sync_interval_sec: Mapped[int] = mapped_column(Integer, default=60, nullable=False)

    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    activated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)