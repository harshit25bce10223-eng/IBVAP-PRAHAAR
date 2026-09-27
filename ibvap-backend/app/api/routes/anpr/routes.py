# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 7 — ANPR API Routes
#
# Public endpoints:
#   GET  /api/v1/anpr/sightings              — paginated sighting list
#   GET  /api/v1/anpr/sightings/recent       — recent sightings (all cameras)
#   GET  /api/v1/anpr/sightings/{sighting_id} — sighting detail
#   GET  /api/v1/anpr/sightings/{sighting_id}/candidates — plate candidates
#   GET  /api/v1/anpr/vehicles/{vehicle_id}   — vehicle detail
#   GET  /api/v1/anpr/vehicles/{vehicle_id}/history — vehicle history
#   GET  /api/v1/anpr/cameras/{camera_id}/vehicles — sightings for one camera
#   GET  /api/v1/anpr/cameras/{camera_id}/vehicles/feed — ANPRFeed (sightings + state)
#   GET  /api/v1/anpr/cameras/{camera_id}/vehicles/summary — count summary
#   GET  /api/v1/anpr/search                  — plate search
#   GET  /api/v1/anpr/summary                 — global ANPR summary
#   GET  /api/v1/anpr/health                  — provider health
#   GET  /api/v1/anpr/config/{camera_id}      — ANPR config for camera
#
# Internal endpoint (service-to-service):
#   POST /api/v1/internal/anpr/observe        — ingest vehicle sightings
#
# Security: reuses existing CORS / internal header pattern.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import IBVAPError, IBVAPErrorCode
from app.core.logging import get_logger
from app.db.database import get_db_session
from app.domain.anpr.constants import ANPRProviderHealthState
from app.domain.anpr.service import (
    ANPRService,
    SightingNotFoundError,
    ANPRProviderUnavailableError,
)
from app.schemas.anpr import (
    ANPRConfigResponse,
    ANPRProviderHealthResponse,
    ANPRSummaryResponse,
    ANPRFilter,
    ANPRSearchRequest,
    SightingPageResponse,
    VehicleHistoryResponse,
    VehicleSightingResponse,
    ANPRIngestRequest,
    ANPRIngestResponse,
)

logger = get_logger("prhaar.anpr.routes")

router = APIRouter(prefix="/anpr", tags=["anpr"])


# ─────────────────────────────────────────────────────────────────────────────
# Dependency helpers
# ─────────────────────────────────────────────────────────────────────────────

def _svc(session: AsyncSession = Depends(get_db_session)) -> ANPRService:
    return ANPRService(session)


def _parse_iso(value: str | None, field_name: str) -> datetime | None:
    if value is None:
        return None
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "INVALID_QUERY", "message": f"Invalid ISO timestamp for {field_name}: {value}"}},
        )


