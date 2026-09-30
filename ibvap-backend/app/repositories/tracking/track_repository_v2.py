# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 6 — TrackRepositoryV2
#
# Full async repository for Component 6 track queries.
# (TrackRepository in app/repositories/track_repository.py is preserved for
#  Component 1 compatibility — this file adds the full tracking engine queries.)
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.tracking.constants import (
    TRACK_STATUSES_ACTIVE_SET,
    TRACK_STATUSES_INACTIVE_SET,
    TRACK_STATUS_STALE,
)
from app.models.tracking import TrackCandidate, TrackHistory, TrackV2


class TrackRepositoryV2:
    """
    Component 6 track query repository.
    All queries are bounded — no unbounded result sets returned.
    """

    MAX_PAGE_SIZE = 200
    DEFAULT_PAGE_SIZE = 20

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── Single record lookups ─────────────────────────────────────────────────

    async def get(self, track_id: str) -> TrackV2 | None:
        result = await self.session.execute(
            select(TrackV2).where(TrackV2.track_id == track_id)
        )
        return result.scalar_one_or_none()

    # ── Active tracks for a camera ────────────────────────────────────────────

    async def get_active_for_camera(
        self, camera_id: str, *, limit: int = 200
    ) -> list[TrackV2]:
        """Current active/tentative/reacquired tracks for a camera."""
        result = await self.session.execute(
            select(TrackV2)
            .where(
                TrackV2.camera_id == camera_id,
                TrackV2.status.in_(TRACK_STATUSES_ACTIVE_SET),
            )
            .order_by(desc(TrackV2.last_seen_at))
            .limit(min(limit, self.MAX_PAGE_SIZE))
        )
        return list(result.scalars().all())

    # ── Recent tracks (for dashboard / camera wall) ───────────────────────────

    async def get_recent_for_camera(
        self,
        camera_id: str,
        *,
        since: datetime | None = None,
        limit: int = 50,
    ) -> list[TrackV2]:
        """Recent tracks (all statuses) for one camera, most-recent first."""
        q = select(TrackV2).where(TrackV2.camera_id == camera_id)
        if since:
            q = q.where(TrackV2.last_seen_at >= since)
        q = q.order_by(desc(TrackV2.last_seen_at)).limit(min(limit, self.MAX_PAGE_SIZE))
        result = await self.session.execute(q)
        return list(result.scalars().all())

    # ── All active tracks (sector overview / dashboard) ───────────────────────

    async def get_all_active(self, *, limit: int = 500) -> list[TrackV2]:
        result = await self.session.execute(
            select(TrackV2)
            .where(TrackV2.status.in_(TRACK_STATUSES_ACTIVE_SET))
            .order_by(desc(TrackV2.last_seen_at))
            .limit(min(limit, 1000))
        )
        return list(result.scalars().all())

    # ── Paginated filtered track list ─────────────────────────────────────────

    async def list_tracks(
        self,
        *,
        camera_id: str | None = None,
        status: str | None = None,
        object_class: str | None = None,
        source: str | None = None,
        sector_id: str | None = None,
        region_profile: str | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        search: str | None = None,
        sort: str = "last_seen",
        order: str = "desc",
        page: int = 1,
        page_size: int = DEFAULT_PAGE_SIZE,
    ) -> tuple[list[TrackV2], int]:
        """Returns (tracks, total_count)."""
        page_size = min(page_size, self.MAX_PAGE_SIZE)
        page = max(page, 1)
        offset = (page - 1) * page_size

        filters: list[Any] = []
        if camera_id:
            filters.append(TrackV2.camera_id == camera_id)
        if status:
            filters.append(TrackV2.status == status)
        if object_class:
            filters.append(TrackV2.object_class == object_class)
        if source:
            filters.append(TrackV2.source == source)
        if sector_id:
            filters.append(TrackV2.sector_id == sector_id)
        if region_profile:
            filters.append(TrackV2.region_profile == region_profile)
        if from_time:
            filters.append(TrackV2.last_seen_at >= from_time)
        if to_time:
            filters.append(TrackV2.last_seen_at <= to_time)
        if search:
            like = f"%{search}%"
            filters.append(or_(
                TrackV2.track_id.ilike(like),
                TrackV2.camera_id.ilike(like),
            ))

        where_clause = and_(*filters) if filters else True

        # Count
        count_q = select(func.count()).select_from(TrackV2).where(where_clause)
        total: int = (await self.session.execute(count_q)).scalar_one()

        # Sort
        # 'longest' orders by track DURATION (last_seen − first_seen), matching
        # the frontend sort contract; other keys are direct column sorts.
        # NOTE: julianday() is SQLite-specific — this stack is SQLite-only
        # (DATABASE_URL sqlite+aiosqlite). If the DB is ever migrated to
        # PostgreSQL, replace with EXTRACT(EPOCH FROM ...) math.
        order_fn = desc if order == "desc" else asc
        if sort == "longest":
            duration_expr = (
                func.julianday(TrackV2.last_seen_at) - func.julianday(TrackV2.first_seen_at)
            )
            order_expr = order_fn(duration_expr)
        else:
            sort_col = {
                "last_seen":     TrackV2.last_seen_at,
                "first_seen":    TrackV2.first_seen_at,
                "observations":  TrackV2.observation_count,
                "camera":        TrackV2.camera_id,
            }.get(sort, TrackV2.last_seen_at)
            order_expr = order_fn(sort_col)

        rows_q = (
            select(TrackV2)
            .where(where_clause)
            .order_by(order_expr)
            .offset(offset)
            .limit(page_size)
        )
        rows = (await self.session.execute(rows_q)).scalars().all()
        return list(rows), total

    # ── Camera summary counts ─────────────────────────────────────────────────

    async def get_camera_summary(self, camera_id: str) -> dict[str, Any]:
        """Count tracks by status for one camera."""
        rows = await self.session.execute(
            select(TrackV2.status, func.count().label("n"))
            .where(TrackV2.camera_id == camera_id)
            .group_by(TrackV2.status)
        )
        by_status: dict[str, int] = {}
        for row in rows:
            by_status[row.status] = row.n

        rows_class = await self.session.execute(
            select(TrackV2.object_class, func.count().label("n"))
            .where(
                TrackV2.camera_id == camera_id,
                TrackV2.status.in_(TRACK_STATUSES_ACTIVE_SET),
            )
            .group_by(TrackV2.object_class)
        )
        by_class: dict[str, int] = {}
        for row in rows_class:
            by_class[row.object_class] = row.n

        total_active = sum(
            v for k, v in by_status.items()
            if k in TRACK_STATUSES_ACTIVE_SET
        )
        total_all = sum(by_status.values())

        last_updated_result = await self.session.execute(
            select(func.max(TrackV2.last_seen_at)).where(TrackV2.camera_id == camera_id)
        )
        last_updated = last_updated_result.scalar_one_or_none()

        return {
            "camera_id": camera_id,
            "total_active": total_active,
            "total_tracks": total_all,
            "by_class": by_class,
            "by_status": by_status,
            # SQLite round-trips drop tzinfo — pin UTC before serializing so
            # browsers parse it as an absolute instant, not local time.
            "last_updated_at": (
                (last_updated if last_updated.tzinfo else last_updated.replace(tzinfo=timezone.utc)).isoformat()
                if last_updated else None
            ),
        }

    # ── Track history ─────────────────────────────────────────────────────────

    async def get_track_history(
        self,
        track_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[TrackHistory], int]:
        count_r = await self.session.execute(
            select(func.count()).select_from(TrackHistory).where(
                TrackHistory.track_id == track_id
            )
        )
        total = count_r.scalar_one()

        rows = await self.session.execute(
            select(TrackHistory)
            .where(TrackHistory.track_id == track_id)
            .order_by(desc(TrackHistory.timestamp))
            .offset(offset)
            .limit(min(limit, 200))
        )
        return list(rows.scalars().all()), total

    # ── Cross-camera candidates ───────────────────────────────────────────────

    async def get_candidates(self, track_id: str) -> list[TrackCandidate]:
        result = await self.session.execute(
            select(TrackCandidate)
            .where(TrackCandidate.source_track_id == track_id)
            .order_by(desc(TrackCandidate.created_at))
            .limit(20)
        )
        return list(result.scalars().all())

    # ── Stale track marking ───────────────────────────────────────────────────

    async def get_tracks_older_than(
        self,
        *,
        camera_id: str | None = None,
        older_than: datetime,
        statuses: list[str] | None = None,
        limit: int = 500,
    ) -> list[TrackV2]:
        """Used by background stale-marking job."""
        filters = [TrackV2.last_seen_at < older_than]
        if camera_id:
            filters.append(TrackV2.camera_id == camera_id)
        if statuses:
            filters.append(TrackV2.status.in_(statuses))

        result = await self.session.execute(
            select(TrackV2)
            .where(and_(*filters))
            .order_by(TrackV2.last_seen_at)
            .limit(limit)
        )
        return list(result.scalars().all())
