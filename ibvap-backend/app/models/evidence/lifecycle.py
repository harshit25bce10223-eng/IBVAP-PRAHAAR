# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — SQLAlchemy 2.x ORM Model: Evidence Lifecycle Events
# ─────────────────────────────────────────────────────────────────────────────
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    String,
    Text,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from .record import EvidenceRecord


LIFECYCLE_EVENT_TYPES = [
    "CAPTURED", "VALIDATED", "STORED", "HASHED", "LEDGERED", "ANCHORED",
    "VERIFIED", "EXPORTED", "ARCHIVED", "EXPORT_REQUESTED", "EXPORT_READY",
    "EXPORT_FAILED", "SYNC_STARTED", "SYNC_COMPLETED", "SYNC_FAILED",
    "MISMATCH_DETECTED", "LEDGER_APPENDED", "ANCHOR_CREATED",
]


def _lifecycle_id() -> str:
    return f"LCE-{uuid.uuid4().hex[:10].upper()}"


class EvidenceLifecycleEvent(Base):
    __tablename__ = "evidence_lifecycle_events"
    __table_args__ = (
        Index("ix_lifecycle_evidence", "evidence_id"),
        Index("ix_lifecycle_time", "timestamp"),
        Index("ix_lifecycle_type", "event_type"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"LCE-{uuid.uuid4().hex[:10].upper()}")
    evidence_id: Mapped[str] = mapped_column(String(64), ForeignKey("evidence_records.evidence_id"), index=True, nullable=False)

    event_type: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, default=lambda: datetime.now(timezone.utc), nullable=False)
    actor: Mapped[str] = mapped_column(String(128), nullable=False)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    evidence: Mapped["EvidenceRecord"] = relationship("EvidenceRecord", back_populates="lifecycle_events")