def _anpr_error_response(code: str, message: str, status: int = 400):
    return HTTPException(
        status_code=status,
        detail={"error": {"code": code, "message": message}},
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/anpr/sightings  — paginated, filtered sighting list
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/sightings",
    response_model=SightingPageResponse,
    summary="List sightings (paginated, filtered)",
    description=(
        "Returns a paginated, filtered list of vehicle sightings. "
        "Supports filtering by camera, vehicle, track, detection, status, quality, "
        "vehicle class, direction, source, sector, zone, time range, and text search."
    ),
)
async def list_sightings(
    camera_id: Optional[str] = Query(None, description="Filter by camera ID"),
    vehicle_id: Optional[str] = Query(None, description="Filter by vehicle ID"),
    track_id: Optional[str] = Query(None, description="Filter by track ID"),
    detection_id: Optional[str] = Query(None, description="Filter by detection ID"),
    status: Optional[str] = Query(None, description="Filter by watchlist status"),
    quality: Optional[str] = Query(None, description="Filter by plate quality"),
    vehicle_class: Optional[str] = Query(None, alias="class", description="Filter by vehicle class"),
    direction: Optional[str] = Query(None, description="Filter by vehicle direction"),
    watchlist_status: Optional[str] = Query(None, description="Filter by watchlist status"),
    source: Optional[str] = Query(None, description="Filter by source"),
    sector_id: Optional[str] = Query(None, description="Filter by sector ID"),
    zone_id: Optional[str] = Query(None, description="Filter by zone ID"),
    from_time: Optional[str] = Query(None, description="ISO 8601 start time"),
    to_time: Optional[str] = Query(None, description="ISO 8601 end time"),
    search: Optional[str] = Query(None, max_length=128, description="Search query"),
    sort: str = Query("observed_at", regex="^(observed_at|received_at|created_at|camera|vehicle_class|quality|confidence|direction)$"),
    order: str = Query("desc", regex="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500, alias="pageSize"),
    svc: ANPRService = Depends(_svc),
):
    from_dt = _parse_iso(from_time, "from_time")
    to_dt = _parse_iso(to_time, "to_time")

    sightings, total = await svc.list_sightings(
        camera_id=camera_id,
        vehicle_id=vehicle_id,
        track_id=track_id,
        detection_id=detection_id,
        status=status,
        quality=quality,
        vehicle_class=vehicle_class,
        direction=direction,
        watchlist_status=watchlist_status,
        source=source,
        sector_id=sector_id,
        zone_id=zone_id,
        from_time=from_dt,
        to_time=to_dt,
        search=search,
        sort=sort,
        order=order,
        page=page,
        page_size=page_size,
    )

    return SightingPageResponse(
        sightings=[VehicleSightingResponse.from_orm(s) for s in sightings],
        has_more=False,
        next_cursor=None,
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/anpr/sightings/recent  — recent sightings across all cameras
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/sightings/recent",
    response_model=list[VehicleSightingResponse],
    summary="Recent sightings across all cameras",
)
async def get_recent_sightings(
    svc: ANPRService = Depends(_svc),
):
    sightings = await svc.sighting_repo.get_recent_for_camera("ALL", limit=100)
    return [VehicleSightingResponse.from_orm(s) for s in sightings]


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/anpr/sightings/{sighting_id}  — single sighting detail
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/sightings/{sighting_id}",
    response_model=VehicleSightingResponse,
    summary="Get sighting detail",
)
async def get_sighting(
    sighting_id: str,
    svc: ANPRService = Depends(_svc),
):
    try:
        sighting = await svc.get_sighting(sighting_id)
    except SightingNotFoundError:
        raise _anpr_error_response("SIGHTING_NOT_FOUND", f"Sighting '{sighting_id}' not found.", 404)
    return VehicleSightingResponse.from_orm(sighting)


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/anpr/sightings/{sighting_id}/candidates  — plate candidates
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/sightings/{sighting_id}/candidates",
    response_model=list,
    summary="Get plate candidates for a sighting",
)
async def get_sighting_candidates(
    sighting_id: str,
    svc: ANPRService = Depends(_svc),
):
    try:
        sighting = await svc.get_sighting(sighting_id)
    except SightingNotFoundError:
        raise _anpr_error_response("SIGHTING_NOT_FOUND", f"Sighting '{sighting_id}' not found.", 404)

    # Get candidates from plate read
    if sighting.plate_read:
        candidates = await svc.plate_read_repo.get_candidates(sighting.plate_read.plate_read_id)
        return [{"rank": c.rank, "raw_read": c.raw_read, "normalized_read": c.normalized_read,
                 "confidence": c.confidence, "format_status": c.format_status} for c in candidates]
    return []


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/anpr/vehicles/{vehicle_id}  — vehicle detail
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/vehicles/{vehicle_id}",
    response_model=VehicleSightingResponse,
    summary="Get vehicle (most recent sighting)",
)
async def get_vehicle(
    vehicle_id: str,
    svc: ANPRService = Depends(_svc),
):
    # Get most recent sighting for this vehicle
    sightings = await svc.sighting_repo.get_vehicle_history(vehicle_id, limit=1)
    if not sightings:
        raise _anpr_error_response("VEHICLE_NOT_FOUND", f"Vehicle '{vehicle_id}' not found.", 404)
    return VehicleSightingResponse.from_orm(sightings[0])


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/anpr/vehicles/{vehicle_id}/history  — vehicle history
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/vehicles/{vehicle_id}/history",
    response_model=VehicleHistoryResponse,
    summary="Get vehicle sighting history",
)
async def get_vehicle_history(
    vehicle_id: str,
    from_time: Optional[str] = Query(None),
    to_time: Optional[str] = Query(None),
    limit: int = Query(200, ge=1, le=500),
    svc: ANPRService = Depends(_svc),
):
    from_dt = _parse_iso(from_time, "from_time")
    to_dt = _parse_iso(to_time, "to_time")

    sightings = await svc.get_vehicle_history(
        vehicle_id,
        limit=limit,
        from_time=from_dt,
        to_time=to_dt,
    )
    return VehicleHistoryResponse.from_sightings(
        vehicle_id, [VehicleSightingResponse.from_orm(s) for s in sightings]
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/anpr/cameras/{camera_id}/vehicles  — sightings for one camera
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/cameras/{camera_id}/vehicles",
    response_model=list[VehicleSightingResponse],
    summary="Get sightings for a camera",
)
async def get_camera_vehicles(
    camera_id: str,
    from_time: Optional[str] = Query(None),
    to_time: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    quality: Optional[str] = Query(None),
    vehicle_class: Optional[str] = Query(None, alias="class"),
    direction: Optional[str] = Query(None),
    watchlist_status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    svc: ANPRService = Depends(_svc),
):
    from_dt = _parse_iso(from_time, "from_time")
    to_dt = _parse_iso(to_time, "to_time")

    sightings = await svc.get_camera_sightings(
        camera_id,
        from_time=from_dt,
        to_time=to_dt,
        status=status,
        quality=quality,
        vehicle_class=vehicle_class,
        direction=direction,
        watchlist_status=watchlist_status,
        limit=limit,
    )
    return [VehicleSightingResponse.from_orm(s) for s in sightings]


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/anpr/cameras/{camera_id}/vehicles/feed  — ANPRFeed
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/cameras/{camera_id}/vehicles/feed",
    response_model=dict,
    summary="Get camera ANPR feed (sightings + provider state)",
)
async def get_camera_vehicle_feed(
    camera_id: str,
    svc: ANPRService = Depends(_svc),
):
    feed_data = await svc.get_camera_feed(camera_id)
    sightings_resp = [VehicleSightingResponse.from_orm(s) for s in feed_data["sightings"]]

    return {
        "cameraId": feed_data["camera_id"],
        "state": feed_data["state"],
        "lastUpdatedAt": feed_data.get("last_updated_at"),
        "sightings": sightings_resp,
        "providerHealth": feed_data.get("provider_health"),
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/anpr/cameras/{camera_id}/vehicles/summary  — camera count summary
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/cameras/{camera_id}/vehicles/summary",
    response_model=dict,
    summary="Get camera ANPR summary (counts only)",
)
async def get_camera_vehicle_summary(
    camera_id: str,
    svc: ANPRService = Depends(_svc),
):
    summary = await svc.get_camera_summary(camera_id)
    return summary


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/anpr/search  — plate search
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/search",
    response_model=list,
    summary="Search plates",
)
async def search_plates(
    q: str = Query(..., min_length=1, max_length=64),
    camera_id: Optional[str] = Query(None),
    match_type: Optional[str] = Query(None, alias="matchType"),
    limit: int = Query(50, ge=1, le=500),
    svc: ANPRService = Depends(_svc),
):
    results = await svc.search_plates(
        q,
        camera_id=camera_id,
        match_type=match_type,
        limit=limit,
    )
    return [{"sighting": VehicleSightingResponse.from_orm(s), "matchType": "PARTIAL_MATCH"} for s in results]


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/anpr/summary  — global ANPR summary
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/summary",
    response_model=ANPRSummaryResponse,
    summary="Global ANPR summary",
)
async def get_anpr_summary(
    svc: ANPRService = Depends(_svc),
):
    return await svc.get_summary()


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/anpr/health  — provider health
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/health",
    response_model=ANPRProviderHealthResponse,
    summary="Get ANPR provider health",
)
async def get_anpr_health(
    svc: ANPRService = Depends(_svc),
):
    h = svc.get_provider_health()
    return ANPRProviderHealthResponse(
        state=h["state"],
        provider=h["provider"],
        providerVersion=h.get("provider_version"),
        trackerName=h.get("tracker_name"),
        trackerVersion=h.get("tracker_version"),
        lastSuccessfulUpdate=h.get("last_successful_update"),
        failureCount=h.get("failure_count", 0),
        queueDepth=h.get("queue_depth", 0),
        processingLatencyMs=h.get("processing_latency_ms"),
        camerasActive=h.get("cameras_active", 0),
        note=h.get("note"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/anpr/config/{camera_id}  — per-camera ANPR config
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/config/{camera_id}",
    response_model=Optional[ANPRConfigResponse],
    summary="Get ANPR configuration for a camera",
)
async def get_anpr_config(
    camera_id: str,
    svc: ANPRService = Depends(_svc),
):
    cfg = await svc.get_config(camera_id)
    if cfg is None:
        return None
    return ANPRConfigResponse.from_orm(cfg)


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/v1/internal/anpr/observe  — internal sighting ingestion
#
# Protected by X-Internal-Service header.
# Accepts vehicle sightings from C5/C6 or edge devices.
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/internal/observe",
    response_model=ANPRIngestResponse,
    summary="[INTERNAL] Ingest vehicle sightings into ANPR pipeline",
    description=(
        "Internal endpoint for Component 5/6 or edge devices to push vehicle sightings. "
        "Requires X-Internal-Service header. Not for public use."
    ),
)
async def ingest_anpr_sightings(
    body: ANPRIngestRequest,
    x_internal_service: Optional[str] = Header(None, alias="X-Internal-Service"),
    svc: ANPRService = Depends(_svc),
):
    if not x_internal_service:
        raise HTTPException(
            status_code=403,
            detail={"error": {
                "code": "FORBIDDEN",
                "message": "X-Internal-Service header required for ANPR ingestion.",
            }},
        )

    # Convert to provider inputs
    from app.domain.anpr.provider import VehicleSightingInput, PlateReadInput, PlateCandidateInput
    provider_inputs = []
    for s in body.sightings:
        plate_read = None
        if s.plate_read:
            plate_read = PlateReadInput(
                raw_read=s.plate_read.rawRead,
                normalized_read=s.plate_read.normalizedRead,
                display_read=s.plate_read.displayRead,
                confidence=s.plate_read.confidence,
                character_confidence=s.plate_read.characterConfidence,
                format_status=s.plate_read.formatStatus,
                quality=s.plate_read.quality,
                crop_reference=s.plate_read.cropReference,
                source_frame_ref=s.plate_read.sourceFrameRef,
                observed_at=datetime.fromisoformat(s.plate_read.observedAt),
                candidates=[
                    PlateCandidateInput(
                        rank=c.rank,
                        raw_read=c.rawRead,
                        normalized_read=c.normalizedRead,
                        confidence=c.confidence,
                        character_confidence=c.characterConfidence,
                        format_status=c.formatStatus,
                    ) for c in s.plate_read.candidates
                ] if s.plate_read.candidates else [],
            )

        provider_inputs.append(VehicleSightingInput(
            camera_id=s.cameraId,
            observed_at=datetime.fromisoformat(s.observedAt),
            received_at=datetime.fromisoformat(s.receivedAt) if s.receivedAt else None,
            vehicle_class=s.vehicleClass,
            vehicle_color=s.vehicleColor,
            vehicle_direction=s.vehicleDirection,
            track_id=s.trackId,
            detection_id=s.detectionId,
            vehicle_id=s.vehicleId,
            plate_read=plate_read,
            confidence=s.confidence,
            detection_quality=s.detectionQuality,
            camera_health_state=s.cameraHealthState,
            camera_health_context_json=s.cameraHealthContextJson,
            location_context=s.locationContext,
            sector_id=s.sectorId,
            zone_id=s.zoneId,
            watchlist_status=s.watchlistStatus,
            evidence_id=s.evidenceId,
            event_id=s.eventId,
            correlation_id=s.correlationId,
            incident_id=s.incidentId,
            thumbnail_url=s.thumbnailUrl,
            plate_crop_url=s.plateCropUrl,
            source_provider=s.sourceProvider,
            sync_payload_hash=s.syncPayloadHash,
            edge_device_id=s.edgeDeviceId,
        ))

    try:
        result = await svc.ingest_sightings(
            camera_id=body.cameraId,
            sightings=provider_inputs,
            source=body.source,
            sector_id=body.sectorId,
            zone_id=body.zoneId,
        )
    except ANPRProviderUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail={"error": {"code": "ANPR_UNAVAILABLE", "message": str(exc)}},
        )
    except Exception as exc:
        logger.exception("anpr_ingestion_failed camera_id=%s error=%s", body.cameraId, exc)
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "PROVIDER_ERROR", "message": "Internal ANPR error."}},
        )

    return ANPRIngestResponse(
        cameraId=body.cameraId,
        processedAt=datetime.now(timezone.utc).isoformat(),
        totalSightings=result.total_sightings,
        created=result.created,
        duplicates=result.duplicates,
        errors=result.errors,
        providerName=result.provider_name,
        providerVersion=result.provider_version,
        processingLatencyMs=result.processing_latency_ms,
    )