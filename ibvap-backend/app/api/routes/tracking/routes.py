# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 6 — Tracking Engine API Routes
#
# Public endpoints:
#   GET  /api/v1/tracks                              — paginated track list
#   GET  /api/v1/tracks/recent                       — recent active tracks (all cameras)
#   GET  /api/v1/tracks/{track_id}                   — track detail
#   GET  /api/v1/tracks/{track_id}/observations      — observation history (paged)
#   GET  /api/v1/tracks/{track_id}/history           — lifecycle state history (paged)
#   GET  /api/v1/tracks/{track_id}/candidates        — cross-camera candidates
#   GET  /api/v1/cameras/{camera_id}/tracks          — tracks for one camera
#   GET  /api/v1/cameras/{camera_id}/tracks/feed     — TrackingFeed (active tracks + state)
#   GET  /api/v1/cameras/{camera_id}/tracks/summary  — count summary
#   GET  /api/v1/tracking/health                     — provider health
#   GET  /api/v1/tracking/config/{camera_id}         — tracking config for camera
#
# Internal endpoint (service-to-service, not public):
#   POST /api/v1/internal/tracking/update            — ingest detection batch
#
# Security: reuses existing CORS / no-auth pattern (consistent with rest of PRHAAR).
# Internal endpoint returns 403 if X-Internal-Service header is missing.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import IBVAPError, IBVAPErrorCode
from app.core.logging import get_logger
from app.db.database import get_db_session
from app.domain.tracking.provider import DetectionInput
from app.domain.tracking.service import (
    ProviderUnavailableError,
    TrackingService,
    TrackNotFoundError,
)
from app.schemas.tracking import (
    TrackCandidateResponse,
    TrackHistoryPageResponse,
    TrackHistoryEntryResponse,
    TrackingIngestRequest,
    TrackingIngestResponse,
    TrackingProviderHealthResponse,
    TrackObservationPageResponse,
    TrackObservationResponse,
    TrackResponse,
    TrackResultPageResponse,
    TrackSummaryResponse,
    TrackingFeedResponse,
    TrackingConfigResponse,
)

logger = get_logger("prhaar.tracking.routes")

router = APIRouter(tags=["tracking"])


# ─────────────────────────────────────────────────────────────────────────────
# Dependency helpers
# ─────────────────────────────────────────────────────────────────────────────

def _svc(session: AsyncSession = Depends(get_db_session)) -> TrackingService:
    return TrackingService(session)


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


