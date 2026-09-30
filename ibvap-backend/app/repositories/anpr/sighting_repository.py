# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 7 — VehicleSighting Repository
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from sqlalchemy import func, select, and_, or_, desc, asc, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.anpr import VehicleSighting, PlateRead, PlateCandidate


# Eager-load the plate observation + candidates for every returned sighting.
# VehicleSightingResponse.from_orm() reads both relationships; with async
# SQLAlchemy a lazy load there would raise MissingGreenlet.
_LOAD_OPTIONS = (
    selectinload(VehicleSighting.plate_read),
    selectinload(VehicleSighting.candidates),
)


def _norm_plate(text: str) -> str:
    """Normalize plate text for comparison: uppercase, alphanumeric only."""
    return "".join(ch for ch in text.upper() if ch.isalnum())


def _iso_utc(dt: datetime | None) -> str | None:
    """ISO-8601 with explicit UTC offset (SQLite returns naive datetimes)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


# Sorting keys accepted by the paginated list endpoints → ORM columns.
_SORT_COLUMNS = {
    "observed_at": "observed_at",
    "received_at": "received_at",
    "created_at": "created_at",
    "camera": "camera_id",
    "vehicle_class": "vehicle_class",
    "quality": "plate_quality",
    "confidence": "confidence",
    "direction": "vehicle_direction",
}

# Search classify map (spec §24). None → no match_type restriction.
_MATCH_TYPE_ALIASES = {
    "exact": "EXACT_NORMALIZED_MATCH",
    "exact_normalized_match": "EXACT_NORMALIZED_MATCH",
    "raw": "RAW_READ_MATCH",
    "raw_read_match": "RAW_READ_MATCH",
    "partial": "PARTIAL_MATCH",
    "partial_match": "PARTIAL_MATCH",
    "candidate": "CANDIDATE_MATCH",
    "candidate_match": "CANDIDATE_MATCH",
    "top_candidate_match": "CANDIDATE_MATCH",
    "related": "RELATED_SIGHTING",
    "related_sighting": "RELATED_SIGHTING",
}


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

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _sort_column(self, sort: str):
        attr = _SORT_COLUMNS.get(sort, "observed_at")
        return getattr(VehicleSighting, attr)

    @staticmethod
    def _order_fn(order: str):
        return desc if order == "desc" else asc

    def _search_clause(self, search: str):
        """Textual search over IDs, camera/vehicle/track links and plate text.

        Covers spec §23: camera, track, plate (normalized/raw/display) and
        candidate text. Uses bounded IN-subqueries so a sighting row is never
        duplicated by the plate joins.
        """
        like = f"%{search.upper()}%"
        q_norm = _norm_plate(search)
        norm_like = f"%{q_norm}%" if q_norm else like
        return or_(
            VehicleSighting.sighting_id.ilike(like),
            VehicleSighting.camera_id.ilike(like),
            VehicleSighting.vehicle_id.ilike(like),
            VehicleSighting.track_id.ilike(like),
            VehicleSighting.detection_id.ilike(like),
            VehicleSighting.sighting_id.in_(
                select(PlateRead.sighting_id).where(or_(
                    PlateRead.raw_read.ilike(like),
                    PlateRead.display_read.ilike(like),
                    PlateRead.normalized_read.ilike(norm_like),
                ))
            ),
            VehicleSighting.sighting_id.in_(
                select(PlateCandidate.sighting_id).where(or_(
                    PlateCandidate.raw_read.ilike(like),
                    PlateCandidate.normalized_read.ilike(norm_like),
                ))
            ),
        )

    # ── Single record lookups ─────────────────────────────────────────────────

    async def get(self, sighting_id: str) -> VehicleSighting | None:
        result = await self.session.execute(
            select(VehicleSighting)
            .options(*_LOAD_OPTIONS)
            .where(VehicleSighting.sighting_id == sighting_id)
        )
        return result.scalar_one_or_none()

    async def get_recent(self, *, limit: int = 100) -> list[VehicleSighting]:
        """Most recent sightings across all cameras."""
        limit = min(max(limit, 1), self.MAX_PAGE_SIZE)
        result = await self.session.execute(
            select(VehicleSighting)
            .options(*_LOAD_OPTIONS)
            .order_by(desc(VehicleSighting.observed_at), desc(VehicleSighting.sighting_id))
            .limit(limit)
        )
        return list(result.scalars().all())

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
            .options(*_LOAD_OPTIONS)
            .where(and_(*filters))
            .order_by(desc(VehicleSighting.observed_at), desc(VehicleSighting.sighting_id))
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
            .options(*_LOAD_OPTIONS)
            .where(and_(*filters))
            .order_by(asc(VehicleSighting.observed_at), asc(VehicleSighting.sighting_id))
            .limit(limit)
        )
        return list(result.scalars().all())

    # ── Paginated filtered sighting list (offset mode) ────────────────────────

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
        confidence_min: float | None = None,
        confidence_max: float | None = None,
        search: str | None = None,
        sort: str = "observed_at",
        order: str = "desc",
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[VehicleSighting], int]:
        """Returns (sightings, total_count)."""
        page_size = min(max(page_size, 1), self.MAX_PAGE_SIZE)
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
        if confidence_min is not None:
            filters.append(VehicleSighting.confidence >= confidence_min)
        if confidence_max is not None:
            filters.append(VehicleSighting.confidence <= confidence_max)
        if search:
            filters.append(self._search_clause(search))

        where_clause = and_(*filters) if filters else True

        # Count
        count_q = select(func.count()).select_from(VehicleSighting).where(where_clause)
        total: int = (await self.session.execute(count_q)).scalar_one()

        sort_col = self._sort_column(sort)
        order_fn = self._order_fn(order)

        rows_q = (
            select(VehicleSighting)
            .options(*_LOAD_OPTIONS)
            .where(where_clause)
            .order_by(order_fn(sort_col), order_fn(VehicleSighting.sighting_id))
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
        confidence_min: float | None = None,
        confidence_max: float | None = None,
        search: str | None = None,
        sort: str = "observed_at",
        order: str = "desc",
        cursor: str | None = None,
        limit: int = 50,
    ) -> tuple[list[VehicleSighting], bool, str | None]:
        """Cursor-based pagination using observed_at + sighting_id as cursor.

        Returns (rows, has_more, next_cursor). A malformed cursor raises
        ValueError so the API layer can answer INVALID_CURSOR instead of
        silently returning page 1.
        """
        limit = min(max(limit, 1), self.MAX_PAGE_SIZE)

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
        if confidence_min is not None:
            filters.append(VehicleSighting.confidence >= confidence_min)
        if confidence_max is not None:
            filters.append(VehicleSighting.confidence <= confidence_max)
        if search:
            filters.append(self._search_clause(search))

        # Parse cursor if provided
        if cursor:
            if sort != "observed_at":
                raise ValueError("Cursor pagination supports sort='observed_at' only.")
            try:
                cursor_ts, cursor_id = cursor.split("|", 1)
                cursor_dt = datetime.fromisoformat(cursor_ts)
            except (ValueError, TypeError):
                raise ValueError(f"Invalid cursor: {cursor!r}")
            if not cursor_id.strip():
                raise ValueError(f"Invalid cursor: {cursor!r}")
            if cursor_dt.tzinfo is None:
                cursor_dt = cursor_dt.replace(tzinfo=timezone.utc)
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

        where_clause = and_(*filters) if filters else True

        sort_col = self._sort_column(sort)
        order_fn = self._order_fn(order)

        rows_q = (
            select(VehicleSighting)
            .options(*_LOAD_OPTIONS)
            .where(where_clause)
            .order_by(order_fn(sort_col), order_fn(VehicleSighting.sighting_id))
            .limit(limit + 1)  # +1 to detect has_more
        )
        rows = (await self.session.execute(rows_q)).scalars().all()

        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]

        next_cursor = None
        if has_more and rows:
            last = rows[-1]
            ts = _iso_utc(last.observed_at)
            if ts:
                next_cursor = f"{ts}|{last.sighting_id}"

        return list(rows), has_more, next_cursor

    # ── Search (spec §23/§24) ─────────────────────────────────────────────────

    async def search_plates(
        self,
        query: str,
        *,
        camera_id: str | None = None,
        match_type: str | None = None,
        limit: int = 50,
    ) -> list[tuple[VehicleSighting, str]]:
        """Search plate observations and classify each hit per spec §24.

        Returns (sighting, match_type) pairs where match_type is one of
        EXACT_NORMALIZED_MATCH | PARTIAL_MATCH | RAW_READ_MATCH |
        CANDIDATE_MATCH | RELATED_SIGHTING.

        Precedence (first match wins): exact normalized read → raw read →
        partial normalized/raw read → plate candidate text → related sighting
        (another sighting of the same vehicle). Partial text matches are never
        reported as exact.

        `match_type` restricts the result to a single classification. Accepts
        the canonical labels or short forms (exact|raw|partial|candidate|related).
        """
        q_raw = query.upper().strip()
        q_norm = _norm_plate(query)
        if not q_raw or not q_norm:
            return []
        limit = min(max(limit, 1), self.MAX_CURSOR_LIMIT)

        asked = _MATCH_TYPE_ALIASES.get((match_type or "").strip().lower())

        async def _fetch(stmt) -> list[VehicleSighting]:
            if camera_id:
                stmt = stmt.where(VehicleSighting.camera_id == camera_id)
            stmt = (
                stmt.options(*_LOAD_OPTIONS)
                .order_by(desc(VehicleSighting.observed_at), desc(VehicleSighting.sighting_id))
                .limit(limit)
            )
            return list((await self.session.execute(stmt)).scalars().all())

        results: list[tuple[VehicleSighting, str]] = []
        seen: set[str] = set()

        def _collect(rows: list[VehicleSighting], label: str) -> None:
            for row in rows:
                if row.sighting_id in seen:
                    continue
                seen.add(row.sighting_id)
                results.append((row, label))

        def _want(label: str) -> bool:
            return asked in (None, label)

        # A — exact normalized read
        if _want("EXACT_NORMALIZED_MATCH") and len(results) < limit:
            rows = await _fetch(
                select(VehicleSighting)
                .join(PlateRead, PlateRead.sighting_id == VehicleSighting.sighting_id)
                .where(func.upper(PlateRead.normalized_read) == q_norm)
            )
            _collect(rows, "EXACT_NORMALIZED_MATCH")

        # B — raw read text
        if _want("RAW_READ_MATCH") and len(results) < limit:
            rows = await _fetch(
                select(VehicleSighting)
                .join(PlateRead, PlateRead.sighting_id == VehicleSighting.sighting_id)
                .where(PlateRead.raw_read.ilike(f"%{q_raw}%"))
            )
            _collect(rows, "RAW_READ_MATCH")

        # C — partial normalized/raw read
        if _want("PARTIAL_MATCH") and len(results) < limit:
            rows = await _fetch(
                select(VehicleSighting)
                .join(PlateRead, PlateRead.sighting_id == VehicleSighting.sighting_id)
                .where(or_(
                    PlateRead.normalized_read.ilike(f"%{q_norm}%"),
                    PlateRead.raw_read.ilike(f"%{q_norm}%"),
                ))
            )
            _collect(rows, "PARTIAL_MATCH")

        # D — plate candidate text
        if _want("CANDIDATE_MATCH") and len(results) < limit:
            rows = await _fetch(
                select(VehicleSighting).where(VehicleSighting.sighting_id.in_(
                    select(PlateCandidate.sighting_id).where(or_(
                        PlateCandidate.raw_read.ilike(f"%{q_raw}%"),
                        PlateCandidate.raw_read.ilike(f"%{q_norm}%"),
                        PlateCandidate.normalized_read.ilike(f"%{q_norm}%"),
                    ))
                ))
            )
            _collect(rows, "CANDIDATE_MATCH")

        # E — related sightings (same vehicle as a matched sighting)
        if _want("RELATED_SIGHTING") and len(results) < limit:
            vehicle_ids = {s.vehicle_id for s, _ in results if s.vehicle_id}
            if vehicle_ids:
                rows = await _fetch(
                    select(VehicleSighting).where(VehicleSighting.vehicle_id.in_(vehicle_ids))
                )
                _collect(rows, "RELATED_SIGHTING")

        return results[:limit]

    # ── Summary / counts ──────────────────────────────────────────────────────

    async def get_camera_summary(self, camera_id: str) -> dict[str, Any]:
        """Count sightings by status/quality/class for one camera."""
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
            "cameraId": camera_id,
            "totalSightings": total,
            "byStatus": by_status,
            "byQuality": by_quality,
            "byClass": by_class,
            "lastUpdatedAt": _iso_utc(last_updated),
        }

    async def get_summary(self) -> dict[str, Any]:
        """Global ANPR summary counts (spec §26 — plate observation counts).

        Classification precedence per sighting:
          unreadable → no plate read, quality UNREADABLE, or format
                       INVALID_FORMAT/UNKNOWN_FORMAT
          partial    → quality PARTIAL or format NOT_ENOUGH_DATA
          readable   → format VALID_FORMAT or POSSIBLE_FORMAT
        """
        total_reads = (
            await self.session.execute(
                select(func.count()).select_from(VehicleSighting)
            )
        ).scalar_one()

        unique_tracked = (
            await self.session.execute(
                select(func.count(func.distinct(VehicleSighting.track_id)))
                .where(VehicleSighting.track_id.is_not(None))
            )
        ).scalar_one()

        cameras_reporting = (
            await self.session.execute(
                select(func.count(func.distinct(VehicleSighting.camera_id)))
            )
        ).scalar_one()

        last_updated = (
            await self.session.execute(
                select(func.max(VehicleSighting.observed_at))
            )
        ).scalar_one_or_none()

        # Single pass over sightings LEFT JOIN their plate read, bucketed.
        bucket = case(
            (
                or_(
                    PlateRead.plate_read_id.is_(None),
                    func.upper(PlateRead.quality) == "UNREADABLE",
                    func.upper(PlateRead.format_status).in_(
                        ["INVALID_FORMAT", "UNKNOWN_FORMAT"]
                    ),
                ),
                "unreadable",
            ),
            (
                or_(
                    func.upper(PlateRead.quality) == "PARTIAL",
                    func.upper(PlateRead.format_status) == "NOT_ENOUGH_DATA",
                ),
                "partial",
            ),
            (
                func.upper(PlateRead.format_status).in_(
                    ["VALID_FORMAT", "POSSIBLE_FORMAT"]
                ),
                "readable",
            ),
            else_="unreadable",
        ).label("bucket")

        rows = await self.session.execute(
            select(bucket, func.count().label("n"))
            .select_from(VehicleSighting)
            .outerjoin(PlateRead, PlateRead.sighting_id == VehicleSighting.sighting_id)
            .group_by(bucket)
        )
        counts = {row.bucket: row.n for row in rows}

        return {
            "totalReads": total_reads,
            "readablePlates": counts.get("readable", 0),
            "partialReads": counts.get("partial", 0),
            "unreadablePlates": counts.get("unreadable", 0),
            "uniqueTrackedSightings": unique_tracked,
            "camerasReporting": cameras_reporting,
            "lastUpdated": _iso_utc(last_updated),
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
        """Check by provider's internal observation ID (stored in sync_payload_hash)."""
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
