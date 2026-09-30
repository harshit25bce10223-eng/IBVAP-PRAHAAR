# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 5 — Detection API Tests
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from httpx import AsyncClient, ASGITransport

from app.main import app
from app.db.database import get_db_session


class TestDetectionAPI:
    """Tests for detection API endpoints."""

    @pytest.fixture
    def client(self, app):
        """Create test client."""
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    @pytest.mark.asyncio
    async def test_health_endpoint(self, client):
        """Health check works."""
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"

    @pytest.mark.asyncio
    async def test_create_detection_config(self, client):
        """Create detection config for a camera."""
        config_data = {
            "camera_id": "CAM-07",
            "provider": "demo",
            "model_name": "demo-detector",
            "model_version": "1.0",
            "source": "EDGE",
            "confidence_threshold": 0.3,
            "iou_threshold": 0.5,
            "max_detections": 100,
            "sample_rate": 1.0,
            "min_frame_interval_ms": 0,
            "nms_enabled": True,
            "clip_bbox": True,
            "queue_size_limit": 50,
            "enable_edge_sync": False,
            "sync_interval_sec": 60,
        }
        resp = await client.post("/api/v1/detections/config", json=config_data)
        assert resp.status_code == 200
        data = resp.json()
        assert data["camera_id"] == "CAM-07"
        assert data["provider"] == "demo"

    @pytest.mark.asyncio
    async def test_get_camera_detection_config(self, client):
        """Get detection config for a camera."""
        # Create config first
        config_data = {
            "camera_id": "CAM-08",
            "provider": "demo",
            "model_name": "demo-detector",
            "model_version": "1.0",
            "source": "EDGE",
            "confidence_threshold": 0.3,
            "iou_threshold": 0.5,
            "max_detections": 100,
            "sample_rate": 1.0,
            "min_frame_interval_ms": 0,
            "nms_enabled": True,
            "clip_bbox": True,
            "queue_size_limit": 50,
            "enable_edge_sync": False,
            "sync_interval_sec": 60,
        }
        await client.post("/api/v1/detections/config", json=config_data)
        
        resp = await client.get("/api/v1/detections/config/CAM-08")
        assert resp.status_code == 200
        data = resp.json()
        assert data["camera_id"] == "CAM-08"
        assert data["provider"] == "demo"

    @pytest.mark.asyncio
    async def test_update_detection_config(self, client):
        """Update detection config."""
        # Create config first
        config_data = {
            "camera_id": "CAM-09",
            "provider": "demo",
            "model_name": "demo-detector",
            "model_version": "1.0",
            "source": "EDGE",
            "confidence_threshold": 0.3,
        }
        await client.post("/api/v1/detections/config", json=config_data)
        
        # Update
        resp = await client.patch("/api/v1/detections/config/CAM-09", json={"confidence_threshold": 0.5})
        assert resp.status_code == 200
        data = resp.json()
        assert data["confidence_threshold"] == 0.5

    @pytest.mark.asyncio
    async def test_delete_detection_config(self, client):
        """Delete detection config."""
        # Create config first
        config_data = {
            "camera_id": "CAM-10",
            "provider": "demo",
            "model_name": "demo-detector",
        }
        await client.post("/api/v1/detections/config", json=config_data)
        
        # Delete
        resp = await client.delete("/api/v1/detections/config/CAM-10")
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

    @pytest.mark.asyncio
    async def test_list_detections(self, client):
        """List detections with pagination."""
        resp = await client.get("/api/v1/detections/", params={"page": 1, "page_size": 10})
        assert resp.status_code == 200
        data = resp.json()
        assert "detections" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data

    @pytest.mark.asyncio
    async def test_list_detections_with_filters(self, client):
        """List detections with filters."""
        resp = await client.get("/api/v1/detections/", params={
            "camera_id": "CAM-07",
            "class_name": "PERSON",
            "state": "DETECTED",
            "page": 1,
            "page_size": 20,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "detections" in data
        assert "total" in data

    @pytest.mark.asyncio
    async def test_get_recent_detections(self, client):
        """Get recent detections."""
        resp = await client.get("/api/v1/detections/recent", params={
            "hours": 24,
            "limit": 50,
        })
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_camera_detections(self, client):
        """Get detections for a specific camera."""
        resp = await client.get("/api/v1/detections/cameras/CAM-07", params={"limit": 10})
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_camera_detection_summary(self, client, db_session):
        """Get detection summary for a camera."""
        # First create camera config and some detections
        from app.repositories.detection import DetectionConfigRepository
        from app.models.detection import DetectionConfig, DetectionSource, Detection
        from datetime import datetime, timezone
        
        config_repo = DetectionConfigRepository(db_session)
        config = await config_repo.get_by_camera("CAM-07")
        if not config:
            config = await config_repo.create(
                camera_id="CAM-07",
                provider="demo",
                model_name="demo-detector",
                model_version="1.0",
                source="EDGE",
                confidence_threshold=0.3,
                iou_threshold=0.5,
                max_detections=100,
                sample_rate=1.0,
                min_frame_interval_ms=0,
                nms_enabled=True,
                clip_bbox=True,
                active=True,
            )
            await db_session.commit()
        
        # Add some detections with unique IDs
        unique_id = uuid4().hex[:8]
        det1 = Detection(
            detection_id=f"DET-SUM-{unique_id}-001",
            camera_id="CAM-07",
            frame_id="FRM-001",
            class_name="PERSON",
            class_id=0,
            taxonomy_version="1.0",
            confidence=0.9,
            quality_state="GOOD",
            occlusion_state="LOW",
            detection_state="DETECTED",
            bbox_x=0.1, bbox_y=0.1, bbox_width=0.3, bbox_height=0.3,
            frame_width=1280, frame_height=720,
            source="EDGE", provider="edge",
            model_name="demo-detector", model_version="1.0",
            schema_version="1.0",
            observed_at=datetime.now(timezone.utc),
            received_at=datetime.now(timezone.utc),
            processed_at=datetime.now(timezone.utc),
        )
        det2 = Detection(
            detection_id=f"DET-SUM-{unique_id}-002",
            camera_id="CAM-07",
            frame_id="FRM-002",
            class_name="VEHICLE",
            class_id=1,
            taxonomy_version="1.0",
            confidence=0.8,
            quality_state="GOOD",
            occlusion_state="LOW",
            detection_state="DETECTED",
            bbox_x=0.2, bbox_y=0.2, bbox_width=0.2, bbox_height=0.2,
            frame_width=1280, frame_height=720,
            source="EDGE", provider="edge",
            model_name="demo-detector", model_version="1.0",
            schema_version="1.0",
            observed_at=datetime.now(timezone.utc),
            received_at=datetime.now(timezone.utc),
            processed_at=datetime.now(timezone.utc),
        )
        db_session.add_all([det1, det2])
        await db_session.commit()
        
        resp = await client.get("/api/v1/detections/cameras/CAM-07/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["camera_id"] == "CAM-07"
        assert "total_detections" in data
        assert "by_class" in data

    @pytest.mark.asyncio
    async def test_get_detection_detail(self, client):
        """Get detection detail."""
        # First create a detection via internal service (or skip if none exist)
        resp = await client.get("/api/v1/detections/DET-NONEXISTENT")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_detections_by_event(self, client):
        """Get detections by event ID."""
        resp = await client.get("/api/v1/detections/events/EVT-NONEXISTENT")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_detections_by_track(self, client):
        """Get detections by track ID."""
        resp = await client.get("/api/v1/detections/tracks/TRK-NONEXISTENT")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_get_detections_by_incident(self, client):
        """Get detections by incident ID."""
        resp = await client.get("/api/v1/detections/incidents/INC-NONEXISTENT")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_inference_health(self, client):
        """Get inference health for all cameras."""
        resp = await client.get("/api/v1/detections/inference/health")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, dict)

    @pytest.mark.asyncio
    async def test_inference_health_for_camera(self, client):
        """Get inference health for specific camera."""
        resp = await client.get("/api/v1/detections/inference/health", params={"camera_id": "CAM-07"})
        # May 404 if no provider, or 200 with health data
        assert resp.status_code in (200, 404)

    @pytest.mark.asyncio
    async def test_inference_metrics(self, client):
        """Get inference metrics."""
        resp = await client.get("/api/v1/detections/inference/metrics", params={"hours": 24})
        assert resp.status_code == 200
        data = resp.json()
        assert "period_hours" in data
        assert "total_detections" in data
        assert "by_camera" in data
        assert "by_class" in data

    @pytest.mark.asyncio
    async def test_invalid_camera_id(self, client):
        """Invalid camera ID returns 404."""
        resp = await client.get("/api/v1/detections/cameras/CAM-NONEXISTENT/summary")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_invalid_confidence_filter(self, client):
        """Invalid confidence filter returns 422."""
        resp = await client.get("/api/v1/detections/", params={"min_confidence": 1.5})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_pagination(self, client):
        """Invalid pagination returns 422."""
        resp = await client.get("/api/v1/detections/", params={"page": 0})
        assert resp.status_code == 422
        
        resp = await client.get("/api/v1/detections/", params={"page_size": 500})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_sort(self, client):
        """Invalid sort field returns 422."""
        resp = await client.get("/api/v1/detections/", params={"sort": "invalid_field"})
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_invalid_date_range(self, client):
        """Invalid date range returns 422."""
        resp = await client.get("/api/v1/detections/", params={
            "from_time": "2026-01-15T10:00:00Z",
            "to_time": "2026-01-14T10:00:00Z",  # to_time before from_time
        })
        assert resp.status_code == 422


class TestDetectionAPIIntegration:
    """Integration tests using actual database."""

    @pytest.fixture
    def client(self, app):
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    @pytest.mark.asyncio
    async def test_config_crud_flow(self, client):
        """Full config CRUD cycle."""
        # Create
        config_data = {
            "camera_id": "CAM-TEST-01",
            "provider": "demo",
            "model_name": "test-model",
            "confidence_threshold": 0.5,
        }
        resp = await client.post("/api/v1/detections/config", json=config_data)
        assert resp.status_code == 200
        config = resp.json()
        config_id = config["config_id"]
        
        # Get
        resp = await client.get(f"/api/v1/detections/config/CAM-TEST-01")
        assert resp.status_code == 200
        assert resp.json()["config_id"] == config_id
        
        # Update
        resp = await client.patch(f"/api/v1/detections/config/CAM-TEST-01", json={"confidence_threshold": 0.7})
        assert resp.status_code == 200
        assert resp.json()["confidence_threshold"] == 0.7
        
        # Delete
        resp = await client.delete(f"/api/v1/detections/config/CAM-TEST-01")
        assert resp.status_code == 200
        assert resp.json()["deleted"] is True

    @pytest.mark.asyncio
    async def test_pagination(self, client):
        """Pagination works correctly."""
        resp = await client.get("/api/v1/detections/", params={"page": 1, "page_size": 5})
        assert resp.status_code == 200
        data = resp.json()
        assert data["page"] == 1
        assert data["page_size"] == 5
        assert len(data["detections"]) <= 5


# ─── Feed & Filter API tests (C5 upgrade) ────────────────────────────────

def _make_detection(
    camera_id: str,
    detection_id: str,
    *,
    class_name: str = "PERSON",
    quality_state: str = "GOOD",
    confidence: float = 0.9,
    observed_at: datetime | None = None,
):
    """Build a stored Detection row faithful to the ORM contract."""
    from app.models.detection import Detection

    ts = observed_at or datetime.now(timezone.utc)
    return Detection(
        detection_id=detection_id,
        camera_id=camera_id,
        frame_id="FRM-FEED-001",
        class_name=class_name,
        class_id=0,
        taxonomy_version="1.0",
        confidence=confidence,
        quality_state=quality_state,
        occlusion_state="LOW",
        detection_state="DETECTED",
        bbox_x=0.1, bbox_y=0.1, bbox_width=0.3, bbox_height=0.3,
        frame_width=1280, frame_height=720,
        source="EDGE", provider="demo",
        model_name="demo-detector", model_version="1.0",
        schema_version="1.0",
        observed_at=ts,
        received_at=ts,
        processed_at=ts,
    )


async def _create_config(db_session, camera_id: str, provider: str = "demo"):
    from app.repositories.detection import DetectionConfigRepository

    repo = DetectionConfigRepository(db_session)
    config = await repo.create(
        camera_id=camera_id,
        provider=provider,
        model_name="demo-detector",
        model_version="1.0",
        source="EDGE",
    )
    await db_session.commit()
    return config


class TestDetectionFeedAPI:
    """Camera feed endpoint: availability is never confused with object presence."""

    @pytest.fixture
    def client(self, app):
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    @pytest.mark.asyncio
    async def test_feed_unconfigured_camera(self, client):
        """No detection config -> UNCONFIGURED, never NO_OBJECTS."""
        resp = await client.get("/api/v1/detections/cameras/CAM-FEED-NOCONFIG/feed")
        assert resp.status_code == 200
        data = resp.json()
        assert data["state"] == "UNCONFIGURED"
        assert data["inference"] == "UNKNOWN"
        assert data["detections"] == []
        assert data["last_updated_at"] is None

    @pytest.mark.asyncio
    async def test_feed_inactive_config_is_unconfigured(self, client, db_session):
        """Inactive config -> UNCONFIGURED (no live pipeline to ask)."""
        config = await _create_config(db_session, "CAM-FEED-INACTIVE")
        from app.repositories.detection import DetectionConfigRepository

        repo = DetectionConfigRepository(db_session)
        await repo.set_active(config.config_id, False)
        await db_session.commit()

        resp = await client.get("/api/v1/detections/cameras/CAM-FEED-INACTIVE/feed")
        assert resp.status_code == 200
        data = resp.json()
        assert data["state"] == "UNCONFIGURED"
        assert data["inference"] == "UNKNOWN"

    @pytest.mark.asyncio
    async def test_feed_no_objects(self, client, db_session):
        """Active provider, zero stored detections -> NO_OBJECTS, not UNAVAILABLE."""
        await _create_config(db_session, "CAM-FEED-EMPTY")

        resp = await client.get("/api/v1/detections/cameras/CAM-FEED-EMPTY/feed")
        assert resp.status_code == 200
        data = resp.json()
        assert data["state"] == "NO_OBJECTS"
        assert data["inference"] == "READY"
        assert data["detections"] == []
        assert data["last_updated_at"] is None

    @pytest.mark.asyncio
    async def test_feed_ready_with_detections(self, client, db_session):
        """Active provider + stored detections -> READY, newest observed_at surfaced."""
        await _create_config(db_session, "CAM-FEED-READY")
        uid = uuid4().hex[:8]
        older = datetime(2026, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
        newer = datetime(2026, 1, 15, 11, 30, 0, tzinfo=timezone.utc)
        db_session.add_all([
            _make_detection("CAM-FEED-READY", f"DET-FEED-{uid}-A", observed_at=older),
            _make_detection("CAM-FEED-READY", f"DET-FEED-{uid}-B", observed_at=newer),
        ])
        await db_session.commit()

        resp = await client.get("/api/v1/detections/cameras/CAM-FEED-READY/feed")
        assert resp.status_code == 200
        data = resp.json()
        assert data["state"] == "READY"
        assert data["inference"] == "READY"
        assert len(data["detections"]) == 2
        # Newest first — list_camera_detections orders by observed_at desc.
        assert data["detections"][0]["detection_id"] == f"DET-FEED-{uid}-B"
        assert data["last_updated_at"].startswith("2026-01-15T11:30:00")

    @pytest.mark.asyncio
    async def test_feed_provider_unavailable_no_demo_fallback(self, client, db_session):
        """A configured provider that cannot be loaded is UNAVAILABLE — never demo output (§22)."""
        # "edge" has no module in app/domain/detection/providers/ — initialization
        # must fail loudly instead of silently substituting the demo provider.
        await _create_config(db_session, "CAM-FEED-EDGE", provider="edge")
        uid = uuid4().hex[:8]
        db_session.add(_make_detection("CAM-FEED-EDGE", f"DET-FEED-{uid}-X"))
        await db_session.commit()

        resp = await client.get("/api/v1/detections/cameras/CAM-FEED-EDGE/feed")
        assert resp.status_code == 200
        data = resp.json()
        assert data["state"] == "UNAVAILABLE"
        assert data["inference"] == "FAILED"
        assert data["detections"] == []
        assert data["last_updated_at"] is None

    @pytest.mark.asyncio
    async def test_feed_unknown_camera_404_free(self, client):
        """Feed for a camera with no config still answers with UNCONFIGURED (no 500)."""
        resp = await client.get("/api/v1/detections/cameras/CAM-UNKNOWN-FEED/feed")
        assert resp.status_code == 200
        assert resp.json()["state"] == "UNCONFIGURED"


class TestDetectionListFiltersAPI:
    """List endpoint filters added in the C5 upgrade."""

    @pytest.fixture
    def client(self, app):
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    @pytest.mark.asyncio
    async def test_filter_by_quality(self, client, db_session):
        """quality param filters on quality_state."""
        uid = uuid4().hex[:8]
        db_session.add_all([
            _make_detection("CAM-FLT-Q", f"DET-FLTQ-{uid}-GOOD", quality_state="GOOD"),
            _make_detection("CAM-FLT-Q", f"DET-FLTQ-{uid}-POOR", quality_state="POOR"),
        ])
        await db_session.commit()

        resp = await client.get(
            "/api/v1/detections/", params={"camera_id": "CAM-FLT-Q", "quality": "POOR"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["detections"][0]["quality_state"] == "POOR"
        assert data["detections"][0]["detection_id"] == f"DET-FLTQ-{uid}-POOR"

    @pytest.mark.asyncio
    async def test_search_matches_detection_id(self, client, db_session):
        """search param matches across ID fields (detection_id here)."""
        uid = uuid4().hex[:8]
        db_session.add(_make_detection("CAM-FLT-S", f"DET-FLTS-{uid}-ZZ9"))
        await db_session.commit()

        resp = await client.get("/api/v1/detections/", params={"search": f"{uid}-ZZ9"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        assert any(d["detection_id"] == f"DET-FLTS-{uid}-ZZ9" for d in data["detections"])

    @pytest.mark.asyncio
    async def test_class_other_expands_to_object_and_unknown(self, client, db_session):
        """class_name=OTHER is a UI grouping -> canonical OBJECT + UNKNOWN only."""
        uid = uuid4().hex[:8]
        db_session.add_all([
            _make_detection("CAM-FLT-C", f"DET-FLTC-{uid}-O", class_name="OBJECT"),
            _make_detection("CAM-FLT-C", f"DET-FLTC-{uid}-U", class_name="UNKNOWN"),
            _make_detection("CAM-FLT-C", f"DET-FLTC-{uid}-P", class_name="PERSON"),
        ])
        await db_session.commit()

        resp = await client.get(
            "/api/v1/detections/",
            params={"camera_id": "CAM-FLT-C", "class_name": "OTHER"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert {d["class_name"] for d in data["detections"]} == {"OBJECT", "UNKNOWN"}

    @pytest.mark.asyncio
    async def test_class_name_exact_filter_still_works(self, client, db_session):
        """A canonical class filter is passed through unchanged (no OTHER expansion)."""
        uid = uuid4().hex[:8]
        db_session.add_all([
            _make_detection("CAM-FLT-E", f"DET-FLTE-{uid}-P", class_name="PERSON"),
            _make_detection("CAM-FLT-E", f"DET-FLTE-{uid}-V", class_name="VEHICLE"),
        ])
        await db_session.commit()

        resp = await client.get(
            "/api/v1/detections/", params={"camera_id": "CAM-FLT-E", "class_name": "PERSON"}
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert data["detections"][0]["class_name"] == "PERSON"


# ─────────────────────────────────────────────────────────────────────────────
# Cross-component reference lookups (§42 critical: track references / §43)
#
# Positive-path regression: a stored detection carrying track / event /
# incident / evidence references must be returned by the reference lookups —
# scoped to the requested id (a decoy row with different refs stays out).
# These are the seams C6 (track), C4 (event), C1 (incident) and C3 (evidence)
# consume; the previous suite only asserted the empty/nonexistent path.
# ─────────────────────────────────────────────────────────────────────────────


class TestDetectionReferenceLookups:
    """Positive-path regressions for detection reference lookups."""

    @pytest.fixture
    def client(self, app):
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    @pytest.mark.asyncio
    async def test_stored_refs_are_queryable_and_scoped(self, client, db_session):
        from app.models.detection import Detection

        suffix = uuid4().hex[:8]
        track_id = f"TRK-C5-{suffix}"
        event_id = f"EVT-C5-{suffix}"
        incident_id = f"INC-C5-{suffix}"
        evidence_id = f"EVD-C5-{suffix}"
        linked_id = f"DET-C5L-{suffix}"
        decoy_id = f"DET-C5D-{suffix}"
        now = datetime.now(timezone.utc)

        def make(detection_id: str, **refs):
            return Detection(
                detection_id=detection_id,
                camera_id="CAM-07",
                frame_id=f"FRM-{detection_id}",
                class_name="PERSON",
                class_id=0,
                taxonomy_version="1.0",
                confidence=0.91,
                quality_state="GOOD",
                occlusion_state="LOW",
                detection_state="DETECTED",
                bbox_x=0.4, bbox_y=0.4, bbox_width=0.1, bbox_height=0.2,
                frame_width=1280, frame_height=720,
                source="EDGE", provider="edge",
                model_name="demo-detector", model_version="1.0",
                schema_version="1.0",
                observed_at=now, received_at=now, processed_at=now,
                **refs,
            )

        db_session.add_all([
            make(linked_id, track_id=track_id, event_id=event_id,
                 incident_id=incident_id, evidence_id=evidence_id),
            make(decoy_id, track_id=f"TRK-OTHER-{suffix}"),
        ])
        await db_session.commit()

        # by track — the C6 reference seam
        resp = await client.get(f"/api/v1/detections/tracks/{track_id}")
        assert resp.status_code == 200
        rows = resp.json()
        assert [r["detection_id"] for r in rows] == [linked_id]
        assert rows[0]["track_id"] == track_id

        # by event — the C4 reference seam
        resp = await client.get(f"/api/v1/detections/events/{event_id}")
        assert resp.status_code == 200
        assert [r["detection_id"] for r in resp.json()] == [linked_id]

        # by incident — the C1 reference seam, carrying the C3 evidence ref
        resp = await client.get(f"/api/v1/detections/incidents/{incident_id}")
        assert resp.status_code == 200
        body = resp.json()
        assert [r["detection_id"] for r in body] == [linked_id]
        assert body[0]["evidence_id"] == evidence_id


# ─── Helper for running tests ────────────────────────────────────────────
if __name__ == "__main__":
    pytest.main([__file__, "-v"])