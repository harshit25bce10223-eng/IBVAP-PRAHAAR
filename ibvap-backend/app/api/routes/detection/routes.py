# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 5 — Detection API Routes
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db_session
from app.domain.detection.service import DetectionService
from app.core.logging import get_logger
from app.schemas.detection import (
    BoundingBox,
    CameraHealthContext,
    DetectionSummary,
    DetectionPage,
    DetectionDetailResponse,
    DetectionFeedResponse,
    CameraDetectionSummary,
    EdgeSyncInfo,
    InferenceHealthResponse,
    LatencyInfo,
    ProviderMetadata,
    DetectionConfigCreate,
    DetectionConfigUpdate,
    DetectionConfigResponse,
    DetectionIngestRequest,
    DetectionIngestResponse,
)

logger = get_logger(__name__)

router = APIRouter(prefix="/detections", tags=["detection"], redirect_slashes=False)


def _camera_health_context(d: Any) -> CameraHealthContext | None:
    """Build the camera health snapshot from stored columns; None when never captured."""
    state = getattr(d, "camera_health_state", None)
    reliability = getattr(d, "camera_health_reliability", None)
    viewpoint = getattr(d, "camera_viewpoint_shift", None)
    captured = getattr(d, "camera_health_captured_at", None)
    if state is None and reliability is None and viewpoint is None and captured is None:
        return None
    return CameraHealthContext(
        state=state,
        reliability=reliability,
        viewpoint_shift=viewpoint,
        captured_at=captured.isoformat() if isinstance(captured, datetime) else captured,
    )


def _provider_metadata(d: Any) -> ProviderMetadata | None:
    """Build provider metadata from stored columns; None when nothing was recorded."""
    fields = {
        "model_name": getattr(d, "model_name", None),
        "model_version": getattr(d, "model_version", None),
        "runtime_version": getattr(d, "runtime_version", None),
        "device": getattr(d, "device", None),
        "inference_mode": getattr(d, "inference_mode", None),
        "postprocess_version": getattr(d, "postprocess_version", None),
    }
    if all(v is None for v in fields.values()):
        return None
    return ProviderMetadata(**fields)


def _edge_sync(d: Any) -> EdgeSyncInfo | None:
    """Build edge sync info from stored columns; None when nothing was recorded."""
    fields = {
        "sync_state": getattr(d, "sync_state", None),
        "payload_hash": getattr(d, "sync_payload_hash", None),
        "edge_device_id": getattr(d, "edge_device_id", None),
        "source_event_id": getattr(d, "source_event_id", None),
        "source_sequence": getattr(d, "source_sequence", None),
    }
    if all(v is None for v in fields.values()):
        return None
    return EdgeSyncInfo(**fields)


def _latency(d: Any) -> LatencyInfo | None:
    """Build the latency breakdown from stored columns; None when never measured."""
    inference_ms = getattr(d, "inference_latency_ms", None)
    queue_ms = getattr(d, "queue_latency_ms", None)
    if inference_ms is None and queue_ms is None:
        return None
    total_ms = inference_ms + queue_ms if inference_ms is not None and queue_ms is not None else None
    return LatencyInfo(inference_ms=inference_ms, queue_ms=queue_ms, total_ms=total_ms)


