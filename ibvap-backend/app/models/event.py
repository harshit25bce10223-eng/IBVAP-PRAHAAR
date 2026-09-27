# ─────────────────────────────────────────────────────────────────────────────
# IBVAP — SQLAlchemy 2.x ORM Model: Event
# ─────────────────────────────────────────────────────────────────────────────
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.event_correlation import CorrelationGroupMember
    from app.models.detection import Detection


def _event_id() -> str:
    return f"EVT-{uuid.uuid4().hex[:10].upper()}"


class Event(Base):
    __tablename__ = "events"
    __table_args__ = (
        Index("ix_events_dedup", "deduplication_key", unique=True),
        Index("ix_events_lookup", "camera_id", "track_id", "zone_id", "ts"),
    )

    event_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_event_id)
    event_type: Mapped[str] = mapped_column(String(32), nullable=False)  # ZONE_ENTRY / ZONE_EXIT
    camera_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    track_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    zone_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    payload_json: Mapped[str] = mapped_column(Text, nullable=True)

    # Used to guarantee exactly-one ENTRY per (camera, track, zone) crossing.
    deduplication_key: Mapped[str] = mapped_column(String(255), nullable=False)

    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    correlation_memberships: Mapped[list["CorrelationGroupMember"]] = relationship(
        "CorrelationGroupMember", back_populates="event", cascade="all, delete-orphan"
    )
    detections: Mapped[list["Detection"]] = relationship(
        "Detection", back_populates="event"
    )