# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — SQLAlchemy 2.x ORM Model: Evidence Record
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
    from .verification import EvidenceVerification
    from .lifecycle import EvidenceLifecycleEvent
    from .ledger import EvidenceLedgerRecord
    from app.models.detection import Detection


# Enum value constants
EVIDENCE_TYPES = ["SNAPSHOT", "VIDEO_CLIP", "FRAME", "METADATA", "EVENT_RECORD", "INCIDENT_PACKAGE"]
EVIDENCE_SOURCES = ["CAMERA", "EDGE", "ANALYTICS", "INCIDENT", "SYSTEM", "UNKNOWN"]
EVIDENCE_ROLES = ["ORIGINAL_CAPTURE", "DERIVED", "ANNOTATED", "EXPORT", "THUMBNAIL"]
INTEGRITY_STATES = ["VERIFIED", "UNVERIFIED", "HASHED", "MISMATCH", "PENDING", "UNAVAILABLE", "UNKNOWN"]
ANCHOR_STATES = ["ANCHORED", "PENDING", "FAILED", "UNAVAILABLE", "UNKNOWN"]
RECORD_STATUSES = ["VALID", "UNDER_REVIEW", "QUARANTINED", "UNKNOWN"]
SYNC_STATES = ["LOCAL_ONLY", "SYNC_PENDING", "SYNCED", "SYNC_FAILED", "UNKNOWN"]


class EvidenceSyncState(str):
    LOCAL_ONLY = "LOCAL_ONLY"
    SYNC_PENDING = "SYNC_PENDING"
    SYNCED = "SYNCED"
    SYNC_FAILED = "SYNC_FAILED"
    UNKNOWN = "UNKNOWN"


def _evidence_id() -> str:
    return f"EVD-{uuid.uuid4().hex[:10].upper()}"


class EvidenceRecord(Base):
    __tablename__ = "evidence_records"
    __table_args__ = (
        Index("ix_evidence_incident", "incident_id"),
        Index("ix_evidence_camera", "camera_id"),
        Index("ix_evidence_event", "event_id"),
        Index("ix_evidence_type", "type"),
        Index("ix_evidence_source", "source"),
        Index("ix_evidence_role", "role"),
        Index("ix_evidence_integrity", "integrity_status"),
        Index("ix_evidence_anchor", "anchor_status"),
        Index("ix_evidence_sync", "sync_state"),
        Index("ix_evidence_captured", "captured_at"),
        Index("ix_evidence_parent", "parent_evidence_id"),
        Index("ix_evidence_content_hash", "content_hash"),
        Index("ix_evidence_capture_time", "captured_at"),
    )

    evidence_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_evidence_id)
    incident_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("incidents.incident_id"), index=True, nullable=True)
    event_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("events.event_id"), index=True, nullable=True)
    camera_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    zone_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    parent_evidence_id: Mapped[str | None] = mapped_column(String(64), ForeignKey("evidence_records.evidence_id"), index=True, nullable=True)

    type: Mapped[str] = mapped_column(SQLEnum(*EVIDENCE_TYPES, name="evidence_type"), nullable=False)
    source: Mapped[str] = mapped_column(SQLEnum(*EVIDENCE_SOURCES, name="evidence_source"), nullable=False)
    role: Mapped[str] = mapped_column(SQLEnum(*EVIDENCE_ROLES, name="evidence_role"), nullable=False)

    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)
    ingested_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    file_size_bytes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    media_duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)

    storage_backend: Mapped[str] = mapped_column(String(64), default="filesystem", nullable=False)
    storage_key: Mapped[str] = mapped_column(String(256), nullable=False)

    content_hash_algorithm: Mapped[str] = mapped_column(String(32), default="SHA-256", nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    ledger_record_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)

    region_profile: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sector: Mapped[str | None] = mapped_column(String(64), nullable=True)

    schema_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    canonicalization_version: Mapped[str] = mapped_column(String(32), default="canonical-json-v1", nullable=False)
    algorithm_version: Mapped[str] = mapped_column(String(32), default="SHA-256", nullable=False)

    sync_state: Mapped[str] = mapped_column(SQLEnum(*SYNC_STATES, name="evidence_sync_state"), default="LOCAL_ONLY", nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="CAPTURED", nullable=False)
    integrity_status: Mapped[str] = mapped_column(SQLEnum(*INTEGRITY_STATES, name="evidence_integrity"), default="UNVERIFIED", nullable=False)
    anchor_status: Mapped[str] = mapped_column(SQLEnum(*ANCHOR_STATES, name="evidence_anchor"), default="UNAVAILABLE", nullable=False)

    created_by_service: Mapped[str | None] = mapped_column(String(64), nullable=True)
    metadata_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Relationships
    verifications: Mapped[list["EvidenceVerification"]] = relationship("EvidenceVerification", back_populates="evidence", cascade="all, delete-orphan")
    lifecycle_events: Mapped[list["EvidenceLifecycleEvent"]] = relationship("EvidenceLifecycleEvent", back_populates="evidence", cascade="all, delete-orphan")
    ledger_records: Mapped[list["EvidenceLedgerRecord"]] = relationship("EvidenceLedgerRecord", back_populates="evidence", cascade="all, delete-orphan")
    detections: Mapped[list["Detection"]] = relationship(
        "Detection", back_populates="evidence"
    )