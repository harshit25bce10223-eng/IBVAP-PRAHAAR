# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 4 — Correlation Group Member Repository
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event_correlation import CorrelationGroupMember
from app.models.event import Event


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
            CorrelationGroupMember.event_id == event_id,
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
            membership_type=membership_type,
            confidence=confidence,
            reason=reason,
            membership_confidence=confidence,
        )
        self.session.add(member)
        try:
            async with self.session.begin_nested():
                await self.session.flush()
        except IntegrityError:
            existing = await self.get_by_group_and_event(correlation_id, event_id)
            if existing:
                return existing
            raise
        return member

    async def _get_member(
        self, correlation_id: str, event_id: str
    ) -> Any | None:
        stmt = select(CorrelationGroupMember).where(
            CorrelationGroupMember.correlation_id == correlation_id,
            CorrelationGroupMember.event_id == event_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def remove_member(
        self, correlation_id: str, event_id: str
    ) -> bool:
        member = await self._get_member(correlation_id, event_id)
        if not member:
            return False
        member.removed_at = datetime.now(timezone.utc)
        await self.session.flush()
        return True

    async def list_by_group(self, correlation_id: str) -> list:
        stmt = (
            select(CorrelationGroupMember)
            .join(Event, Event.event_id == CorrelationGroupMember.event_id)
            .where(CorrelationGroupMember.correlation_id == correlation_id)
            .order_by(
                Event.ts.asc(),
                Event.event_id.asc(),
            )
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_groups(self, correlation_ids: list[str]) -> dict[str, list]:
        """Batched form of :meth:`list_by_group` (one query per id chunk).

        Returns ``{correlation_id: [members...]}`` where each list carries the
        exact ordering of :meth:`list_by_group` (Event.ts asc, Event.event_id
        asc): a group's members always share one correlation_id, ids are
        deduplicated, and a chunk never splits one correlation_id across two
        queries, so per-group order is preserved.
        """
        if not correlation_ids:
            return {}
        unique_ids = list(dict.fromkeys(correlation_ids))
        grouped: dict[str, list] = {}
        chunk_size = 500
        for start in range(0, len(unique_ids), chunk_size):
            chunk = unique_ids[start : start + chunk_size]
            stmt = (
                select(CorrelationGroupMember)
                .join(Event, Event.event_id == CorrelationGroupMember.event_id)
                .where(CorrelationGroupMember.correlation_id.in_(chunk))
                .order_by(
                    CorrelationGroupMember.correlation_id.asc(),
                    Event.ts.asc(),
                    Event.event_id.asc(),
                )
            )
            result = await self.session.execute(stmt)
            for member in result.scalars().all():
                grouped.setdefault(member.correlation_id, []).append(member)
        return grouped

    async def list_by_event(self, event_id: str) -> list:
        stmt = select(CorrelationGroupMember).where(
            CorrelationGroupMember.event_id == event_id
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def latest_event_ts_by_groups(
        self, correlation_ids: list[str]
    ) -> dict[str, datetime]:
        """MAX(Event.ts) per group, chunked IN-queries.

        Used by the ingest temporal prefilter: the rule engine compares the
        incoming event against a group's ``started_at`` and its latest member
        timestamp, so both bounds must be known without hydrating the members.
        Groups whose member events cannot be loaded produce no entry here,
        matching the member loader that skips unloadable member rows.
        """
        if not correlation_ids:
            return {}
        unique_ids = list(dict.fromkeys(correlation_ids))
        latest: dict[str, datetime] = {}
        chunk_size = 500
        for start in range(0, len(unique_ids), chunk_size):
            chunk = unique_ids[start : start + chunk_size]
            stmt = (
                select(
                    CorrelationGroupMember.correlation_id,
                    func.max(Event.ts),
                )
                .join(Event, Event.event_id == CorrelationGroupMember.event_id)
                .where(CorrelationGroupMember.correlation_id.in_(chunk))
                .group_by(CorrelationGroupMember.correlation_id)
            )
            result = await self.session.execute(stmt)
            for correlation_id, ts in result.all():
                latest[correlation_id] = ts
        return latest

    async def update(self, membership_id: str, **data: Any) -> Any | None:
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