# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 4 — Correlation Group Service
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event_correlation import (
    CorrelationGroup,
    CorrelationGroupMember,
    CorrelationRelationship,
    CorrelationHistory,
    CorrelationConfig,
    CorrelationConfigProfile,
    CorrelationStatus,
    CorrelationGroupState,
    CorrelationCompleteness,
    CorrelationGroupMember as CorrelationGroupMemberModel,
    CorrelationRelationship as CorrelationRelationshipModel,
    CorrelationHistory as CorrelationHistoryModel,
)
from app.models.event import Event
from sqlalchemy import select, func, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta, timezone
from typing import Any

from app.domain.event_correlation.temporal_engine import temporal_engine
from app.domain.event_correlation.spatial_engine import spatial_engine
from app.domain.event_correlation.entity_engine import entity_engine
from app.domain.event_correlation.rule_engine import rule_engine, CorrelationResult
from app.domain.event_correlation.temporal_engine import temporal_engine as temporal_engine_singleton
from app.domain.event_correlation.spatial_engine import spatial_engine as spatial_engine_singleton
from app.domain.event_correlation.entity_engine import entity_engine as entity_engine_singleton
from app.domain.event_correlation.rule_engine import rule_engine as rule_engine_singleton
from app.repositories.event_correlation import (
    CorrelationGroupRepository,
    CorrelationGroupMemberRepository,
    CorrelationRelationshipRepository,
    CorrelationHistoryRepository,
    CorrelationConfigRepository,
)
from app.domain.event_correlation.compatibility import get_compatibility, get_event_type_compatibility
from app.core.config import settings
from app.core.errors import IBVAPError, IBVAPErrorCode


