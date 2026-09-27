# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — Camera Health Baseline Repository
# ─────────────────────────────────────────────────────────────────────────────
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.camera_health import CameraHealthBaseline, IlluminationRegime


class CameraHealthBaselineRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(
        self, camera_id: str, metric_name: str, regime: str = IlluminationRegime.UNKNOWN
    ) -> CameraHealthBaseline | None:
        stmt = select(CameraHealthBaseline).where(
            CameraHealthBaseline.camera_id == camera_id,
            CameraHealthBaseline.metric_name == metric_name,
            CameraHealthBaseline.illumination_regime == regime,
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def get_or_create(
        self,
        camera_id: str,
        metric_name: str,
        regime: str = IlluminationRegime.UNKNOWN,
        **defaults: Any,
    ) -> CameraHealthBaseline:
        baseline = await self.get(camera_id, metric_name, regime)
        if baseline:
            return baseline
        baseline = CameraHealthBaseline(
            camera_id=camera_id,
            metric_name=metric_name,
            illumination_regime=regime,
            **defaults,
        )
        self.session.add(baseline)
        await self.session.flush()
        return baseline

    async def upsert(
        self,
        camera_id: str,
        metric_name: str,
        regime: str = IlluminationRegime.UNKNOWN,
        **data: Any,
    ) -> CameraHealthBaseline:
        stmt = sqlite_insert(CameraHealthBaseline).values(
            camera_id=camera_id,
            metric_name=metric_name,
            illumination_regime=regime,
            **data,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["camera_id", "metric_name", "illumination_regime"],
            set_=data,
        ).returning(CameraHealthBaseline)
        result = await self.session.execute(stmt)
        return result.scalar_one()

    async def list_for_camera(self, camera_id: str) -> list[CameraHealthBaseline]:
        stmt = select(CameraHealthBaseline).where(
            CameraHealthBaseline.camera_id == camera_id
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def increment_version(
        self, camera_id: str, metric_name: str, regime: str = IlluminationRegime.UNKNOWN
    ) -> CameraHealthBaseline | None:
        baseline = await self.get(camera_id, metric_name, regime)
        if baseline:
            baseline.baseline_version += 1
            baseline.reference_updated_at = datetime.now(timezone.utc)
            await self.session.flush()
        return baseline

    async def freeze(
        self, camera_id: str, metric_name: str, regime: str = IlluminationRegime.UNKNOWN
    ) -> CameraHealthBaseline | None:
        baseline = await self.get(camera_id, metric_name, regime)
        if baseline:
            baseline.is_frozen = True
            await self.session.flush()
        return baseline

    async def unfreeze(
        self, camera_id: str, metric_name: str, regime: str = IlluminationRegime.UNKNOWN
    ) -> CameraHealthBaseline | None:
        baseline = await self.get(camera_id, metric_name, regime)
        if baseline:
            baseline.is_frozen = False
            await self.session.flush()
        return baseline