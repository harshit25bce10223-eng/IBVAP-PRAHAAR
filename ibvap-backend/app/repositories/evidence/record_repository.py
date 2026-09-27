# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — Evidence Record Repository
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evidence import EvidenceRecord


class EvidenceRecordRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, evidence_id: str) -> EvidenceRecord | None:
        res = await self.session.execute(
            select(EvidenceRecord).where(EvidenceRecord.evidence_id == evidence_id)
        )
        return res.scalar_one_or_none()

    async def create(self, **data: Any) -> EvidenceRecord:
        record = EvidenceRecord(**data)
        self.session.add(record)
        await self.session.flush()
        return record

    async def update(self, evidence_id: str, **data: Any) -> EvidenceRecord | None:
        record = await self.get(evidence_id)
        if not record:
            return None
        for key, value in data.items():
            if hasattr(record, key):
                setattr(record, key, value)
        await self.session.flush()
        return record

    async def delete(self, evidence_id: str) -> bool:
        record = await self.get(evidence_id)
        if not record:
            return False
        await self.session.delete(record)
        return True

    async def list_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        camera_id: str | None = None,
        incident_id: str | None = None,
        event_id: str | None = None,
        search: str | None = None,
        type_: str | None = None,
        integrity: str | None = None,
        anchor: str | None = None,
        source: str | None = None,
        sort: str = "captured_at",
        order: str = "desc",
    ) -> tuple[list[EvidenceRecord], int]:
        stmt = select(EvidenceRecord)

        if camera_id:
            stmt = stmt.where(EvidenceRecord.camera_id == camera_id)
        if incident_id:
            stmt = stmt.where(EvidenceRecord.incident_id == incident_id)
        if event_id:
            stmt = stmt.where(EvidenceRecord.event_id == event_id)
        if search:
            stmt = stmt.where(
                EvidenceRecord.evidence_id.contains(search)
                | EvidenceRecord.incident_id.contains(search)
            )
        if type_:
            stmt = stmt.where(EvidenceRecord.type == type_)
        if integrity:
            stmt = stmt.where(EvidenceRecord.integrity_status == integrity)
        if anchor:
            stmt = stmt.where(EvidenceRecord.anchor_status == anchor)
        if source:
            stmt = stmt.where(EvidenceRecord.source == source)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        # Apply sorting
        sort_column = getattr(EvidenceRecord, sort, EvidenceRecord.captured_at)
        if order == "desc":
            stmt = stmt.order_by(sort_column.desc())
        else:
            stmt = stmt.order_by(sort_column.asc())

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        res = await self.session.execute(stmt)
        records = list(res.scalars().all())

        return records, total

    async def list_by_incident(self, incident_id: str) -> list[EvidenceRecord]:
        stmt = select(EvidenceRecord).where(EvidenceRecord.incident_id == incident_id)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def list_by_camera(self, camera_id: str, limit: int = 50) -> list[EvidenceRecord]:
        stmt = (
            select(EvidenceRecord)
            .where(EvidenceRecord.camera_id == camera_id)
            .order_by(EvidenceRecord.captured_at.desc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def list_by_event(self, event_id: str) -> list[EvidenceRecord]:
        stmt = select(EvidenceRecord).where(EvidenceRecord.event_id == event_id)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def list_by_parent(self, parent_evidence_id: str) -> list[EvidenceRecord]:
        stmt = select(EvidenceRecord).where(EvidenceRecord.parent_evidence_id == parent_evidence_id)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_by_content_hash(self, content_hash: str) -> EvidenceRecord | None:
        stmt = select(EvidenceRecord).where(EvidenceRecord.content_hash == content_hash)
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def count_recent(self, since: datetime) -> int:
        stmt = select(func.count(EvidenceRecord.id)).where(
            EvidenceRecord.created_at >= since
        )
        res = await self.session.execute(stmt)
        return res.scalar_one()

    async def count_by_camera(self, camera_id: str) -> int:
        stmt = select(func.count(EvidenceRecord.id)).where(
            EvidenceRecord.camera_id == camera_id
        )
        res = await self.session.execute(stmt)
        return res.scalar_one()