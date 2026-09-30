# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 7 — ANPR API Routes
#
# Public endpoints:
#   GET  /api/v1/anpr/sightings              — cursor-paginated sighting list
#   GET  /api/v1/anpr/sightings/recent       — recent sightings (all cameras)
#   GET  /api/v1/anpr/sightings/{sighting_id} — sighting detail
#   GET  /api/v1/anpr/sightings/{sighting_id}/candidates — plate candidates
#   GET  /api/v1/anpr/vehicles/{vehicle_id}   — vehicle detail (newest sighting)
#   GET  /api/v1/anpr/vehicles/{vehicle_id}/history — vehicle history
#   GET  /api/v1/anpr/cameras/{camera_id}/vehicles — sightings for one camera
#   GET  /api/v1/anpr/cameras/{camera_id}/vehicles/feed — ANPRFeed (sightings + state)
#   GET  /api/v1/anpr/cameras/{camera_id}/vehicles/summary — count summary
#   GET  /api/v1/anpr/search                  — plate search (§23) with §24 labels
#   GET  /api/v1/anpr/summary                 — global ANPR summary (§26)
#   GET  /api/v1/anpr/health                  — provider health (§28)
#   GET  /api/v1/anpr/config/{camera_id}      — ANPR config for camera
#
# Internal endpoint (service-to-service):
#   POST /api/v1/anpr/internal/observe        — ingest vehicle sightings
#
# Security: reuses existing CORS / internal header pattern.
#
# Wire format: response schemas declare camelCase FIELD names with snake_case
# aliases; every route uses response_model_by_alias=False so serialization is
# by FIELD NAME → camelCase on the wire (matches frontend types).
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.db.database import get_db_session
from app.domain.anpr.provider import (
    PlateCandidateInput,
    PlateReadInput,
    VehicleSightingInput,
)
from app.domain.anpr.service import (
    ANPRService,
    SightingNotFoundError,
    ANPRProviderUnavailableError,
)
from app.schemas.anpr import (
    ANPRConfigResponse,
    ANPRProviderHealthResponse,
    ANPRSearchResultResponse,
    ANPRSummaryResponse,
    ANPRIngestRequest,
    ANPRIngestResponse,
    PlateCandidateResponse,
    SightingPageResponse,
    VehicleHistoryResponse,
    VehicleSightingResponse,
)

logger = get_logger("prhaar.anpr.routes")

router = APIRouter(prefix="/anpr", tags=["anpr"])


# ─────────────────────────────────────────────────────────────────────────────
# Dependency helpers
# ─────────────────────────────────────────────────────────────────────────────

def _svc(session: AsyncSession = Depends(get_db_session)) -> ANPRService:
    return ANPRService(session)


