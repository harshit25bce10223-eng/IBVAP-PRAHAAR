# ─────────────────────────────────────────────────────────────────────────────
# IBVAP — SQLAlchemy 2.x ORM Model: Track
# ─────────────────────────────────────────────────────────────────────────────
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


def _track_id() -> str:
    return f"TRK-{uuid.uuid4().hex[:8].upper()}"


class Track(Base):
    __tablename__ = "tracks"

    track_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_track_id)
    camera_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    object_type: Mapped[str] = mapped_column(String(32), nullable=False)

    current_bbox_json: Mapped[str] = mapped_column(Text, nullable=True)
    previous_bbox_json: Mapped[str] = mapped_column(Text, nullable=True)

    # Zone membership persistence: { zone_id: bool }
    current_membership_json: Mapped[str] = mapped_column(Text, nullable=True)
    previous_membership_json: Mapped[str] = mapped_column(Text, nullable=True)

    # Timestamped positions: [{x, y, ts}, ...] bounded by TRACK_PATH_MAX_POSITIONS.
    path_json: Mapped[str] = mapped_column(Text, nullable=True)

    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
