# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 7 — PlateRead Repository
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.anpr import PlateRead, PlateCandidate


class PlateReadRepository:
    """
    Component 7 plate read query repository.
    All queries are bounded.
    """

    MAX_PAGE_SIZE = 500
    DEFAULT_PAGE_SIZE = 50

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── Single record lookups ─────────────────────────────────────────────────

    async def get(self, plate_read_id: str) -> PlateRead | None:
        result = await self.session.execute(
            select(PlateRead).where(PlateRead.plate_read_id == plate_read_id)
        )
        return result.scalar_one_or_none()

    async def get_by_sighting(self, sighting_id: str) -> PlateRead | None:
        result = await self.session.execute(
            select(PlateRead).where(PlateRead.sighting_id == sighting_id)
        )
        return result.scalar_one_or_none()

    # ── Plate read by normalized/raw ──────────────────────────────────────────

    async def get_by_normalized(self, normalized_read: str) -> PlateRead | None:
        """Exact match on normalized plate read."""
        result = await self.session.execute(
            select(PlateRead).where(PlateRead.normalized_read == normalized_read)
        )
        return result.scalar_one_or_none()

    async def search_normalized(
        self,
        query: str,
        *,
        limit: int = 50,
    ) -> list[PlateRead]:
        """Search normalized reads (partial match)."""
        q = query.upper().replace(" ", "")
        if not q:
            return []

        result = await self.session.execute(
            select(PlateRead)
            .where(PlateRead.normalized_read.ilike(f"%{q}%"))
            .order_by(desc(PlateRead.observed_at))
            .limit(min(limit, self.MAX_PAGE_SIZE))
        )
        return list(result.scalars().all())

    async def search_raw(
        self,
        query: str,
        *,
        limit: int = 50,
    ) -> list[PlateRead]:
        """Search raw reads (partial match)."""
        q = query.upper().replace(" ", "")
        if not q:
            return []

        result = await self.session.execute(
            select(PlateRead)
            .where(PlateRead.raw_read.ilike(f"%{q}%"))
            .order_by(desc(PlateRead.observed_at))
            .limit(min(limit, self.MAX_PAGE_SIZE))
        )
        return list(result.scalars().all())

    # ── Candidates for a plate read ───────────────────────────────────────────

    async def get_candidates(self, plate_read_id: str) -> list[PlateCandidate]:
        result = await self.session.execute(
            select(PlateCandidate)
            .where(PlateCandidate.plate_read_id == plate_read_id)
            .order_by(PlateCandidate.rank)
        )
        return list(result.scalars().all())

    # ── Paginated list ────────────────────────────────────────────────────────

    async def list_plate_reads(
        self,
        *,
        sighting_id: str | None = None,
        quality: str | None = None,
        format_status: str | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        search: str | None = None,
        sort: str = "observed_at",
        order: str = "desc",
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[PlateRead], int]:
        """Returns (plate_reads, total_count)."""
        page_size = min(page_size, self.MAX_PAGE_SIZE)
        page = max(page, 1)
        offset = (page - 1) * page_size

        filters: list[Any] = []
        if sighting_id:
            filters.append(PlateRead.sighting_id == sighting_id)
        if quality:
            filters.append(PlateRead.quality == quality)
        if format_status:
            filters.append(PlateRead.format_status == format_status)
        if from_time:
            filters.append(PlateRead.observed_at >= from_time)
        if to_time:
            filters.append(PlateRead.observed_at <= to_time)
        if search:
            q = search.upper().replace(" ", "")
            filters.append(or_(
                PlateRead.raw_read.ilike(f"%{q}%"),
                PlateRead.normalized_read.ilike(f"%{q}%"),
                PlateRead.display_read.ilike(f"%{q}%"),
            ))

        where_clause = and_(*filters) if filters else True

        # Count
        count_q = select(func.count()).select_from(PlateRead).where(where_clause)
        total: int = (await self.session.execute(count_q)).scalar_one()

        # Sort
        sort_col = {
            "observed_at": PlateRead.observed_at,
            "raw_read": PlateRead.raw_read,
            "normalized_read": PlateRead.normalized_read,
            "confidence": PlateRead.confidence,
            "quality": PlateRead.quality,
        }.get(sort, PlateRead.observed_at)

        order_fn = desc if order == "desc" else asc

        rows_q = (
            select(PlateRead)
            .where(where_clause)
            .order_by(order_fn(sort_col))
            .offset(offset)
            .limit(page_size)
        )
        rows = (await self.session.execute(rows_q)).scalars().all()
        return list(rows), total

    # ── Candidates list ───────────────────────────────────────────────────────

    async def list_candidates(
        self,
        *,
        plate_read_id: str | None = None,
        sighting_id: str | None = None,
        rank: int | None = None,
        format_status: str | None = None,
        min_confidence: float | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[PlateCandidate], int]:
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

        where_clause = and_(*filters) if filters else True

        # Count
        count_q = select(func.count()).select_from(PlateCandidate).where(where_clause)
        total: int = (await self.session.execute(count_q)).scalar_one()

        rows_q = (
            select(PlateCandidate)
            .where(where_clause)
            .order_by(PlateCandidate.rank)
            .offset(offset)
            .limit(page_size)
        )
        rows = (await self.session.execute(rows_q)).scalars().all()
        return list(rows), total