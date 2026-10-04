# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — Camera Health API Routes
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.errors import IBVAPError
from app.db.database import get_db_session
from app.domain.camera_health.analyzer import camera_health_analyzer
from app.domain.camera_health.provider import get_camera_health_provider, set_camera_health_provider
from app.domain.camera_health.state_engine import (
    ImageQualityMetrics,
    NetworkMetrics,
    StreamHealthMetrics,
    ViewpointMetrics,
)
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

_CAMEL_BOUNDARY = re.compile(r"(?<!^)(?=[A-Z])")


def _config_kwargs(payload: dict[str, Any]) -> dict[str, Any]:
    """Map camelCase config payload keys to ORM snake_case kwargs.

    The config schemas use camelCase field names while the ORM model uses
    snake_case columns; passing the raw model_dump() to the repository raised
    TypeError (HTTP 500) on create and silently no-op'd on update (§34
    clean-environment validation defect). 'cameraId' is dropped because
    camera_id is already the path parameter.
    """
    out: dict[str, Any] = {}
    for key, value in payload.items():
        if key == "cameraId":
            continue
        out[_CAMEL_BOUNDARY.sub("_", key).lower()] = value
    return out


def _config_to_response(config: Any) -> CameraHealthConfigResponse:
    """Build the camelCase response from the snake_case ORM row.

    from_attributes alone cannot bridge the naming gap, so map explicitly
    (same §34 defect family: create/read/update config endpoints must return
    valid contracts, not HTTP 500).
    """
    data: dict[str, Any] = {}
    for field in CameraHealthConfigResponse.model_fields:
        snake = _CAMEL_BOUNDARY.sub("_", field).lower()
        if hasattr(config, snake):
            data[field] = getattr(config, snake)
    return CameraHealthConfigResponse.model_validate(data)


def _ensure_utc(dt: datetime) -> datetime:
    """F8 policy: naive timestamps are interpreted as UTC.

    SQLite (aiosqlite) drops tzinfo on read-back, so rows written as aware-UTC
    come back naive-UTC. Comparing them against ``datetime.now()`` (naive local
    IST, +5:30) produced false LAST_KNOWN sources and skewed history buckets
    (§34 clean-environment validation defect). Normalize before any age/range
    comparison; never treat stored values as local time.
    """
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


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
            age = (datetime.now(timezone.utc) - _ensure_utc(current.last_updated)).total_seconds()
            if age > 60:
                source = "LAST_KNOWN"

    return CameraHealthResponse(
        cameraId=current.camera_id,
        status=current.overall_status,
        statusReason=current.status_reason,
        lastUpdated=_ensure_utc(current.last_updated).isoformat() if current.last_updated else None,
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
            "detectedAt": _ensure_utc(current.shift_detected_at).isoformat() if current.shift_detected_at else None,
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
            "at": _ensure_utc(current.last_known_at).isoformat() if current.last_known_at else None,
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
            age = (datetime.now(timezone.utc) - _ensure_utc(current.last_updated)).total_seconds()
            if age > 60:
                source = "LAST_KNOWN"

        results.append(CameraHealthSummary(
            cameraId=current.camera_id,
            status=current.overall_status,
            statusReason=current.status_reason,
            lastUpdated=_ensure_utc(current.last_updated).isoformat() if current.last_updated else None,
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
                "detectedAt": _ensure_utc(current.shift_detected_at).isoformat() if current.shift_detected_at else None,
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
                "at": _ensure_utc(current.last_known_at).isoformat() if current.last_known_at else None,
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

    # Default to last 24 hours (normalize both ends: query params may arrive
    # naive, stored telemetry is UTC per the F8 policy).
    to_dt = _ensure_utc(to_ts) if to_ts is not None else datetime.now(timezone.utc)
    from_dt = _ensure_utc(from_ts) if from_ts is not None else (to_dt - timedelta(hours=24))

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
            "firstSeen": _ensure_utc(event.first_seen).isoformat() if event.first_seen else None,
            "lastSeen": _ensure_utc(event.last_seen).isoformat() if event.last_seen else None,
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

    # Convert observation to internal format. F8 time policy: naive datetimes
    # are interpreted as UTC (documented rule); internal "now" is UTC-aware.
    # Normalize caller timestamps to UTC before persisting: SQLite drops
    # tzinfo, so a raw aware-IST value would be stored as a local wall clock
    # and then bucketed/compared as if it were UTC (5:30 shift, §34 defect).
    now = datetime.now(timezone.utc)
    source_ts = _ensure_utc(observation.sourceTimestamp) if observation.sourceTimestamp else now
    received_at = _ensure_utc(observation.receivedTimestamp) if observation.receivedTimestamp else now

    # Build stream metrics (typed contract — the analyzer/state engine expect
    # StreamHealthMetrics/ImageQualityMetrics/NetworkMetrics/ViewpointMetrics,
    # not dicts; dataclass defaults fill absent telemetry)
    stream = None
    if observation.stream:
        s = observation.stream
        stream = StreamHealthMetrics(
            connected=s.streamConnected,
            observed_fps=s.observedFps,
            expected_fps=s.expectedFps if s.expectedFps is not None else 25.0,
            frame_drop_rate=s.frameDropRate if s.frameDropRate is not None else 0.0,
            frame_age_ms=s.frameAgeMs if s.frameAgeMs is not None else 0.0,
            reconnect_count=s.reconnectCount if s.reconnectCount is not None else 0,
        )

    # Build image metrics
    image = None
    if observation.image:
        im = observation.image
        image = ImageQualityMetrics(
            sharpness=im.sharpness,
            brightness=im.brightness,
            exposure=im.exposure,
            contrast=im.contrast,
            noise=im.noise,
        )

    # Build network metrics
    network = None
    if observation.network:
        nw = observation.network
        network = NetworkMetrics(
            latency_ms=nw.latencyMs,
            latency_variance_ms=nw.latencyVarianceMs,
            packet_loss_percent=nw.packetLossPercent,
            heartbeat_age_sec=nw.heartbeatAgeSec,
        )

    # Build viewpoint metrics (caller/edge-computed evidence; reference
    # lifecycle is managed by the analyzer when frames are supplied)
    viewpoint = None
    if observation.viewpoint:
        vp = observation.viewpoint
        viewpoint = ViewpointMetrics(
            shift_score=vp.shiftScore,
            shift_confidence=vp.shiftConfidence,
            reference_features=vp.referenceFeaturesCount,
            inlier_ratio=vp.inlierRatio,
        )

    # Run analyzer (async)
    result = camera_health_analyzer.analyze_observation(
        camera_id=camera_id,
        config=config,
        source_timestamp=source_ts,
        received_at=received_at,
        stream=stream,
        image=image,
        network=network,
        viewpoint=viewpoint,
        algorithm_version=observation.algorithmVersion,
    )

    # Persist observation (typed attribute access; engine-derived stream and
    # viewpoint status are recorded — the raw telemetry payload carries no
    # status field)
    obs_kwargs = dict(
        camera_id=camera_id,
        source_timestamp=source_ts,
        received_at=received_at,
        source_sequence=observation.sourceSequence,
        observed_fps=stream.observed_fps if stream else None,
        expected_fps=stream.expected_fps if stream else None,
        frame_drop_rate=stream.frame_drop_rate if stream else None,
        frame_age_ms=stream.frame_age_ms if stream else None,
        stream_state=result.stream_state,
        reconnect_count=stream.reconnect_count if stream else None,
        sharpness_raw=image.sharpness if image else None,
        sharpness_score=image.sharpness if image else None,
        brightness_mean=image.brightness if image else None,
        brightness_status=result.brightness_status,
        exposure_status=image.exposure if image else None,
        contrast_score=image.contrast if image else None,
        noise_score=image.noise if image else None,
        network_latency_ms=network.latency_ms if network else None,
        network_latency_variance_ms=network.latency_variance_ms if network else None,
        packet_loss_percent=network.packet_loss_percent if network else None,
        viewpoint_shift_score=viewpoint.shift_score if viewpoint else None,
        viewpoint_shift_confidence=viewpoint.shift_confidence if viewpoint else None,
        viewpoint_status=result.viewpoint_status,
        overall_status=result.overall_status.value,
        reliability=result.reliability,
        quality_flags=result.quality_flags,
        algorithm_version=observation.algorithmVersion,
    )

    # Idempotent ingest: (camera_id, source_sequence) is unique. Adapter
    # retries and camera reboots (sequence counter resets) must not raise an
    # unhandled UNIQUE-constraint 500 — a duplicate sequence updates the
    # existing row and is reported via `duplicate: true`, while the derived
    # current state below still reflects the re-sent telemetry.
    duplicate = False
    if observation.sourceSequence is not None:
        existing = await obs_repo.get_by_sequence(camera_id, observation.sourceSequence)
        if existing is not None:
            duplicate = True
            created = await obs_repo.apply_update(existing, **obs_kwargs)
        else:
            created = await obs_repo.create(**obs_kwargs)
    else:
        created = await obs_repo.create(**obs_kwargs)

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

    # observation_id is the persisted row id (assigned at flush) — carry it
    # on the result for downstream observability (§43) and on the response.
    observation_id = created.id if created is not None else None
    result.observation_id = observation_id
    return HealthObservationIngestResponse(
        accepted=True,
        observationId=observation_id,
        currentStatus=result.overall_status.value,
        duplicate=duplicate,
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
    config = await config_repo.create(camera_id, **_config_kwargs(config_data.model_dump()))
    await session.commit()
    return _config_to_response(config)


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
    return _config_to_response(config)


@router.patch("/{camera_id}/health/config", response_model=CameraHealthConfigResponse)
async def update_camera_health_config(
    camera_id: str,
    config_data: CameraHealthConfigUpdate,
    session: AsyncSession = Depends(get_db_session),
):
    """Update health config for a camera."""
    config_repo = CameraHealthConfigRepository(session)
    config = await config_repo.update(camera_id, **_config_kwargs(config_data.model_dump(exclude_unset=True)))
    if not config:
        raise HTTPException(status_code=404, detail=f"Health config for camera {camera_id} not found")
    await session.commit()
    return _config_to_response(config)


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