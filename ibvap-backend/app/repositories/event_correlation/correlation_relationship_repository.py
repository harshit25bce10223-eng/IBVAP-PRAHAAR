# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 4 — Correlation Relationship Repository
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event_correlation import CorrelationRelationship


class CorrelationRelationshipRepository:
    def __init__(self, session) -> None:
        self.session = session

    async def get(self, relationship_id: str) -> Any | None:
        from app.models.event_correlation import CorrelationRelationship
        stmt = select(CorrelationRelationship).where(
            CorrelationRelationship.id == relationship_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, **data: Any) -> Any:
        from app.models.event_correlation import CorrelationRelationship
        relationship = CorrelationRelationship(**data)
        self.session.add(relationship)
        await self.session.flush()
        return relationship

    async def create_relationship(
        self,
        correlation_id: str,
        from_event_id: str,
        to_event_id: str,
        rel_type: str,
        strength: int | None = None,
        evidence_json: dict | None = None,
        explanation: str | None = None,
        algorithm_version: str = "1.0",
    ) -> Any:
        from app.models.event_correlation import CorrelationRelationship
        relationship = CorrelationRelationship(
            correlation_id=correlation_id,
            from_event_id=from_event_id,
            to_event_id=to_event_id,
            type=rel_type,
            strength=strength,
            evidence_json=evidence_json,
            explanation=explanation,
            algorithm_version=algorithm_version,
        )
        self.session.add(relationship)
        await self.session.flush()
        return relationship

    async def list_by_group(self, correlation_id: str) -> list:
        from app.models.event_correlation import CorrelationRelationship
        stmt = (
            select(CorrelationRelationship)
            .where(CorrelationRelationship.correlation_id == correlation_id)
            .order_by(CorrelationRelationship.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_event(self, event_id: str) -> list:
        from app.models.event_correlation import CorrelationRelationship
        stmt = (
            select(CorrelationRelationship)
            .where(
                (CorrelationRelationship.from_event_id == event_id)
                | (CorrelationRelationship.to_event_id == event_id)
            )
            .order_by(CorrelationRelationship.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_type(self, correlation_id: str, rel_type: str) -> list:
        from app.models.event_correlation import CorrelationRelationship
        stmt = select(CorrelationRelationship).where(
            CorrelationRelationship.correlation_id == correlation_id,
            CorrelationRelationship.type == rel_type,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_events(
        self, correlation_id: str, from_event_id: str, to_event_id: str
    ) -> Any | None:
        from app.models.event_correlation import CorrelationRelationship
        stmt = select(CorrelationRelationship).where(
            CorrelationRelationship.correlation_id == correlation_id,
            CorrelationRelationship.from_event_id == from_event_id,
            CorrelationRelationship.to_event_id == to_event_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete(self, relationship_id: str) -> bool:
        from app.models.event_correlation import CorrelationRelationship
        stmt = select(CorrelationRelationship).where(
            CorrelationRelationship.id == relationship_id
        )
        result = await self.session.execute(stmt)
        relationship = result.scalar_one_or_none()
        if not relationship:
            return False
        await self.session.delete(relationship)
        return True

    async def list_by_group(self, correlation_id: str) -> list:
        from app.models.event_correlation import CorrelationRelationship
        stmt = (
            select(CorrelationRelationship)
            .where(CorrelationRelationship.correlation_id == correlation_id)
            .order_by(CorrelationRelationship.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())