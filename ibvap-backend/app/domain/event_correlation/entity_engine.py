# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 4 — Entity Relationship Engine
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class EntityRelation:
    from_event_id: str
    to_event_id: str
    relation_type: str  # ENTITY
    strength: int
    evidence: dict | None = None
    reid_candidate_id: str | None = None
    reid_confidence: float | None = None


@dataclass
class ReIDCandidate:
    track_id: str
    similarity: float
    camera_id: str
    timestamp: str


class EntityRelationEngine:
    """
    Determines entity-based relationships between events.
    
    Supports:
    - Same track ID across events
    - Re-ID candidate matches
    - Track continuity across cameras
    """

    def __init__(
        self,
        min_reid_confidence: float = 0.7,
        track_continuity_window_seconds: int = 60,
    ):
        self.min_reid_confidence = min_reid_confidence
        self.track_continuity_window = track_continuity_window_seconds

    def classify_relation(self, event_a: dict, event_b: dict) -> dict | None:
        """
        Classify entity-based relationship between two events.
        """
        # Same track ID - strongest entity relationship
        track_a = event_a.get("track_id")
        track_b = event_b.get("track_id")
        
        if track_a and track_b and track_a == track_b:
            return {
                "type": "ENTITY",
                "subtype": "SAME_TRACK",
                "strength": 100,
                "evidence": {"track_id": track_a},
            }

        # Re-ID candidate
        reid_a = event_a.get("reid_candidate")
        reid_b = event_b.get("reid_candidate")
        
        if reid_a and reid_b:
            # Check if they reference the same candidate
            if reid_a.get("candidate_id") == reid_b.get("candidate_id"):
                confidence = min(
                    reid_a.get("confidence", 0),
                    reid_b.get("confidence", 0),
                )
                if confidence >= 0.7:  # min_reid_confidence
                    return {
                        "type": "ENTITY",
                        "subtype": "REID_CANDIDATE",
                        "strength": int(confidence * 100),
                        "evidence": {
                            "candidate_id": reid_a.get("candidate_id"),
                            "similarity": confidence,
                        },
                    }

        # Check track continuity (same track appearing in sequence)
        track_a = event_a.get("track_id")
        track_b = event_b.get("track_id")
        
        if track_a and track_b and track_a != track_b:
            # Could be same entity with different track IDs (e.g., re-identification)
            # This would require Re-ID which is handled above
            pass

        return None

    def find_candidates(
        self,
        target_event: dict,
        candidate_events: list[dict],
    ) -> list[dict]:
        """Find entity-related candidate events."""
        candidates = []
        
        for event in candidate_events:
            relation = self.classify_relation(target_event, event)
            if relation:
                relation["to_event_id"] = event.get("event_id")
                relation["from_event_id"] = target_event.get("event_id")
                candidates.append(relation)
        
        return sorted(candidates, key=lambda x: -x.get("strength", 0))

    def find_track_continuity(self, track_id: str, events: list[dict]) -> list[dict]:
        """Find all events belonging to the same track."""
        return [e for e in events if e.get("track_id") == track_id]

    def find_reid_matches(self, track_id: str, events: list[dict], min_confidence: float = 0.7) -> list[dict]:
        """Find Re-ID candidate matches for a track."""
        matches = []
        for event in events:
            reid = event.get("reid_candidate")
            if reid and reid.get("track_id") == track_id:
                if reid.get("confidence", 0) >= 0.7:
                    matches.append({
                        "event_id": event.get("event_id"),
                        "candidate_id": reid.get("candidate_id"),
                        "confidence": reid.get("confidence"),
                        "camera_id": event.get("camera_id"),
                    })
        return sorted(matches, key=lambda x: -x["confidence"])


# Global instance
entity_engine = EntityRelationEngine()