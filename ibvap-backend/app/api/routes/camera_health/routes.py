# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — Camera Health API Routes
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import IBVAPError
from app.db.database import get_db_session
from app.domain.camera_health.analyzer import camera_health_analyzer
from app.domain.camera_health.provider import get_camera_health_provider, set_camera_health_provider
from app.repositories.camera_health import (
    CameraHealthConfigRepository,
    CameraHealthCurrentRepository,
    CameraHealthEventRepository,
    CameraHealthObservationRepository,
)
from app.schemas.camera_health import (
    CameraHealthConfigCreate,
    CameraHealthConfigResponse,
    CameraHealthConfigUpdate,
    CameraHealthResponse,
    CameraHealthSummary,
    HealthHistoryRequest,
    HealthHistoryResponse,
    HealthIssueResponse,
    HealthObservationIngest,
    HealthObservationIngestResponse,
)

router = APIRouter(prefix="/cameras", tags=["camera-health"])


def _to_response(current: Any, config: Any, events: list[Any]) -> CameraHealthResponse:
    """Convert current state + config + events to API response."""
    # Build trends
    trends = []
    if current.trends_json:
        for metric, data in current.trends_json.items():
            trends.append({
                "metric": data.get("metric", metric),
                "label": data.get("label", metric.capitalize()),
                "direction": data.get("direction", "UNKNOWN"),
                "deltaPercent": data.get("deltaPercent"),
                "window": data.get("window"),
                "persistence": data.get("persistence"),
                "series": data.get("series", []),
            })

    # Build issues
    issues = []
    if current.issues_json:
        for idx, issue in enumerate(current.issues_json.get("issues", [])):
            issues.append({
                "issueId": issue.get("title", f"ISS-{current.camera_id}-{idx}").replace(" ", "-").upper(),
                "title": issue.get("title", "Unknown issue"),
                "impact": issue.get("impact", "MEDIUM"),
                "firstSeen": issue.get("firstSeen"),
                "lastSeen": issue.get("lastSeen"),
                "count": issue.get("count", 1),
                "durationLabel": issue.get("durationLabel"),
                "impactNote": issue.get("impactNote"),
                "affectedModules": issue.get("affectedModules", []),
            })

    # Determine data source
    source = current.data_source or "LIVE"
    if source == "LIVE":
        # Check if data is actually stale
        if current.last_updated:
            age = (datetime.now() - current.last_updated).total_seconds()
            if age > 60:
                source = "LAST_KNOWN"

    return CameraHealthResponse(
        cameraId=current.camera_id,
        status=current.overall_status,
        statusReason=current.status_reason,
        lastUpdated=current.last_updated.isoformat() if current.last_updated else None,
        source=source,
        regionProfile={
            "configured": True,
            "region": config.region_profile if config else None,
            "terrain": config.terrain_profile if config else None,
            "location": None,
        },
        stream={
            "state": current.stream_state,
            "fps": current.fps,
            "expectedFps": current.expected_fps,
            "frameDropPercent": current.frame_drop_percent,
            "staleSeconds": current.stale_seconds,
            "reconnectCount": current.reconnect_count,
        },
        image={
            "status": current.image_status,
            "metrics": [
                {
                    "metric": "sharpness",
                    "label": "Sharpness",
                    "value": current.sharpness_value,
                    "unit": "ratio",
                    "status": current.sharpness_status,
                    "reason": current.sharpness_reason,
                },
                {
                    "metric": "brightness",
                    "label": "Brightness",
                    "value": current.brightness_value,
                    "unit": "ratio",
                    "status": current.brightness_status,
                    "reason": current.brightness_reason,
                },
                {
                    "metric": "exposure",
                    "label": "Exposure",
                    "value": current.exposure_status,
                    "unit": None,
                    "status": current.exposure_status,
                    "reason": None,
                },
                {
                    "metric": "noise",
                    "label": "Noise",
                    "value": None,
                    "unit": None,
                    "status": current.noise_status,
                    "reason": None,
                },
            ],
            "backgroundStability": current.background_stability,
        },
        network={
            "status": current.network_status,
            "latencyMs": current.latency_ms,
            "latencyVarianceMs": current.latency_variance_ms,
            "packetLossPercent": current.packet_loss_percent,
            "heartbeatAgeSec": current.heartbeat_age_sec,
        },
        viewpoint={
            "status": current.viewpoint_status,
            "shiftScore": current.shift_score,
            "detectedAt": current.shift_detected_at.isoformat() if current.shift_detected_at else None,
            "shiftDetected": current.shift_detected,
            "fenceConfidenceNote": current.fence_confidence_note,
        },
        trends=trends,
        issues=issues,
        operationalImpact={
            "level": current.impact_level,
            "coverage": current.coverage,
            "affectedModules": current.affected_modules or [],
            "message": current.impact_message,
        },
        maintenance={
            "recommended": current.maintenance_recommended,
            "reason": current.maintenance_reason,
            "durationLabel": current.maintenance_duration,
            "impactNote": current.maintenance_impact_note,
        } if current.maintenance_recommended else None,
        lastKnown={
            "status": current.last_known_status,
            "at": current.last_known_at.isoformat() if current.last_known_at else None,
        } if current.last_known_status else None,
    )


