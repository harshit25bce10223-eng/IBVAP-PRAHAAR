# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 7 — ANPRConfig Repository
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.anpr import ANPRConfig


class ANPRConfigRepository:
    """
    Component 7 ANPR configuration repository.
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── Single record lookups ─────────────────────────────────────────────────

    async def get(self, config_id: str) -> ANPRConfig | None:
        result = await self.session.execute(
            select(ANPRConfig).where(ANPRConfig.config_id == config_id)
        )
        return result.scalar_one_or_none()

    async def get_by_camera(self, camera_id: str) -> ANPRConfig | None:
        """Get active config for a camera."""
        result = await self.session.execute(
            select(ANPRConfig)
            .where(ANPRConfig.camera_id == camera_id, ANPRConfig.active == True)  # noqa: E712
            .order_by(ANPRConfig.updated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_by_camera_any(self, camera_id: str) -> ANPRConfig | None:
        """Get most recent config for a camera (active or inactive)."""
        result = await self.session.execute(
            select(ANPRConfig)
            .where(ANPRConfig.camera_id == camera_id)
            .order_by(ANPRConfig.updated_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    # ── List ──────────────────────────────────────────────────────────────────

    async def list_configs(
        self,
        *,
        camera_id: str | None = None,
        active: bool | None = None,
        provider: str | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ANPRConfig], int]:
        page_size = min(page_size, 200)
        page = max(page, 1)
        offset = (page - 1) * page_size

        filters = []
        if camera_id:
            filters.append(ANPRConfig.camera_id == camera_id)
        if active is not None:
            filters.append(ANPRConfig.active == active)
        if provider:
            filters.append(ANPRConfig.provider == provider)

        where_clause = and_(*filters) if filters else True

        # Count
        count_q = select(ANPRConfig).where(where_clause)
        total = len((await self.session.execute(count_q)).scalars().all())

        rows = (await self.session.execute(
            select(ANPRConfig)
            .where(where_clause)
            .order_by(ANPRConfig.updated_at.desc())
            .offset(offset)
            .limit(page_size)
        )).scalars().all()

        return list(rows), total

    # ── Create/Update ─────────────────────────────────────────────────────────

    async def create(self, config: ANPRConfig) -> ANPRConfig:
        self.session.add(config)
        await self.session.flush()
        return config

    async def update(self, config: ANPRConfig) -> ANPRConfig:
        config.updated_at = datetime.now(timezone.utc)
        config.revision = (config.revision or 0) + 1
        await self.session.flush()
        return config

    async def deactivate(self, camera_id: str) -> int:
        """Deactivate all configs for a camera."""
        result = await self.session.execute(
            select(ANPRConfig).where(ANPRConfig.camera_id == camera_id, ANPRConfig.active == True)  # noqa: E712
        )
        configs = result.scalars().all()
        for cfg in configs:
            cfg.active = False
            cfg.updated_at = datetime.now(timezone.utc)
            cfg.revision = (cfg.revision or 0) + 1
        await self.session.flush()
        return len(configs)