def _iso_utc(dt: datetime | None) -> str | None:
    """ISO-8601 with explicit UTC offset (SQLite returns naive datetimes)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


def _parse_iso(value: str | None, field_name: str) -> datetime | None:
    """Parse an ISO-8601 query timestamp; naive values are pinned to UTC."""
    if value is None:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "INVALID_QUERY", "message": f"Invalid ISO timestamp for {field_name}: {value}"}},
        )
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _parse_body_iso(value: str, field_name: str) -> datetime:
    """Parse an ISO-8601 ingest timestamp; naive values are pinned to UTC."""
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        raise HTTPException(
            status_code=422,
            detail={"error": {"code": "INVALID_SIGHTING", "message": f"Invalid ISO timestamp for {field_name}: {value}"}},
        )
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _anpr_error_response(code: str, message: str, status: int = 400) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail={"error": {"code": code, "message": message}},
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/anpr/sightings  — cursor-paginated, filtered sighting list
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/sightings",
    response_model=SightingPageResponse,
    response_model_by_alias=False,
    summary="List sightings (cursor-paginated, filtered)",
    description=(
        "Returns a cursor-paginated, filtered list of vehicle sightings. "
        "Supports filtering by camera, vehicle, track, detection, status, quality, "
        "vehicle class, direction, source, sector, zone, time range, confidence range "
        "and text search. Cursor is only valid with sort=observed_at."
    ),
)
async def list_sightings(
    camera_id: Optional[str] = Query(None, description="Filter by camera ID"),
    vehicle_id: Optional[str] = Query(None, description="Filter by vehicle ID"),
    track_id: Optional[str] = Query(None, description="Filter by track ID"),
    detection_id: Optional[str] = Query(None, description="Filter by detection ID"),
    status: Optional[str] = Query(None, description="Filter by sighting status"),
    quality: Optional[str] = Query(None, description="Filter by plate quality"),
    vehicle_class: Optional[str] = Query(None, description="Filter by vehicle class"),
    direction: Optional[str] = Query(None, description="Filter by vehicle direction"),
    watchlist_status: Optional[str] = Query(None, description="Filter by watchlist status"),
    source: Optional[str] = Query(None, description="Filter by source"),
    sector_id: Optional[str] = Query(None, description="Filter by sector ID"),
    zone_id: Optional[str] = Query(None, description="Filter by zone ID"),
    from_time: Optional[str] = Query(None, alias="from", description="ISO 8601 start time"),
    to_time: Optional[str] = Query(None, alias="to", description="ISO 8601 end time"),
    confidence_min: Optional[float] = Query(None, ge=0.0, le=1.0, description="Minimum confidence"),
    confidence_max: Optional[float] = Query(None, ge=0.0, le=1.0, description="Maximum confidence"),
    search: Optional[str] = Query(None, max_length=128, description="Text search (plate / camera / vehicle)"),
    sort: str = Query("observed_at", pattern="^(observed_at|received_at|created_at|camera|vehicle_class|quality|confidence|direction)$"),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    cursor: Optional[str] = Query(None, max_length=256, description="Pagination cursor from nextCursor"),
    limit: int = Query(50, ge=1, le=500, description="Page size"),
    svc: ANPRService = Depends(_svc),
):
    from_dt = _parse_iso(from_time, "from")
    to_dt = _parse_iso(to_time, "to")

    try:
        rows, has_more, next_cursor = await svc.list_sightings_cursor(
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
            confidence_min=confidence_min,
            confidence_max=confidence_max,
            search=search,
            sort=sort,
            order=order,
            cursor=cursor,
            limit=limit,
        )
    except ValueError as exc:
        raise _anpr_error_response("INVALID_CURSOR", str(exc), 422)

    return SightingPageResponse(
        sightings=[VehicleSightingResponse.from_orm(s) for s in rows],
        has_more=has_more,
        next_cursor=next_cursor,
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/anpr/sightings/recent  — recent sightings across all cameras
# NOTE: must be declared BEFORE /sightings/{sighting_id} (route ordering).
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/sightings/recent",
    response_model=list[VehicleSightingResponse],
    response_model_by_alias=False,
    summary="Recent sightings across all cameras",
)
async def get_recent_sightings(
    limit: int = Query(100, ge=1, le=500),
    svc: ANPRService = Depends(_svc),
):
    sightings = await svc.get_recent_sightings(limit=limit)
    return [VehicleSightingResponse.from_orm(s) for s in sightings]


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/anpr/sightings/{sighting_id}  — single sighting detail
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/sightings/{sighting_id}",
    response_model=VehicleSightingResponse,
    response_model_by_alias=False,
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
    response_model=list[PlateCandidateResponse],
    response_model_by_alias=False,
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

    plate_read = getattr(sighting, "plate_read", None)
    if plate_read is None:
        return []
    candidates = await svc.plate_read_repo.get_candidates(plate_read.plate_read_id)
    return [PlateCandidateResponse.from_orm(c) for c in candidates]


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/anpr/vehicles/{vehicle_id}  — vehicle detail (newest sighting)
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/vehicles/{vehicle_id}",
    response_model=VehicleSightingResponse,
    response_model_by_alias=False,
    summary="Get vehicle (most recent sighting)",
)
async def get_vehicle(
    vehicle_id: str,
    svc: ANPRService = Depends(_svc),
):
    rows, _ = await svc.list_sightings(
        vehicle_id=vehicle_id,
        sort="observed_at",
        order="desc",
        page=1,
        page_size=1,
    )
    if not rows:
        raise _anpr_error_response("VEHICLE_NOT_FOUND", f"Vehicle '{vehicle_id}' not found.", 404)
    return VehicleSightingResponse.from_orm(rows[0])


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/anpr/vehicles/{vehicle_id}/history  — vehicle history
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/vehicles/{vehicle_id}/history",
    response_model=VehicleHistoryResponse,
    response_model_by_alias=False,
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
    response_model_by_alias=False,
    summary="Get sightings for a camera",
)
async def get_camera_vehicles(
    camera_id: str,
    from_time: Optional[str] = Query(None),
    to_time: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    quality: Optional[str] = Query(None),
    vehicle_class: Optional[str] = Query(None),
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
    response_model_by_alias=False,
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
    response_model_by_alias=False,
    summary="Get camera ANPR summary (counts only)",
)
async def get_camera_vehicle_summary(
    camera_id: str,
    svc: ANPRService = Depends(_svc),
):
    summary = await svc.get_camera_summary(camera_id)
    return summary


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/anpr/search  — plate search (spec §23, five §24 labels)
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/search",
    response_model=list[ANPRSearchResultResponse],
    response_model_by_alias=False,
    summary="Search plates",
    description=(
        "Plate search across normalized reads, raw reads and candidate text. "
        "Results are labeled EXACT_NORMALIZED_MATCH | RAW_READ_MATCH | "
        "PARTIAL_MATCH | CANDIDATE_MATCH | RELATED_SIGHTING. Partial matches "
        "are never reported as exact identity."
    ),
)
async def search_plates(
    q: str = Query(..., min_length=1, max_length=64),
    camera_id: Optional[str] = Query(None),
    match_type: Optional[str] = Query(None, description="Filter to one §24 label"),
    limit: int = Query(50, ge=1, le=500),
    svc: ANPRService = Depends(_svc),
):
    results = await svc.search_plates(
        q,
        camera_id=camera_id,
        match_type=match_type,
        limit=limit,
    )
    return [
        ANPRSearchResultResponse(
            sighting=VehicleSightingResponse.from_orm(sighting),
            match_type=label,
        )
        for sighting, label in results
    ]


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/anpr/summary  — global ANPR summary (spec §26)
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/summary",
    response_model=ANPRSummaryResponse,
    response_model_by_alias=False,
    summary="Global ANPR summary",
    description=(
        "Counts of plate observations (total / readable / partial / unreadable), "
        "unique track-linked sightings and cameras with ANPR data. Counts only — "
        "this platform does not compute OCR accuracy metrics."
    ),
)
async def get_anpr_summary(
    svc: ANPRService = Depends(_svc),
):
    return ANPRSummaryResponse(**await svc.get_summary())


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/anpr/health  — provider health (spec §28)
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/health",
    response_model=ANPRProviderHealthResponse,
    response_model_by_alias=False,
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
    response_model_by_alias=False,
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
# POST /api/v1/anpr/internal/observe  — internal sighting ingestion
#
# Protected by X-Internal-Service header.
# Accepts vehicle sightings from C5/C6 or edge devices.
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/internal/observe",
    response_model=ANPRIngestResponse,
    response_model_by_alias=False,
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
        raise _anpr_error_response(
            "FORBIDDEN",
            "X-Internal-Service header required for ANPR ingestion.",
            403,
        )

    # Convert to provider inputs. Caller-supplied sighting ID precedence:
    # sighting-level > plateRead-level > provider-fabricated.
    provider_inputs: list[VehicleSightingInput] = []
    for s in body.sightings:
        plate_read = None
        if s.plateRead:
            plate_read = PlateReadInput(
                raw_read=s.plateRead.rawRead,
                normalized_read=s.plateRead.normalizedRead,
                display_read=s.plateRead.displayRead,
                confidence=s.plateRead.confidence,
                character_confidence=s.plateRead.characterConfidence,
                format_status=s.plateRead.formatStatus,
                quality=s.plateRead.quality,
                crop_reference=s.plateRead.cropReference,
                source_frame_ref=s.plateRead.sourceFrameRef,
                observed_at=_parse_body_iso(s.plateRead.observedAt, "plateRead.observed_at"),
                candidates=[
                    PlateCandidateInput(
                        rank=c.rank,
                        raw_read=c.rawRead,
                        normalized_read=c.normalizedRead,
                        confidence=c.confidence,
                        character_confidence=c.characterConfidence,
                        format_status=c.formatStatus,
                    ) for c in s.plateRead.candidates
                ] if s.plateRead.candidates else [],
            )

        provider_inputs.append(VehicleSightingInput(
            sighting_id=s.sightingId or (s.plateRead.sightingId if s.plateRead else None),
            camera_id=s.cameraId,
            observed_at=_parse_body_iso(s.observedAt, "observed_at"),
            received_at=_parse_body_iso(s.receivedAt, "received_at") if s.receivedAt else None,
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
        raise _anpr_error_response("ANPR_UNAVAILABLE", str(exc), 503)
    except Exception as exc:
        logger.exception("anpr_ingest_failed camera_id=%s", body.cameraId)
        raise _anpr_error_response("PROVIDER_ERROR", f"ANPR ingestion failed: {exc}", 500)

    return ANPRIngestResponse(
        camera_id=result.camera_id,
        processed_at=_iso_utc(result.processed_at) or "",
        total_sightings=result.total_sightings,
        created=result.created,
        duplicates=result.duplicates,
        errors=result.errors,
        provider_name=result.provider_name,
        provider_version=result.provider_version,
        processing_latency_ms=result.processing_latency_ms,
    )
