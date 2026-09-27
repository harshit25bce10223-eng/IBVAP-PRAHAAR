# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 7 — PlateCandidate Repository
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.anpr import PlateCandidate


class PlateCandidateRepository:
    """
    Component 7 plate candidate query repository.
    All queries are bounded.
    """

    MAX_PAGE_SIZE = 500
    DEFAULT_PAGE_SIZE = 50

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── Single record lookups ─────────────────────────────────────────────────

    async def get(self, candidate_id: str) -> PlateCandidate | None:
        result = await self.session.execute(
            select(PlateCandidate).where(PlateCandidate.candidate_id == candidate_id)
        )
        return result.scalar_one_or_none()

    # ── Paginated list ────────────────────────────────────────────────────────

    async def list_candidates(
        self,
        *,
        plate_read_id: str | None = None,
        sighting_id: str | None = None,
        rank: int | None = None,
        format_status: str | None = None,
        min_confidence: float | None = None,
        search: str | None = None,
        sort: str = "rank",
        order: str = "asc",
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[PlateCandidate], int]:
        """Returns (candidates, total_count)."""
        page_size = min(page_size, self.MAX_PAGE_SIZE)
        page = max(page, 1)
        offset = (page - 1) * page_size

        filters: list[Any] = []
        if plate_read_id:
            filters.append(PlateCandidate.plate_read_id == plate_read_id)
        if sighting_id:
            filters.append(PlateCandidate.sighting_id == sighting_id)
        if rank:
            filters.append(PlateCandidate.rank == rank)
        if format_status:
            filters.append(PlateCandidate.format_status == format_status)
        if min_confidence is not None:
            filters.append(PlateCandidate.confidence >= min_confidence)
        if search:
            q = search.upper().replace(" ", "")
            filters.append(or_(
                PlateCandidate.raw_read.ilike(f"%{q}%"),
                PlateCandidate.normalized_read.ilike(f"%{q}%"),
            ))

        where_clause = and_(*filters) if filters else True

        # Count
        count_q = select(func.count()).select_from(PlateCandidate).where(where_clause)
        total: int = (await self.session.execute(count_q)).scalar_one()

        # Sort
        sort_col = {
            "rank": PlateCandidate.rank,
            "confidence": PlateCandidate.confidence,
            "format_status": PlateCandidate.format_status,
            "raw_read": PlateCandidate.raw_read,
        }.get(sort, PlateCandidate.rank)

        order_fn = desc if order == "desc" else asc

        rows_q = (
            select(PlateCandidate)
            .where(where_clause)
            .order_by(order_fn(sort_col))
            .offset(offset)
            .limit(page_size)
        )
        rows = (await self.session.execute(rows_q)).scalars().all()
        return list(rows), total