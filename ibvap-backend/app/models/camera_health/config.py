# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — SQLAlchemy 2.x ORM Model: Camera Health Config
# ─────────────────────────────────────────────────────────────────────────────
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum as SQLEnum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class DeploymentProfile(str):
    INDO_NEPAL_FOOTHILL_PLAINS = "INDO_NEPAL_FOOTHILL_PLAINS"
    INDO_NEPAL_RURAL_FRINGE = "INDO_NEPAL_RURAL_FRINGE"
    INDO_BHUTAN_HILLY_FOREST = "INDO_BHUTAN_HILLY_FOREST"
    MIXED_BORDER_SECTOR = "MIXED_BORDER_SECTOR"


class IlluminationMode(str):
    DAY = "DAY"
    LOW_LIGHT = "LOW_LIGHT"
    NIGHT = "NIGHT"
    IR = "IR"
    UNKNOWN = "UNKNOWN"


class CameraHealthConfig(Base):
    __tablename__ = "camera_health_configs"

    camera_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, index=True
    )

    # Expected stream properties
    expected_fps: Mapped[float] = mapped_column(Float, default=25.0)
    stale_after_seconds: Mapped[int] = mapped_column(Integer, default=30)
    offline_after_seconds: Mapped[int] = mapped_column(Integer, default=120)
    freeze_window_seconds: Mapped[int] = mapped_column(Integer, default=10)

    # Sampling
    health_sampling_interval_seconds: Mapped[int] = mapped_column(Integer, default=5)

    # Deployment profile
    region_profile: Mapped[str] = mapped_column(
        String(64), default=DeploymentProfile.MIXED_BORDER_SECTOR
    )
    terrain_profile: Mapped[str] = mapped_column(String(64), nullable=True)
    illumination_mode: Mapped[str] = mapped_column(
        String(32), default=IlluminationMode.DAY
    )
    timezone: Mapped[str] = mapped_column(String(64), default="UTC")

    # Viewpoint detection sensitivity
    viewpoint_shift_threshold: Mapped[float] = mapped_column(Float, default=0.3)
    min_feature_matches: Mapped[int] = mapped_column(Integer, default=10)
    min_ransac_inlier_ratio: Mapped[float] = mapped_column(Float, default=0.5)

    # Image quality thresholds (camera-specific overrides)
    sharpness_degraded_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    brightness_low_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)
    brightness_high_threshold: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Trend settings
    trend_window_days: Mapped[int] = mapped_column(Integer, default=7)
    trend_persistence_days: Mapped[int] = mapped_column(Integer, default=3)
    baseline_adaptation_rate: Mapped[float] = mapped_column(Float, default=0.1)

    # Retention
    observation_retention_days: Mapped[int] = mapped_column(Integer, default=30)
    event_retention_days: Mapped[int] = mapped_column(Integer, default=90)

    # Status
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )