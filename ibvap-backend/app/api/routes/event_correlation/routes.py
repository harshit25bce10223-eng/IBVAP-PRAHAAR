# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 4 — Event Correlation API Routes
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db_session
from app.domain.event_correlation import (
    ingest_event,
    get_correlation_group,
    list_correlation_groups,
    CorrelationService,
)

router = APIRouter(prefix="/correlations", tags=["event-correlation"])


# ─── Ingestion ────────────────────────────────────────────────────────────────

@router.post("/events/ingest")
async def ingest_event_endpoint(
    event_data: dict,
    source: str = "SYSTEM",
    session: AsyncSession = Depends(get_db_session),
):
    """
    Ingest an event for correlation processing.

    This is the main entry point for the Event Correlation Engine. Accepts
    events from various sources (Virtual Fence, Detection, Tracking, ANPR, ...)
    and performs correlation grouping.
    """
    if not event_data or not isinstance(event_data, dict):
        raise HTTPException(status_code=400, detail="event_data must be an object")
    try:
        from app.domain.event_correlation import ingest_event
        # CorrelationService commits internally on all write paths
        return await ingest_event(session, event_data, source)
    except HTTPException:
        raise
    except Exception as e:
        await session.rollback()
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


# ─── Correlation Group CRUD ──────────────────────────────────────────────────