def _tracking_error_response(code: str, message: str, status: int = 400):
    return HTTPException(
        status_code=status,
        detail={"error": {"code": code, "message": message}},
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/tracks  — paginated, filtered track list
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/tracks",
    response_model=TrackResultPageResponse,
    summary="List tracks (paginated, filtered)",
    description=(
        "Returns a paginated, filtered list of tracks. "
        "Supports filtering by camera, status, class, source, sector, region, time range, and text search."
    ),
)
async def list_tracks(
    camera_id: Optional[str] = Query(None, description="Filter by camera ID"),
    status: Optional[str] = Query(None, description="Filter by TrackStatus"),
    object_class: Optional[str] = Query(None, alias="class", description="Filter by object class"),
    source: Optional[str] = Query(None, description="Filter by source"),
    sector_id: Optional[str] = Query(None),
    region_profile: Optional[str] = Query(None),
    from_time: Optional[str] = Query(None, description="ISO 8601 start time"),
    to_time: Optional[str] = Query(None, description="ISO 8601 end time"),
    search: Optional[str] = Query(None, max_length=128),
    sort: str = Query("last_seen", regex="^(last_seen|first_seen|observations|camera|longest)$"),
    order: str = Query("desc", regex="^(asc|desc)$"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=200, alias="pageSize"),
    svc: TrackingService = Depends(_svc),
):
    from_dt = _parse_iso(from_time, "from_time")
    to_dt = _parse_iso(to_time, "to_time")

    tracks, total = await svc.list_tracks(
        camera_id=camera_id,
        status=status,
        object_class=object_class,
        source=source,
        sector_id=sector_id,
        region_profile=region_profile,
        from_time=from_dt,
        to_time=to_dt,
        search=search,
        sort=sort,
        order=order,
        page=page,
        page_size=page_size,
    )

    return TrackResultPageResponse(
        tracks=[TrackResponse.from_orm(t) for t in tracks],
        total=total,
        page=page,
        pageSize=page_size,
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/tracks/recent  — all active tracks (dashboard / sector overview)
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/tracks/recent",
    response_model=list[TrackResponse],
    summary="All active tracks across all cameras",
)
async def get_all_active_tracks(
    svc: TrackingService = Depends(_svc),
):
    tracks = await svc.get_all_active_tracks()
    return [TrackResponse.from_orm(t) for t in tracks]


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/tracks/{track_id}  — single track detail
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/tracks/{track_id}",
    response_model=TrackResponse,
    summary="Get track detail",
)
async def get_track(
    track_id: str,
    include_trajectory: bool = Query(False, alias="includeTrajectory"),
    max_trajectory_points: int = Query(50, ge=1, le=500, alias="maxTrajectoryPoints"),
    svc: TrackingService = Depends(_svc),
):
    try:
        track = await svc.get_track(track_id)
    except TrackNotFoundError:
        raise _tracking_error_response("TRACK_NOT_FOUND", f"Track '{track_id}' not found.", 404)

    trajectory = None
    if include_trajectory:
        trajectory = await svc.get_trajectory(track_id, max_points=max_trajectory_points)

    return TrackResponse.from_orm(track, trajectory=trajectory)


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/tracks/{track_id}/observations  — observation history
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/tracks/{track_id}/observations",
    response_model=TrackObservationPageResponse,
    summary="Get track observation history (paged)",
)
async def get_track_observations(
    track_id: str,
    from_time: Optional[str] = Query(None),
    to_time: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=500, alias="pageSize"),
    svc: TrackingService = Depends(_svc),
):
    try:
        from_dt = _parse_iso(from_time, "from_time")
        to_dt = _parse_iso(to_time, "to_time")
        observations, total = await svc.get_track_observations(
            track_id,
            from_time=from_dt,
            to_time=to_dt,
            page=page,
            page_size=page_size,
        )
    except TrackNotFoundError:
        raise _tracking_error_response("TRACK_NOT_FOUND", f"Track '{track_id}' not found.", 404)

    return TrackObservationPageResponse(
        observations=[TrackObservationResponse.from_orm(o) for o in observations],
        total=total,
        page=page,
        pageSize=page_size,
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/tracks/{track_id}/history  — lifecycle state history
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/tracks/{track_id}/history",
    response_model=TrackHistoryPageResponse,
    summary="Get track lifecycle history (paged)",
)
async def get_track_history(
    track_id: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200, alias="pageSize"),
    svc: TrackingService = Depends(_svc),
):
    try:
        history, total = await svc.get_track_history(
            track_id, page=page, page_size=page_size
        )
    except TrackNotFoundError:
        raise _tracking_error_response("TRACK_NOT_FOUND", f"Track '{track_id}' not found.", 404)

    return TrackHistoryPageResponse(
        history=[TrackHistoryEntryResponse.from_orm(h) for h in history],
        total=total,
        page=page,
        pageSize=page_size,
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/tracks/{track_id}/candidates  — cross-camera continuation candidates
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/tracks/{track_id}/candidates",
    response_model=list[TrackCandidateResponse],
    summary="Get cross-camera continuation candidates",
    description=(
        "Returns POSSIBLE_CONTINUATION / POSSIBLE_SAME_ENTITY hypotheses only. "
        "Never implies confirmed identity."
    ),
)
async def get_track_candidates(
    track_id: str,
    svc: TrackingService = Depends(_svc),
):
    try:
        candidates = await svc.get_track_candidates(track_id)
    except TrackNotFoundError:
        raise _tracking_error_response("TRACK_NOT_FOUND", f"Track '{track_id}' not found.", 404)
    return [TrackCandidateResponse.from_orm(c) for c in candidates]


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/cameras/{camera_id}/tracks  — tracks for one camera
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/cameras/{camera_id}/tracks",
    response_model=list[TrackResponse],
    summary="Get active tracks for a camera",
)
async def get_camera_tracks(
    camera_id: str,
    svc: TrackingService = Depends(_svc),
):
    tracks = await svc.get_active_tracks(camera_id)
    return [TrackResponse.from_orm(t) for t in tracks]


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/cameras/{camera_id}/tracks/feed  — TrackingFeed
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/cameras/{camera_id}/tracks/feed",
    response_model=TrackingFeedResponse,
    summary="Get camera tracking feed (tracks + provider state)",
)
async def get_camera_track_feed(
    camera_id: str,
    svc: TrackingService = Depends(_svc),
):
    feed_data = await svc.get_track_feed(camera_id)
    tracks_resp = [TrackResponse.from_orm(t) for t in feed_data["tracks"]]

    return TrackingFeedResponse(
        cameraId=feed_data["camera_id"],
        state=feed_data["state"],
        lastUpdatedAt=feed_data.get("last_updated_at"),
        tracks=tracks_resp,
        providerHealth=feed_data.get("provider_health"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/cameras/{camera_id}/tracks/summary  — camera count summary
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/cameras/{camera_id}/tracks/summary",
    response_model=TrackSummaryResponse,
    summary="Get camera track summary (counts only, no threat scores)",
)
async def get_camera_track_summary(
    camera_id: str,
    svc: TrackingService = Depends(_svc),
):
    summary = await svc.get_camera_summary(camera_id)
    return TrackSummaryResponse(
        cameraId=summary["camera_id"],
        totalActive=summary["total_active"],
        totalTracks=summary["total_tracks"],
        byClass=summary["by_class"],
        byStatus=summary["by_status"],
        lastUpdatedAt=summary.get("last_updated_at"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /api/v1/tracking/health  — provider health
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/tracking/health",
    response_model=TrackingProviderHealthResponse,
    summary="Get tracking provider health",
)
async def get_tracking_health(
    svc: TrackingService = Depends(_svc),
):
    h = svc.get_provider_health()
    return TrackingProviderHealthResponse(
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
# GET /api/v1/tracking/config/{camera_id}  — per-camera tracking config
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/tracking/config/{camera_id}",
    response_model=Optional[TrackingConfigResponse],
    summary="Get tracking configuration for a camera",
)
async def get_tracking_config(
    camera_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    from sqlalchemy import select
    from app.models.tracking import TrackingConfig

    result = await session.execute(
        select(TrackingConfig)
        .where(TrackingConfig.camera_id == camera_id, TrackingConfig.active == True)  # noqa: E712
        .order_by(TrackingConfig.updated_at.desc())
        .limit(1)
    )
    cfg = result.scalar_one_or_none()
    if cfg is None:
        return None
    return TrackingConfigResponse.from_orm(cfg)


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/v1/internal/tracking/update  — internal detection batch ingestion
#
# Protected by X-Internal-Service header (existing internal auth pattern).
# Not intended for public or frontend use.
# Accepts DetectionInput list, runs through provider → track pipeline.
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/internal/tracking/update",
    response_model=TrackingIngestResponse,
    summary="[INTERNAL] Ingest detection batch into tracking pipeline",
    description=(
        "Internal endpoint for Component 5 or edge devices to push detections. "
        "Requires X-Internal-Service header. Not for public use."
    ),
)
async def ingest_tracking_update(
    body: TrackingIngestRequest,
    x_internal_service: Optional[str] = Header(None, alias="X-Internal-Service"),
    svc: TrackingService = Depends(_svc),
):
    # Minimal internal auth — header presence check
    # (Full RBAC will replace this when auth layer is added)
    if not x_internal_service:
        raise HTTPException(
            status_code=403,
            detail={"error": {
                "code": "FORBIDDEN",
                "message": "X-Internal-Service header required for tracking ingestion.",
            }},
        )

    # Convert request items to DetectionInput
    detection_inputs: list[DetectionInput] = []
    for item in body.detections:
        try:
            observed_at = datetime.fromisoformat(item.observedAt)
            if observed_at.tzinfo is None:
                observed_at = observed_at.replace(tzinfo=timezone.utc)
        except ValueError:
            logger.warning("invalid_timestamp detection_id=%s ts=%s", item.detectionId, item.observedAt)
            continue

        detection_inputs.append(DetectionInput(
            detection_id=item.detectionId,
            camera_id=item.cameraId,
            observed_at=observed_at,
            bbox_x=item.bboxX,
            bbox_y=item.bboxY,
            bbox_width=item.bboxWidth,
            bbox_height=item.bboxHeight,
            object_class=item.objectClass,
            confidence=item.confidence,
            quality=item.quality,
            occlusion=item.occlusion,
            source=item.source,
            frame_id=item.frameId,
            frame_number=item.frameNumber,
            region_profile=item.regionProfile,
            sector_id=item.sectorId,
            camera_health_state=item.cameraHealthState,
            camera_health_reliability=item.cameraHealthReliability,
            camera_viewpoint_shift=item.cameraViewpointShift,
        ))

    if not detection_inputs:
        return TrackingIngestResponse(
            cameraId=body.cameraId,
            processedAt=datetime.now(timezone.utc).isoformat(),
            totalDetections=0,
            matched=0,
            newTracks=0,
            unmatched=0,
            rejected=len(body.detections),
            duplicateRejected=0,
            errors=0,
        )

    try:
        result = await svc.ingest_detections(
            camera_id=body.cameraId,
            detections=detection_inputs,
            source=body.source,
            sector_id=body.sectorId,
            region_profile=body.regionProfile,
        )
    except ProviderUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail={"error": {"code": "TRACKING_UNAVAILABLE", "message": str(exc)}},
        )
    except Exception as exc:
        logger.exception("tracking_update_failed camera_id=%s error=%s", body.cameraId, exc)
        raise HTTPException(
            status_code=500,
            detail={"error": {"code": "PROVIDER_ERROR", "message": "Internal tracking error."}},
        )

    return TrackingIngestResponse(
        cameraId=result.camera_id,
        processedAt=result.processed_at.isoformat(),
        totalDetections=result.total_detections,
        matched=result.matched,
        newTracks=result.new_tracks,
        unmatched=result.unmatched,
        rejected=result.rejected,
        duplicateRejected=result.duplicate_rejected,
        errors=result.errors,
        providerName=result.provider_name,
        providerVersion=result.provider_version,
        processingLatencyMs=result.processing_latency_ms,
    )
