# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 4 — Correlation Config Repository
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event_correlation import CorrelationConfig


class CorrelationConfigRepository:
    def __init__(self, session) -> None:
        self.session = session

    async def get(self, config_id: str):
        from app.models.event_correlation import CorrelationConfig
        from sqlalchemy import select

        stmt = select(CorrelationConfig).where(
            CorrelationConfig.config_id == config_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_by_profile(
        self, profile: str, event_pair: str | None = None
    ):
        from app.models.event_correlation import CorrelationConfig
        from sqlalchemy import select

        stmt = select(CorrelationConfig).where(
            CorrelationConfig.profile == profile,
            CorrelationConfig.active == True,
        )
        if event_pair:
            stmt = stmt.where(CorrelationConfig.event_pair == event_pair)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_active_for_profile(self, profile: str):
        from app.models.event_correlation import CorrelationConfig
        from sqlalchemy import select

        stmt = (
            select(CorrelationConfig)
            .where(
                CorrelationConfig.profile == profile,
                CorrelationConfig.active == True,
            )
            .order_by(CorrelationConfig.revision.desc())
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def create(self, **data: Any):
        from app.models.event_correlation import CorrelationConfig

        config = CorrelationConfig(**data)
        self.session.add(config)
        await self.session.flush()
        return config

    async def update(self, config_id: str, **data: Any):
        from app.models.event_correlation import CorrelationConfig
        from sqlalchemy import select

        stmt = select(CorrelationConfig).where(
            CorrelationConfig.config_id == config_id
        )
        result = await self.session.execute(stmt)
        config = result.scalar_one_or_none()
        if not config:
            return None

        for key, value in data.items():
            if hasattr(config, key):
                setattr(config, key, value)
        config.revision += 1
        config.updated_at = datetime.now()
        await self.session.flush()
        return config

    async def set_active(self, config_id: str, active: bool):
        from app.models.event_correlation import CorrelationConfig
        from sqlalchemy import select

        stmt = select(CorrelationConfig).where(
            CorrelationConfig.config_id == config_id
        )
        result = await self.session.execute(stmt)
        config = result.scalar_one_or_none()
        if not config:
            return None
        config.active = active
        config.revision += 1
        if active:
            config.activated_at = datetime.now()
        await self.session.flush()
        return config

    async def list_active(self):
        from app.models.event_correlation import CorrelationConfig
        from sqlalchemy import select

        stmt = select(CorrelationConfig).where(CorrelationConfig.active == True)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_all(self):
        from app.models.event_correlation import CorrelationConfig
        from sqlalchemy import select

        stmt = select(CorrelationConfig).order_by(
            CorrelationConfig.profile, CorrelationConfig.revision.desc()
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete(self, config_id: str) -> bool:
        from app.models.event_correlation import CorrelationConfig
        from sqlalchemy import select, delete

        stmt = select(CorrelationConfig).where(
            CorrelationConfig.config_id == config_id
        )
        result = await self.session.execute(stmt)
        config = result.scalar_one_or_none()
        if not config:
            return False
        
        await self.session.delete(config)
        await self.session.flush()
        return True