def _to_detection_summary(d: Any) -> DetectionSummary:
    if isinstance(d, DetectionSummary):
        return d
    
    obs = d.observed_at.isoformat() if isinstance(d.observed_at, datetime) else str(d.observed_at or "")
    rec = d.received_at.isoformat() if isinstance(d.received_at, datetime) else str(d.received_at or "")
    proc = d.processed_at.isoformat() if isinstance(d.processed_at, datetime) else (str(d.processed_at) if d.processed_at else None)
    
    if hasattr(d, "bbox") and d.bbox is not None:
        bbox = d.bbox if isinstance(d.bbox, BoundingBox) else BoundingBox(**d.bbox)
    else:
        bbox = BoundingBox(
            x=getattr(d, "bbox_x", 0.0),
            y=getattr(d, "bbox_y", 0.0),
            width=getattr(d, "bbox_width", 0.0),
            height=getattr(d, "bbox_height", 0.0),
        )
    
    return DetectionSummary(
        detection_id=d.detection_id,
        camera_id=d.camera_id,
        frame_id=getattr(d, "frame_id", None),
        event_id=getattr(d, "event_id", None),
        track_id=getattr(d, "track_id", None),
        incident_id=getattr(d, "incident_id", None),
        evidence_id=getattr(d, "evidence_id", None),
        class_name=d.class_name,
        class_id=getattr(d, "class_id", None),
        confidence=getattr(d, "confidence", None),
        bbox=bbox,
        frame_width=getattr(d, "frame_width", None),
        frame_height=getattr(d, "frame_height", None),
        # Missing stored values surface as UNKNOWN — never silently upgraded
        # to a positive state (GOOD / DETECTED / DEMO).
        quality_state=getattr(d, "quality_state", None) or "UNKNOWN",
        occlusion_state=getattr(d, "occlusion_state", None) or "UNKNOWN",
        detection_state=getattr(d, "detection_state", None) or "UNKNOWN",
        source=getattr(d, "source", None) or "UNKNOWN",
        provider=getattr(d, "provider", None),
        observed_at=obs,
        received_at=rec,
        processed_at=proc,
        camera_health_context=_camera_health_context(d),
        provider_metadata=_provider_metadata(d),
        edge_sync=_edge_sync(d),
        latency=_latency(d),
    )


def _to_detection_detail(d: Any, anpr_ref: str | None = None) -> DetectionDetailResponse:
    if isinstance(d, DetectionDetailResponse):
        return d
    
    obs = d.observed_at.isoformat() if isinstance(d.observed_at, datetime) else str(d.observed_at or "")
    rec = d.received_at.isoformat() if isinstance(d.received_at, datetime) else str(d.received_at or "")
    proc = d.processed_at.isoformat() if isinstance(d.processed_at, datetime) else (str(d.processed_at) if d.processed_at else None)
    
    if hasattr(d, "bbox") and d.bbox is not None:
        bbox = d.bbox if isinstance(d.bbox, BoundingBox) else BoundingBox(**d.bbox)
    else:
        bbox = BoundingBox(
            x=getattr(d, "bbox_x", 0.0),
            y=getattr(d, "bbox_y", 0.0),
            width=getattr(d, "bbox_width", 0.0),
            height=getattr(d, "bbox_height", 0.0),
        )
    
    return DetectionDetailResponse(
        detection_id=d.detection_id,
        camera_id=d.camera_id,
        frame_id=getattr(d, "frame_id", None),
        event_id=getattr(d, "event_id", None),
        track_id=getattr(d, "track_id", None),
        incident_id=getattr(d, "incident_id", None),
        evidence_id=getattr(d, "evidence_id", None),
        class_name=d.class_name,
        class_id=getattr(d, "class_id", None),
        taxonomy_version=getattr(d, "taxonomy_version", None),
        provider_class=getattr(d, "provider_class", None),
        confidence=getattr(d, "confidence", None),
        bbox=bbox,
        frame_width=getattr(d, "frame_width", None),
        frame_height=getattr(d, "frame_height", None),
        quality_state=getattr(d, "quality_state", None) or "UNKNOWN",
        occlusion_state=getattr(d, "occlusion_state", None) or "UNKNOWN",
        detection_state=getattr(d, "detection_state", None) or "UNKNOWN",
        source=getattr(d, "source", None) or "UNKNOWN",
        provider=getattr(d, "provider", None),
        model_name=getattr(d, "model_name", None),
        model_version=getattr(d, "model_version", None),
        runtime_version=getattr(d, "runtime_version", None),
        device=getattr(d, "device", None),
        inference_mode=getattr(d, "inference_mode", None),
        postprocess_version=getattr(d, "postprocess_version", None),
        schema_version=getattr(d, "schema_version", None) or "UNKNOWN",
        region_profile=getattr(d, "region_profile", None),
        sector_id=getattr(d, "sector_id", None),
        observed_at=obs,
        received_at=rec,
        processed_at=proc,
        inference_latency_ms=getattr(d, "inference_latency_ms", None),
        queue_latency_ms=getattr(d, "queue_latency_ms", None),
        payload_json=getattr(d, "payload_json", None),
        camera_health_context=_camera_health_context(d),
        provider_metadata=_provider_metadata(d),
        edge_sync=_edge_sync(d),
        latency=_latency(d),
        anpr_ref=anpr_ref,
    )


