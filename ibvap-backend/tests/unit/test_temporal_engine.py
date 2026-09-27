"""Component 4 — Temporal Relation Engine Tests."""

from __future__ import annotations

import pytest
from datetime import datetime, timezone, timedelta

from app.domain.event_correlation.temporal_engine import (
    TemporalRelationEngine,
    TemporalEvent,
    TemporalRelationType,
    temporal_engine,
)


class TestTemporalRelationEngine:
    """Tests for temporal relation classification."""

    def test_same_timestamp(self):
        """Events with same timestamp are OVERLAP."""
        e1 = {"event_id": "e1", "event_time": datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)}
        e2 = {"event_id": "e2", "event_time": datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)}
        rel = temporal_engine.classify_relation(e1, e2)
        assert rel is not None
        assert rel["type"] == "TEMPORAL"
        assert rel["subtype"] == "OVERLAP"
        assert rel["confidence"] == 100

    def test_within_window_before(self):
        """Event before within window is ADJACENT."""
        e1 = {"event_id": "e1", "event_time": datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)}
        e2 = {"event_id": "e2", "event_time": datetime(2026, 1, 1, 12, 0, 30, tzinfo=timezone.utc)}
        rel = temporal_engine.classify_relation(e1, e2)
        assert rel is not None
        assert rel["subtype"] in ("OVERLAP", "ADJACENT")
        assert rel["confidence"] >= 50

    def test_outside_window(self):
        """Events outside window return None."""
        e1 = {"event_id": "e1", "event_time": datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)}
        e2 = {"event_id": "e2", "event_time": datetime(2026, 1, 1, 13, 0, 0, tzinfo=timezone.utc)}
        rel = temporal_engine.classify_relation(e1, e2)
        assert rel is None

    def test_distant_events(self):
        """Far apart events return None."""
        e1 = {"event_id": "e1", "event_time": datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)}
        e2 = {"event_id": "e2", "event_time": datetime(2026, 1, 2, 12, 0, 0, tzinfo=timezone.utc)}
        rel = temporal_engine.classify_relation(e1, e2)
        assert rel is None

    def test_confidence_decay(self):
        """Confidence decays with time distance."""
        base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        e1 = {"event_id": "e1", "event_time": base}
        e2 = {"event_id": "e2", "event_time": base + timedelta(seconds=10)}
        e3 = {"event_id": "e3", "event_time": base + timedelta(seconds=30)}

        rel1 = temporal_engine.classify_relation(e1, e2)
        rel2 = temporal_engine.classify_relation(e1, e3)
        assert rel1 is not None and rel2 is not None
        assert rel1["confidence"] > rel2["confidence"]

    def test_custom_window(self):
        """Custom window parameter is respected."""
        e1 = {"event_id": "e1", "event_time": datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)}
        e2 = {"event_id": "e2", "event_time": datetime(2026, 1, 1, 12, 10, 0, tzinfo=timezone.utc)}
        
        # Default window (60s) - too far
        rel = temporal_engine.classify_relation(e1, e2)
        assert rel is None
        
        # Custom engine with larger window
        custom_engine = TemporalRelationEngine(default_window_seconds=7200)
        rel2 = custom_engine.classify_relation(e1, e2)
        assert rel2 is not None

    def test_engine_singleton(self):
        """Singleton engine instance exists."""
        assert temporal_engine is not None
        assert isinstance(temporal_engine, TemporalRelationEngine)


class TestTemporalEvent:
    """Tests for TemporalEvent dataclass."""

    def test_creation_point_event(self):
        """Create point event."""
        e = TemporalEvent(
            event_id="e1",
            start_time=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
        )
        assert e.event_id == "e1"
        assert e.event_type == "POINT"

    def test_creation_duration_event(self):
        """Create duration event."""
        e = TemporalEvent(
            event_id="e1",
            start_time=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            end_time=datetime(2026, 1, 1, 12, 5, 0, tzinfo=timezone.utc),
        )
        assert e.end_time is not None

    def test_with_camera(self):
        """Create event with camera_id."""
        e = TemporalEvent(
            event_id="e1",
            start_time=datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc),
            camera_id="CAM-01",
        )
        assert e.camera_id == "CAM-01"


class TestTemporalRelationType:
    """Tests for TemporalRelationType enum."""

    def test_values(self):
        """All expected values exist."""
        assert TemporalRelationType.OVERLAP == "OVERLAP"
        assert TemporalRelationType.BEFORE == "BEFORE"
        assert TemporalRelationType.AFTER == "AFTER"
        assert TemporalRelationType.CONTAINS == "CONTAINS"
        assert TemporalRelationType.WITHIN == "WITHIN"
        assert TemporalRelationType.ADJACENT == "ADJACENT"
        assert TemporalRelationType.NONE == "NONE"