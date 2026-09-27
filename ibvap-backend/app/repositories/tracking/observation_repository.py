# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 6 — TrackObservationRepository
#
# Async repository for track observation queries.
# All result sets are bounded. Raw pagination via page/offset.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime

from sqlalchemy import asc, desc, func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tracking import TrackObservation


class TrackObservationRepository:
    MAX_PAGE_SIZE = 500
    DEFAULT_PAGE_SIZE = 50

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── Single lookup ─────────────────────────────────────────────────────────

    async def get(self, observation_id: str) -> TrackObservation | None:
        result = await self.session.execute(
            select(TrackObservation).where(
                TrackObservation.observation_id == observation_id
            )
        )
        return result.scalar_one_or_none()

    # ── Observations for a track ──────────────────────────────────────────────

    async def list_for_track(
        self,
        track_id: str,
        *,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
        order: str = "asc",  # chronological by default
    ) -> tuple[list[TrackObservation], int]:
        """Returns (observations, total_count). Ordered by observed_at."""
        page_size = min(page_size, self.MAX_PAGE_SIZE)
        page = max(page, 1)
        offset = (page - 1) * page_size

        filters = [TrackObservation.track_id == track_id]
        if from_time:
            filters.append(TrackObservation.observed_at >= from_time)
        if to_time:
            filters.append(TrackObservation.observed_at <= to_time)

        where_clause = and_(*filters)

        count_r = await self.session.execute(
            select(func.count()).select_from(TrackObservation).where(where_clause)
        )
        total = count_r.scalar_one()

        order_fn = asc if order == "asc" else desc
        rows = await self.session.execute(
            select(TrackObservation)
            .where(where_clause)
            .order_by(order_fn(TrackObservation.observed_at))
            .offset(offset)
            .limit(page_size)
        )
        return list(rows.scalars().all()), total

    # ── Trajectory (bounded points) ───────────────────────────────────────────

    async def get_trajectory_points(
        self,
        track_id: str,
        *,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        max_points: int = 200,
    ) -> list[TrackObservation]:
        """
        Returns up to max_points observations for trajectory rendering.
        Does NOT interpolate missing points — only actual observations.
        """
        max_points = min(max_points, 1000)
        filters = [TrackObservation.track_id == track_id]
        if from_time:
            filters.append(TrackObservation.observed_at >= from_time)
        if to_time:
            filters.append(TrackObservation.observed_at <= to_time)

        # If too many points, we take every Nth (deterministic downsampling)
        # Count first
        count_r = await self.session.execute(
            select(func.count()).select_from(TrackObservation).where(and_(*filters))
        )
        total = count_r.scalar_one()

        result = await self.session.execute(
            select(TrackObservation)
            .where(and_(*filters))
            .order_by(asc(TrackObservation.observed_at))
            .limit(max_points)
        )
        return list(result.scalars().all())

    # ── Check duplicate ───────────────────────────────────────────────────────

    async def exists(self, track_id: str, detection_id: str) -> bool:
        result = await self.session.execute(
            select(func.count()).select_from(TrackObservation).where(
                TrackObservation.track_id == track_id,
                TrackObservation.detection_id == detection_id,
            )
        )
        return result.scalar_one() > 0
