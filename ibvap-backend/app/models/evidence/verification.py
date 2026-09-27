# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — SQLAlchemy 2.x ORM Model: Evidence Verification History
# ─────────────────────────────────────────────────────────────────────────────
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    Enum as SQLEnum,
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


# VerifyOutcome constants
VERIFY_OUTCOME_MATCH = "MATCH"
VERIFY_OUTCOME_MISMATCH = "MISMATCH"
VERIFY_OUTCOME_ERROR = "ERROR"
VERIFY_OUTCOME_UNAVAILABLE = "UNAVAILABLE"
VERIFY_OUTCOMES = [
    VERIFY_OUTCOME_MATCH,
    VERIFY_OUTCOME_MISMATCH,
    VERIFY_OUTCOME_ERROR,
    VERIFY_OUTCOME_UNAVAILABLE,
]


def _verification_id() -> str:
    return f"VER-{uuid.uuid4().hex[:10].upper()}"


class EvidenceVerification(Base):
    __tablename__ = "evidence_verifications"
    __table_args__ = (
        Index("ix_verification_evidence", "evidence_id"),
        Index("ix_verification_time", "verified_at"),
        Index("ix_verification_outcome", "outcome"),
    )

    verification_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=lambda: f"VER-{uuid.uuid4().hex[:10].upper()}")
    evidence_id: Mapped[str] = mapped_column(String(64), ForeignKey("evidence_records.evidence_id"), index=True, nullable=False)

    algorithm: Mapped[str] = mapped_column(String(32), default="SHA-256", nullable=False)
    recorded_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    computed_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    outcome: Mapped[str] = mapped_column(SQLEnum(*["MATCH", "MISMATCH", "ERROR", "UNAVAILABLE"], name="verify_outcome"), nullable=False)

    verified_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, default=lambda: datetime.now(timezone.utc), nullable=False)
    verifier_service: Mapped[str] = mapped_column(String(64), nullable=False)
    actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    context_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    evidence: Mapped["EvidenceRecord"] = relationship("EvidenceRecord", back_populates="verifications")