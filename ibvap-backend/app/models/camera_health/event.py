# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — SQLAlchemy 2.x ORM Model: Camera Health Event
# ─────────────────────────────────────────────────────────────────────────────
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class HealthEventType(str):
    CAMERA_OFFLINE = "CAMERA_OFFLINE"
    CAMERA_RECOVERED = "CAMERA_RECOVERED"
    STREAM_STALE = "STREAM_STALE"
    FRAME_FROZEN = "FRAME_FROZEN"
    IMAGE_QUALITY_DEGRADED = "IMAGE_QUALITY_DEGRADED"
    SHARPNESS_DEGRADING = "SHARPNESS_DEGRADING"
    MAINTENANCE_RECOMMENDED = "MAINTENANCE_RECOMMENDED"
    VIEWPOINT_SHIFT_DETECTED = "VIEWPOINT_SHIFT_DETECTED"
    VIEWPOINT_SHIFT_CLEARED = "VIEWPOINT_SHIFT_CLEARED"
    NETWORK_DEGRADED = "NETWORK_DEGRADED"
    NETWORK_RECOVERED = "NETWORK_RECOVERED"
    TELEMETRY_UNAVAILABLE = "TELEMETRY_UNAVAILABLE"


class HealthEventSeverity(str):
    INFO = "INFO"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class CameraHealthEvent(Base):
    __tablename__ = "camera_health_events"

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"HEV-{uuid.uuid4().hex[:12].upper()}")
    camera_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("camera_health_configs.camera_id"), index=True, nullable=False
    )

    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), default=HealthEventSeverity.WARNING)

    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cleared_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    occurrence_count: Mapped[int] = mapped_column(Integer, default=1)
    deduplication_key: Mapped[str] = mapped_column(String(256), unique=True, index=True, nullable=False)

    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    operational_impact: Mapped[str | None] = mapped_column(Text, nullable=True)

    payload_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Indexes
    __table_args__ = (
        Index("ix_health_events_camera_type", "camera_id", "event_type"),
        Index("ix_health_events_camera_first_seen", "camera_id", "first_seen"),
        Index("ix_health_events_camera_last_seen", "camera_id", "last_seen"),
        Index("ix_health_events_dedup", "deduplication_key", unique=True),
    )