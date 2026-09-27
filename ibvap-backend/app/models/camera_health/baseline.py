# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — SQLAlchemy 2.x ORM Model: Camera Health Baseline
# ─────────────────────────────────────────────────────────────────────────────
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base


class IlluminationRegime(str):
    DAY = "DAY"
    LOW_LIGHT = "LOW_LIGHT"
    NIGHT = "NIGHT"
    IR = "IR"
    UNKNOWN = "UNKNOWN"


class CameraHealthBaseline(Base):
    __tablename__ = "camera_health_baselines"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    camera_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("camera_health_configs.camera_id"), index=True, nullable=False
    )

    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)
    illumination_regime: Mapped[str] = mapped_column(String(16), default=IlluminationRegime.UNKNOWN)

    baseline_version: Mapped[int] = mapped_column(Integer, default=1)
    sample_count: Mapped[int] = mapped_column(Integer, default=0)

    # Robust statistics
    median_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    mad_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    p05: Mapped[float | None] = mapped_column(Float, nullable=True)
    p95: Mapped[float | None] = mapped_column(Float, nullable=True)
    ewma_value: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Metadata
    reference_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_frozen: Mapped[bool] = mapped_column(default=False)
    algorithm_version: Mapped[str | None] = mapped_column(String(32), nullable=True)

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
        UniqueConstraint("camera_id", "metric_name", "illumination_regime", name="uq_baseline_camera_metric_regime"),
        Index("ix_baseline_camera_metric", "camera_id", "metric_name"),
    )