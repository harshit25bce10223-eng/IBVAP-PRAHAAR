# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 4 — Correlation Group Repository
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event_correlation import (
    CorrelationGroup,
    CorrelationGroupMember,
    CorrelationRelationship,
    CorrelationHistory,
    CorrelationConfig,
    CorrelationStatus,
    CorrelationGroupState,
    CorrelationCompleteness,
)


class CorrelationGroupRepository:
    def __init__(self, session) -> None:
        self.session = session

    async def get(self, correlation_id: str) -> Any | None:
        stmt = select(CorrelationGroup).where(
            CorrelationGroup.correlation_id == correlation_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, **data: Any) -> Any:
        group = CorrelationGroup(**data)
        self.session.add(group)
        await self.session.flush()
        return group

    async def update(self, correlation_id: str, **data: Any) -> Any | None:
        group = await self.get(correlation_id)
        if not group:
            return None
        for key, value in data.items():
            if hasattr(group, key):
                setattr(group, key, value)
        group.revision += 1
        group.updated_at = datetime.now()
        await self.session.flush()
        return group

    async def delete(self, correlation_id: str) -> bool:
        group = await self.get(correlation_id)
        if not group:
            return False
        await self.session.delete(group)
        return True

    async def list_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        camera_id: str | None = None,
        sector_id: str | None = None,
        source: str | None = None,
        sort: str = "started_at",
        order: str = "desc",
    ) -> tuple[list, int]:
        stmt = select(CorrelationGroup)

        if status:
            stmt = stmt.where(CorrelationGroup.status == status)
        if sector_id:
            stmt = stmt.where(CorrelationGroup.sector_id == sector_id)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        # Apply sorting
        sort_column = getattr(CorrelationGroup, sort, CorrelationGroup.started_at)
        if order == "desc":
            stmt = stmt.order_by(sort_column.desc())
        else:
            stmt = stmt.order_by(sort_column.asc())

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        res = await self.session.execute(stmt)
        records = list(res.scalars().all())

        return records, total

    async def list_active(self) -> list:
        stmt = select(CorrelationGroup).where(
            CorrelationGroup.status.in_(["OPEN", "ACTIVE", "STABLE"])
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_camera(self, camera_id: str, limit: int = 50) -> list:
        # Find groups that have members from this camera
        stmt = (
            select(CorrelationGroup)
            .join(CorrelationGroupMember)
            .where(CorrelationGroupMember.camera_id == camera_id)
            .order_by(CorrelationGroup.started_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_event(self, event_id: str) -> list:
        # Find groups that contain this event
        stmt = (
            select(CorrelationGroup)
            .join(CorrelationGroupMember)
            .where(CorrelationGroupMember.event_id == event_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_event(self, event_id: str) -> list:
        """Get all correlation groups that contain a specific event"""
        return await self.list_by_event(event_id)

    async def get_active_for_camera(self, camera_id: str) -> list:
        stmt = (
            select(CorrelationGroup)
            .join(CorrelationGroupMember)
            .where(
                CorrelationGroupMember.camera_id == camera_id,
                CorrelationGroup.status.in_(["OPEN", "ACTIVE", "STABLE"]),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_recent(self, hours: int = 24, limit: int = 100) -> list:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        stmt = (
            select(CorrelationGroup)
            .where(CorrelationGroup.started_at >= datetime.utcnow() - timedelta(hours=hours))
            .order_by(CorrelationGroup.started_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())