class CorrelationService:
    """
    Main orchestration service for event correlation.
    
    Orchestrates:
    - Event ingestion and candidate group search
    - Temporal, spatial, and entity relationship analysis
    - Correlation group creation and lifecycle management
    - Ledger integration and audit trail
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.group_repo = CorrelationGroupRepository(session)
        self.member_repo = CorrelationGroupMemberRepository(session)
        self.relationship_repo = CorrelationRelationshipRepository(session)
        self.history_repo = CorrelationHistoryRepository(session)
        self.config_repo = CorrelationConfigRepository(session)

    # ─────────────────────────────────────────────────────────────────────────
    # Main Entry Point
    # ─────────────────────────────────────────────────────────────────────────

    async def ingest_event(
        self,
        event_data: dict,
        source: str = "SYSTEM",
    ) -> dict:
        """
        Main entry point for event ingestion.
        
        Args:
            event_data: Raw event data from upstream source
            source: Source system identifier
            
        Returns:
            dict with correlation_id, action, group details
        """
        # 1. Validate and normalize event
        event_data = self._normalize_event(event_data, source)
        
        # 2. Check for duplicate (idempotency)
        existing = await self._check_duplicate(event_data)
        if existing:
            return {
                "correlation_id": existing.correlation_id,
                "action": "DUPLICATE",
                "group_id": existing.correlation_id,
                "message": "Duplicate event ignored",
            }

        # 2. Find candidate groups
        candidates = await self._find_candidate_groups(event_data)
        
        # 3. Evaluate against existing groups
        best_match = None
        best_score = 0
        
        for candidate in candidates:
            score = await self._score_match(event_data, candidate)
            if score > best_score:
                best_score = score
                best_match = candidate

        # 4. Decide action
        if best_score >= 50:  # min_correlation_score
            # Add to existing group
            group = await self._add_to_group(best_match["group"], event_data)
            return {
                "correlation_id": best_match["group"].correlation_id,
                "action": "UPDATED",
                "group_id": best_match["group"].correlation_id,
                "score": best_score,
            }
        else:
            # Create new correlation group
            group = await self._create_new_group(event_data)
            return {
                "correlation_id": group.correlation_id,
                "action": "CREATED",
                "group_id": group.correlation_id,
                "score": 0,
            }

    def _normalize_event(self, event_data: dict, source: str) -> dict:
        """Normalize incoming event data to canonical format."""
        normalized = {
            "event_id": event_data.get("event_id") or f"EVT-{uuid.uuid4().hex[:10].upper()}",
            "event_type": event_data.get("event_type") or event_data.get("kind", "DETECTION"),
            "source": event_data.get("source", "SYSTEM"),
            "camera_id": event_data.get("camera_id"),
            "zone_id": event_data.get("zone_id"),
            "sector_id": event_data.get("sector_id"),
            "track_id": event_data.get("track_id"),
            "event_time": event_data.get("event_time") or event_data.get("ts"),
            "source_event_id": event_data.get("source_event_id"),
            "source_sequence": event_data.get("source_sequence"),
            "object_type": event_data.get("object_type"),
            "bbox": event_data.get("bbox"),
            "confidence": event_data.get("confidence"),
            "is_night": event_data.get("is_night", False),
            "multi_camera_confirmed": event_data.get("multi_camera_confirmed", False),
            "reliability": event_data.get("reliability", "HIGH"),
            "track_id": event_data.get("track_id"),
            "source_event_id": event_data.get("source_event_id"),
            "source_sequence": event_data.get("source_sequence"),
            "reid_candidate": event_data.get("reid_candidate"),
            "source": source,
            "payload_json": event_data.get("payload"),
        }
        
        # Ensure timestamp is timezone-aware
        if "event_time" in normalized and normalized["event_time"]:
            if isinstance(normalized["event_time"], str):
                normalized["event_time"] = datetime.fromisoformat(
                    normalized["event_time"].replace("Z", "+00:00")
                )
            if normalized["event_time"].tzinfo is None:
                normalized["event_time"] = normalized["event_time"].replace(tzinfo=timezone.utc)
        
        return normalized

    async def _get_by_event_id(self, event_id: str) -> Any | None:
        """Check if event_id already exists in any group."""
        from app.repositories.event_correlation import CorrelationGroupMemberRepository
        member_repo = CorrelationGroupMemberRepository(self.session)
        members = await member_repo.list_by_event(event_id)
        if members:
            # Get the group for the first member
            from app.repositories.event_correlation import CorrelationGroupRepository
            group_repo = CorrelationGroupRepository(self.session)
            return await group_repo.get(members[0].correlation_id)
        return None

    async def _check_duplicate(self, event_data: dict) -> Any | None:
        """Check for duplicate event based on idempotency key."""
        # Check by event_id
        existing = await self._get_by_event_id(event_data.get("event_id"))
        if existing:
            return existing
        
        # Check by deduplication key (source_event_id + source_sequence)
        source_event_id = event_data.get("source_event_id")
        source_sequence = event_data.get("source_sequence")
        if source_event_id and source_sequence:
            dedup_key = f"{event_data.get('camera_id')}|{source_event_id}|{source_sequence}"
            # Would check against stored deduplication keys
            pass
        
        return None

    async def _find_candidate_groups(self, event_data: dict) -> list:
        """Find existing correlation groups that could be related to this event."""
        # Get active groups in the same sector/camera
        repo = CorrelationGroupRepository(self.session)
        
        # Get active groups
        active_groups = await self.group_repo.list_active()
        
        # Filter by sector/camera/time
        candidates = []
        for group in active_groups:
            # Check if group is expired
            if group.ended_at:
                continue
            
            # Check temporal proximity
            group_start = group.started_at
            event_time = event_data.get("event_time")
            if group.started_at and event_data.get("event_time"):
                if isinstance(event_time, str):
                    event_time = datetime.fromisoformat(event_time.replace("Z", "+00:00"))
                if group.started_at:
                    time_diff = abs((event_time - group.started_at).total_seconds())
                    if time_diff > 300:  # max_group_duration
                        continue
            
            # Check spatial compatibility
            if not self._spatially_compatible(group):
                continue
            
            candidates.append(group)
        
        return candidates

    def _spatially_compatible(self, group) -> bool:
        """Check if event is spatially compatible with group."""
        # For now, return True - would check sector, camera, zone compatibility
        return True

    async def _score_match(self, event_data: dict, candidate: Any) -> int:
        """Score how well an event matches an existing group."""
        # This would use the rule engine
        return 75  # placeholder

    async def _add_to_group(self, group: Any, event_data: dict) -> Any:
        """Add event to existing correlation group."""
        # Add member
        member = await self.member_repo.add_member(
            correlation_id=group.correlation_id,
            event_id=event_data["event_id"],
            membership_type="SUPPORTING",
            confidence=75,
            reason="Temporal and spatial correlation",
        )
        
        # Update group counts
        group.event_count += 1
        # Note: camera_ids, zone_ids don't exist as fields - would need to query members
        # For now, just increment counts
        group.camera_count += 1
        group.zone_count += 1
        
        # Update timestamps
        group.ended_at = datetime.now(timezone.utc)
        group.revision += 1
        
        # Log lifecycle
        from app.domain.evidence.lifecycle import evidence_lifecycle_service
        await evidence_lifecycle_service.log_event(
            evidence_id=group.correlation_id,
            event_type="GROUP_UPDATED",
            actor="correlation_service",
            metadata={"added_event": event_data["event_id"]},
            session=self.session,
        )
        
        # Update member relationships
        await self._update_relationships(group)
        
        await self.session.commit()
        return group

    async def _create_new_group(self, event_data: dict) -> Any:
        """Create a new correlation group for a standalone event."""
        group = await self.group_repo.create(
            status=CorrelationStatus.STANDALONE,
            state=CorrelationGroupState.OPEN,
            started_at=event_data.get("event_time", datetime.now(timezone.utc)),
            primary_event_id=event_data.get("event_id"),
            event_count=1,
            camera_count=1,
            zone_count=0,
            source_count=1,
            sources=[event_data.get("source", "SYSTEM")],
            modalities=[event_data.get("modality", "VIDEO")],
            sector_id=event_data.get("sector_id"),
            region_profile=event_data.get("region_profile"),
            algorithm_version="1.0",
            configuration_version="1.0",
        )
        
        # Add first member
        await self.member_repo.add_member(
            correlation_id=group.correlation_id,
            event_id=event_data["event_id"],
            membership_type="PRIMARY",
            confidence=100,
            reason="Primary event of new correlation group",
        )
        
        # Log lifecycle
        from app.domain.evidence.lifecycle import evidence_lifecycle_service
        await evidence_lifecycle_service.log_event(
            evidence_id=group.correlation_id,
            event_type="GROUP_CREATED",
            actor="correlation_service",
            metadata={"primary_event": event_data["event_id"]},
            session=self.session,
        )
        
        await self.session.commit()
        return group

    async def _update_relationships(self, group: Any) -> None:
        """Update relationships within the group after adding a member."""
        # Get all members
        members = await self.member_repo.list_by_group(group.correlation_id)
        
        # Create relationships between new member and existing members
        new_member_event_id = members[-1].event_id if members else None
        if not new_member_event_id:
            return
        
        for member in members[:-1]:  # Exclude the new member
            # Temporal relationship
            from_event = await self.session.get(Event, new_member_event_id)
            to_event = await self.session.get(Event, member.event_id)
            
            if from_event and to_event:
                temporal_rel = temporal_engine.classify_relation(
                    {"event_id": from_event.event_id, "event_time": from_event.ts, "camera_id": from_event.camera_id},
                    {"event_id": to_event.event_id, "event_time": to_event.ts, "camera_id": to_event.camera_id},
                )
                
                if temporal_rel:
                    await self.relationship_repo.create_relationship(
                        correlation_id=group.correlation_id,
                        from_event_id=from_event.event_id,
                        to_event_id=to_event.event_id,
                        rel_type="TEMPORAL",
                        strength=temporal_rel.get("confidence"),
                        evidence_json=temporal_rel,
                        explanation=temporal_rel.get("reason"),
                    )
                
                # Spatial relationship
                spatial_rel = spatial_engine.classify_relation(
                    {"event_id": from_event.event_id, "camera_id": from_event.camera_id, "zone_id": from_event.zone_id, "sector_id": from_event.sector_id},
                    {"event_id": to_event.event_id, "camera_id": to_event.camera_id, "zone_id": to_event.zone_id, "sector_id": to_event.sector_id},
                )
                
                if spatial_rel:
                    await self.relationship_repo.create_relationship(
                        correlation_id=group.correlation_id,
                        from_event_id=from_event.event_id,
                        to_event_id=to_event.event_id,
                        rel_type="SPATIAL",
                        strength=spatial_rel.get("confidence"),
                        evidence_json=spatial_rel,
                        explanation=spatial_rel.get("reason"),
                    )
                
                # Entity relationship
                entity_rel = entity_engine.classify_relation(
                    {"track_id": from_event.track_id, "event_id": from_event.event_id},
                    {"track_id": to_event.track_id, "event_id": to_event.event_id},
                )
                
                if entity_rel:
                    await self.relationship_repo.create_relationship(
                        correlation_id=group.correlation_id,
                        from_event_id=from_event.event_id,
                        to_event_id=to_event.event_id,
                        rel_type="ENTITY",
                        strength=entity_rel.get("strength"),
                        evidence_json=entity_rel,
                        explanation=entity_rel.get("reason"),
                    )

    async def verify_correlation(self, correlation_id: str) -> bool:
        """Verify a correlation group's integrity."""
        # Would verify ledger integrity, member consistency, etc.
        return True


