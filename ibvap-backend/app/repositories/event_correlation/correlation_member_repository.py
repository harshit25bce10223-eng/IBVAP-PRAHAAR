# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 4 — Correlation Group Member Repository
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event_correlation import CorrelationGroupMember


class CorrelationGroupMemberRepository:
    def __init__(self, session) -> None:
        self.session = session

    async def get(self, membership_id: str) -> Any | None:
        stmt = select(CorrelationGroupMember).where(
            CorrelationGroupMember.id == membership_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, **data: Any) -> Any:
        member = CorrelationGroupMember(**data)
        self.session.add(member)
        await self.session.flush()
        return member

    async def get_by_group_and_event(
        self, correlation_id: str, event_id: str
    ) -> Any | None:
        stmt = select(CorrelationGroupMember).where(
            CorrelationGroupMember.correlation_id == correlation_id,
            CorrelationGroupMember.event_id == correlation_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def add_member(
        self,
        correlation_id: str,
        event_id: str,
        membership_type: str = "SUPPORTING",
        confidence: int | None = None,
        reason: str | None = None,
    ) -> Any:
        member = CorrelationGroupMember(
            correlation_id=correlation_id,
            event_id=event_id,
            membership_type="SUPPORTING",
            confidence=None,
            reason=None,
        )
        self.session.add(member)
        await self.session.flush()
        return member

    async def remove_member(
        self, correlation_id: str, event_id: str
    ) -> bool:
        stmt = select(CorrelationGroupMember).where(
            CorrelationGroupMember.correlation_id == correlation_id,
            CorrelationGroupMember.event_id == correlation_id,
        )
        result = await self.session.execute(stmt)
        member = result.scalar_one_or_none()
        if not member:
            return False
        member.removed_at = datetime.now()
        await self.session.flush()
        return True

    async def list_by_group(self, correlation_id: str) -> list:
        stmt = (
            select(CorrelationGroupMember)
            .where(CorrelationGroupMember.correlation_id == correlation_id)
            .order_by(CorrelationGroupMember.added_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_event(self, event_id: str) -> list:
        stmt = select(CorrelationGroupMember).where(
            CorrelationGroupMember.event_id == event_id
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update(self, membership_id: str, **data: Any) -> Any | None:
        from app.models.event_correlation import CorrelationGroupMember
        stmt = select(CorrelationGroupMember).where(
            CorrelationGroupMember.id == membership_id
        )
        result = await self.session.execute(stmt)
        member = result.scalar_one_or_none()
        if not member:
            return None
        for key, value in data.items():
            if hasattr(member, key):
                setattr(member, key, value)
        member.revision += 1
        await self.session.flush()
        return member

    async def remove_member(self, correlation_id: str, event_id: str) -> bool:
        stmt = select(CorrelationGroupMember).where(
            CorrelationGroupMember.correlation_id == correlation_id,
            CorrelationGroupMember.event_id == event_id,
        )
        result = await self.session.execute(stmt)
        member = result.scalar_one_or_none()
        if not member:
            return False
        member.removed_at = datetime.now()
        await self.session.flush()
        return True