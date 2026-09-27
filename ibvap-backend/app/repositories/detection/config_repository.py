# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 5 — Detection Config Repository
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.detection import DetectionConfig


class DetectionConfigRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, config_id: str) -> DetectionConfig | None:
        stmt = select(DetectionConfig).where(DetectionConfig.config_id == config_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_camera(self, camera_id: str) -> DetectionConfig | None:
        stmt = select(DetectionConfig).where(
            DetectionConfig.camera_id == camera_id,
            DetectionConfig.active == True,
        ).order_by(DetectionConfig.revision.desc())
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, **data: Any) -> DetectionConfig:
        config = DetectionConfig(**data)
        self.session.add(config)
        await self.session.flush()
        return config

    async def update(self, config_id: str, **data: Any) -> DetectionConfig | None:
        config = await self.get(config_id)
        if not config:
            return None
        for key, value in data.items():
            if hasattr(config, key):
                setattr(config, key, value)
        config.revision += 1
        config.updated_at = datetime.now()
        await self.session.flush()
        return config

    async def set_active(self, config_id: str, active: bool) -> DetectionConfig | None:
        config = await self.get(config_id)
        if not config:
            return None
        config.active = active
        config.revision += 1
        if active:
            config.activated_at = datetime.now()
        await self.session.flush()
        return config

    async def list_active(self) -> list[DetectionConfig]:
        stmt = select(DetectionConfig).where(DetectionConfig.active == True)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_camera(self, camera_id: str) -> list[DetectionConfig]:
        stmt = select(DetectionConfig).where(
            DetectionConfig.camera_id == camera_id
        ).order_by(DetectionConfig.revision.desc())
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, config_id: str) -> bool:
        config = await self.get(config_id)
        if not config:
            return False
        await self.session.delete(config)
        return True