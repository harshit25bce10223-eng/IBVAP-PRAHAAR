# ─────────────────────────────────────────────────────────────────────────────
# IBVAP — Incident & Event Routes
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db_session
from app.repositories.event_repository import EventRepository
from app.repositories.incident_repository import IncidentRepository
from app.schemas.incident import EventOut, IncidentOut

router = APIRouter(tags=["incidents"])


def _incident_out(incident) -> IncidentOut:
    return IncidentOut(
        incident_id=incident.incident_id,
        risk_score=incident.risk_score,
        severity=incident.severity,
        factors=json.loads(incident.factors_json),
        event_id=incident.event_id,
        camera_id=incident.camera_id,
        track_id=incident.track_id,
        zone_id=incident.zone_id,
        created_at=incident.created_at,
    )


def _event_out(event) -> EventOut:
    return EventOut(
        event_id=event.event_id,
        event_type=event.event_type,
        camera_id=event.camera_id,
        track_id=event.track_id,
        zone_id=event.zone_id,
        payload=json.loads(event.payload_json) if event.payload_json else None,
        ts=event.ts,
    )


@router.get("/incidents", response_model=list[IncidentOut], response_model_exclude_none=True)
async def list_incidents(
    camera_id: str | None = None,
    zone_id: str | None = None,
    track_id: str | None = None,
    limit: int = 50,
    session: AsyncSession = Depends(get_db_session),
):
    repo = IncidentRepository(session)
    incidents = await repo.list_recent(camera_id=camera_id, zone_id=zone_id, track_id=track_id, limit=limit)
    return [_incident_out(i) for i in incidents]


@router.get("/incidents/{incident_id}", response_model=IncidentOut)
async def get_incident(incident_id: str, session: AsyncSession = Depends(get_db_session)):
    from app.core.errors import IncidentNotFoundError

    repo = IncidentRepository(session)
    incident = await repo.get(incident_id)
    if incident is None:
        raise IncidentNotFoundError(incident_id)
    return _incident_out(incident)


@router.get("/events", response_model=list[EventOut], response_model_exclude_none=True)
async def list_events(
    camera_id: str | None = None,
    limit: int = 50,
    session: AsyncSession = Depends(get_db_session),
):
    repo = EventRepository(session)
    events = await repo.list_recent(camera_id=camera_id, limit=limit)
    return [_event_out(e) for e in events]