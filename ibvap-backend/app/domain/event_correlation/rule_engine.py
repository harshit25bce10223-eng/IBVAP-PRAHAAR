# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 4 — Correlation Rule Engine
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from app.domain.event_correlation.temporal_engine import temporal_engine, TemporalRelationEngine
from app.domain.event_correlation.spatial_engine import spatial_engine, SpatialRelationEngine
from app.domain.event_correlation.entity_engine import entity_engine, EntityRelationEngine
from app.domain.event_correlation.compatibility import (
    get_compatibility,
    get_event_type_compatibility,
    DEFAULT_COMPATIBILITY_MATRIX,
)
from app.models.event_correlation import (
    CorrelationGroup,
    CorrelationGroupMember,
    CorrelationRelationship,
    CorrelationHistory,
    CorrelationGroupMember as CorrelationGroupMemberModel,
    CorrelationRelationship as CorrelationRelationshipModel,
    CorrelationHistory as CorrelationHistoryModel,
)
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timedelta
from typing import Any

# ─────────────────────────────────────────────────────────────────────────────
# Data Classes
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class CorrelationCandidate:
    event_id: str
    event_data: dict
    existing_group_id: str | None = None
    temporal_relations: list[dict] = field(default_factory=list)
    spatial_relations: list[dict] = field(default_factory=list)
    entity_relations: list[dict] = field(default_factory=list)
    compatibility_score: int = 0


@dataclass
class CorrelationResult:
    group_id: str | None = None
    status: str = "STANDALONE"
    action: str = "CREATED"
    revision: int = 1
    relationships: list[dict] = field(default_factory=list)
    confidence: int | None = None
    completeness: str = "UNKNOWN"
    reason: str = ""


# ─────────────────────────────────────────────────────────────────────────────
# Correlation Rule Engine
# ─────────────────────────────────────────────────────────────────────────────

