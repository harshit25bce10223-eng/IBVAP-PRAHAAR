# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 4 — Temporal Relation Engine
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any


class TemporalRelationType(str):
    OVERLAP = "OVERLAP"
    BEFORE = "BEFORE"
    AFTER = "AFTER"
    CONTAINS = "CONTAINS"
    WITHIN = "WITHIN"
    ADJACENT = "ADJACENT"
    NONE = "NONE"


class TemporalEventType(str):
    POINT = "POINT"
    DURATION = "DURATION"


@dataclass
class TemporalEvent:
    event_id: str
    start_time: datetime
    end_time: datetime | None = None
    event_type: TemporalEventType = TemporalEventType.POINT
    camera_id: str | None = None
    zone_id: str | None = None
    source: str | None = None


@dataclass
class TemporalRelation:
    from_event_id: str
    to_event_id: str
    relation_type: str
    temporal_distance_seconds: float | None
    overlap_seconds: float | None
    confidence: int
    evidence: dict | None = None


class TemporalRelationEngine:
    """
    Determines temporal relationships between events.
    
    Supports:
    - Point events (instant timestamps)
    - Duration events (start + end time)
    - Configurable temporal windows
    - Clock skew tolerance
    """

    def __init__(
        self,
        default_window_seconds: int = 60,
        clock_skew_tolerance_seconds: int = 5,
        max_group_duration_seconds: int = 300,
    ):
        self.default_window = default_window_seconds
        self.clock_skew_tolerance = clock_skew_tolerance_seconds
        self.max_group_duration = max_group_duration_seconds

    def _get_event_bounds(self, event: dict) -> tuple[datetime, datetime | None]:
        """Extract start and end time from event data."""
        event_time = event.get("event_time") or event.get("ts") or event.get("timestamp")
        if isinstance(event_time, str):
            event_time = datetime.fromisoformat(event_time.replace("Z", "+00:00"))
        if event_time is not None and event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=timezone.utc)

        end_time = event.get("end_time")
        if end_time and isinstance(end_time, str):
            end_time = datetime.fromisoformat(end_time.replace("Z", "+00:00"))
        if end_time is not None and end_time.tzinfo is None:
            end_time = end_time.replace(tzinfo=timezone.utc)

        return event_time, end_time

    def classify_relation(
        self,
        event_a: dict,
        event_b: dict,
        window_seconds: int | None = None,
    ) -> dict | None:
        """
        Classify the temporal relationship between two events.

        Correlation uses the events' observed timestamps, not arrival order.
        Returns None if no temporal relationship exists within the configured window.
        """
        window = window_seconds or self.default_window

        start_a, end_a = self._get_event_bounds(event_a)
        start_b, end_b = self._get_event_bounds(event_b)

        if start_a is None or start_b is None:
            return None

        # Apply clock skew tolerance
        skew = self.clock_skew_tolerance

        # Both point events
        if not end_a and not end_b:
            delta = abs((start_a - start_b).total_seconds())
            if delta <= window + 2 * skew:
                return {
                    "type": "TEMPORAL",
                    "subtype": "ADJACENT" if delta > skew else "OVERLAP",
                    "time_diff_seconds": delta,
                    "confidence": max(0, 100 - int(delta / window * 100)),
                }
            return None

        # One or both have duration
        start_a_eff = start_a
        end_a_eff = end_a or start_a
        start_b_eff = start_b
        end_b_eff = end_b or start_b

        # Check overlap
        overlap_start = max(start_a_eff, start_b_eff)
        overlap_end = min(end_a_eff, end_b_eff)

        if overlap_start <= end_b_eff + timedelta(seconds=self.clock_skew_tolerance) and \
           overlap_end >= start_b_eff - timedelta(seconds=self.clock_skew_tolerance):
            overlap_seconds = max(0, (overlap_end - overlap_start).total_seconds())
            return {
                "type": "TEMPORAL",
                "subtype": "OVERLAP",
                "overlap_seconds": overlap_seconds,
                "confidence": min(100, int(overlap_seconds / max(1, (end_a_eff - start_a_eff).total_seconds()) * 100)),
            }

        # Check containment
        if start_a_eff <= start_b_eff and end_a_eff >= end_b_eff:
            return {
                "type": "TEMPORAL",
                "subtype": "CONTAINS",
                "confidence": 80,
            }
        if start_b_eff <= start_a_eff and end_b_eff >= end_a_eff:
            return {
                "type": "TEMPORAL",
                "subtype": "WITHIN",
                "confidence": 80,
            }

        # Check adjacency (close in time but no overlap) within the configured window
        gap_after_a = (start_b - end_a_eff).total_seconds() if end_a_eff < start_b else 0
        gap_after_b = (start_a - end_b_eff).total_seconds() if end_b_eff < start_a else 0

        min_gap = min(gap_after_a, gap_after_b) if gap_after_a > 0 and gap_after_b > 0 else max(gap_after_a, gap_after_b)

        if 0 < min_gap <= window + 2 * skew:
            return {
                "type": "TEMPORAL",
                "subtype": "ADJACENT",
                "time_diff_seconds": min_gap,
                "confidence": max(0, 100 - int(min_gap / window * 100)),
            }

        return None

    def find_candidates(
        self, 
        target_event: dict, 
        candidate_events: list[dict],
        window_seconds: int | None = None,
    ) -> list[dict]:
        """Find candidate events that could be temporally related to target."""
        window = window_seconds or self.default_window

        candidates = []
        for event in candidate_events:
            if event.get("event_id") == target_event.get("event_id"):
                continue
            relation = self.classify_relation(target_event, event, window_seconds=window)
            if relation and relation.get("confidence", 0) > 0:
                relation["to_event_id"] = event.get("event_id")
                relation["from_event_id"] = target_event.get("event_id")
                candidates.append(relation)
        
        return sorted(candidates, key=lambda x: -x.get("confidence", 0))

    def is_within_group_window(self, group_start: datetime, event_time: datetime, max_duration: int | None = None) -> bool:
        """Check if an event falls within the group's time window."""
        max_duration = max_duration or self.max_group_duration
        if isinstance(group_start, str):
            group_start = datetime.fromisoformat(group_start.replace("Z", "+00:00"))
        if isinstance(event_time, str):
            event_time = datetime.fromisoformat(event_time.replace("Z", "+00:00"))
        if group_start is None or event_time is None:
            return False
        if group_start.tzinfo is None:
            group_start = group_start.replace(tzinfo=timezone.utc)
        if event_time.tzinfo is None:
            event_time = event_time.replace(tzinfo=timezone.utc)
        return abs((event_time - group_start).total_seconds()) <= max_duration


# Global instance
temporal_engine = TemporalRelationEngine()