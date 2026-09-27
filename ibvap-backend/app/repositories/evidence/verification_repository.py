# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — Evidence Verification Repository
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evidence import EvidenceVerification


class EvidenceVerificationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, **data: Any) -> EvidenceVerification:
        verification = EvidenceVerification(**data)
        self.session.add(verification)
        await self.session.flush()
        return verification

    async def get(self, verification_id: str) -> EvidenceVerification | None:
        res = await self.session.execute(
            select(EvidenceVerification).where(
                EvidenceVerification.verification_id == verification_id
            )
        )
        return res.scalar_one_or_none()

    async def list_by_evidence(
        self, evidence_id: str, limit: int = 50
    ) -> list[EvidenceVerification]:
        stmt = (
            select(EvidenceVerification)
            .where(EvidenceVerification.evidence_id == evidence_id)
            .order_by(EvidenceVerification.verified_at.desc())
            .limit(limit)
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_latest(self, evidence_id: str) -> EvidenceVerification | None:
        stmt = (
            select(EvidenceVerification)
            .where(EvidenceVerification.evidence_id == evidence_id)
            .order_by(EvidenceVerification.verified_at.desc())
            .limit(1)
        )
        res = await self.session.execute(stmt)
        return res.scalar_one_or_none()

    async def count_by_outcome(
        self, evidence_id: str, outcome: str
    ) -> int:
        from sqlalchemy import func
        stmt = select(func.count(EvidenceVerification.id)).where(
            EvidenceVerification.evidence_id == evidence_id,
            EvidenceVerification.outcome == outcome,
        )
        res = await self.session.execute(stmt)
        return res.scalar_one()