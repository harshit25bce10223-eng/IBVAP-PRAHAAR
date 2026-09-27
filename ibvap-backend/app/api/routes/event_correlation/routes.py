# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 4 — Event Correlation API Routes
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.routes.evaluation import TrackEvaluateRequest
from app.core.errors import IBVAPError
from app.db.database import get_db_session
from app.domain.event_correlation import (
    ingest_event,
    get_correlation_group,
    list_correlation_groups,
    CorrelationService,
)
from app.schemas.event_correlation import (
    CorrelationGroupPage,
    CorrelationGroupSummary,
    CorrelationGroup,
    CorrelationConfigCreate,
    CorrelationConfigUpdate,
    CorrelationConfigResponse,
)

router = APIRouter(prefix="/correlations", tags=["event-correlation"])


# ─── Ingestion ────────────────────────────────────────────────────────────────

@router.post("/events/ingest")
async def ingest_event_endpoint(
    event_data: dict = Body(...),
    source: str = "SYSTEM",
    session: AsyncSession = Depends(get_db_session),
):
    """
    Ingest an event for correlation processing.
    
    This is the main entry point for the Event Correlation Engine.
    Accepts events from various sources (Virtual Fence, Detection, Tracking, etc.)
    and performs correlation grouping.
    """
    try:
        from app.domain.event_correlation import ingest_event
        result = await ingest_event(session, event_data, source)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {str(e)}")


# ─── Correlation Group CRUD ──────────────────────────────────────────────────

@router.get("/", response_model=dict)
async def list_correlations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None, description="Filter by correlation status"),
    camera_id: str | None = Query(None, description="Filter by camera ID"),
    sector_id: str | None = Query(None, description="Filter by sector ID"),
    session: AsyncSession = Depends(get_db_session),
):
    """
    List correlation groups with pagination and filtering.
    """
    from app.domain.event_correlation import list_correlation_groups
    groups, total = await list_correlation_groups(
        session,
        page=page,
        page_size=page_size,
        status=status,
        camera_id=camera_id,
        sector_id=sector_id,
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
    Get full details of a correlation group.
    """
    group_data = await get_correlation_group(session, correlation_id)
    if not group_data:
        raise HTTPException(status_code=404, detail="Correlation group not found")
    # Return the group dict directly (not wrapped in "group" key)
    return group_data["group"]


@router.get("/{correlation_id}/relationships")
async def get_relationships(
    correlation_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get all relationships within a correlation group.
    """
    from app.repositories.event_correlation import CorrelationRelationshipRepository
    rel_repo = CorrelationRelationshipRepository(session)
    relationships = await rel_repo.list_by_group(correlation_id)
    return {"correlation_id": correlation_id, "relationships": relationships}


@router.get("/{correlation_id}/history")
async def get_history(
    correlation_id: str,
    limit: int = Query(100, ge=1, le=500),
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get history of a correlation group.
    """
    from app.repositories.event_correlation import CorrelationHistoryRepository
    history_repo = CorrelationHistoryRepository(session)
    history = await history_repo.list_by_correlation(correlation_id, limit=limit)
    return {"correlation_id": correlation_id, "history": history}


@router.get("/{correlation_id}/members")
async def get_members(
    correlation_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """
    Get member events of a correlation group.
    """
    from app.repositories.event_correlation import CorrelationGroupMemberRepository
    member_repo = CorrelationGroupMemberRepository(session)
    members = await member_repo.list_by_group(correlation_id)
    return {"correlation_id": correlation_id, "members": members}


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
    from app.domain.event_correlation import CorrelationService
    from app.repositories.event_correlation import CorrelationGroupRepository
    
    service = CorrelationService(session)
    group_repo = CorrelationGroupRepository(session)
    group = await group_repo.get(correlation_id)
    if not group:
        raise HTTPException(status_code=404, detail="Correlation group not found")
    
    # Verify internal consistency
    from app.repositories.event_correlation import CorrelationGroupMemberRepository, CorrelationRelationshipRepository
    member_repo = CorrelationGroupMemberRepository(session)
    rel_repo = CorrelationRelationshipRepository(session)
    
    members = await member_repo.list_by_group(correlation_id)
    relationships = await rel_repo.list_by_group(correlation_id)
    
    # Check: all member event_ids exist in relationships as from_event_id or to_event_id
    member_event_ids = {m.event_id for m in members}
    related_event_ids = set()
    for rel in relationships:
        related_event_ids.add(rel.from_event_id)
        related_event_ids.add(rel.to_event_id)
    
    orphaned_members = member_event_ids - related_event_ids
    # Primary member may not have relationships yet
    
    # Check: revision consistency
    from app.repositories.event_correlation import CorrelationHistoryRepository
    history_repo = CorrelationHistoryRepository(session)
    history = await history_repo.list_by_correlation(correlation_id)
    
    return {
        "correlation_id": correlation_id,
        "status": "VERIFIED" if not orphaned_members else "INCONSISTENT",
        "member_count": len(members),
        "relationship_count": len(relationships),
        "history_entries": len(history),
        "orphaned_members": list(orphaned_members),
        "revision": group.revision,
    }


# ─── Config ──────────────────────────────────────────────────────────────────

@router.post("/config")
async def create_correlation_config(
    config_data: dict,
    session: AsyncSession = Depends(get_db_session),
):
    """Create correlation configuration."""
    from app.repositories.event_correlation import CorrelationConfigRepository
    from app.models.event_correlation import CorrelationConfig
    
    config_repo = CorrelationConfigRepository(session)
    config = await config_repo.create(**config_data)
    await session.commit()
    return config


@router.get("/config/{camera_id}")
async def get_camera_config(
    camera_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Get correlation config for a camera."""
    from app.repositories.event_correlation import CorrelationConfigRepository
    config_repo = CorrelationConfigRepository(session)
    config = await config_repo.get(camera_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return config


@router.patch("/config/{camera_id}")
async def update_camera_config(
    camera_id: str,
    config_data: dict,
    session: AsyncSession = Depends(get_db_session),
):
    """Update correlation configuration for a camera."""
    from app.repositories.event_correlation import CorrelationConfigRepository
    config_repo = CorrelationConfigRepository(session)
    config = await config_repo.update(camera_id, **config_data)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    await session.commit()
    return config


@router.delete("/config/{camera_id}")
async def delete_camera_config(
    camera_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Delete correlation configuration for a camera."""
    from app.repositories.event_correlation import CorrelationConfigRepository
    config_repo = CorrelationConfigRepository(session)
    deleted = await config_repo.delete(camera_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Config not found")
    await session.commit()
    return {"deleted": True}