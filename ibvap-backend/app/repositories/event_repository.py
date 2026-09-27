# ─────────────────────────────────────────────────────────────────────────────
# IBVAP — Event Repository
# ─────────────────────────────────────────────────────────────────────────────
# The unique constraint on `deduplication_key` is the database-level guard that
# makes concurrent duplicate creation impossible.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DatabaseError
from app.domain.tracking.track_state import entry_generation_prefix
from app.models.event import Event


class EventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(
        self,
        *,
        event_type: str,
        camera_id: str,
        track_id: str,
        zone_id: str,
        payload: dict[str, Any] | None,
        deduplication_key: str,
        ts: datetime,
    ) -> Event:
        event = Event(
            event_type=event_type,
            camera_id=camera_id,
            track_id=track_id,
            zone_id=zone_id,
            payload_json=json.dumps(payload) if payload is not None else None,
            deduplication_key=deduplication_key,
            ts=ts,
            created_at=datetime.now(timezone.utc),
        )
        try:
            self.session.add(event)
            await self.session.flush()
        except IntegrityError as exc:
            raise DatabaseError(
                f"Duplicate event rejected by unique deduplication key: {deduplication_key}"
            ) from exc
        return event

    async def count_entries(self, camera_id: str, track_id: str, zone_id: str) -> int:
        prefix = entry_generation_prefix(camera_id, track_id, zone_id)
        res = await self.session.execute(
            select(func.count(Event.event_id)).where(
                Event.deduplication_key.like(f"{prefix}%"),
                Event.event_type == "ZONE_ENTRY",
            )
        )
        return int(res.scalar_one())

    async def count_exits(self, camera_id: str, track_id: str, zone_id: str) -> int:
        prefix = f"{camera_id}|{track_id}|{zone_id}|EXIT|"
        res = await self.session.execute(
            select(func.count(Event.event_id)).where(
                Event.deduplication_key.like(f"{prefix}%"),
                Event.event_type == "ZONE_EXIT",
            )
        )
        return int(res.scalar_one())

    async def list_recent(self, camera_id: str | None = None, limit: int = 50) -> list[Event]:
        stmt = select(Event).order_by(Event.ts.desc()).limit(min(limit, 200))
        if camera_id:
            stmt = select(Event).where(Event.camera_id == camera_id).order_by(Event.ts.desc()).limit(limit)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())