@router.get("/{camera_id}/health", response_model=CameraHealthResponse)
async def get_camera_health(
    camera_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get current health for a single camera.
    
    Returns the complete CameraHealthResponse matching the frontend contract.
    """
    config_repo = CameraHealthConfigRepository(session)
    current_repo = CameraHealthCurrentRepository(session)
    event_repo = CameraHealthEventRepository(session)

    config = await config_repo.get(camera_id)
    current = await current_repo.get(camera_id)

    if not current:
        # Check if camera config exists
        if not config:
            raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")
        # Config exists but no health data yet
        # Return a default UNKNOWN response
        from app.schemas.camera_health import CameraHealthResponse, RegionProfile, StreamHealth, ImageHealth, NetworkHealth, ViewpointHealth, OperationalImpact
        return CameraHealthResponse(
            cameraId=camera_id,
            status="UNKNOWN",
            statusReason="Health telemetry unavailable for this camera.",
            lastUpdated=None,
            source="UNAVAILABLE",
            regionProfile=RegionProfile(
                configured=bool(config),
                region=config.region_profile if config else None,
                terrain=config.terrain_profile if config else None,
                location=None,
            ),
            stream=StreamHealth(state="UNKNOWN", fps=None, expectedFps=config.expected_fps if config else None, frameDropPercent=None, staleSeconds=None, reconnectCount=None),
            image=ImageHealth(status="UNKNOWN", metrics=[], backgroundStability=None),
            network=NetworkHealth(status="UNKNOWN", latencyMs=None, latencyVarianceMs=None, packetLossPercent=None, heartbeatAgeSec=None),
            viewpoint=ViewpointHealth(status="UNKNOWN", shiftScore=None, detectedAt=None, shiftDetected=False, fenceConfidenceNote=None),
            trends=[],
            issues=[],
            operationalImpact=OperationalImpact(level="UNKNOWN", coverage="UNKNOWN", affectedModules=[], message="Health telemetry unavailable. State cannot be established."),
            maintenance=None,
            lastKnown=None,
        )

    events = await event_repo.get_active_for_camera(camera_id)

    return _to_response(current, config, events)


@router.get("/health", response_model=list[CameraHealthSummary])
async def list_camera_health(
    ids: str | None = Query(default=None, description="Comma-separated camera IDs"),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get compact health summaries for multiple cameras.
    
    Used by Dashboard mini-panel and Camera Wall.
    """
    config_repo = CameraHealthConfigRepository(session)
    current_repo = CameraHealthCurrentRepository(session)

    if ids:
        camera_ids = [cid.strip() for cid in ids.split(",")]
        configs = {}
        for cid in camera_ids:
            config = await config_repo.get(cid)
            if config:
                configs[cid] = config
    else:
        configs_list = await config_repo.list_active()
        configs = {c.camera_id: c for c in configs_list}

    currents = await current_repo.list_all()
    currents_map = {c.camera_id: c for c in currents}

    results = []
    for camera_id, config in configs.items():
        current = currents_map.get(camera_id)
        if not current:
            # No health data yet
            results.append(CameraHealthSummary(
                cameraId=camera_id,
                status="UNKNOWN",
                statusReason="Health telemetry unavailable",
                lastUpdated=None,
                source="UNAVAILABLE",
                regionProfile={
                    "configured": True,
                    "region": config.region_profile,
                    "terrain": config.terrain_profile,
                    "location": None,
                },
                stream={"state": "UNKNOWN", "fps": None, "expectedFps": config.expected_fps, "frameDropPercent": None, "staleSeconds": None, "reconnectCount": None},
                image={"status": "UNKNOWN", "metrics": [], "backgroundStability": None},
                network={"status": "UNKNOWN", "latencyMs": None, "latencyVarianceMs": None, "packetLossPercent": None, "heartbeatAgeSec": None},
                viewpoint={"status": "UNKNOWN", "shiftScore": None, "detectedAt": None, "shiftDetected": False, "fenceConfidenceNote": None},
                operationalImpact={"level": "UNKNOWN", "coverage": "UNKNOWN", "affectedModules": [], "message": "Health telemetry unavailable"},
                lastKnown=None,
            ))
            continue

        # Build compact summary
        source = current.data_source or "LIVE"
        if source == "LIVE" and current.last_updated:
            age = (datetime.now() - current.last_updated).total_seconds()
            if age > 60:
                source = "LAST_KNOWN"

        results.append(CameraHealthSummary(
            cameraId=current.camera_id,
            status=current.overall_status,
            statusReason=current.status_reason,
            lastUpdated=current.last_updated.isoformat() if current.last_updated else None,
            source=source,
            regionProfile={
                "configured": True,
                "region": config.region_profile,
                "terrain": config.terrain_profile,
                "location": None,
            },
            stream={
                "state": current.stream_state,
                "fps": current.fps,
                "expectedFps": current.expected_fps,
                "frameDropPercent": current.frame_drop_percent,
                "staleSeconds": current.stale_seconds,
                "reconnectCount": current.reconnect_count,
            },
            image={
                "status": current.image_status,
                "metrics": [
                    {"metric": "sharpness", "label": "Sharpness", "value": current.sharpness_value, "unit": "ratio", "status": current.sharpness_status, "reason": current.sharpness_reason},
                ],
                "backgroundStability": current.background_stability,
            },
            network={
                "status": current.network_status,
                "latencyMs": current.latency_ms,
                "latencyVarianceMs": current.latency_variance_ms,
                "packetLossPercent": current.packet_loss_percent,
                "heartbeatAgeSec": current.heartbeat_age_sec,
            },
            viewpoint={
                "status": current.viewpoint_status,
                "shiftScore": current.shift_score,
                "detectedAt": current.shift_detected_at.isoformat() if current.shift_detected_at else None,
                "shiftDetected": current.shift_detected,
                "fenceConfidenceNote": current.fence_confidence_note,
            },
            operationalImpact={
                "level": current.impact_level,
                "coverage": current.coverage,
                "affectedModules": current.affected_modules or [],
                "message": current.impact_message,
            },
            lastKnown={
                "status": current.last_known_status,
                "at": current.last_known_at.isoformat() if current.last_known_at else None,
            } if current.last_known_status else None,
        ))

    return results


@router.get("/{camera_id}/health/history", response_model=HealthHistoryResponse)
async def get_camera_health_history(
    camera_id: str,
    from_ts: datetime | None = Query(default=None, alias="from"),
    to_ts: datetime | None = Query(default=None, alias="to"),
    metrics: str | None = Query(default=None, description="Comma-separated metrics"),
    resolution: str = Query(default="5m", regex="^(1m|5m|15m|1h|6h|1d)$"),
    limit: int = Query(default=1000, ge=1, le=10000),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get historical health telemetry for a camera.
    
    Supports time range, metric selection, and resolution.
    """
    config_repo = CameraHealthConfigRepository(session)
    obs_repo = CameraHealthObservationRepository(session)

    config = await config_repo.get(camera_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")

    # Default to last 24 hours
    to_dt = to_ts or datetime.now()
    from_dt = from_ts or (to_dt - timedelta(hours=24))

    # Enforce maximum window (e.g., 30 days)
    max_window = timedelta(days=settings.ENV == "development" and 1 or 30)
    if to_dt - from_dt > max_window:
        raise HTTPException(status_code=400, detail=f"Time window exceeds maximum of {max_window.days} days")

    metric_list = metrics.split(",") if metrics else None

    # Resolution to seconds
    resolution_map = {
        "1m": 60, "5m": 300, "15m": 900, "1h": 3600, "6h": 21600, "1d": 86400
    }
    bucket_seconds = resolution_map.get(resolution, 300)

    obs = await obs_repo.get_aggregated(camera_id, from_dt, to_dt, bucket_seconds, metric_list)
    obs = obs[:limit]

    points = []
    for bucket in obs:
        points.append({
            "timestamp": bucket["timestamp"].isoformat() if isinstance(bucket["timestamp"], datetime) else bucket["timestamp"],
            "metrics": {k: v for k, v in bucket.items() if k != "timestamp"},
        })

    return HealthHistoryResponse(
        cameraId=camera_id,
        resolution=resolution,
        points=points,
    )


@router.get("/{camera_id}/health/issues", response_model=HealthIssueResponse)
async def get_camera_health_issues(
    camera_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get active/recent health issues for a camera.
    """
    config_repo = CameraHealthConfigRepository(session)
    event_repo = CameraHealthEventRepository(session)

    config = await config_repo.get(camera_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Camera {camera_id} not found")

    events = await event_repo.get_active_for_camera(camera_id)
    recent = await event_repo.get_recent_for_camera(camera_id, limit=50)

    all_events = {e.event_id: e for e in events}
    for e in recent:
        all_events[e.event_id] = e

    issues = []
    for event in sorted(all_events.values(), key=lambda e: e.first_seen, reverse=True):
        issues.append({
            "issueId": event.event_id,
            "title": event.event_type.replace("_", " ").title(),
            "impact": event.severity,
            "firstSeen": event.first_seen.isoformat() if event.first_seen else None,
            "lastSeen": event.last_seen.isoformat() if event.last_seen else None,
            "count": event.occurrence_count,
            "durationLabel": (
                f"{(event.last_seen - event.first_seen).total_seconds():.0f}s"
                if event.last_seen and event.first_seen else None
            ),
            "impactNote": event.operational_impact,
            "affectedModules": [event.event_type.replace("_", " ").title()],
        })

    return HealthIssueResponse(cameraId=camera_id, issues=issues)


# ── Internal Ingestion Endpoint ────────────────────────────────────────────

@router.post("/{camera_id}/health/observations", response_model=HealthObservationIngestResponse)
async def ingest_health_observation(
    camera_id: str,
    observation: HealthObservationIngest,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Internal endpoint for edge/video adapters to ingest health telemetry.
    
    This is NOT a user-facing endpoint. It is called by the Edge/Ingestion component.
    """
    config_repo = CameraHealthConfigRepository(session)
    current_repo = CameraHealthCurrentRepository(session)
    obs_repo = CameraHealthObservationRepository(session)

    config = await config_repo.get(camera_id)
    if not config:
        # Auto-create config for unknown cameras (development mode)
        if settings.ENV == "development":
            config = await config_repo.get_or_create(camera_id)
        else:
            raise HTTPException(status_code=404, detail=f"Camera {camera_id} not configured")

    # Convert observation to internal format
    now = datetime.now()
    received_at = observation.receivedTimestamp or now

    # Build stream metrics
    stream = None
    if observation.stream:
        stream = {
            "connected": observation.stream.streamConnected,
            "observed_fps": observation.stream.observedFps,
            "expected_fps": observation.stream.expectedFps,
            "frame_drop_rate": observation.stream.frameDropRate,
            "frame_age_ms": observation.stream.frameAgeMs,
            "reconnect_count": observation.stream.reconnectCount,
        }

    # Build image metrics
    image = None
    if observation.image:
        image = {
            "sharpness": observation.image.sharpness,
            "brightness": observation.image.brightness,
            "exposure": observation.image.exposure,
            "contrast": observation.image.contrast,
            "noise": observation.image.noise,
        }

    # Build network metrics
    network = None
    if observation.network:
        network = {
            "latency_ms": observation.network.latencyMs,
            "latency_variance_ms": observation.network.latencyVarianceMs,
            "packet_loss_percent": observation.network.packetLossPercent,
            "heartbeat_age_sec": observation.network.heartbeatAgeSec,
        }

    # Build viewpoint metrics
    viewpoint = None
    if observation.viewpoint:
        viewpoint = {
            "shift_score": observation.viewpoint.shiftScore,
            "shift_confidence": observation.viewpoint.shiftConfidence,
            "reference_features": observation.viewpoint.referenceFeaturesCount,
            "inlier_ratio": observation.viewpoint.inlierRatio,
        }

    # Run analyzer (async)
    result = camera_health_analyzer.analyze_observation(
        camera_id=camera_id,
        config=config,
        source_timestamp=observation.sourceTimestamp,
        received_at=received_at,
        stream=stream,
        image=image,
        network=network,
        viewpoint=viewpoint,
        algorithm_version=observation.algorithmVersion,
    )

    # Persist observation
    await obs_repo.create(
        camera_id=camera_id,
        source_timestamp=observation.sourceTimestamp,
        received_at=received_at,
        source_sequence=observation.sourceSequence,
        observed_fps=stream.get("observed_fps") if stream else None,
        expected_fps=stream.get("expected_fps") if stream else None,
        frame_drop_rate=stream.get("frame_drop_rate") if stream else None,
        frame_age_ms=stream.get("frame_age_ms") if stream else None,
        stream_state=stream.get("state") if stream else None,
        reconnect_count=stream.get("reconnect_count") if stream else None,
        sharpness_raw=image.get("sharpness") if image else None,
        sharpness_score=image.get("sharpness") if image else None,
        brightness_mean=image.get("brightness") if image else None,
        brightness_status=None,  # Will be derived
        exposure_status=image.get("exposure") if image else None,
        contrast_score=image.get("contrast") if image else None,
        noise_score=image.get("noise") if image else None,
        network_latency_ms=network.get("latency_ms") if network else None,
        network_latency_variance_ms=network.get("latency_variance_ms") if network else None,
        packet_loss_percent=network.get("packet_loss_percent") if network else None,
        viewpoint_shift_score=viewpoint.get("shift_score") if viewpoint else None,
        viewpoint_shift_confidence=viewpoint.get("shift_confidence") if viewpoint else None,
        viewpoint_status=viewpoint.get("status") if viewpoint else None,
        overall_status=result.overall_status.value,
        reliability=result.reliability,
        quality_flags=result.quality_flags,
        algorithm_version=observation.algorithmVersion,
    )

    # Update current state
    await current_repo.upsert(camera_id, **{
        "overall_status": result.overall_status.value,
        "status_reason": result.status_reason,
        "reliability": result.reliability,
        "stream_state": result.stream_state,
        "fps": result.fps,
        "expected_fps": result.expected_fps,
        "frame_drop_percent": result.frame_drop_percent,
        "stale_seconds": result.stale_seconds,
        "reconnect_count": result.reconnect_count,
        "image_status": result.image_status,
        "sharpness_value": result.sharpness_value,
        "sharpness_status": result.sharpness_status,
        "sharpness_reason": result.sharpness_reason,
        "brightness_value": result.brightness_value,
        "brightness_status": result.brightness_status,
        "brightness_reason": result.brightness_reason,
        "exposure_status": result.exposure_status,
        "noise_status": result.noise_status,
        "background_stability": result.background_stability,
        "network_status": result.network_status,
        "latency_ms": result.latency_ms,
        "latency_variance_ms": result.latency_variance_ms,
        "packet_loss_percent": result.packet_loss_percent,
        "heartbeat_age_sec": result.heartbeat_age_sec,
        "viewpoint_status": result.viewpoint_status,
        "shift_score": result.shift_score,
        "shift_confidence": result.shift_confidence,
        "shift_detected": result.shift_detected,
        "shift_detected_at": result.shift_detected_at,
        "fence_confidence_note": result.fence_confidence_note,
        "trends_json": result.trends_json,
        "issues_json": result.issues_json,
        "impact_level": result.impact_level,
        "coverage": result.coverage,
        "affected_modules": result.affected_modules,
        "impact_message": result.impact_message,
        "maintenance_recommended": result.maintenance_recommended,
        "maintenance_reason": result.maintenance_reason,
        "maintenance_duration": result.maintenance_duration,
        "maintenance_impact_note": result.maintenance_impact_note,
        "data_source": result.data_source,
        "last_updated": result.last_updated,
        "algorithm_version": result.algorithm_version,
    })

    await session.commit()

    return HealthObservationIngestResponse(
        accepted=True,
        observationId=None,  # Would need to return the created ID
        currentStatus=result.overall_status.value,
    )


# ── Config Management ──────────────────────────────────────────────────────

@router.post("/{camera_id}/health/config", response_model=CameraHealthConfigResponse)
async def create_camera_health_config(
    camera_id: str,
    config_data: CameraHealthConfigCreate,
    session: AsyncSession = Depends(get_db_session),
):
    """Create health config for a camera."""
    config_repo = CameraHealthConfigRepository(session)
    config = await config_repo.create(camera_id, **config_data.model_dump())
    await session.commit()
    return CameraHealthConfigResponse.model_validate(config)


@router.get("/{camera_id}/health/config", response_model=CameraHealthConfigResponse)
async def get_camera_health_config(
    camera_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Get health config for a camera."""
    config_repo = CameraHealthConfigRepository(session)
    config = await config_repo.get(camera_id)
    if not config:
        raise HTTPException(status_code=404, detail=f"Health config for camera {camera_id} not found")
    return CameraHealthConfigResponse.model_validate(config)


@router.patch("/{camera_id}/health/config", response_model=CameraHealthConfigResponse)
async def update_camera_health_config(
    camera_id: str,
    config_data: CameraHealthConfigUpdate,
    session: AsyncSession = Depends(get_db_session),
):
    """Update health config for a camera."""
    config_repo = CameraHealthConfigRepository(session)
    config = await config_repo.update(camera_id, **config_data.model_dump(exclude_unset=True))
    if not config:
        raise HTTPException(status_code=404, detail=f"Health config for camera {camera_id} not found")
    await session.commit()
    return CameraHealthConfigResponse.model_validate(config)


@router.delete("/{camera_id}/health/config")
async def delete_camera_health_config(
    camera_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Delete health config for a camera."""
    config_repo = CameraHealthConfigRepository(session)
    deleted = await config_repo.delete(camera_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Health config for camera {camera_id} not found")
    await session.commit()
    return {"deleted": True}


# ── Provider Setup ────────────────────────────────────────────────────────

def setup_camera_health_provider():
    """Initialize the Camera Health Provider for Component 1 integration."""
    from app.domain.camera_health.provider import set_camera_health_provider
    from app.domain.camera_health.analyzer import camera_health_analyzer
    from app.domain.camera_health.provider import CameraHealthProviderImpl

    provider = CameraHealthProviderImpl(camera_health_analyzer)
    set_camera_health_provider(provider)