# ─────────────────────────────────────────────────────────────────────────────
# Ingestion Endpoint Handler
# ─────────────────────────────────────────────────────────────────────────────

async def ingest_event(
    session: AsyncSession,
    event_data: dict,
    source: str = "SYSTEM",
) -> dict:
    """
    Main ingestion endpoint for event correlation.
    
    This is the main entry point for the Event Correlation Engine.
    """
    service = CorrelationService(session)
    return await service.ingest_event(event_data, source)


async def get_correlation_group(
    session: AsyncSession,
    correlation_id: str,
) -> dict | None:
    """Get full correlation group details."""
    from app.repositories.event_correlation import CorrelationGroupRepository
    from app.domain.event_correlation.rule_engine import rule_engine
    
    repo = CorrelationGroupRepository(session)
    group = await repo.get(correlation_id)
    if not group:
        return None
    
    # Get members
    from app.repositories.event_correlation import CorrelationGroupMemberRepository
    member_repo = CorrelationGroupMemberRepository(session)
    members = await member_repo.list_by_group(correlation_id)
    
    # Get relationships
    from app.repositories.event_correlation import CorrelationRelationshipRepository
    rel_repo = CorrelationRelationshipRepository(session)
    relationships = await rel_repo.list_by_group(correlation_id)
    
    # Get history
    from app.repositories.event_correlation import CorrelationHistoryRepository
    history_repo = CorrelationHistoryRepository(session)
    history = await history_repo.list_by_correlation(correlation_id)
    
    # Convert group to dict
    group_dict = {
        "correlation_id": group.correlation_id,
        "incident_id": group.incident_id,
        "primary_event_id": group.primary_event_id,
        "status": group.status,
        "state": group.state,
        "sector_id": group.sector_id,
        "region_profile": group.region_profile,
        "started_at": group.started_at.isoformat() if group.started_at else None,
        "ended_at": group.ended_at.isoformat() if group.ended_at else None,
        "event_count": group.event_count,
        "camera_count": group.camera_count,
        "zone_count": group.zone_count,
        "source_count": group.source_count,
        "confidence": group.confidence,
        "completeness": group.completeness,
        "uncertainty_reliability": group.uncertainty_reliability,
        "uncertainty_note": group.uncertainty_note,
        "track_candidate_id": group.track_candidate_id,
        "track_candidate_confidence": group.track_candidate_confidence,
        "track_candidate_label": group.track_candidate_label,
        "camera_chain": group.camera_chain,
        "modalities": group.modalities,
        "sources": group.sources,
        "health_context": group.health_context,
        "evidence_count": group.evidence_count,
        "connectivity": group.connectivity,
        "duplicated_or_suppressed": group.duplicated_or_suppressed,
        "revision": group.revision,
        "algorithm_version": group.algorithm_version,
        "configuration_version": group.configuration_version,
        "updated_at": group.updated_at.isoformat() if group.updated_at else None,
        "created_at": group.created_at.isoformat() if group.created_at else None,
    }
    
    # Convert members to dicts
    members_list = []
    for m in members:
        members_list.append({
            "id": m.id,
            "correlation_id": m.correlation_id,
            "event_id": m.event_id,
            "membership_type": m.membership_type,
            "confidence": m.confidence,
            "reason": m.reason,
            "added_at": m.added_at.isoformat() if m.added_at else None,
            "removed_at": m.removed_at.isoformat() if m.removed_at else None,
            "membership_confidence": m.membership_confidence,
            "revision": m.revision,
        })
    
    # Convert relationships to dicts
    relationships_list = []
    for r in relationships:
        relationships_list.append({
            "id": r.id,
            "correlation_id": r.correlation_id,
            "from_event_id": r.from_event_id,
            "to_event_id": r.to_event_id,
            "type": r.type,
            "strength": r.strength,
            "evidence_json": r.evidence_json,
            "explanation": r.explanation,
            "algorithm_version": r.algorithm_version,
            "revision": r.revision,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        })
    
    # Convert history to dicts
    history_list = []
    for h in history:
        history_list.append({
            "id": h.id,
            "correlation_id": h.correlation_id,
            "revision": h.revision,
            "status": h.status,
            "state": h.state,
            "snapshot_json": h.snapshot_json,
            "reason": h.reason,
            "trigger_event_id": h.trigger_event_id,
            "algorithm_version": h.algorithm_version,
            "configuration_version": h.configuration_version,
            "timestamp": h.timestamp.isoformat() if h.timestamp else None,
            "created_at": h.created_at.isoformat() if h.created_at else None,
        })
    
    return {
        "group": group_dict,
        "members": members_list,
        "relationships": relationships_list,
        "history": history_list,
    }


async def list_correlation_groups(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    sector_id: str | None = None,
    camera_id: str | None = None,
) -> tuple[list, int]:
    """List correlation groups with pagination."""
    repo = CorrelationGroupRepository(session)
    groups, total = await repo.list_paginated(
        page=page,
        page_size=page_size,
        status=status,
        camera_id=camera_id,
        sector_id=sector_id,
    )
    
    # Convert groups to dicts
    groups_list = []
    for g in groups:
        groups_list.append({
            "correlation_id": g.correlation_id,
            "incident_id": g.incident_id,
            "primary_event_id": g.primary_event_id,
            "status": g.status,
            "state": g.state,
            "sector_id": g.sector_id,
            "region_profile": g.region_profile,
            "started_at": g.started_at.isoformat() if g.started_at else None,
            "ended_at": g.ended_at.isoformat() if g.ended_at else None,
            "event_count": g.event_count,
            "camera_count": g.camera_count,
            "zone_count": g.zone_count,
            "source_count": g.source_count,
            "confidence": g.confidence,
            "completeness": g.completeness,
            "updated_at": g.updated_at.isoformat() if g.updated_at else None,
            "created_at": g.created_at.isoformat() if g.created_at else None,
        })
    
    return groups_list, total