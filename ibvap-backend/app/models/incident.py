# ─────────────────────────────────────────────────────────────────────────────
# IBVAP — SQLAlchemy 2.x ORM Model: Incident
# ─────────────────────────────────────────────────────────────────────────────
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, Float, Index, Integer, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    from app.models.detection import Detection


def _incident_id() -> str:
    return f"INC-{uuid.uuid4().hex[:10].upper()}"


class Incident(Base):
    __tablename__ = "incidents"
    __table_args__ = (
        Index("ix_incidents_lookup", "camera_id", "track_id", "zone_id", "created_at"),
    )

    incident_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_incident_id)

    risk_score: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_score: Mapped[int] = mapped_column(Integer, nullable=True)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)

    # Persist the explainable factor breakdown: [{code, label, points, evidence}]
    factors_json: Mapped[str] = mapped_column(Text, nullable=False)

    event_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    camera_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    track_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    zone_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    # Relationships
    detections: Mapped[list["Detection"]] = relationship(
        "Detection", back_populates="incident"
    )
