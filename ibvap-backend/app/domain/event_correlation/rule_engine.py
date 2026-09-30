# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 4 — Correlation Rule Engine
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from app.domain.event_correlation.temporal_engine import TemporalRelationEngine
from app.domain.event_correlation.spatial_engine import SpatialRelationEngine
from app.domain.event_correlation.entity_engine import EntityRelationEngine
from app.domain.event_correlation.compatibility import (
    get_compatibility,
    DEFAULT_COMPATIBILITY_MATRIX,
)

UNKNOWN_TOKEN = "UNKNOWN"


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


def _to_aware(value: Any) -> datetime | None:
    """Normalize a datetime (str, naive, aware) to an aware UTC datetime.

    Aware values from any offset are converted to UTC (not just re-labelled):
    aiosqlite stores wall-clock strings and drops tzinfo, so comparisons against
    values re-read from the database are only correct in UTC.
    """
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    return None


class CorrelationRuleEngine:
    """
    Orchestrates the correlation process by combining signals from temporal,
    spatial, and entity engines.

    Scoring is gated: a genuinely-correlated relationship must satisfy the
    temporal window AND share at least one spatial or entity overlap. Mere
    simultaneity across unrelated sectors is NOT a correlation.
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

    # ─────────────────────────────────────────────────────────────────────────
    # Main entry point
    # ─────────────────────────────────────────────────────────────────────────

    def evaluate_event(self, event: dict, existing_groups: list[dict]) -> CorrelationResult:
        """Evaluate an incoming event against existing correlation groups."""
        candidates = self.find_candidate_groups(event, existing_groups)

        if not candidates:
            return CorrelationResult(
                group_id=None,
                status="STANDALONE",
                action="CREATED",
                revision=1,
                reason="No candidate groups within temporal/spatial/source coverage",
            )

        best = candidates[0]
        score = best["score"]
        group = best["group_data"]

        if score >= self.min_correlation_score:
            relationships = self.build_relationships(event, group)
            support = len(group.get("member_events") or []) + 1
            if support < self.min_support_events:
                status = "UNCERTAIN"
                reason = (
                    f"Joined {group.get('correlation_id')} (score {score}) but only "
                    f"{support} supporting events (minimum {self.min_support_events}); "
                    f"correlation held provisional"
                )
            else:
                status = "CORRELATED" if score >= 70 else "RELATED"
                reason = (
                    f"Correlated with {group.get('correlation_id')} "
                    f"(score {score}): {self._reason_summary(relationships)}"
                )
            completeness = "COMPLETE" if len(relationships) >= 2 else "PARTIAL"
            return CorrelationResult(
                group_id=group.get("correlation_id"),
                status=status,
                action="UPDATED",
                revision=int(group.get("revision", 0)) + 1,
                relationships=relationships,
                confidence=score,
                completeness=completeness,
                reason=reason,
            )

        return CorrelationResult(
            group_id=None,
            status="STANDALONE",
            action="CREATED",
            revision=1,
            reason=f"Best candidate score {score} below threshold {self.min_correlation_score}",
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Candidate selection
    # ─────────────────────────────────────────────────────────────────────────

    def find_candidate_groups(self, event: dict, existing_groups: list[dict]) -> list[dict]:
        """Find existing correlation groups that could be related to this event."""
        candidates = []
        for group in existing_groups:
            if not isinstance(group, dict) or not group.get("correlation_id"):
                continue

            temporal = self._temporal_vs_group(event, group)
            if not temporal:
                continue

            if self._exceeds_max_duration(event, group):
                continue

            if not self._spatially_compatible(event, group):
                continue

            if not self._source_compatible(event, group):
                continue

            score = self._score_group_match(event, group, temporal)
            if score >= 30:
                candidates.append({
                    "group_id": group.get("correlation_id"),
                    "group_data": group,
                    "score": score,
                })

        return sorted(candidates, key=lambda x: -x["score"])

    def _temporal_vs_group(self, event: dict, group: dict) -> dict | None:
        """Classify the event against the group's observed time span.

        Correlation is based on observed time, not arrival order, so an event
        that falls anywhere inside (or adjacent to) the group's span is a
        candidate even when it arrives out of order.
        """
        anchor = {"event_id": group.get("correlation_id")}
        bounds = _to_aware(group.get("started_at")), _to_aware(group.get("ended_at"))
        best: dict | None = None
        for bound in bounds:
            if bound is None:
                continue
            anchor["event_time"] = bound
            rel = self.temporal.classify_relation(event, anchor, window_seconds=self.temporal_window)
            if rel:
                if best is None or rel.get("confidence", 0) > best.get("confidence", 0):
                    best = rel
        return best

    def _exceeds_max_duration(self, event: dict, group: dict) -> bool:
        """True when joining this event would extend the group's observed span
        beyond the configured maximum situation duration. Such events start a
        separate situation instead of chaining one group forever.
        """
        if not self.max_group_duration:
            return False
        started = _to_aware(group.get("started_at"))
        latest = _to_aware(group.get("ended_at"))
        event_time = _to_aware(event.get("event_time"))
        if started is None or event_time is None:
            return False
        lower = min(started, event_time)
        upper = max(latest or started, event_time)
        return (upper - lower).total_seconds() > self.max_group_duration

    def _spatially_compatible(self, event: dict, group: dict) -> bool:
        """Block candidate groups that share no spatial overlap with the event.

        When either side has no spatial context, the gate is not enforced
        (temporal + source + entity signals decide).
        """
        cam = event.get("camera_id")
        cams = group.get("camera_ids") or []
        zone = event.get("zone_id")
        zones = group.get("zone_ids") or []
        sector = event.get("sector_id")
        sectors = group.get("sector_ids") or []

        has_event = any(bool(v) and str(v) != UNKNOWN_TOKEN for v in (cam, zone, sector))
        has_group = any(bool(v) and str(v) != UNKNOWN_TOKEN for v in (cams, zones, sectors))
        if not has_event or not has_group:
            return True

        if cam and cam != UNKNOWN_TOKEN and cam in cams:
            return True
        if cam and cam != UNKNOWN_TOKEN and self._adjacent_to_group(cam, cams):
            return True
        if zone and zone != UNKNOWN_TOKEN and zone in zones:
            return True
        if sector and sector != UNKNOWN_TOKEN and sector in sectors:
            return True
        return False

    def _source_compatible(self, event: dict, group: dict) -> bool:
        """Check if event source is compatible with group sources.

        Unknown sources are treated as neutral (never hard-blocked); known
        incompatible pairs (e.g. CAMERA_HEALTH x DETECTION) are blocked.
        """
        group_sources = group.get("sources") or []
        if not group_sources:
            return True
        event_source = event.get("source", "UNKNOWN")
        for group_source in group_sources:
            if event_source not in DEFAULT_COMPATIBILITY_MATRIX:
                return True
            if group_source not in DEFAULT_COMPATIBILITY_MATRIX:
                return True
            if get_compatibility(event_source, group_source) >= 30:
                return True
        return False

    # ─────────────────────────────────────────────────────────────────────────
    # Scoring
    # ─────────────────────────────────────────────────────────────────────────

    def _score_group_match(self, event: dict, group: dict, temporal_rel: dict | None = None) -> int:
        """Score how well an event matches an existing group."""
        temporal = temporal_rel or self._temporal_vs_group(event, group)
        if not temporal:
            return 0

        temporal_score = temporal.get("confidence", 0)
        spatial_score = self._spatial_score_vs_group(event, group)
        entity_score = self._entity_score_vs_group(event, group)

        # Gate: temporal proximity alone is never a correlation.
        if spatial_score == 0 and entity_score == 0:
            return 0

        compat_score = self._compatibility_score(event, group)
        score = 0.45 * temporal_score + 0.30 * spatial_score + 0.15 * entity_score + 0.10 * compat_score
        return int(score)

    def _spatial_score_vs_group(self, event: dict, group: dict) -> int:
        """Score spatial overlap between event and group aggregates."""
        cam = event.get("camera_id")
        cams = group.get("camera_ids") or []
        zone = event.get("zone_id")
        zones = group.get("zone_ids") or []
        sector = event.get("sector_id")
        sectors = group.get("sector_ids") or []

        if cam and cam != UNKNOWN_TOKEN and cam in cams:
            return 100
        if zone and zone != UNKNOWN_TOKEN and zone in zones:
            return 90
        if sector and sector != UNKNOWN_TOKEN and sector in sectors:
            return 60
        if cam and cam != UNKNOWN_TOKEN and self._adjacent_to_group(cam, cams):
            return 60
        return 0

    def _entity_score_vs_group(self, event: dict, group: dict) -> int:
        """Score entity continuity (track / Re-ID) with the group."""
        track = event.get("track_id")
        tracks = group.get("track_ids") or []
        if track and track != UNKNOWN_TOKEN and track in tracks:
            return 100
        reid = event.get("reid_candidate") or {}
        candidate_track = reid.get("track_id") or reid.get("candidate_id")
        if candidate_track and candidate_track in tracks:
            return 80
        return 0

    def _compatibility_score(self, event: dict, group: dict) -> int:
        """Score based on source compatibility."""
        group_sources = group.get("sources") or []
        if not group_sources:
            return 50
        event_source = event.get("source", "UNKNOWN")
        if event_source not in DEFAULT_COMPATIBILITY_MATRIX:
            return 50
        scores = []
        for src in group_sources:
            if src not in DEFAULT_COMPATIBILITY_MATRIX:
                return 50
            scores.append(get_compatibility(event_source, src))
        return max(scores)

    def _adjacent_to_group(self, camera_id: str, group_cameras: list) -> bool:
        """Check if a camera is adjacent (per topology) to any group camera."""
        adjacency = getattr(self.spatial, "camera_adjacency", {}) or {}
        for cam in group_cameras:
            if camera_id in adjacency.get(cam, []) or cam in adjacency.get(camera_id, []):
                return True
        return False

    # ─────────────────────────────────────────────────────────────────────────
    # Relationship construction
    # ─────────────────────────────────────────────────────────────────────────

    def build_relationships(self, event: dict, group: dict) -> list[dict]:
        """Build concrete relationships between the event and group members.

        Every relationship carries a real explanation, so operators can see
        WHY two events were linked.
        """
        relationships: list[dict] = []
        seen: set[tuple[str, str]] = set()
        event_id = event.get("event_id")

        members = group.get("member_events") or []
        if len(members) > self.max_group_size:
            members = members[-self.max_group_size:]

        for member in members:
            member_id = member.get("event_id")
            if not member_id or member_id == event_id:
                continue

            temporal = self.temporal.classify_relation(event, member, window_seconds=self.temporal_window)
            if temporal:
                key = (member_id, "TEMPORAL")
                if key not in seen:
                    seen.add(key)
                    relationships.append({
                        "from_event_id": event_id,
                        "to_event_id": member_id,
                        "type": "TEMPORAL",
                        "subtype": temporal.get("subtype"),
                        "strength": temporal.get("confidence"),
                        "evidence": temporal,
                        "explanation": self._explain("TEMPORAL", event, member, temporal),
                    })

            spatial = self.spatial.classify_relation(event, member)
            if spatial:
                key = (member_id, "SPATIAL")
                if key not in seen:
                    seen.add(key)
                    relationships.append({
                        "from_event_id": event_id,
                        "to_event_id": member_id,
                        "type": "SPATIAL",
                        "subtype": spatial.get("subtype"),
                        "strength": spatial.get("confidence"),
                        "evidence": spatial,
                        "explanation": self._explain("SPATIAL", event, member, spatial),
                    })

            entity = self.entity.classify_relation(event, member)
            if entity:
                key = (member_id, "ENTITY")
                if key not in seen:
                    seen.add(key)
                    relationships.append({
                        "from_event_id": event_id,
                        "to_event_id": member_id,
                        "type": "ENTITY",
                        "subtype": entity.get("subtype"),
                        "strength": entity.get("strength"),
                        "evidence": entity,
                        "explanation": self._explain("ENTITY", event, member, entity),
                    })

        return relationships

    @staticmethod
    def _explain(rel_type: str, event: dict, member: dict, rel: dict) -> str:
        """Build a human-readable explanation for a relationship."""
        event_id = event.get("event_id", "?")
        member_id = member.get("event_id", "?")
        if rel_type == "TEMPORAL":
            delta = rel.get("time_diff_seconds")
            delta_txt = f"{delta:.1f}s apart" if delta is not None else "overlapping in time"
            return (
                f"Event {event_id} and {member_id} are {delta_txt} "
                f"(TEMPORAL {rel.get('subtype')}, confidence {rel.get('confidence')})"
            )
        if rel_type == "SPATIAL":
            subtype = rel.get("subtype")
            evidence = rel.get("evidence") or {}
            if subtype == "SAME_CAMERA":
                return f"Both events observed by camera {evidence.get('camera_id')}"
            if subtype == "SAME_ZONE":
                return f"Both events inside zone {evidence.get('zone_id')}"
            if subtype == "SAME_SECTOR":
                return f"Both events inside sector {evidence.get('sector_id')}"
            if subtype == "ADJACENT_CAMERA":
                return (
                    f"Events on adjacent cameras {evidence.get('camera_a')} / "
                    f"{evidence.get('camera_b')} (POSSIBLE CONTINUATION)"
                )
            distance = rel.get("distance_meters")
            if distance is not None:
                return f"Events within {distance:.0f}m of each other"
            return f"Spatial relation {subtype}"
        if rel_type == "ENTITY":
            subtype = rel.get("subtype")
            evidence = rel.get("evidence") or {}
            if subtype == "SAME_TRACK":
                return f"Same track {evidence.get('track_id')} across both events"
            similarity = evidence.get("similarity")
            return (
                f"Re-ID candidate {evidence.get('candidate_id')} "
                f"(similarity {similarity:.0%}) links the events"
            )
        return f"Related to {member_id}"

    def _reason_summary(self, relationships: list[dict]) -> str:
        if not relationships:
            return "no explicit relations"
        types = sorted({rel["type"] for rel in relationships})
        return f"{len(relationships)} explicit relations ({', '.join(types)})"


# Global rule engine instance
rule_engine = CorrelationRuleEngine()