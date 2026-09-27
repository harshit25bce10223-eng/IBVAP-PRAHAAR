# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 7 — VehicleSighting Repository
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select, and_, or_, desc, asc
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.anpr import VehicleSighting

from app.domain.anpr.constants import (
    ANPR_SOURCES,
    PLATE_QUALITIES,
    VEHICLE_CLASSES,
    VEHICLE_DIRECTIONS,
    WATCHLIST_STATUSES,
)


class VehicleSightingRepository:
    """
    Component 7 vehicle sighting query repository.
    All queries are bounded — no unbounded result sets returned.
    """

    MAX_PAGE_SIZE = 500
    DEFAULT_PAGE_SIZE = 50
    MAX_CURSOR_LIMIT = 1000

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── Single record lookups ─────────────────────────────────────────────────

    async def get(self, sighting_id: str) -> VehicleSighting | None:
        result = await self.session.execute(
            select(VehicleSighting).where(VehicleSighting.sighting_id == sighting_id)
        )
        return result.scalar_one_or_none()

    # ── Camera sightings ──────────────────────────────────────────────────────

    async def get_for_camera(
        self,
        camera_id: str,
        *,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        status: str | None = None,
        quality: str | None = None,
        vehicle_class: str | None = None,
        direction: str | None = None,
        watchlist_status: str | None = None,
        limit: int = 100,
    ) -> list[VehicleSighting]:
        """Recent sightings for one camera, most-recent first."""
        filters = [VehicleSighting.camera_id == camera_id]

        if from_time:
            filters.append(VehicleSighting.observed_at >= from_time)
        if to_time:
            filters.append(VehicleSighting.observed_at <= to_time)
        if status:
            filters.append(VehicleSighting.watchlist_status == status)
        if quality:
            filters.append(VehicleSighting.plate_quality == quality)
        if vehicle_class:
            filters.append(VehicleSighting.vehicle_class == vehicle_class)
        if direction:
            filters.append(VehicleSighting.vehicle_direction == direction)
        if watchlist_status:
            filters.append(VehicleSighting.watchlist_status == watchlist_status)

        limit = min(limit, self.MAX_PAGE_SIZE)

        result = await self.session.execute(
            select(VehicleSighting)
            .where(and_(*filters))
            .order_by(desc(VehicleSighting.observed_at))
            .limit(limit)
        )
        return list(result.scalars().all())

    # ── Vehicle history (cross-camera) ────────────────────────────────────────

    async def get_vehicle_history(
        self,
        vehicle_id: str,
        *,
        limit: int = 200,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
    ) -> list[VehicleSighting]:
        """All sightings for a vehicle, chronological by observed_at."""
        filters = [VehicleSighting.vehicle_id == vehicle_id]

        if from_time:
            filters.append(VehicleSighting.observed_at >= from_time)
        if to_time:
            filters.append(VehicleSighting.observed_at <= to_time)

        limit = min(limit, self.MAX_CURSOR_LIMIT)

        result = await self.session.execute(
            select(VehicleSighting)
            .where(and_(*filters))
            .order_by(asc(VehicleSighting.observed_at))
            .limit(min(limit, self.MAX_CURSOR_LIMIT))
        )
        return list(result.scalars().all())

    # ── Paginated filtered sighting list ──────────────────────────────────────

    async def list_sightings(
        self,
        *,
        camera_id: str | None = None,
        vehicle_id: str | None = None,
        track_id: str | None = None,
        detection_id: str | None = None,
        status: str | None = None,
        quality: str | None = None,
        vehicle_class: str | None = None,
        direction: str | None = None,
        watchlist_status: str | None = None,
        source: str | None = None,
        sector_id: str | None = None,
        zone_id: str | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        search: str | None = None,
        sort: str = "observed_at",
        order: str = "desc",
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[VehicleSighting], int]:
        """Returns (sightings, total_count). Cursor-based pagination also supported."""
        page_size = min(page_size, self.MAX_PAGE_SIZE)
        page = max(page, 1)
        offset = (page - 1) * page_size

        filters: list[Any] = []
        if camera_id:
            filters.append(VehicleSighting.camera_id == camera_id)
        if vehicle_id:
            filters.append(VehicleSighting.vehicle_id == vehicle_id)
        if track_id:
            filters.append(VehicleSighting.track_id == track_id)
        if detection_id:
            filters.append(VehicleSighting.detection_id == detection_id)
        if status:
            filters.append(VehicleSighting.watchlist_status == status)
        if quality:
            filters.append(VehicleSighting.plate_quality == quality)
        if vehicle_class:
            filters.append(VehicleSighting.vehicle_class == vehicle_class)
        if direction:
            filters.append(VehicleSighting.vehicle_direction == direction)
        if watchlist_status:
            filters.append(VehicleSighting.watchlist_status == watchlist_status)
        if source:
            filters.append(VehicleSighting.source == source)
        if sector_id:
            filters.append(VehicleSighting.sector_id == sector_id)
        if zone_id:
            filters.append(VehicleSighting.zone_id == zone_id)
        if from_time:
            filters.append(VehicleSighting.observed_at >= from_time)
        if to_time:
            filters.append(VehicleSighting.observed_at <= to_time)
        if search:
            like = f"%{search}%"
            filters.append(or_(
                VehicleSighting.sighting_id.ilike(like),
                VehicleSighting.camera_id.ilike(like),
                VehicleSighting.vehicle_id.ilike(like),
                VehicleSighting.track_id.ilike(like),
            ))

        where_clause = and_(*filters) if filters else True

        # Count
        count_q = select(func.count()).select_from(VehicleSighting).where(where_clause)
        total: int = (await self.session.execute(count_q)).scalar_one()

        # Sort
        sort_col = {
            "observed_at": VehicleSighting.observed_at,
            "received_at": VehicleSighting.received_at,
            "created_at": VehicleSighting.created_at,
            "camera": VehicleSighting.camera_id,
            "vehicle_class": VehicleSighting.vehicle_class,
            "quality": VehicleSighting.plate_quality,
            "confidence": VehicleSighting.confidence,
            "direction": VehicleSighting.vehicle_direction,
        }.get(sort, VehicleSighting.observed_at)

        order_fn = desc if order == "desc" else asc

        rows_q = (
            select(VehicleSighting)
            .where(where_clause)
            .order_by(order_fn(sort_col))
            .offset(offset)
            .limit(page_size)
        )
        rows = (await self.session.execute(rows_q)).scalars().all()
        return list(rows), total

    # ── Cursor-based pagination (for large datasets) ──────────────────────────

    async def list_sightings_cursor(
        self,
        *,
        camera_id: str | None = None,
        vehicle_id: str | None = None,
        track_id: str | None = None,
        detection_id: str | None = None,
        status: str | None = None,
        quality: str | None = None,
        vehicle_class: str | None = None,
        direction: str | None = None,
        watchlist_status: str | None = None,
        source: str | None = None,
        sector_id: str | None = None,
        zone_id: str | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        search: str | None = None,
        sort: str = "observed_at",
        order: str = "desc",
        cursor: str | None = None,
        limit: int = 50,
    ) -> tuple[list[VehicleSighting], str | None]:
        """Cursor-based pagination using observed_at + sighting_id as cursor."""
        limit = min(limit, self.MAX_PAGE_SIZE)

        filters: list[Any] = []
        if camera_id:
            filters.append(VehicleSighting.camera_id == camera_id)
        if vehicle_id:
            filters.append(VehicleSighting.vehicle_id == vehicle_id)
        if track_id:
            filters.append(VehicleSighting.track_id == track_id)
        if detection_id:
            filters.append(VehicleSighting.detection_id == detection_id)
        if status:
            filters.append(VehicleSighting.watchlist_status == status)
        if quality:
            filters.append(VehicleSighting.plate_quality == quality)
        if vehicle_class:
            filters.append(VehicleSighting.vehicle_class == vehicle_class)
        if direction:
            filters.append(VehicleSighting.vehicle_direction == direction)
        if watchlist_status:
            filters.append(VehicleSighting.watchlist_status == watchlist_status)
        if source:
            filters.append(VehicleSighting.source == source)
        if sector_id:
            filters.append(VehicleSighting.sector_id == sector_id)
        if zone_id:
            filters.append(VehicleSighting.zone_id == zone_id)
        if from_time:
            filters.append(VehicleSighting.observed_at >= from_time)
        if to_time:
            filters.append(VehicleSighting.observed_at <= to_time)
        if search:
            like = f"%{search}%"
            filters.append(or_(
                VehicleSighting.sighting_id.ilike(like),
                VehicleSighting.camera_id.ilike(like),
                VehicleSighting.vehicle_id.ilike(like),
                VehicleSighting.track_id.ilike(like),
            ))

        # Parse cursor if provided
        if cursor:
            try:
                cursor_ts, cursor_id = cursor.split("|", 1)
                cursor_dt = datetime.fromisoformat(cursor_ts)
                if order == "desc":
                    filters.append(or_(
                        VehicleSighting.observed_at < cursor_dt,
                        and_(
                            VehicleSighting.observed_at == cursor_dt,
                            VehicleSighting.sighting_id < cursor_id
                        )
                    ))
                else:
                    filters.append(or_(
                        VehicleSighting.observed_at > cursor_dt,
                        and_(
                            VehicleSighting.observed_at == cursor_dt,
                            VehicleSighting.sighting_id > cursor_id
                        )
                    ))
            except Exception:
                pass  # Invalid cursor, ignore

        where_clause = and_(*filters) if filters else True

        sort_col = {
            "observed_at": VehicleSighting.observed_at,
            "received_at": VehicleSighting.received_at,
            "created_at": VehicleSighting.created_at,
            "camera": VehicleSighting.camera_id,
            "vehicle_class": VehicleSighting.vehicle_class,
            "quality": VehicleSighting.plate_quality,
            "confidence": VehicleSighting.confidence,
            "direction": VehicleSighting.vehicle_direction,
        }.get(sort, VehicleSighting.observed_at)

        order_fn = desc if order == "desc" else asc

        rows_q = (
            select(VehicleSighting)
            .where(where_clause)
            .order_by(order_fn(sort_col))
            .limit(limit + 1)  # +1 to detect has_more
        )
        rows = (await self.session.execute(rows_q)).scalars().all()

        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]

        next_cursor = None
        if has_more and rows:
            last = rows[-1]
            next_cursor = f"{last.observed_at.isoformat()}|{last.sighting_id}"

        return list(rows), next_cursor

    # ── Search ────────────────────────────────────────────────────────────────

    async def search_plates(
        self,
        query: str,
        *,
        camera_id: str | None = None,
        match_type: str | None = None,  # exact | partial | raw | candidate
        limit: int = 50,
    ) -> list[VehicleSighting]:
        """
        Search for plates by normalized, raw, or candidate text.
        match_type: 'exact' (normalized), 'partial', 'raw', 'candidate'
        """
        q = query.upper().replace(" ", "")
        if not q:
            return []

        filters: list[Any] = []
        if camera_id:
            filters.append(VehicleSighting.camera_id == camera_id)

        if match_type == "exact":
            # Exact normalized match - would need join with PlateRead
            from app.models.anpr import PlateRead
            filters.append(VehicleSighting.plate_read_id.is_not(None))
        elif match_type == "raw":
            from app.models.anpr import PlateRead
            filters.append(VehicleSighting.plate_read_id.is_not(None))
        elif match_type == "candidate":
            from app.models.anpr import PlateCandidate
            filters.append(VehicleSighting.sighting_id.in_(
                select(PlateCandidate.sighting_id).where(
                    PlateCandidate.raw_read.ilike(f"%{q}%")
                )
            ))

        limit = min(limit, self.MAX_CURSOR_LIMIT)

        # For exact/partial/raw, we'd need to join with PlateRead
        # For now, use a simple ILIKE on sighting_id or vehicle_id as fallback
        if not match_type or match_type == "partial":
            filters.append(or_(
                VehicleSighting.sighting_id.ilike(f"%{q}%"),
                VehicleSighting.vehicle_id.ilike(f"%{q}%"),
                VehicleSighting.track_id.ilike(f"%{q}%"),
                VehicleSighting.camera_id.ilike(f"%{q}%"),
            ))

        where_clause = and_(*filters) if filters else True

        rows_q = (
            select(VehicleSighting)
            .where(where_clause)
            .order_by(desc(VehicleSighting.observed_at))
            .limit(min(limit, self.MAX_CURSOR_LIMIT))
        )
        return list((await self.session.execute(rows_q)).scalars().all())

    # ── Summary / counts ──────────────────────────────────────────────────────

    async def get_camera_summary(self, camera_id: str) -> dict[str, Any]:
        """Count sightings by status/quality for one camera."""
        rows = await self.session.execute(
            select(VehicleSighting.watchlist_status, func.count().label("n"))
            .where(VehicleSighting.camera_id == camera_id)
            .group_by(VehicleSighting.watchlist_status)
        )
        by_status: dict[str, int] = {}
        for row in rows:
            by_status[row.watchlist_status] = row.n

        rows_quality = await self.session.execute(
            select(VehicleSighting.plate_quality, func.count().label("n"))
            .where(
                VehicleSighting.camera_id == camera_id,
                VehicleSighting.plate_quality.is_not(None),
            )
            .group_by(VehicleSighting.plate_quality)
        )
        by_quality: dict[str, int] = {}
        for row in rows_quality:
            by_quality[row.plate_quality] = row.n

        rows_class = await self.session.execute(
            select(VehicleSighting.vehicle_class, func.count().label("n"))
            .where(VehicleSighting.camera_id == camera_id)
            .group_by(VehicleSighting.vehicle_class)
        )
        by_class: dict[str, int] = {}
        for row in rows_class:
            by_class[row.vehicle_class] = row.n

        total = sum(by_status.values())

        last_updated_result = await self.session.execute(
            select(func.max(VehicleSighting.observed_at)).where(VehicleSighting.camera_id == camera_id)
        )
        last_updated = last_updated_result.scalar_one_or_none()

        return {
            "camera_id": camera_id,
            "total_sightings": total,
            "by_status": by_status,
            "by_quality": by_quality,
            "by_class": by_class,
            "last_updated_at": last_updated.isoformat() if last_updated else None,
        }

    # ── Sighting existence check (for idempotency) ────────────────────────────

    async def get_by_detection_track_frame(
        self,
        detection_id: str,
        track_id: str,
    ) -> VehicleSighting | None:
        """Check if a sighting already exists for this detection+track combo."""
        result = await self.session.execute(
            select(VehicleSighting).where(
                VehicleSighting.detection_id == detection_id,
                VehicleSighting.track_id == track_id,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_provider_observation_id(
        self,
        provider_obs_id: str,
    ) -> VehicleSighting | None:
        """Check by provider's internal observation ID (if stored in sync_payload_hash)."""
        result = await self.session.execute(
            select(VehicleSighting).where(
                VehicleSighting.sync_payload_hash == provider_obs_id,
            )
        )
        return result.scalar_one_or_none()

    # ── Stale marking ─────────────────────────────────────────────────────────

    async def get_stale_sightings(
        self,
        *,
        camera_id: str | None = None,
        older_than: datetime,
        statuses: list[str] | None = None,
        limit: int = 500,
    ) -> list[VehicleSighting]:
        """Used by background stale-marking job."""
        filters = [VehicleSighting.observed_at < older_than]
        if camera_id:
            filters.append(VehicleSighting.camera_id == camera_id)
        if statuses:
            filters.append(VehicleSighting.watchlist_status.in_(statuses))

        result = await self.session.execute(
            select(VehicleSighting)
            .where(and_(*filters))
            .order_by(VehicleSighting.observed_at)
            .limit(limit)
        )
        return list(result.scalars().all())