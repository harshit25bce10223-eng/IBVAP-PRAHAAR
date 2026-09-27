# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — SQLAlchemy 2.x ORM Model: Evidence Ledger Records (Append-Only)
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
    UniqueConstraint,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from .record import EvidenceRecord


def _ledger_record_id() -> str:
    return f"LGR-{uuid.uuid4().hex[:10].upper()}"


class EvidenceLedgerRecord(Base):
    __tablename__ = "evidence_ledger_records"
    __table_args__ = (
        Index("ix_ledger_evidence", "evidence_id"),
        Index("ix_ledger_sequence", "sequence_number"),
        Index("ix_ledger_time", "created_at"),
        UniqueConstraint("sequence_number", name="uq_ledger_sequence"),
        UniqueConstraint("record_hash", name="uq_ledger_record_hash"),
    )

    ledger_record_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"LGR-{uuid.uuid4().hex[:10].upper()}")
    evidence_id: Mapped[str] = mapped_column(String(64), ForeignKey("evidence_records.evidence_id"), index=True, nullable=False)

    sequence_number: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    previous_record_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    record_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)

    canonical_payload_json: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    anchor_status: Mapped[str] = mapped_column(String(32), default="UNAVAILABLE", nullable=False)
    anchor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    anchor_timestamp: Mapped[datetime | None] = mapped_column(nullable=True)
    root_reference: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tree_size: Mapped[int | None] = mapped_column(Integer, nullable=True)

    algorithm_version: Mapped[str] = mapped_column(String(32), default="SHA-256", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="ACTIVE", nullable=False)

    evidence: Mapped["EvidenceRecord"] = relationship("EvidenceRecord", back_populates="ledger_records")