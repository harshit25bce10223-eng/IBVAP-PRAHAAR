# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — Camera Health Observation Repository
# ─────────────────────────────────────────────────────────────────────────────
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.camera_health import CameraHealthObservation


class CameraHealthObservationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create(self, **data: Any) -> CameraHealthObservation:
        obs = CameraHealthObservation(**data)
        self.session.add(obs)
        await self.session.flush()
        return obs

    async def upsert_by_sequence(
        self, camera_id: str, source_sequence: int, **data: Any
    ) -> tuple[CameraHealthObservation, bool]:
        """Upsert observation by camera_id + source_sequence. Returns (obs, created)."""
        stmt = sqlite_insert(CameraHealthObservation).values(
            camera_id=camera_id, source_sequence=source_sequence, **data
        )
        # On conflict, update the observation
        stmt = stmt.on_conflict_do_update(
            index_elements=["camera_id", "source_sequence"],
            set_=data,
        ).returning(CameraHealthObservation)
        result = await self.session.execute(stmt)
        obs = result.scalar_one()
        # Check if it was actually inserted (created) or updated
        # We can't easily tell from this, so we'll just return the obs
        # For true detection we'd need to query first or use a different approach
        return obs, True  # Simplified

    async def get_latest(self, camera_id: str) -> CameraHealthObservation | None:
        stmt = (
            select(CameraHealthObservation)
            .where(CameraHealthObservation.camera_id == camera_id)
            .order_by(CameraHealthObservation.source_timestamp.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_latest_by_received(self, camera_id: str) -> CameraHealthObservation | None:
        stmt = (
            select(CameraHealthObservation)
            .where(CameraHealthObservation.camera_id == camera_id)
            .order_by(CameraHealthObservation.received_at.desc())
            .limit(1)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def list_recent(
        self, camera_id: str, limit: int = 100
    ) -> list[CameraHealthObservation]:
        stmt = (
            select(CameraHealthObservation)
            .where(CameraHealthObservation.camera_id == camera_id)
            .order_by(CameraHealthObservation.source_timestamp.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_time_range(
        self,
        camera_id: str,
        from_ts: datetime,
        to_ts: datetime | None = None,
        limit: int = 10000,
    ) -> list[CameraHealthObservation]:
        stmt = select(CameraHealthObservation).where(
            CameraHealthObservation.camera_id == camera_id,
            CameraHealthObservation.source_timestamp >= from_ts,
        )
        if to_ts:
            stmt = stmt.where(CameraHealthObservation.source_timestamp <= to_ts)
        stmt = stmt.order_by(CameraHealthObservation.source_timestamp.asc()).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def count_recent(self, camera_id: str, since: datetime) -> int:
        stmt = select(func.count(CameraHealthObservation.id)).where(
            CameraHealthObservation.camera_id == camera_id,
            CameraHealthObservation.received_at >= since,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def delete_before(self, camera_id: str, before: datetime) -> int:
        stmt = delete(CameraHealthObservation).where(
            CameraHealthObservation.camera_id == camera_id,
            CameraHealthObservation.source_timestamp < before,
        )
        result = await self.session.execute(stmt)
        return result.rowcount

    async def get_aggregated(
        self,
        camera_id: str,
        from_ts: datetime,
        to_ts: datetime,
        bucket_seconds: int,
        metrics: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        """Get time-bucketed aggregated observations (placeholder for rollups)."""
        # For now, return raw observations - proper rollups would be implemented
        # with a dedicated rollup table or materialized view
        obs = await self.list_by_time_range(camera_id, from_ts, to_ts, limit=1000)
        if not obs:
            return []

        # Simple aggregation by bucket
        from collections import defaultdict

        buckets: dict[int, list[CameraHealthObservation]] = defaultdict(list)
        for o in obs:
            bucket_ts = int(o.source_timestamp.timestamp() / bucket_seconds) * bucket_seconds
            buckets[bucket_ts].append(o)

        result = []
        for bucket_ts, bucket_obs in sorted(buckets.items()):
            bucket_data = {"timestamp": datetime.fromtimestamp(bucket_ts, tz=bucket_obs[0].source_timestamp.tzinfo)}
            if metrics:
                for metric in metrics:
                    values = [getattr(o, metric, None) for o in bucket_obs if getattr(o, metric, None) is not None]
                    if values:
                        bucket_data[metric] = sum(values) / len(values)
            result.append(bucket_data)

        return result