@router.get("/events/{event_id}")
async def get_event_member(
    event_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Get a member event inside its correlation group (frontend contract)."""
    from app.repositories.event_correlation import CorrelationGroupMemberRepository
    from app.domain.event_correlation.group_service import _serialize_member_full

    member_repo = CorrelationGroupMemberRepository(session)
    members = await member_repo.list_by_event(event_id)
    if not members:
        raise HTTPException(status_code=404, detail="Event not found in any correlation group")

    joined = await get_correlation_group(session, members[0].correlation_id)
    if not joined:
        raise HTTPException(status_code=404, detail="Correlation group not found")

    member = await _serialize_member_full(session, members[0], joined["group"].get("sector_id"))
    return {
        "event_id": event_id,
        "correlation_id": members[0].correlation_id,
        "member": member,
        "group": joined["group"],
    }


@router.get("/config")
async def list_configs(
    session: AsyncSession = Depends(get_db_session),
):
    """List all correlation configurations."""
    from app.repositories.event_correlation import CorrelationConfigRepository
    config_repo = CorrelationConfigRepository(session)
    configs = await config_repo.list_all()
    return {"configs": configs, "total": len(configs)}


@router.get("/", response_model=dict)
async def list_correlations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, description="Filter by correlation status"),
    camera_id: str | None = Query(None, description="Filter by camera ID"),
    sector_id: str | None = Query(None, description="Filter by sector ID"),
    source: str | None = Query(None, description="Filter by source system"),
    search: str | None = Query(
        None, description="Search by correlation/event/sector/camera/track/incident id"
    ),
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] | None = Query(
        None, description="Filter by severity band of the highest-scoring referenced incident"
    ),
    time_range: Literal["15m", "1h", "today"] | None = Query(
        None, description="Filter by started_at recency window (UTC)"
    ),
    sort: str = Query("started_at", description="Sort column"),
    order: str = Query("desc", description="Sort order (asc|desc)"),
    session: AsyncSession = Depends(get_db_session),
):
    """List correlation groups with pagination and filtering."""
    from app.domain.event_correlation import list_correlation_groups
    groups, total = await list_correlation_groups(
        session,
        page=page,
        page_size=page_size,
        status=status,
        camera_id=camera_id,
        sector_id=sector_id,
        source=source,
        search=search,
        severity=severity,
        time_range=time_range,
        sort=sort,
        order=order,
    )
    return {
        "groups": groups,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/{correlation_id}")
async def get_correlation(
    correlation_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get full details of a correlation group: summary, members,
    relationships and history in one payload.
    """
    joined = await get_correlation_group(session, correlation_id)
    if not joined:
        raise HTTPException(status_code=404, detail="Correlation group not found")
    return {**joined["group"], "members": joined["members"], "relationships": joined["relationships"], "history": joined["history"]}


@router.get("/{correlation_id}/relationships")
async def get_relationships(
    correlation_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Get all relationships within a correlation group."""
    joined = await get_correlation_group(session, correlation_id)
    if not joined:
        raise HTTPException(status_code=404, detail="Correlation group not found")
    return {"correlation_id": correlation_id, "relationships": joined["relationships"]}


@router.get("/{correlation_id}/history")
async def get_history(
    correlation_id: str,
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session),
):
    """Get history of a correlation group."""
    from app.repositories.event_correlation import CorrelationHistoryRepository
    from app.domain.event_correlation.group_service import _serialize_history

    history_repo = CorrelationHistoryRepository(session)
    history = await history_repo.list_by_correlation(correlation_id, limit=limit)
    return {
        "correlation_id": correlation_id,
        "history": [_serialize_history(h) for h in history],
    }


@router.get("/{correlation_id}/members")
async def get_members(
    correlation_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Get member events of a correlation group."""
    from app.repositories.event_correlation import CorrelationGroupMemberRepository
    from app.domain.event_correlation.group_service import _serialize_member

    member_repo = CorrelationGroupMemberRepository(session)
    members = await member_repo.list_by_group(correlation_id)
    return {
        "correlation_id": correlation_id,
        "members": [_serialize_member(m) for m in members],
    }


# ─── Verification (Correlation Integrity Only) ─────────────────────────────────

@router.post("/{correlation_id}/verify")
async def verify_correlation(
    correlation_id: str,
    actor_id: str | None = None,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Verify the integrity of a correlation group (internal consistency only).

    This verifies correlation-specific integrity: member consistency,
    relationship validity, revision history. It does NOT verify evidence
    hashes - that is Component 3's responsibility.
    """
    service = CorrelationService(session)
    result = await service.verify_correlation(correlation_id)
    if result.get("status") == "NOT_FOUND":
        raise HTTPException(status_code=404, detail="Correlation group not found")
    return result


# ─── Human Review (preserves existing status vocabulary; history records the decision) ─

_REVIEW_TO_STATUS = {
    "UNDER_REVIEW": "UNCERTAIN",
    "CONFIRMED_RELATED": "CORRELATED",
    "SEPARATED": "DISSOLVED",
    "DISMISSED": "DISSOLVED",
    "AUTO_CORRELATED": "CORRELATED",
}


@router.post("/{correlation_id}/review")
async def review_correlation(
    correlation_id: str,
    decision: str,
    reason: str | None = None,
    actor_id: str | None = None,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Record an operator review decision on a correlation group.

    Human review supports: AUTO_CORRELATED, UNDER_REVIEW, CONFIRMED_RELATED,
    SEPARATED, DISMISSED. Decisions map to the existing status vocabulary so no
    duplicate state enum is introduced. The decision + reason are persisted as a
    history transition; "confirmed related" is an operational correlation, NOT an
    identity confirmation.
    """
    if decision not in _REVIEW_TO_STATUS:
        raise HTTPException(
            status_code=422,
            detail="decision must be one of AUTO_CORRELATED, UNDER_REVIEW, CONFIRMED_RELATED, SEPARATED, DISMISSED",
        )

    from app.models.event_correlation import CorrelationGroupState
    from app.repositories.event_correlation import (
        CorrelationGroupRepository,
        CorrelationHistoryRepository,
    )

    group_repo = CorrelationGroupRepository(session)
    group = await group_repo.get(correlation_id)
    if not group:
        raise HTTPException(status_code=404, detail="Correlation group not found")

    old_status = group.status
    new_status = _REVIEW_TO_STATUS[decision]
    group.status = new_status
    if new_status == "DISSOLVED":
        group.state = CorrelationGroupState.DISSOLVED
        group.ended_at = datetime.now(timezone.utc)
    else:
        group.state = CorrelationGroupState.STABLE
    group.revision += 1
    group.updated_at = datetime.now(timezone.utc)

    note = f"Review: {decision}"
    if reason:
        note = f"{note} — {reason}"

    history_repo = CorrelationHistoryRepository(session)
    await history_repo.log_transition(
        correlation_id=correlation_id,
        old_status=old_status,
        new_status=new_status,
        reason=note,
        state=group.state,
        revision=group.revision,
        snapshot_json={
            "event_count": group.event_count,
            "status": new_status,
            "state": group.state,
            "review_decision": decision,
        },
    )
    await session.commit()

    return {
        "correlation_id": correlation_id,
        "status": new_status,
        "state": group.state,
        "review_decision": decision,
        "note": note,
    }


# ─── Config ──────────────────────────────────────────────────────────────────

# Writable CorrelationConfig columns (model-managed fields excluded: config_id,
# revision, timestamps, activated_at).
_CONFIG_KEYS = {
    "profile",
    "event_pair",
    "temporal_window_seconds",
    "spatial_window_meters",
    "camera_adjacency",
    "min_relationship_strength",
    "max_group_duration_seconds",
    "min_support_events",
    "compatibility_matrix",
    "temporal_windows",
    "spatial_windows",
    "active",
}


def _reject_unknown_keys(config_data: dict) -> None:
    unknown = sorted(set(config_data) - _CONFIG_KEYS)
    if unknown:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown correlation config keys: {', '.join(unknown)}",
        )


def _validate_duration_vs_temporal(temporal: int | None, duration: int | None) -> None:
    if temporal is not None and duration is not None and duration <= temporal:
        raise HTTPException(
            status_code=422,
            detail="max_group_duration_seconds must be greater than temporal_window_seconds",
        )


def _validate_config_values(config_data: dict) -> None:
    """Reject clearly-invalid configuration values (422, not 500)."""
    _reject_unknown_keys(config_data)
    if "temporal_window_seconds" in config_data:
        v = config_data["temporal_window_seconds"]
        if v is not None and (not isinstance(v, int) or v <= 0):
            raise HTTPException(status_code=422, detail="temporal_window_seconds must be a positive integer")
    if "max_group_duration_seconds" in config_data:
        v = config_data["max_group_duration_seconds"]
        if v is not None and (not isinstance(v, int) or v <= 0):
            raise HTTPException(status_code=422, detail="max_group_duration_seconds must be a positive integer")
    if "min_relationship_strength" in config_data:
        v = config_data["min_relationship_strength"]
        if v is not None and (not isinstance(v, int) or not (0 <= v <= 100)):
            raise HTTPException(status_code=422, detail="min_relationship_strength must be between 0 and 100")
    if "min_support_events" in config_data:
        v = config_data["min_support_events"]
        if v is not None and (not isinstance(v, int) or v <= 0):
            raise HTTPException(status_code=422, detail="min_support_events must be a positive integer")
    if "spatial_window_meters" in config_data:
        v = config_data["spatial_window_meters"]
        if v is not None and (not isinstance(v, int) or v <= 0):
            raise HTTPException(status_code=422, detail="spatial_window_meters must be a positive integer")
    if config_data.get("camera_adjacency") is not None:
        adjacency = config_data["camera_adjacency"]
        if not isinstance(adjacency, dict):
            raise HTTPException(status_code=422, detail="camera_adjacency must be an object")
        for cam, neighbors in adjacency.items():
            if not isinstance(cam, str) or not cam:
                raise HTTPException(status_code=422, detail="camera_adjacency keys must be non-empty camera ids")
            if not isinstance(neighbors, list) or not all(isinstance(n, str) for n in neighbors):
                raise HTTPException(status_code=422, detail="camera_adjacency values must be lists of camera ids")


@router.post("/config")
async def create_correlation_config(
    config_data: dict,
    session: AsyncSession = Depends(get_db_session),
):
    """Create correlation configuration."""
    _validate_config_values(config_data)
    # Effective values against model defaults (temporal 60, duration 300) so a
    # single-key payload cannot create an internally inconsistent config.
    _validate_duration_vs_temporal(
        config_data.get("temporal_window_seconds", 60),
        config_data.get("max_group_duration_seconds", 300),
    )
    from app.repositories.event_correlation import CorrelationConfigRepository

    config_repo = CorrelationConfigRepository(session)
    config = await config_repo.create(**config_data)
    await session.commit()
    return config


@router.get("/config/{config_id}")
async def get_config(
    config_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Get a correlation config by its config_id."""
    from app.repositories.event_correlation import CorrelationConfigRepository
    config_repo = CorrelationConfigRepository(session)
    config = await config_repo.get(config_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return config


@router.patch("/config/{config_id}")
async def update_config(
    config_id: str,
    config_data: dict,
    session: AsyncSession = Depends(get_db_session),
):
    """Update correlation configuration for a config_id."""
    from app.repositories.event_correlation import CorrelationConfigRepository
    config_repo = CorrelationConfigRepository(session)
    existing = await config_repo.get(config_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Config not found")

    _validate_config_values(config_data)
    # Validate the merged result so a partial PATCH cannot leave the stored
    # config internally inconsistent (e.g. duration <= temporal window).
    _validate_duration_vs_temporal(
        config_data.get("temporal_window_seconds", existing.temporal_window_seconds),
        config_data.get("max_group_duration_seconds", existing.max_group_duration_seconds),
    )

    config = await config_repo.update(config_id, **config_data)
    await session.commit()
    return config


@router.delete("/config/{config_id}")
async def delete_config(
    config_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Delete correlation configuration for a config_id."""
    from app.repositories.event_correlation import CorrelationConfigRepository
    config_repo = CorrelationConfigRepository(session)
    deleted = await config_repo.delete(config_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Config not found")
    await session.commit()
    return {"deleted": True}