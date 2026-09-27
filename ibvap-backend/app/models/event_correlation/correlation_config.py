# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 4 — SQLAlchemy 2.x ORM Model: Correlation Configuration
# ─────────────────────────────────────────────────────────────────────────────
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from .correlation_group import CorrelationGroup


def _config_id() -> str:
    return f"CFC-{uuid.uuid4().hex[:10].upper()}"


class CorrelationConfigProfile(str):
    INDO_NEPAL_FOOTHILL_PLAINS = "INDO_NEPAL_FOOTHILL_PLAINS"
    INDO_NEPAL_RURAL_FRINGE = "INDO_NEPAL_RURAL_FRINGE"
    INDO_BHUTAN_HILLY_FOREST = "INDO_BHUTAN_HILLY_FOREST"
    MIXED_BORDER_SECTOR = "MIXED_BORDER_SECTOR"


class CorrelationConfig(Base):
    __tablename__ = "correlation_configs"
    __table_args__ = (
        Index("ix_correlation_configs_profile", "profile"),
        Index("ix_correlation_configs_active", "active"),
    )

    config_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"CFC-{uuid.uuid4().hex[:10].upper()}"
    )

    # Profile this config belongs to
    profile: Mapped[str] = mapped_column(String(64), default=CorrelationConfigProfile.MIXED_BORDER_SECTOR, nullable=False)

    # Event type pair specific rules (e.g., "ZONE_ENTRY:DETECTION")
    event_pair: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Temporal window in seconds
    temporal_window_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False)

    # Spatial window in meters (when GPS available)
    spatial_window_meters: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Camera adjacency override
    camera_adjacency: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Minimum relationship strength (0-100)
    min_relationship_strength: Mapped[int] = mapped_column(Integer, default=50, nullable=False)

    # Maximum group duration in seconds
    max_group_duration_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)

    # Minimum support events for correlation
    min_support_events: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Event-type compatibility matrix
    compatibility_matrix: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Temporal windows per event type
    temporal_windows: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Spatial windows per deployment profile
    spatial_windows: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Profile this config belongs to
    profile: Mapped[str] = mapped_column(String(64), default=CorrelationConfigProfile.MIXED_BORDER_SECTOR, nullable=False)

    # Active flag
    active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Revision
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Timestamps
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