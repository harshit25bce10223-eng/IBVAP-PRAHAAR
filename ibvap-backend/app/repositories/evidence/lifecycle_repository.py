# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — Evidence Lifecycle Repository
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evidence import EvidenceLifecycleEvent


class EvidenceLifecycleRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, **data: Any) -> EvidenceLifecycleEvent:
        event = EvidenceLifecycleEvent(**data)
        self.session.add(event)
        await self.session.flush()
        return event

    async def list_by_evidence(
        self, evidence_id: str, limit: int = 100
    ) -> list[EvidenceLifecycleEvent]:
        stmt = (
            select(EvidenceLifecycleEvent)
            .where(EvidenceLifecycleEvent.evidence_id == evidence_id)
            .order_by(EvidenceLifecycleEvent.timestamp.desc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_latest(self, evidence_id: str) -> EvidenceLifecycleEvent | None:
        stmt = (
            select(EvidenceLifecycleEvent)
            .where(EvidenceLifecycleEvent.evidence_id == evidence_id)
            .order_by(EvidenceLifecycleEvent.timestamp.desc())
            .limit(1)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def list_all(self, limit: int = 100) -> list[EvidenceLifecycleEvent]:
        """List all lifecycle events across all evidence records, ordered by timestamp desc."""
        stmt = (
            select(EvidenceLifecycleEvent)
            .order_by(EvidenceLifecycleEvent.timestamp.desc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())