# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — Evaluation Routes
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import IBVAPError
from app.db.database import get_db_session
from app.domain.camera_health.provider import get_camera_health_provider
from app.domain.incidents.incident_service import IncidentService
from app.repositories.event_repository import EventRepository
from app.repositories.incident_repository import IncidentRepository
from app.repositories.track_repository import TrackRepository
from app.repositories.zone_repository import ZoneRepository
from app.schemas.evaluation import TrackEvaluateRequest
from app.schemas.incident import TrackEvaluateResponse

router = APIRouter(prefix="/evaluation", tags=["evaluation"])


@router.post("/track_and_evaluate", response_model=TrackEvaluateResponse)
async def track_and_evaluate(
    body: TrackEvaluateRequest,
    session: AsyncSession = Depends(get_db_session),
):
    # Get camera health context for Component 1 integration
    health_provider = get_camera_health_provider()
    health_context = None
    if health_provider:
        health_context = await health_provider.get_latest_health_context(body.camera_id)

    # Extract health signals for IncidentService
    viewpoint_shift_detected = False
    fence_confidence_override = None
    uncertainty_margin = 0.02  # default from config
    reliability = body.reliability

    if health_context:
        viewpoint_shift_detected = health_context.get("viewpoint_shift_detected", False)
        fence_confidence_override = health_context.get("fence_confidence_override")
        # Override reliability if health context provides it
        if health_context.get("reliability"):
            reliability = health_context["reliability"]
        uncertainty_margin = health_context.get("uncertainty_margin", 0.02)

    service = IncidentService(
        session=session,
        zone_repo=ZoneRepository(session),
        track_repo=TrackRepository(session),
        event_repo=EventRepository(session),
        incident_repo=IncidentRepository(session),
    )
    try:
        result = await service.evaluate_track(
            track_id=body.track_id,
            camera_id=body.camera_id,
            object_type=body.object_type,
            bbox=body.bbox.model_dump(),
            confidence=body.confidence,
            is_night=body.is_night,
            multi_camera_confirmed=body.multi_camera_confirmed,
            reliability=reliability,
            ts=body.timestamp,
            viewpoint_shift_detected=viewpoint_shift_detected,
            fence_confidence_override=fence_confidence_override,
            uncertainty_margin=uncertainty_margin,
        )
    except IBVAPError as exc:
        raise exc
    return result