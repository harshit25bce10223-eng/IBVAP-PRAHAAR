# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — SQLAlchemy 2.x ORM Model: Camera Health Current State (Snapshot)
# ─────────────────────────────────────────────────────────────────────────────
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class CameraHealthCurrent(Base):
    __tablename__ = "camera_health_current"

    camera_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("camera_health_configs.camera_id"), primary_key=True
    )

    # Overall state
    overall_status: Mapped[str] = mapped_column(String(16), nullable=False, default="UNKNOWN")
    status_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    reliability: Mapped[str] = mapped_column(String(16), nullable=True)

    # Stream
    stream_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    fps: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_fps: Mapped[float | None] = mapped_column(Float, nullable=True)
    frame_drop_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    stale_seconds: Mapped[float | None] = mapped_column(Float, nullable=True)
    reconnect_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Image quality
    image_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    sharpness_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    sharpness_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    sharpness_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    brightness_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    brightness_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    brightness_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    exposure_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    noise_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    background_stability: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Network
    network_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    latency_variance_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    packet_loss_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    heartbeat_age_sec: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Viewpoint
    viewpoint_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    shift_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    shift_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    shift_detected: Mapped[bool] = mapped_column(default=False)
    shift_detected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    fence_confidence_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Trends (JSON for flexibility)
    trends_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Issues (JSON)
    issues_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Operational impact
    impact_level: Mapped[str | None] = mapped_column(String(16), nullable=True)
    coverage: Mapped[str | None] = mapped_column(String(16), nullable=True)
    affected_modules: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    impact_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Maintenance
    maintenance_recommended: Mapped[bool] = mapped_column(default=False)
    maintenance_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    maintenance_duration: Mapped[str | None] = mapped_column(Text, nullable=True)
    maintenance_impact_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Data source
    data_source: Mapped[str] = mapped_column(String(16), default="UNAVAILABLE")
    last_updated: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_known_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    last_known_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Metadata
    algorithm_version: Mapped[str | None] = mapped_column(String(32), nullable=True)

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Indexes
    __table_args__ = (
        Index("ix_health_current_status", "overall_status"),
        Index("ix_health_current_updated", "last_updated"),
    )