async def get_detection_service(session: AsyncSession = Depends(get_db_session)) -> DetectionService:
    from app.domain.detection.service import DetectionService
    return DetectionService(session)


# ─────────────────────────────────────────────────────────────────────────────
# Detection List / Query
# ─────────────────────────────────────────────────────────────────────────────

# Allowed sort fields
ALLOWED_SORT_FIELDS = {"observed_at", "received_at", "created_at", "confidence", "class_name", "camera_id"}

@router.get("/", response_model=DetectionPage)
async def list_detections(
    camera_id: str | None = Query(None, description="Filter by camera ID"),
    class_name: str | None = Query(None, description="Filter by detection class (OTHER expands to OBJECT + UNKNOWN)"),
    source: str | None = Query(None, description="Filter by source (EDGE, CENTRAL, REMOTE)"),
    state: str | None = Query(None, description="Filter by detection state"),
    quality: str | None = Query(None, description="Filter by quality state (GOOD, LIMITED, POOR, UNKNOWN)"),
    search: str | None = Query(None, description="Case-insensitive search across ID fields"),
    region_profile: str | None = Query(None, description="Filter by region profile"),
    sector_id: str | None = Query(None, description="Filter by sector ID"),
    event_id: str | None = Query(None, description="Filter by event ID"),
    track_id: str | None = Query(None, description="Filter by track ID"),
    incident_id: str | None = Query(None, description="Filter by incident ID"),
    from_time: str | None = Query(None, description="Start time (ISO format)"),
    to_time: str | None = Query(None, description="End time (ISO format)"),
    min_confidence: float | None = Query(None, ge=0.0, le=1.0, description="Minimum confidence"),
    sort: str = Query("observed_at", description="Sort field"),
    order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Page size"),
    service: DetectionService = Depends(get_detection_service),
) -> DetectionPage:
    """List detections with filtering, sorting, and pagination."""
    from_time_dt = datetime.fromisoformat(from_time.replace("Z", "+00:00")) if from_time else None
    to_time_dt = datetime.fromisoformat(to_time.replace("Z", "+00:00")) if to_time else None
    
    # Validate date range
    if from_time_dt and to_time_dt and from_time_dt > to_time_dt:
        raise HTTPException(status_code=422, detail="from_time must be before or equal to to_time")
    
    # Validate sort field
    if sort not in ALLOWED_SORT_FIELDS:
        raise HTTPException(status_code=422, detail=f"Invalid sort field: {sort}. Allowed: {', '.join(sorted(ALLOWED_SORT_FIELDS))}")
    
    # "OTHER" is a UI grouping, not a canonical class — expand to the actual
    # canonical classes it covers (OBJECT + UNKNOWN).
    class_names: list[str] | None = None
    effective_class = class_name
    if class_name and class_name.upper() == "OTHER":
        class_names = ["OBJECT", "UNKNOWN"]
        effective_class = None
    
    detections, total = await service.list_detections(
        camera_id=camera_id,
        class_name=effective_class,
        class_names=class_names,
        source=source,
        state=state,
        quality=quality,
        search=search,
        region_profile=region_profile,
        sector_id=sector_id,
        event_id=event_id,
        track_id=track_id,
        incident_id=incident_id,
        from_time=from_time_dt,
        to_time=to_time_dt,
        min_confidence=min_confidence,
        sort=sort,
        order=order,
        page=page,
        page_size=page_size,
    )
    
    return DetectionPage(
        detections=[_to_detection_summary(d) for d in detections],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/recent", response_model=list[DetectionSummary])
async def get_recent_detections(
    hours: int = Query(24, ge=1, le=168, description="Hours to look back"),
    camera_id: str | None = Query(None, description="Filter by camera ID"),
    sector_id: str | None = Query(None, description="Filter by sector ID"),
    limit: int = Query(100, ge=1, le=500, description="Maximum results"),
    service: DetectionService = Depends(get_detection_service),
) -> list[DetectionSummary]:
    """Get recent detections for dashboard/wall."""
    detections = await service.get_recent(
        hours=hours,
        camera_id=camera_id,
        sector_id=sector_id,
        limit=limit,
    )
    return [_to_detection_summary(d) for d in detections]


# ─────────────────────────────────────────────────────────────────────────────
# Camera-Scoped Detections
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/cameras/{camera_id}", response_model=list[DetectionSummary])
async def list_camera_detections(
    camera_id: str,
    from_time: str | None = Query(None, description="Start time (ISO format)"),
    to_time: str | None = Query(None, description="End time (ISO format)"),
    class_name: str | None = Query(None, description="Filter by class"),
    state: str | None = Query(None, description="Filter by state"),
    limit: int = Query(100, ge=1, le=500, description="Maximum results"),
    service: DetectionService = Depends(get_detection_service),
) -> list[DetectionSummary]:
    """Get detections for a specific camera (Single Camera integration)."""
    from_time_dt = datetime.fromisoformat(from_time.replace("Z", "+00:00")) if from_time else None
    to_time_dt = datetime.fromisoformat(to_time.replace("Z", "+00:00")) if to_time else None
    
    detections = await service.list_camera_detections(
        camera_id=camera_id,
        from_time=from_time_dt,
        to_time=to_time_dt,
        class_name=class_name,
        state=state,
        limit=limit,
    )
    return [_to_detection_summary(d) for d in detections]


@router.get("/cameras/{camera_id}/summary", response_model=CameraDetectionSummary)
async def get_camera_detection_summary(
    camera_id: str,
    from_time: str | None = Query(None, description="Start time (ISO format)"),
    to_time: str | None = Query(None, description="End time (ISO format)"),
    service: DetectionService = Depends(get_detection_service),
) -> CameraDetectionSummary:
    """Get detection summary for a camera."""
    from_time_dt = datetime.fromisoformat(from_time.replace("Z", "+00:00")) if from_time else None
    to_time_dt = datetime.fromisoformat(to_time.replace("Z", "+00:00")) if to_time else None
    
    # Validate camera exists by checking config
    config = await service.config_repo.get_by_camera(camera_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")
    
    summary = await service.get_camera_summary(
        camera_id=camera_id,
        from_time=from_time_dt,
        to_time=to_time_dt,
    )
    return CameraDetectionSummary(**summary)


@router.get("/cameras/{camera_id}/feed", response_model=DetectionFeedResponse)
async def get_camera_detection_feed(
    camera_id: str,
    limit: int = Query(100, ge=1, le=500, description="Maximum detections to include"),
    service: DetectionService = Depends(get_detection_service),
) -> DetectionFeedResponse:
    """
    Composed feed for one camera: pipeline availability + recent detections.

    Availability is deliberately separated from object presence:
    - UNCONFIGURED: no active detection config — no pipeline exists to ask.
    - UNAVAILABLE:  the provider could not be initialized (FAILED / UNAVAILABLE).
    - STALE:        provider is loading/warming/degraded — output not fresh.
    - NO_OBJECTS:   provider answered, zero detections for this camera.
    - READY:        provider answered and detections are included below.
    A failed provider request never reads as "no objects detected".
    """
    config = await service.config_repo.get_by_camera(camera_id)
    if not config or not config.active:
        # No pipeline exists to ask — do not claim the detector "found nothing".
        return DetectionFeedResponse(
            camera_id=camera_id,
            state="UNCONFIGURED",
            inference="UNKNOWN",
            last_updated_at=None,
            detections=[],
        )

    try:
        # Same provider/service boundary as frame processing. No silent
        # fallback to demo when a real provider cannot be loaded.
        provider = await service.initialize_provider(camera_id, config)
        health = await provider.health()
    except Exception as exc:
        logger.warning("Detection feed provider unavailable for %s: %s", camera_id, exc)
        return DetectionFeedResponse(
            camera_id=camera_id,
            state="UNAVAILABLE",
            inference="FAILED",
            last_updated_at=None,
            detections=[],
        )

    detections = await service.list_camera_detections(camera_id=camera_id, limit=limit)
    summaries = [_to_detection_summary(d) for d in detections]
    # list_camera_detections orders by observed_at desc — first row is newest.
    last_updated_at = summaries[0].observed_at if summaries else None

    raw_state = (health.state or "UNKNOWN").upper()
    if raw_state == "READY":
        state = "READY" if summaries else "NO_OBJECTS"
        inference = "READY"
    elif raw_state in ("LOADING", "WARMING"):
        # Provider is coming up; any listed rows are historical, not fresh.
        state = "STALE"
        inference = raw_state
    elif raw_state == "PROCESSING":
        state = "READY" if summaries else "STALE"
        inference = "PROCESSING"
    elif raw_state == "DEGRADED":
        state = "STALE"
        inference = "DEGRADED"
    elif raw_state in ("FAILED", "UNAVAILABLE"):
        state = "UNAVAILABLE"
        inference = raw_state
    else:
        # Unrecognized/unreported provider state — surfaced as-is, never
        # upgraded to a positive state.
        state = "STALE"
        inference = "UNKNOWN"

    return DetectionFeedResponse(
        camera_id=camera_id,
        state=state,
        inference=inference,
        last_updated_at=last_updated_at,
        detections=summaries,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Detection Detail
# ─────────────────────────────────────────────────────────────────────────────

async def _resolve_anpr_ref(detection_id: str, session: AsyncSession) -> str | None:
    """
    Read-only soft reference to Component 7: the newest vehicle sighting that
    cites this detection, if any. C5 never writes or interprets ANPR data.
    """
    from sqlalchemy import select
    from app.models.anpr.models import VehicleSighting

    stmt = (
        select(VehicleSighting.sighting_id)
        .where(VehicleSighting.detection_id == detection_id)
        .order_by(VehicleSighting.observed_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    return result.scalar_one_or_none()


@router.get("/{detection_id}", response_model=DetectionDetailResponse)
async def get_detection(
    detection_id: str,
    service: DetectionService = Depends(get_detection_service),
) -> DetectionDetailResponse:
    """Get full detection detail."""
    detection = await service.get_detection(detection_id)
    if not detection:
        raise HTTPException(status_code=404, detail="Detection not found")
    anpr_ref = await _resolve_anpr_ref(detection_id, service.session)
    return _to_detection_detail(detection, anpr_ref=anpr_ref)


# ─────────────────────────────────────────────────────────────────────────────
# Related Detections
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/events/{event_id}", response_model=list[DetectionSummary])
async def get_detections_by_event(
    event_id: str,
    service: DetectionService = Depends(get_detection_service),
) -> list[DetectionSummary]:
    """Get detections associated with an event."""
    detections = await service.get_by_event(event_id)
    return [_to_detection_summary(d) for d in detections]


@router.get("/tracks/{track_id}", response_model=list[DetectionSummary])
async def get_detections_by_track(
    track_id: str,
    service: DetectionService = Depends(get_detection_service),
) -> list[DetectionSummary]:
    """Get detections associated with a track."""
    detections = await service.get_by_track(track_id)
    return [_to_detection_summary(d) for d in detections]


@router.get("/incidents/{incident_id}", response_model=list[DetectionSummary])
async def get_detections_by_incident(
    incident_id: str,
    service: DetectionService = Depends(get_detection_service),
) -> list[DetectionSummary]:
    """Get detections associated with an incident."""
    detections = await service.get_by_incident(incident_id)
    return [_to_detection_summary(d) for d in detections]


# ─────────────────────────────────────────────────────────────────────────────
# Inference Health
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/inference/health", response_model=dict[str, Any])
async def get_inference_health(
    camera_id: str | None = Query(None, description="Specific camera, or all if omitted"),
    service: DetectionService = Depends(get_detection_service),
) -> dict[str, Any]:
    """Get inference provider health status."""
    if camera_id:
        health = await service.get_provider_health(camera_id)
        if not health:
            raise HTTPException(status_code=404, detail=f"No provider for camera {camera_id}")
        return health
    return await service.get_all_provider_health()


@router.get("/inference/metrics", response_model=dict[str, Any])
async def get_inference_metrics(
    hours: int = Query(24, ge=1, le=168),
    service: DetectionService = Depends(get_detection_service),
) -> dict[str, Any]:
    """Get inference performance metrics."""
    return await service.get_inference_metrics(hours=hours)


# ─────────────────────────────────────────────────────────────────────────────
# Internal / Edge Ingestion
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/internal/ingest", response_model=DetectionIngestResponse)
async def ingest_detections(
    request: DetectionIngestRequest,
    service: DetectionService = Depends(get_detection_service),
) -> DetectionIngestResponse:
    """
    Internal endpoint for edge/central ingestion of pre-computed detections.
    
    This endpoint accepts canonical detection results (already normalized)
    and stores them with idempotency guarantees.
    """
    # This would be used by edge devices or central inference workers
    # to push detection results directly
    raise HTTPException(status_code=501, detail="Not implemented - use frame ingestion")


# ─────────────────────────────────────────────────────────────────────────────
# Config Management
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/config", response_model=DetectionConfigResponse)
async def create_detection_config(
    config_data: DetectionConfigCreate,
    session=Depends(get_db_session),
) -> DetectionConfigResponse:
    """Create detection configuration for a camera."""
    from app.repositories.detection import DetectionConfigRepository
    config_repo = DetectionConfigRepository(session)
    
    # Check if config already exists for camera
    existing = await config_repo.get_by_camera(config_data.camera_id)
    if existing:
        raise HTTPException(status_code=409, detail=f"Config already exists for camera {config_data.camera_id}")
    
    config = await config_repo.create(**config_data.model_dump())
    await session.commit()
    return DetectionConfigResponse.model_validate(config, from_attributes=True)


@router.get("/config/{camera_id}", response_model=DetectionConfigResponse)
async def get_camera_detection_config(
    camera_id: str,
    session=Depends(get_db_session),
) -> DetectionConfigResponse:
    """Get detection config for a camera."""
    from app.repositories.detection import DetectionConfigRepository
    config_repo = DetectionConfigRepository(session)
    config = await config_repo.get_by_camera(camera_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return DetectionConfigResponse.model_validate(config, from_attributes=True)


@router.patch("/config/{camera_id}", response_model=DetectionConfigResponse)
async def update_detection_config(
    camera_id: str,
    config_data: DetectionConfigUpdate,
    session=Depends(get_db_session),
) -> DetectionConfigResponse:
    """Update detection configuration for a camera."""
    from app.repositories.detection import DetectionConfigRepository
    config_repo = DetectionConfigRepository(session)
    config = await config_repo.get_by_camera(camera_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    
    config = await config_repo.update(config.config_id, **config_data.model_dump(exclude_unset=True))
    await session.commit()
    return DetectionConfigResponse.model_validate(config, from_attributes=True)


@router.delete("/config/{camera_id}")
async def delete_detection_config(
    camera_id: str,
    session=Depends(get_db_session),
) -> dict[str, bool]:
    """Delete detection configuration for a camera."""
    from app.repositories.detection import DetectionConfigRepository
    config_repo = DetectionConfigRepository(session)
    config = await config_repo.get_by_camera(camera_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    
    deleted = await config_repo.delete(config.config_id)
    await session.commit()
    return {"deleted": deleted}