class CorrelationRuleEngine:
    """
    Orchestrates the correlation process by combining signals from
    temporal, spatial, and entity engines.
    """

    def __init__(
        self,
        temporal_engine: Any = None,
        spatial_engine: Any = None,
        entity_engine: Any = None,
        config: dict | None = None,
    ):
        self.temporal = temporal_engine or TemporalRelationEngine()
        self.spatial = spatial_engine or SpatialRelationEngine()
        self.entity = entity_engine or EntityRelationEngine()
        
        # Configuration
        self.config = config or {}
        self.min_correlation_score = self.config.get("min_correlation_score", 50)
        self.min_support_events = self.config.get("min_support_events", 1)
        self.max_group_duration = self.config.get("max_group_duration_seconds", 300)
        self.temporal_window = self.config.get("temporal_window_seconds", 60)
        self.max_group_size = self.config.get("max_group_size", 50)

    def _calculate_compatibility(self, event_a: dict, event_b: dict) -> int:
        """Calculate overall compatibility score between two events."""
        source_a = event_a.get("source", "UNKNOWN")
        source_b = event_b.get("source", "UNKNOWN")
        type_a = event_a.get("event_type") or event_a.get("kind", "UNKNOWN")
        type_b = event_b.get("event_type") or event_b.get("kind", "UNKNOWN")

        # Source compatibility
        source_score = 0
        if hasattr(self, 'compatibility_matrix'):
            source_score = self.compatibility_matrix.get(source_a, {}).get(source_b, 20)
        else:
            from app.domain.event_correlation.compatibility import get_compatibility
            source_score = get_compatibility(source_a, source_b)

        # Event type compatibility
        type_score = 0
        if hasattr(event_a, 'get') and hasattr(event_b, 'get'):
            type_a = event_a.get("event_type") or event_a.get("kind", "UNKNOWN")
            type_b = event_b.get("event_type") or event_b.get("kind", "UNKNOWN")
            type_score = get_event_type_compatibility(type_a, type_b)

        # Weighted combination
        return int(source_score * 0.4 + type_score * 0.6)

    def evaluate_event(self, event: dict, existing_groups: list[dict]) -> dict:
        """
        Evaluate an incoming event against existing correlation groups.
        
        Returns a CorrelationResult indicating the action to take.
        """
        # Find candidate groups
        candidates = self.find_candidate_groups(event, existing_groups)
        
        if not candidates:
            return CorrelationResult(
                group_id=None,
                status="STANDALONE",
                action="CREATED",
                reason="No correlation candidates found",
            )

        # Evaluate each candidate
        best_candidate = None
        best_score = 0
        
        for candidate in candidates:
            score = self.score_candidate(target_event, candidate)
            if score > best_score:
                best_score = score
                best_candidate = candidate

        if best_score >= self.min_correlation_score and best_candidate:
            return CorrelationResult(
                group_id=best_candidate["group_id"],
                status="CORRELATED",
                action="UPDATED",
                relationships=self.build_relationships(target_event, best_candidate),
                confidence=best_score,
                completeness="COMPLETE",
                reason=f"Correlated with group {best_candidate['group_id']} (score: {best_score})",
            )

        return CorrelationResult(
            group_id=None,
            status="STANDALONE",
            action="CREATED",
            reason="No sufficient correlation found",
        )

    def find_candidate_groups(self, event: dict, existing_groups: list[dict]) -> list[dict]:
        """Find existing correlation groups that could be related to this event."""
        candidates = []
        
        for group in existing_groups:
            # Check temporal proximity
            group_start = group.get("started_at")
            event_time = event.get("event_time") or event.get("ts")
            
            if group_start and event_time:
                time_diff = abs((event_time - group_start).total_seconds())
                if time_diff > 300:  # max_group_duration
                    continue

            # Check spatial overlap
            if not self._spatially_compatible(event, group):
                continue

            # Check source compatibility
            if not self._source_compatible(event, group):
                continue

            # Score this group
            score = self._score_group_match(event, group)
            if score >= 30:  # Minimum threshold for consideration
                candidates.append({
                    "group_id": group.get("correlation_id"),
                    "group_data": group,
                    "score": score,
                })

        return sorted(candidates, key=lambda x: -x["score"])

    def _spatially_compatible(self, event: dict, group: dict) -> bool:
        """Check if event is spatially compatible with group."""
        # Same sector
        event_sector = event.get("sector_id")
        group_sector = group.get("sector_id")
        if event_sector and group_sector and event_sector == group_sector:
            return True
        
        # Same camera
        event_cam = event.get("camera_id")
        group_cameras = group.get("camera_ids", [])
        if event_cam and event_cam in group_cameras:
            return True

        # Adjacent cameras
        event_cam = event.get("camera_id")
        group_cameras = group.get("camera_ids", [])
        for cam in group_cameras:
            # Would check camera adjacency here
            pass

        return True  # Default to compatible for now

    def _source_compatible(self, event: dict, group: dict) -> bool:
        """Check if event source is compatible with group sources."""
        event_source = event.get("source", "UNKNOWN")
        group_sources = group.get("sources", [])
        
        if not group_sources:
            return True
        
        # Check compatibility matrix
        for group_source in group_sources:
            score = get_compatibility(event.get("source", "UNKNOWN"), group_source)
            if score >= 30:
                return True
        
        return False

    def _score_group_match(self, event: dict, group: dict) -> int:
        """Score how well an event matches an existing group."""
        score = 0
        
        # Temporal score
        temporal_score = self._temporal_score(event, group)
        score += temporal_score * 0.4
        
        # Spatial score
        spatial_score = self._spatial_score(event, group)
        score += spatial_score * 0.3
        
        # Entity score
        entity_score = self._entity_score(event, group)
        score += entity_score * 0.2
        
        # Compatibility score
        compat_score = self._compatibility_score(event, group)
        score += compat_score * 0.1
        
        return int(score)

    def _temporal_score(self, event: dict, group: dict) -> int:
        """Score based on temporal proximity to group."""
        group_start = group.get("started_at")
        event_time = event.get("event_time") or event.get("ts")
        
        if not group_start or not event_time:
            return 50
        
        if isinstance(group_start, str):
            group_start = datetime.fromisoformat(group_start.replace("Z", "+00:00"))
        if isinstance(event_time, str):
            event_time = datetime.fromisoformat(event_time.replace("Z", "+00:00"))
        
        diff = abs((event_time - group_start).total_seconds())
        if diff <= 60:
            return 100
        elif diff <= 300:
            return 70
        elif diff <= 600:
            return 40
        return 0

    def _spatial_score(self, event: dict, group: dict) -> int:
        """Score based on spatial compatibility."""
        score = 0
        
        # Same camera
        event_cam = event.get("camera_id")
        group_cameras = group.get("camera_ids", [])
        if event_cam and event_cam in group_cameras:
            score += 50
        
        # Same zone
        event_zone = event.get("zone_id")
        group_zones = group.get("zone_ids", [])
        if event_zone and event_zone in group_zones:
            score += 30
        
        # Same sector
        event_sector = event.get("sector_id")
        group_sector = group.get("sector_id")
        if event_sector and group_sector and event_sector == group_sector:
            score += 20
        
        return min(score, 100)

    def _entity_score(self, event: dict, group: dict) -> int:
        """Score based on entity continuity."""
        event_track = event.get("track_id")
        group_tracks = group.get("track_ids", [])
        
        if event_track and event_track in group_tracks:
            return 100
        
        # Check for Re-ID candidates
        reid = event.get("reid_candidate")
        if reid and reid.get("track_id") in group_tracks:
            return 80
        
        return 0

    def _compatibility_score(self, event: dict, group: dict) -> int:
        """Score based on source/type compatibility."""
        event_source = event.get("source", "UNKNOWN")
        group_sources = group.get("sources", [])
        
        if not group_sources:
            return 50
        
        max_score = 0
        for group_source in group_sources:
            score = get_compatibility(event.get("source", "UNKNOWN"), group_source)
            max_score = max(max_score, score)
        
        return max_score

    def build_relationships(self, event: dict, group: dict) -> list[dict]:
        """Build relationships between event and group members."""
        relationships = []
        
        # This would create relationships with existing group members
        # For now, return basic relationships
        return []


# Global rule engine instance
rule_engine = CorrelationRuleEngine()