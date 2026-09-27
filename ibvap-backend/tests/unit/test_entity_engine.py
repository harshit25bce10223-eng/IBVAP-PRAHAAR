"""Component 4 — Entity Relation Engine Tests."""

from __future__ import annotations

import pytest

from app.domain.event_correlation.entity_engine import (
    EntityRelationEngine,
    EntityRelation,
    ReIDCandidate,
    entity_engine,
)


class TestEntityRelationEngine:
    """Tests for entity relation classification."""

    def test_same_track_id(self):
        """Same track_id = SAME_TRACK."""
        e1 = {"track_id": "TRK-001", "event_id": "e1"}
        e2 = {"track_id": "TRK-001", "event_id": "e2"}
        rel = entity_engine.classify_relation(e1, e2)
        assert rel is not None
        assert rel["type"] == "ENTITY"
        assert rel["subtype"] == "SAME_TRACK"
        assert rel["strength"] == 100

    def test_different_track_id(self):
        """Different track_id = no relation."""
        e1 = {"track_id": "TRK-001", "event_id": "e1"}
        e2 = {"track_id": "TRK-002", "event_id": "e2"}
        rel = entity_engine.classify_relation(e1, e2)
        assert rel is None

    def test_reid_candidate(self):
        """Re-ID candidate creates REID_CANDIDATE."""
        e1 = {"track_id": "TRK-001", "event_id": "e1", "reid_candidate": {"candidate_id": "REID-001", "confidence": 0.85}}
        e2 = {"track_id": "TRK-002", "event_id": "e2", "reid_candidate": {"candidate_id": "REID-001", "confidence": 0.9}}
        rel = entity_engine.classify_relation(e1, e2)
        assert rel is not None
        assert rel["subtype"] == "REID_CANDIDATE"
        assert rel["strength"] >= 70

    def test_reid_below_threshold(self):
        """Re-ID below threshold = no relation."""
        e1 = {"track_id": "TRK-001", "event_id": "e1", "reid_candidate": {"candidate_id": "REID-001", "confidence": 0.5}}
        e2 = {"track_id": "TRK-002", "event_id": "e2", "reid_candidate": {"candidate_id": "REID-001", "confidence": 0.6}}
        rel = entity_engine.classify_relation(e1, e2)
        assert rel is None

    def test_no_track_info(self):
        """Missing track info = no relation."""
        e1 = {"event_id": "e1"}
        e2 = {"event_id": "e2"}
        rel = entity_engine.classify_relation(e1, e2)
        assert rel is None

    def test_partial_track_info(self):
        """One with track, one without = no relation."""
        e1 = {"track_id": "TRK-001", "event_id": "e1"}
        e2 = {"event_id": "e2"}
        rel = entity_engine.classify_relation(e1, e2)
        assert rel is None

    def test_engine_singleton(self):
        """Singleton engine instance exists."""
        assert entity_engine is not None
        assert isinstance(entity_engine, EntityRelationEngine)


class TestReIDCandidate:
    """Tests for ReIDCandidate dataclass."""

    def test_creation(self):
        """Create Re-ID candidate."""
        c = ReIDCandidate(
            track_id="TRK-001",
            similarity=0.85,
            camera_id="CAM-01",
            timestamp="2026-01-01T12:00:00Z",
        )
        assert c.track_id == "TRK-001"
        assert c.similarity == 0.85


class TestEntityRelation:
    """Tests for EntityRelation dataclass."""

    def test_fields(self):
        """Relation has required fields."""
        rel = EntityRelation(
            from_event_id="e1",
            to_event_id="e2",
            relation_type="ENTITY",
            strength=100,
            evidence={"track_id": "TRK-001"},
        )
        assert rel.from_event_id == "e1"
        assert rel.to_event_id == "e2"
        assert rel.relation_type == "ENTITY"
        assert rel.strength == 100