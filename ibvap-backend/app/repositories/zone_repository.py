# ─────────────────────────────────────────────────────────────────────────────
# IBVAP — Zone Repository
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.zone import Zone


class ZoneRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, zone_id: str) -> Zone | None:
        res = await self.session.execute(select(Zone).where(Zone.zone_id == zone_id))
        return res.scalar_one_or_none()

    async def list_by_camera(self, camera_id: str, active_only: bool = False) -> list[Zone]:
        stmt = select(Zone).where(Zone.camera_id == camera_id)
        if active_only:
            stmt = stmt.where(Zone.active.is_(True))
        stmt = stmt.order_by(Zone.created_at)
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def list_all(self) -> list[Zone]:
        res = await self.session.execute(select(Zone).order_by(Zone.created_at))
        return list(res.scalars().all())

    async def create(
        self,
        *,
        zone_id: str | None,
        camera_id: str,
        name: str,
        polygon: list[dict],
        rules: dict,
        active: bool = True,
    ) -> Zone:
        now = datetime.now(timezone.utc)
        zone = Zone(
            zone_id=zone_id,
            camera_id=camera_id,
            name=name,
            polygon_json=json.dumps(polygon),
            rules_json=json.dumps(rules),
            active=active,
            created_at=now,
            updated_at=now,
        )
        self.session.add(zone)
        await self.session.flush()
        return zone

    async def update(
        self,
        zone: Zone,
        *,
        name: str | None = None,
        polygon: list[dict] | None = None,
        rules: dict | None = None,
        active: bool | None = None,
    ) -> Zone:
        now = datetime.now(timezone.utc)
        if name is not None:
            zone.name = name
        if polygon is not None:
            zone.polygon_json = json.dumps(polygon)
        if rules is not None:
            zone.rules_json = json.dumps(rules)
        if active is not None:
            zone.active = active
        zone.updated_at = now
        await self.session.flush()
        return zone

    async def delete(self, zone_id: str) -> bool:
        zone = await self.get(zone_id)
        if zone is None:
            return False
        await self.session.delete(zone)
        await self.session.flush()
        return True