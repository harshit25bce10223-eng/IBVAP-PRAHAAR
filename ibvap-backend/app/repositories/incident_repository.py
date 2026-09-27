# ─────────────────────────────────────────────────────────────────────────────
# IBVAP — Incident Repository
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.incident import Incident


class IncidentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, incident_id: str) -> Incident | None:
        res = await self.session.execute(select(Incident).where(Incident.incident_id == incident_id))
        return res.scalar_one_or_none()

    async def create(
        self,
        *,
        risk_score: int,
        raw_score: int | None,
        severity: str,
        factors: list[dict[str, Any]],
        event_id: str,
        camera_id: str,
        track_id: str,
        zone_id: str,
        created_at: datetime | None = None,
    ) -> Incident:
        incident = Incident(
            risk_score=risk_score,
            raw_score=raw_score,
            severity=severity,
            factors_json=json.dumps(factors),
            event_id=event_id,
            camera_id=camera_id,
            track_id=track_id,
            zone_id=zone_id,
            created_at=created_at or datetime.now(timezone.utc),
        )
        self.session.add(incident)
        await self.session.flush()
        return incident

    async def list_recent(
        self,
        camera_id: str | None = None,
        zone_id: str | None = None,
        track_id: str | None = None,
        limit: int = 50,
    ) -> list[Incident]:
        stmt = select(Incident)
        if camera_id:
            stmt = stmt.where(Incident.camera_id == camera_id)
        if zone_id:
            stmt = stmt.where(Incident.zone_id == zone_id)
        if track_id:
            stmt = stmt.where(Incident.track_id == track_id)
        stmt = stmt.order_by(Incident.created_at.desc()).limit(min(limit, 300))
        res = await self.session.execute(stmt)
        return list(res.scalars().all())