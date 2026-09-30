# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 4 — SQLAlchemy 2.x ORM Model: Correlation Group Member
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
    UniqueConstraint,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from .correlation_group import CorrelationGroup
    from ..event import Event


def _membership_id() -> str:
    return f"MEM-{uuid.uuid4().hex[:10].upper()}"


class MembershipType(str):
    PRIMARY = "PRIMARY"
    SUPPORTING = "SUPPORTING"
    CONTEXT = "CONTEXT"
    UNCERTAIN = "UNCERTAIN"


class CorrelationGroupMember(Base):
    __tablename__ = "correlation_group_members"
    __table_args__ = (
        UniqueConstraint(
            "correlation_id",
            "event_id",
            name="uq_correlation_members_group_event",
        ),
        Index("ix_correlation_members_group", "correlation_id"),
        Index("ix_correlation_members_event", "event_id"),
        Index("ix_correlation_members_type", "membership_type"),
    )

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"MEM-{uuid.uuid4().hex[:10].upper()}"
    )
    correlation_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("correlation_groups.correlation_id"), index=True, nullable=False
    )
    event_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("events.event_id"), index=True, nullable=False
    )

    # Role in the correlation
    membership_type: Mapped[str] = mapped_column(
        String(16), default="SUPPORTING", nullable=False
    )

    # Confidence in this membership (0-100)
    confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Reason for membership
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Temporal bounds
    added_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    removed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Membership confidence (0-100)
    membership_confidence: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Revision for optimistic locking
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    # Relationships
    group: Mapped["CorrelationGroup"] = relationship(
        "CorrelationGroup", back_populates="members"
    )
    event: Mapped["Event"] = relationship("Event", back_populates="correlation_memberships")