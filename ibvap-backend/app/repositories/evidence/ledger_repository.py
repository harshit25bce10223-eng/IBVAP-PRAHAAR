# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — Evidence Ledger Repository
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evidence import EvidenceLedgerRecord


class EvidenceLedgerRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, ledger_record_id: str):
        from app.models.evidence import EvidenceLedgerRecord
        res = await self.session.execute(
            select(EvidenceLedgerRecord).where(
                EvidenceLedgerRecord.ledger_record_id == ledger_record_id
            )
        )
        return res.scalar_one_or_none()

    async def get_last(self) -> Any:
        from app.models.evidence import EvidenceLedgerRecord
        stmt = (
            select(EvidenceLedgerRecord)
            .order_by(EvidenceLedgerRecord.sequence_number.desc())
            .limit(1)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def get_by_evidence(self, evidence_id: str) -> Any:
        from app.models.evidence import EvidenceLedgerRecord
        stmt = select(EvidenceLedgerRecord).where(
            EvidenceLedgerRecord.evidence_id == evidence_id
        ).order_by(EvidenceLedgerRecord.sequence_number.desc())
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def create(self, **data: Any) -> Any:
        from app.models.evidence import EvidenceLedgerRecord
        record = EvidenceLedgerRecord(**data)
        self.session.add(record)
        await self.session.flush()
        return record

    async def append_atomic(
        self,
        evidence_id: str,
        sequence_number: int,
        previous_record_hash: str | None,
        content_hash: str,
        record_hash: str,
        canonical_payload_json: str,
        algorithm_version: str = "SHA-256",
        status: str = "ACTIVE",
    ) -> Any:
        """Append a ledger record atomically with unique sequence number."""
        from app.models.evidence import EvidenceLedgerRecord
        from sqlalchemy.exc import IntegrityError

        record = EvidenceLedgerRecord(
            evidence_id=evidence_id,
            sequence_number=sequence_number,
            previous_record_hash=previous_record_hash,
            content_hash=content_hash,
            record_hash=record_hash,
            canonical_payload_json=canonical_payload_json,
            algorithm_version=algorithm_version,
            status=status,
        )
        self.session.add(record)
        try:
            await self.session.flush()
        except IntegrityError:
            await self.session.rollback()
            raise
        return record

    async def get_all_ordered(self) -> list[Any]:
        from app.models.evidence import EvidenceLedgerRecord
        stmt = select(EvidenceLedgerRecord).order_by(EvidenceLedgerRecord.sequence_number.asc())
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def count(self) -> int:
        from sqlalchemy import func
        from app.models.evidence import EvidenceLedgerRecord
        stmt = select(func.count(EvidenceLedgerRecord.id))
        res = await self.session.execute(stmt)
        return res.scalar_one()