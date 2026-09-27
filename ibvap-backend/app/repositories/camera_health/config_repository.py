# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — Camera Health Config Repository
# ─────────────────────────────────────────────────────────────────────────────
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.camera_health import CameraHealthConfig


class CameraHealthConfigRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, camera_id: str) -> CameraHealthConfig | None:
        stmt = select(CameraHealthConfig).where(CameraHealthConfig.camera_id == camera_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(self, camera_id: str, **defaults: Any) -> CameraHealthConfig:
        config = await self.get(camera_id)
        if config:
            return config
        config = CameraHealthConfig(camera_id=camera_id, **defaults)
        self.session.add(config)
        await self.session.flush()
        return config

    async def create(self, camera_id: str, **data: Any) -> CameraHealthConfig:
        config = CameraHealthConfig(camera_id=camera_id, **data)
        self.session.add(config)
        await self.session.flush()
        return config

    async def update(self, camera_id: str, **data: Any) -> CameraHealthConfig | None:
        config = await self.get(camera_id)
        if not config:
            return None
        for key, value in data.items():
            if hasattr(config, key):
                setattr(config, key, value)
        await self.session.flush()
        return config

    async def delete(self, camera_id: str) -> bool:
        config = await self.get(camera_id)
        if not config:
            return False
        await self.session.delete(config)
        return True

    async def list_active(self) -> list[CameraHealthConfig]:
        stmt = select(CameraHealthConfig).where(CameraHealthConfig.active == True)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_all(self) -> list[CameraHealthConfig]:
        stmt = select(CameraHealthConfig)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())