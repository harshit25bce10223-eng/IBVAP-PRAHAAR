# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — Camera Health Current State Repository
# ─────────────────────────────────────────────────────────────────────────────
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.camera_health import CameraHealthCurrent


class CameraHealthCurrentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, camera_id: str) -> CameraHealthCurrent | None:
        stmt = select(CameraHealthCurrent).where(CameraHealthCurrent.camera_id == camera_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert(self, camera_id: str, **data: Any) -> CameraHealthCurrent:
        stmt = sqlite_insert(CameraHealthCurrent).values(camera_id=camera_id, **data)
        stmt = stmt.on_conflict_do_update(
            index_elements=["camera_id"],
            set_=data,
        ).returning(CameraHealthCurrent)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def update(self, camera_id: str, **data: Any) -> CameraHealthCurrent | None:
        current = await self.get(camera_id)
        if not current:
            return None
        for key, value in data.items():
            if hasattr(current, key):
                setattr(current, key, value)
        await self.session.flush()
        return current

    async def list_all(self) -> list[CameraHealthCurrent]:
        stmt = select(CameraHealthCurrent)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_status(self, status: str) -> list[CameraHealthCurrent]:
        stmt = select(CameraHealthCurrent).where(CameraHealthCurrent.overall_status == status)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, camera_id: str) -> bool:
        current = await self.get(camera_id)
        if not current:
            return False
        await self.session.delete(current)
        return True