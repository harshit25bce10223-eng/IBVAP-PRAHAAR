# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — SQLAlchemy 2.x ORM Model: Camera Health Observation
# ─────────────────────────────────────────────────────────────────────────────
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
    Float,
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

if TYPE_CHECKING:
    from .config import CameraHealthConfig


class CameraHealthObservation(Base):
    __tablename__ = "camera_health_observations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    camera_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("camera_health_configs.camera_id"), index=True, nullable=False
    )

    # Source timestamps
    source_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    source_sequence: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Stream health
    observed_fps: Mapped[float | None] = mapped_column(Float, nullable=True)
    expected_fps: Mapped[float | None] = mapped_column(Float, nullable=True)
    frame_drop_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    frame_age_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    stream_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    reconnect_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Image quality
    sharpness_raw: Mapped[float | None] = mapped_column(Float, nullable=True)
    sharpness_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    brightness_mean: Mapped[float | None] = mapped_column(Float, nullable=True)
    brightness_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    exposure_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    contrast_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    noise_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Network health
    network_latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    network_latency_variance_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    packet_loss_percent: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Viewpoint
    viewpoint_shift_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    viewpoint_shift_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    viewpoint_status: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Overall
    background_stability: Mapped[float | None] = mapped_column(Float, nullable=True)
    overall_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    reliability: Mapped[str | None] = mapped_column(String(16), nullable=True)
    quality_flags: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Metadata
    algorithm_version: Mapped[str | None] = mapped_column(String(32), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    config: Mapped["CameraHealthConfig"] = relationship("CameraHealthConfig", backref="observations")

    # Indexes
    __table_args__ = (
        Index("ix_obs_camera_time", "camera_id", "source_timestamp"),
        Index("ix_obs_camera_received", "camera_id", "received_at"),
        Index("ix_obs_camera_status", "camera_id", "overall_status"),
        UniqueConstraint("camera_id", "source_sequence", name="uq_obs_camera_seq"),
    )