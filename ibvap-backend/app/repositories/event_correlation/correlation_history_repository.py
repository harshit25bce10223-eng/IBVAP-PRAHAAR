# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 4 — Correlation History Repository
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event_correlation import CorrelationHistory, CorrelationGroup


class CorrelationHistoryRepository:
    def __init__(self, session) -> None:
        self.session = session

    async def create(self, **data: Any) -> Any:
        record = CorrelationHistory(**data)
        self.session.add(record)
        await self.session.flush()
        return record

    async def log_transition(
        self,
        correlation_id: str,
        old_status: str,
        new_status: str,
        reason: str | None = None,
        trigger_event_id: str | None = None,
        algorithm_version: str = "1.0",
        configuration_version: str | None = None,
        snapshot_json: dict | None = None,
        state: str | None = None,
        revision: int | None = None,
    ) -> Any:
        if revision is None:
            stmt = select(CorrelationGroup).where(
                CorrelationGroup.correlation_id == correlation_id
            )
            result = await self.session.execute(stmt)
            group = result.scalar_one_or_none()
            revision = (int(group.revision) + 1) if group else 1

        record = CorrelationHistory(
            correlation_id=correlation_id,
            revision=revision,
            status=new_status,
            state=state,
            snapshot_json=snapshot_json,
            reason=reason,
            trigger_event_id=trigger_event_id,
            algorithm_version=algorithm_version,
            configuration_version=configuration_version,
        )
        self.session.add(record)
        await self.session.flush()
        return record

    async def get_latest(self, correlation_id: str):
        stmt = (
            select(CorrelationHistory)
            .where(CorrelationHistory.correlation_id == correlation_id)
            .order_by(CorrelationHistory.timestamp.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_correlation(
        self, correlation_id: str, limit: int | None = 100
    ) -> list:
        stmt = (
            select(CorrelationHistory)
            .where(CorrelationHistory.correlation_id == correlation_id)
            .order_by(
                CorrelationHistory.revision.asc(),
                CorrelationHistory.timestamp.asc(),
                CorrelationHistory.id.asc(),
            )
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_time_range(
        self, start: datetime, end: datetime, limit: int = 1000
    ) -> list:
        stmt = (
            select(CorrelationHistory)
            .where(
                CorrelationHistory.timestamp >= start,
                CorrelationHistory.timestamp <= end,
            )
            .order_by(CorrelationHistory.timestamp.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())