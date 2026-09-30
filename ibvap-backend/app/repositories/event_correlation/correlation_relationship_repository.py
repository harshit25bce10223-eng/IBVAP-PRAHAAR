# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 4 — Correlation Relationship Repository
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event_correlation import CorrelationRelationship


class CorrelationRelationshipRepository:
    def __init__(self, session) -> None:
        self.session = session

    async def get(self, relationship_id: str) -> Any | None:
        stmt = select(CorrelationRelationship).where(
            CorrelationRelationship.id == relationship_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, **data: Any) -> Any:
        relationship = CorrelationRelationship(**data)
        self.session.add(relationship)
        await self.session.flush()
        return relationship

    async def get_by_triplet(
        self,
        correlation_id: str,
        from_event_id: str,
        to_event_id: str,
        rel_type: str,
    ) -> Any | None:
        stmt = select(CorrelationRelationship).where(
            CorrelationRelationship.correlation_id == correlation_id,
            CorrelationRelationship.from_event_id == from_event_id,
            CorrelationRelationship.to_event_id == to_event_id,
            CorrelationRelationship.type == rel_type,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def upsert_relationship(
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
        """Create a relationship, or update the existing one (dedupe)."""
        existing = await self.get_by_triplet(
            correlation_id, from_event_id, to_event_id, rel_type
        )
        if existing:
            if strength is not None:
                existing.strength = strength
            if evidence_json is not None:
                existing.evidence_json = evidence_json
            if explanation is not None:
                existing.explanation = explanation
            existing.revision += 1
            await self.session.flush()
            return existing

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
        return await self.upsert_relationship(
            correlation_id=correlation_id,
            from_event_id=from_event_id,
            to_event_id=to_event_id,
            rel_type=rel_type,
            strength=strength,
            evidence_json=evidence_json,
            explanation=explanation,
            algorithm_version=algorithm_version,
        )

    async def list_by_group(self, correlation_id: str) -> list:
        stmt = (
            select(CorrelationRelationship)
            .where(CorrelationRelationship.correlation_id == correlation_id)
            .order_by(CorrelationRelationship.created_at)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_groups(self, correlation_ids: list[str]) -> dict[str, list]:
        """Batched form of :meth:`list_by_group` (one query per id chunk).

        Per-group ordering stays ``created_at`` asc, as in :meth:`list_by_group`.
        """
        if not correlation_ids:
            return {}
        unique_ids = list(dict.fromkeys(correlation_ids))
        grouped: dict[str, list] = {}
        chunk_size = 500
        for start in range(0, len(unique_ids), chunk_size):
            chunk = unique_ids[start : start + chunk_size]
            stmt = (
                select(CorrelationRelationship)
                .where(CorrelationRelationship.correlation_id.in_(chunk))
                .order_by(
                    CorrelationRelationship.correlation_id.asc(),
                    CorrelationRelationship.created_at.asc(),
                )
            )
            result = await self.session.execute(stmt)
            for rel in result.scalars().all():
                grouped.setdefault(rel.correlation_id, []).append(rel)
        return grouped

    async def list_by_event(self, event_id: str) -> list:
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
        stmt = select(CorrelationRelationship).where(
            CorrelationRelationship.correlation_id == correlation_id,
            CorrelationRelationship.type == rel_type,
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_events(
        self, correlation_id: str, from_event_id: str, to_event_id: str
    ) -> Any | None:
        stmt = select(CorrelationRelationship).where(
            CorrelationRelationship.correlation_id == correlation_id,
            CorrelationRelationship.from_event_id == from_event_id,
            CorrelationRelationship.to_event_id == to_event_id,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def delete(self, relationship_id: str) -> bool:
        stmt = select(CorrelationRelationship).where(
            CorrelationRelationship.id == relationship_id
        )
        result = await self.session.execute(stmt)
        relationship = result.scalar_one_or_none()
        if not relationship:
            return False
        await self.session.delete(relationship)
        return True