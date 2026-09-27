# ─────────────────────────────────────────────────────────────────────────────
# IBVAP — SQLAlchemy 2.x ORM Model: Zone
# ─────────────────────────────────────────────────────────────────────────────
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, Text
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


def _zone_id() -> str:
    return f"ZONE-{uuid.uuid4().hex[:8].upper()}"


class Zone(Base):
    __tablename__ = "zones"

    zone_id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_zone_id)
    camera_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)

    # Normalized coordinates: [{x, y}, ...] in the range [0, 1]
    polygon_json: Mapped[str] = mapped_column(Text, nullable=False)

    # Zone rules: allowed_object_types, active_start, active_end, dwell_time_seconds
    rules_json: Mapped[str] = mapped_column(Text, nullable=False, default="{}")

    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
