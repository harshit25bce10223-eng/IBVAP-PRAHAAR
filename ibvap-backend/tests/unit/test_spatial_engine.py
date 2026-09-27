"""Component 4 — Spatial Relation Engine Tests."""

from __future__ import annotations

import pytest

from app.domain.event_correlation.spatial_engine import (
    SpatialRelationEngine,
    SpatialEvent,
    SpatialRelation,
    spatial_engine,
)


class TestSpatialRelationEngine:
    """Tests for spatial relation classification."""

    def test_same_camera(self):
        """Same camera = SAME_CAMERA."""
        e1 = {"event_id": "e1", "camera_id": "CAM-01"}
        e2 = {"event_id": "e2", "camera_id": "CAM-01"}
        rel = spatial_engine.classify_relation(e1, e2)
        assert rel is not None
        assert rel["type"] == "SPATIAL"
        assert rel["subtype"] == "SAME_CAMERA"
        assert rel["confidence"] == 100

    def test_same_zone(self):
        """Same zone = SAME_ZONE."""
        e1 = {"event_id": "e1", "camera_id": "CAM-01", "zone_id": "ZONE-A"}
        e2 = {"event_id": "e2", "camera_id": "CAM-02", "zone_id": "ZONE-A"}
        rel = spatial_engine.classify_relation(e1, e2)
        assert rel is not None
        assert rel["subtype"] == "SAME_ZONE"
        assert rel["confidence"] >= 70

    def test_same_sector(self):
        """Same sector = SAME_SECTOR."""
        e1 = {"event_id": "e1", "camera_id": "CAM-01", "sector_id": "SEC-1"}
        e2 = {"event_id": "e2", "camera_id": "CAM-02", "sector_id": "SEC-1"}
        rel = spatial_engine.classify_relation(e1, e2)
        assert rel is not None
        assert rel["subtype"] == "SAME_SECTOR"
        assert rel["confidence"] == 60

    def test_different_sector(self):
        """Different sector = no relation (None)."""
        e1 = {"event_id": "e1", "camera_id": "CAM-01", "sector_id": "SEC-1"}
        e2 = {"event_id": "e2", "camera_id": "CAM-02", "sector_id": "SEC-2"}
        rel = spatial_engine.classify_relation(e1, e2)
        # No camera, zone, or sector match - returns None
        assert rel is None

    def test_missing_zone_info(self):
        """Missing zone info - falls back to sector/camera."""
        e1 = {"event_id": "e1", "camera_id": "CAM-01", "sector_id": "SEC-1"}
        e2 = {"event_id": "e2", "camera_id": "CAM-02", "sector_id": "SEC-1"}
        rel = spatial_engine.classify_relation(e1, e2)
        assert rel is not None
        assert rel["subtype"] == "SAME_SECTOR"

    def test_engine_singleton(self):
        """Singleton engine instance exists."""
        assert spatial_engine is not None
        assert isinstance(spatial_engine, SpatialRelationEngine)


class TestSpatialEvent:
    """Tests for SpatialEvent dataclass."""

    def test_creation(self):
        """Create with required fields."""
        e = SpatialEvent(event_id="e1", camera_id="CAM-01", zone_id="ZONE-A", sector_id="SEC-1")
        assert e.event_id == "e1"
        assert e.camera_id == "CAM-01"
        assert e.zone_id == "ZONE-A"
        assert e.sector_id == "SEC-1"

    def test_optional_fields(self):
        """Optional fields can be None."""
        e = SpatialEvent(event_id="e1", camera_id=None, zone_id=None, sector_id="SEC-1")
        assert e.camera_id is None
        assert e.zone_id is None


class TestSpatialRelation:
    """Tests for SpatialRelation dataclass."""

    def test_fields(self):
        """Relation has required fields."""
        rel = SpatialRelation(
            from_event_id="e1",
            to_event_id="e2",
            relation_type="SAME_ZONE",
            confidence=90,
        )
        assert rel.from_event_id == "e1"
        assert rel.to_event_id == "e2"
        assert rel.relation_type == "SAME_ZONE"
        assert rel.confidence == 90