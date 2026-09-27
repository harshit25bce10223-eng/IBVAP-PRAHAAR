# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 4 — SQLAlchemy 2.x ORM Model: Correlation Relationship
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
    from ..event import Event


def _relationship_id() -> str:
    return f"REL-{uuid.uuid4().hex[:10].upper()}"


class CorrelationRelationType(str):
    TEMPORAL = "TEMPORAL"
    SPATIAL = "SPATIAL"
    ENTITY = "ENTITY"
    CAMERA = "CAMERA"
    ZONE = "ZONE"
    SEQUENCE = "SEQUENCE"
    SUPPORTING = "SUPPORTING"
    CONTEXTUAL = "CONTEXTUAL"


class CorrelationRelationship(Base):
    __tablename__ = "correlation_relationships"
    __table_args__ = (
        Index("ix_correlation_rels_group", "correlation_id"),
        Index("ix_correlation_rels_from", "from_event_id"),
        Index("ix_correlation_rels_to", "to_event_id"),
        Index("ix_correlation_rels_type", "type"),
    )

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"REL-{uuid.uuid4().hex[:10].upper()}"
    )
    correlation_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("correlation_groups.correlation_id"), index=True, nullable=False
    )
    from_event_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("events.event_id"), index=True, nullable=False
    )
    to_event_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("events.event_id"), index=True, nullable=False
    )

    # Type of relationship
    type: Mapped[str] = mapped_column(String(16), nullable=False)

    # Relationship strength (0-100) when provided
    strength: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Evidence for this relationship
    evidence_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Explanation for this relationship
    explanation: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Algorithm version that created this relationship
    algorithm_version: Mapped[str] = mapped_column(String(32), default="1.0", nullable=False)

    # Revision for optimistic locking
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

    # Relationships
    group: Mapped["CorrelationGroup"] = relationship(
        "CorrelationGroup", back_populates="relationships"
    )
    from_event: Mapped["Event"] = relationship(
        "Event", foreign_keys=[from_event_id]
    )
    to_event: Mapped["Event"] = relationship(
        "Event", foreign_keys=[to_event_id]
    )