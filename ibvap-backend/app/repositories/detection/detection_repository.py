# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 5 — Detection Repository
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.detection import Detection, DetectionConfig, DetectionSyncState


class DetectionRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ─────────────────────────────────────────────────────────────────────────
    # Detection CRUD
    # ─────────────────────────────────────────────────────────────────────────

    async def get(self, detection_id: str) -> Detection | None:
        stmt = select(Detection).where(Detection.detection_id == detection_id)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, **data: Any) -> Detection:
        detection = Detection(**data)
        self.session.add(detection)
        await self.session.flush()
        return detection

    async def create_batch(self, detections: list[dict[str, Any]]) -> list[Detection]:
        """Create multiple detections atomically."""
        objs = [Detection(**d) for d in detections]
        self.session.add_all(objs)
        await self.session.flush()
        return objs

    async def update(self, detection_id: str, **data: Any) -> Detection | None:
        detection = await self.get(detection_id)
        if not detection:
            return None
        for key, value in data.items():
            if hasattr(detection, key):
                setattr(detection, key, value)
        await self.session.flush()
        return detection

    async def delete(self, detection_id: str) -> bool:
        detection = await self.get(detection_id)
        if not detection:
            return False
        await self.session.delete(detection)
        return True

    # ─────────────────────────────────────────────────────────────────────────
    # Queries
    # ─────────────────────────────────────────────────────────────────────────

    async def list_detections(
        self,
        camera_id: str | None = None,
        class_name: str | None = None,
        source: str | None = None,
        state: str | None = None,
        region_profile: str | None = None,
        sector_id: str | None = None,
        event_id: str | None = None,
        track_id: str | None = None,
        incident_id: str | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        min_confidence: float | None = None,
        sort: str = "observed_at",
        order: str = "desc",
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[Detection], int]:
        """List detections with filtering and pagination."""
        stmt = select(Detection)

        if camera_id:
            stmt = stmt.where(Detection.camera_id == camera_id)
        if class_name:
            stmt = stmt.where(Detection.class_name == class_name)
        if source:
            stmt = stmt.where(Detection.source == source)
        if state:
            stmt = stmt.where(Detection.detection_state == state)
        if region_profile:
            stmt = stmt.where(Detection.region_profile == region_profile)
        if sector_id:
            stmt = stmt.where(Detection.sector_id == sector_id)
        if event_id:
            stmt = stmt.where(Detection.event_id == event_id)
        if track_id:
            stmt = stmt.where(Detection.track_id == track_id)
        if incident_id:
            stmt = stmt.where(Detection.incident_id == incident_id)
        if from_time:
            stmt = stmt.where(Detection.observed_at >= from_time)
        if to_time:
            stmt = stmt.where(Detection.observed_at <= to_time)
        if min_confidence is not None:
            stmt = stmt.where(Detection.confidence >= min_confidence)

        # Count total
        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        # Apply sorting
        sort_column = getattr(Detection, sort, Detection.observed_at)
        if order == "desc":
            stmt = stmt.order_by(sort_column.desc())
        else:
            stmt = stmt.order_by(sort_column.asc())

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        result = await self.session.execute(stmt)
        records = list(result.scalars().all())

        return records, total

    async def list_camera_detections(
        self,
        camera_id: str,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        class_name: str | None = None,
        state: str | None = None,
        limit: int = 100,
    ) -> list[Detection]:
        """Get recent detections for a specific camera."""
        stmt = select(Detection).where(Detection.camera_id == camera_id)

        if from_time:
            stmt = stmt.where(Detection.observed_at >= from_time)
        if to_time:
            stmt = stmt.where(Detection.observed_at <= to_time)
        if class_name:
            stmt = stmt.where(Detection.class_name == class_name)
        if state:
            stmt = stmt.where(Detection.detection_state == state)

        stmt = stmt.order_by(Detection.observed_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_camera_summary(
        self,
        camera_id: str,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
    ) -> dict[str, Any]:
        """Get detection summary for a camera."""
        stmt = select(Detection).where(Detection.camera_id == camera_id)

        if from_time:
            stmt = stmt.where(Detection.observed_at >= from_time)
        if to_time:
            stmt = stmt.where(Detection.observed_at <= to_time)

        result = await self.session.execute(stmt)
        detections = list(result.scalars().all())

        total = len(detections)
        by_class: dict[str, int] = {}
        low_confidence = 0
        quality_summary: dict[str, int] = {}

        for d in detections:
            by_class[d.class_name] = by_class.get(d.class_name, 0) + 1
            if d.confidence is not None and d.confidence < 0.5:
                low_confidence += 1
            quality_summary[d.quality_state] = quality_summary.get(d.quality_state, 0) + 1

        last_observed = max((d.observed_at for d in detections), default=None)

        return {
            "camera_id": camera_id,
            "total_detections": total,
            "by_class": by_class,
            "low_confidence_count": low_confidence,
            "quality_summary": quality_summary,
            "last_observed_at": last_observed.isoformat() if last_observed else None,
            "from_time": from_time.isoformat() if from_time else None,
            "to_time": to_time.isoformat() if to_time else None,
        }

    async def get_recent(
        self,
        hours: int = 24,
        camera_id: str | None = None,
        sector_id: str | None = None,
        limit: int = 100,
    ) -> list[Detection]:
        """Get recent detections."""
        from datetime import datetime, timezone, timedelta
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        stmt = select(Detection).where(Detection.observed_at >= cutoff)

        if camera_id:
            stmt = stmt.where(Detection.camera_id == camera_id)
        if sector_id:
            stmt = stmt.where(Detection.sector_id == sector_id)

        stmt = stmt.order_by(Detection.observed_at.desc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_event(self, event_id: str) -> list[Detection]:
        """Get detections associated with an event."""
        stmt = select(Detection).where(Detection.event_id == event_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_track(self, track_id: str) -> list[Detection]:
        """Get detections associated with a track."""
        stmt = select(Detection).where(Detection.track_id == track_id).order_by(Detection.observed_at)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_incident(self, incident_id: str) -> list[Detection]:
        """Get detections associated with an incident."""
        stmt = select(Detection).where(Detection.incident_id == incident_id).order_by(Detection.observed_at)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_unsynced(self, limit: int = 100) -> list[Detection]:
        """Get detections pending sync (for edge)."""
        stmt = select(Detection).where(
            Detection.sync_state.in_([DetectionSyncState.LOCAL_ONLY, DetectionSyncState.SYNC_PENDING])
        ).order_by(Detection.observed_at).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def mark_synced(self, detection_ids: list[str], sync_hash: str) -> int:
        """Mark detections as synced."""
        if not detection_ids:
            return 0
        stmt = (
            select(Detection)
            .where(Detection.detection_id.in_(detection_ids))
        )
        result = await self.session.execute(stmt)
        detections = list(result.scalars().all())
        
        count = 0
        for d in detections:
            d.sync_state = DetectionSyncState.SYNCED
            d.sync_payload_hash = sync_hash
            count += 1
        
        await self.session.flush()
        return count

    async def mark_sync_failed(self, detection_ids: list[str]) -> int:
        """Mark detections as sync failed."""
        if not detection_ids:
            return 0
        stmt = select(Detection).where(Detection.detection_id.in_(detection_ids))
        result = await self.session.execute(stmt)
        detections = list(result.scalars().all())
        
        count = 0
        for d in detections:
            d.sync_state = DetectionSyncState.SYNC_FAILED
            count += 1
        
        await self.session.flush()
        return count

    # ─────────────────────────────────────────────────────────────────────────
    # Idempotency / Deduplication
    # ─────────────────────────────────────────────────────────────────────────

    async def get_by_source_event(
        self, camera_id: str, source_event_id: str, source_sequence: int
    ) -> Detection | None:
        """Get detection by source event (for edge idempotency)."""
        stmt = (
            select(Detection)
            .where(
                Detection.camera_id == camera_id,
                Detection.source_event_id == source_event_id,
                Detection.source_sequence == source_sequence,
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def get_by_payload_hash(self, camera_id: str, payload_hash: str) -> Detection | None:
        """Get detection by payload hash (secondary deduplication)."""
        stmt = (
            select(Detection)
            .where(
                Detection.camera_id == camera_id,
                Detection.sync_payload_hash == payload_hash,
            )
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    # ─────────────────────────────────────────────────────────────────────────
    # Statistics
    # ─────────────────────────────────────────────────────────────────────────

    async def count_by_camera(
        self,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
    ) -> dict[str, int]:
        """Count detections per camera."""
        stmt = select(Detection.camera_id, func.count(Detection.detection_id))
        
        if from_time:
            stmt = stmt.where(Detection.observed_at >= from_time)
        if to_time:
            stmt = stmt.where(Detection.observed_at <= to_time)
        
        stmt = stmt.group_by(Detection.camera_id)
        result = await self.session.execute(stmt)
        return dict(result.all())

    async def count_by_class(
        self,
        camera_id: str | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
    ) -> dict[str, int]:
        """Count detections by class."""
        stmt = select(Detection.class_name, func.count(Detection.detection_id))
        
        if camera_id:
            stmt = stmt.where(Detection.camera_id == camera_id)
        if from_time:
            stmt = stmt.where(Detection.observed_at >= from_time)
        if to_time:
            stmt = stmt.where(Detection.observed_at <= to_time)
        
        stmt = stmt.group_by(Detection.class_name)
        result = await self.session.execute(stmt)
        return dict(result.all())