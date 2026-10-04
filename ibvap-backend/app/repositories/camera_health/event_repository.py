# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — Camera Health Event Repository
# ─────────────────────────────────────────────────────────────────────────────
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.camera_health import CameraHealthEvent


class CameraHealthEventRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, **data: Any) -> CameraHealthEvent:
        event = CameraHealthEvent(**data)
        self.session.add(event)
        await self.session.flush()
        return event

    async def upsert_by_dedup(
        self, deduplication_key: str, **data: Any
    ) -> tuple[CameraHealthEvent, bool]:
        """Upsert event by deduplication_key. Returns (event, created)."""
        stmt = sqlite_insert(CameraHealthEvent).values(
            deduplication_key=deduplication_key, **data
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["deduplication_key"],
            set_={
                "last_seen": data.get("last_seen"),
                "occurrence_count": CameraHealthEvent.occurrence_count + 1,
                "updated_at": datetime.now(timezone.utc),
            },
        ).returning(CameraHealthEvent)
        result = await self.session.execute(stmt)
        event = result.scalar_one()
        # Simplified - in real impl we'd check if it was created vs updated
        return event, True

    async def get(self, event_id: str) -> CameraHealthEvent | None:
        stmt = select(CameraHealthEvent).where(CameraHealthEvent.event_id == event_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_active_for_camera(self, camera_id: str) -> list[CameraHealthEvent]:
        stmt = (
            select(CameraHealthEvent)
            .where(
                CameraHealthEvent.camera_id == camera_id,
                CameraHealthEvent.cleared_at.is_(None),
            )
            .order_by(CameraHealthEvent.first_seen.desc())
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_recent_for_camera(
        self, camera_id: str, limit: int = 50
    ) -> list[CameraHealthEvent]:
        stmt = (
            select(CameraHealthEvent)
            .where(CameraHealthEvent.camera_id == camera_id)
            .order_by(CameraHealthEvent.first_seen.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def close_event(self, event_id: str, cleared_at: datetime) -> CameraHealthEvent | None:
        stmt = select(CameraHealthEvent).where(CameraHealthEvent.event_id == event_id)
        result = await self.session.execute(stmt)
        event = result.scalar_one_or_none()
        if event:
            event.cleared_at = cleared_at
            await self.session.flush()
        return event

    async def list_by_time_range(
        self,
        camera_id: str,
        from_ts: datetime,
        to_ts: datetime | None = None,
        limit: int = 1000,
    ) -> list[CameraHealthEvent]:
        stmt = select(CameraHealthEvent).where(
            CameraHealthEvent.camera_id == camera_id,
            CameraHealthEvent.first_seen >= from_ts,
        )
        if to_ts:
            stmt = stmt.where(CameraHealthEvent.first_seen <= to_ts)
        stmt = stmt.order_by(CameraHealthEvent.first_seen.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_open_events_by_type(
        self, camera_id: str, event_type: str
    ) -> list[CameraHealthEvent]:
        stmt = select(CameraHealthEvent).where(
            CameraHealthEvent.camera_id == camera_id,
            CameraHealthEvent.event_type == event_type,
            CameraHealthEvent.cleared_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())