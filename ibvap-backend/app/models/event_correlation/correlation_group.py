# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 4 — SQLAlchemy 2.x ORM Model: Correlation Group
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
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from .correlation_member import CorrelationGroupMember
    from .correlation_relationship import CorrelationRelationship
    from .correlation_history import CorrelationHistory


def _correlation_id() -> str:
    return f"COR-{uuid.uuid4().hex[:10].upper()}"


class CorrelationStatus(str):
    STANDALONE = "STANDALONE"
    RELATED = "RELATED"
    CORRELATED = "CORRELATED"
    UNCERTAIN = "UNCERTAIN"
    DISSOLVED = "DISSOLVED"
    UNKNOWN = "UNKNOWN"


class CorrelationGroupState(str):
    OPEN = "OPEN"
    ACTIVE = "ACTIVE"
    STABLE = "STABLE"
    RESOLVED = "RESOLVED"
    DISSOLVED = "DISSOLVED"
    UNKNOWN = "UNKNOWN"


class CorrelationCompleteness(str):
    COMPLETE = "COMPLETE"
    PARTIAL = "PARTIAL"
    UNKNOWN = "UNKNOWN"


class CorrelationGroup(Base):
    __tablename__ = "correlation_groups"
    __table_args__ = (
        Index("ix_correlation_groups_status", "status"),
        Index("ix_correlation_groups_started_at", "started_at"),
        Index("ix_correlation_groups_sector", "sector_id"),
        Index("ix_correlation_groups_incident", "incident_id"),
    )

    correlation_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"COR-{uuid.uuid4().hex[:10].upper()}"
    )
    incident_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("incidents.incident_id"), index=True, nullable=True
    )
    primary_event_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("events.event_id"), index=True, nullable=True
    )

    # Canonical status from the correlation state machine
    status: Mapped[str] = mapped_column(
        String(16), default=CorrelationStatus.STANDALONE, nullable=False
    )

    # Group state for display/logic
    state: Mapped[str] = mapped_column(
        String(16), default="OPEN", nullable=False
    )

    # Spatial context
    sector_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    region_profile: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Time window
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Aggregated counts
    event_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    camera_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    zone_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    source_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Correlation confidence (0-100) when provided by the rule engine
    confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Completeness of the correlation
    completeness: Mapped[str] = mapped_column(
        String(16), default=CorrelationCompleteness.UNKNOWN, nullable=False
    )

    # Uncertainty context
    uncertainty_reliability: Mapped[str | None] = mapped_column(
        String(16), nullable=True
    )
    uncertainty_note: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Track candidate information
    track_candidate_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    track_candidate_confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)
    track_candidate_label: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Camera chain order
    camera_chain: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Modalities involved
    modalities: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Sources involved
    sources: Mapped[list | None] = mapped_column(JSON, nullable=True)

    # Health context for supporting cameras
    health_context: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Evidence count
    evidence_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Connectivity status
    connectivity: Mapped[str] = mapped_column(String(16), default="LIVE", nullable=False)

    # Duplication/suppression flag
    duplicated_or_suppressed: Mapped[bool] = mapped_column(default=False, nullable=False)

    # Revision for optimistic locking/history
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Algorithm and configuration version
    algorithm_version: Mapped[str] = mapped_column(String(32), default="1.0", nullable=False)
    configuration_version: Mapped[str] = mapped_column(String(32), default="1.0", nullable=False)

    # Timestamps
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    members: Mapped[list["CorrelationGroupMember"]] = relationship(
        "CorrelationGroupMember", back_populates="group", cascade="all, delete-orphan"
    )
    relationships: Mapped[list["CorrelationRelationship"]] = relationship(
        "CorrelationRelationship", back_populates="group", cascade="all, delete-orphan"
    )
    history: Mapped[list["CorrelationHistory"]] = relationship(
        "CorrelationHistory", back_populates="group", cascade="all, delete-orphan"
    )