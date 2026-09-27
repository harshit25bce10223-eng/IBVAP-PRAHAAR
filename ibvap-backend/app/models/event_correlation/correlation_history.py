# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 4 — SQLAlchemy 2.x ORM Model: Correlation History
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


def _history_id() -> str:
    return f"HIS-{uuid.uuid4().hex[:10].upper()}"


class CorrelationHistory(Base):
    __tablename__ = "correlation_history"
    __table_args__ = (
        Index("ix_correlation_history_group", "correlation_id"),
        Index("ix_correlation_history_time", "timestamp"),
        Index("ix_correlation_history_trigger", "trigger_event_id"),
    )

    id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=lambda: f"HIS-{uuid.uuid4().hex[:10].upper()}"
    )
    correlation_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("correlation_groups.correlation_id"), index=True, nullable=False
    )

    # Snapshot of the correlation state at this point
    revision: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    state: Mapped[str | None] = mapped_column(String(16), nullable=True)

    # Snapshot of key fields
    snapshot_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    # Trigger for this change
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    trigger_event_id: Mapped[str | None] = mapped_column(
        String(64), ForeignKey("events.event_id"), index=True, nullable=True
    )

    # Metadata
    algorithm_version: Mapped[str] = mapped_column(String(32), default="1.0", nullable=False)
    configuration_version: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Timestamps
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # Relationships
    group: Mapped["CorrelationGroup"] = relationship(
        "CorrelationGroup", back_populates="history"
    )
    trigger_event: Mapped["Event"] = relationship(
        "Event", foreign_keys=[trigger_event_id]
    )