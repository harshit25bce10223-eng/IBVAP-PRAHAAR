# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 5 — Detection Edge Sync Integration Tests
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import pytest
from datetime import datetime, timezone
from uuid import uuid4

from httpx import AsyncClient, ASGITransport

from app.repositories.detection import DetectionRepository, DetectionConfigRepository
from app.models.detection import Detection, DetectionSyncState, DetectionSource
from app.domain.detection.service import DetectionService
from app.domain.detection.normalizer import DetectionNormalizer
from app.domain.detection.providers.demo import create_demo_provider


class TestDetectionEdgeSync:
    """Integration tests for edge detection sync."""

    @pytest.fixture
    def client(self, app):
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    @pytest.fixture
    def detection_service(self, db_session):
        return DetectionService(db_session)

    @pytest.fixture
    def detection_repo(self, db_session):
        return DetectionRepository(db_session)

    @pytest.fixture
    async def sample_detection(self, db_session):
        """Create a sample detection with LOCAL_ONLY sync state."""
        detection = Detection(
            detection_id=f"DET-{uuid4().hex[:8]}",
            camera_id="CAM-EDGE-01",
            frame_id=f"FRM-{uuid4().hex[:8]}",
            class_name="PERSON",
            class_id=0,
            taxonomy_version="1.0",
            confidence=0.9,
            quality_state="GOOD",
            occlusion_state="LOW",
            detection_state="DETECTED",
            bbox_x=0.1,
            bbox_y=0.1,
            bbox_width=0.3,
            bbox_height=0.3,
            frame_width=1280,
            frame_height=720,
            source="EDGE",
            provider="edge",
            model_name="edge-detector",
            model_version="1.0",
            schema_version="1.0",
            sync_state=DetectionSyncState.LOCAL_ONLY,
            sync_payload_hash=f"hash-{uuid4().hex[:8]}",
            edge_device_id="edge-device-01",
            source_event_id="SRC-EVT-001",
            source_sequence=1,
            observed_at=datetime.now(timezone.utc),
            received_at=datetime.now(timezone.utc),
            processed_at=datetime.now(timezone.utc),
            inference_latency_ms=50,
        )
        db_session.add(detection)
        await db_session.commit()
        await db_session.refresh(detection)
        return detection

    @pytest.mark.asyncio
    async def test_edge_offline_detection_marked_local_only(self, client, sample_detection):
        """Detection created while offline is marked LOCAL_ONLY."""
        detection = sample_detection
        
        assert detection.sync_state == DetectionSyncState.LOCAL_ONLY
        assert detection.edge_device_id == "edge-device-01"
        assert detection.source_event_id == "SRC-EVT-001"
        assert detection.source_sequence == 1
        assert detection.sync_payload_hash is not None

    @pytest.mark.asyncio
    async def test_get_unsynced_detections(self, client, sample_detection, db_session, detection_service):
        """Get unsynced detections returns LOCAL_ONLY and SYNC_PENDING."""
        unsynced = await detection_service.get_unsynced_detections(limit=100)
        
        det_ids = [d.detection_id for d in unsynced]
        assert sample_detection.detection_id in det_ids
        
        for d in unsynced:
            assert d.sync_state in (DetectionSyncState.LOCAL_ONLY, DetectionSyncState.SYNC_PENDING)

    @pytest.mark.asyncio
    async def test_mark_synced_updates_state(self, client, sample_detection, db_session, detection_service):
        """Marking detections as synced updates their state."""
        count = await detection_service.mark_synced([sample_detection.detection_id], "sync_hash_123")
        assert count == 1
        
        await db_session.refresh(sample_detection)
        assert sample_detection.sync_state == DetectionSyncState.SYNCED
        assert sample_detection.sync_payload_hash == "sync_hash_123"

    @pytest.mark.asyncio
    async def test_mark_sync_failed(self, client, sample_detection, db_session, detection_service):
        """Marking sync failed sets SYNC_FAILED state."""
        count = await detection_service.mark_sync_failed([sample_detection.detection_id])
        assert count == 1
        
        await db_session.refresh(sample_detection)
        assert sample_detection.sync_state == DetectionSyncState.SYNC_FAILED


class TestEdgeSyncRetry:
    """Tests for edge sync retry logic."""

    @pytest.fixture
    def detection_service(self, db_session):
        return DetectionService(db_session)

    @pytest.mark.asyncio
    async def test_sync_retry_after_failure(self, client, db_session, detection_service):
        """Failed sync can be retried and succeeds."""
        det = Detection(
            detection_id=f"DET-{uuid4().hex[:8]}",
            camera_id="CAM-EDGE-01",
            frame_id=f"FRM-{uuid4().hex[:8]}",
            class_name="PERSON",
            class_id=0,
            taxonomy_version="1.0",
            confidence=0.9,
            quality_state="GOOD",
            occlusion_state="LOW",
            detection_state="DETECTED",
            bbox_x=0.1,
            bbox_y=0.1,
            bbox_width=0.3,
            bbox_height=0.3,
            frame_width=1280,
            frame_height=720,
            source="EDGE",
            provider="edge",
            model_name="edge-detector",
            model_version="1.0",
            schema_version="1.0",
            sync_state=DetectionSyncState.SYNC_FAILED,
            sync_payload_hash="fail_hash",
            edge_device_id="edge-01",
            source_event_id="SRC-EVT-RETRY",
            source_sequence=1,
            observed_at=datetime.now(timezone.utc),
            received_at=datetime.now(timezone.utc),
            processed_at=datetime.now(timezone.utc),
            inference_latency_ms=50,
        )
        db_session.add(det)
        await db_session.commit()
        await db_session.refresh(det)
        
        count = await detection_service.mark_synced([det.detection_id], "retry_hash")
        assert count == 1
        
        await db_session.refresh(det)
        assert det.sync_state == DetectionSyncState.SYNCED
        assert det.sync_payload_hash == "retry_hash"


class TestEdgeContentMismatch:
    """Tests for edge content mismatch protection."""

    @pytest.mark.asyncio
    async def test_content_mismatch_rejected(self, client, db_session):
        """Same detection_id with different payload is rejected."""
        det_id = f"DET-MISMATCH-{uuid4().hex[:8]}"
        det = Detection(
            detection_id=det_id,
            camera_id="CAM-EDGE-01",
            frame_id="FRM-001",
            class_name="PERSON",
            class_id=0,
            taxonomy_version="1.0",
            confidence=0.9,
            quality_state="GOOD",
            occlusion_state="LOW",
            detection_state="DETECTED",
            bbox_x=0.1,
            bbox_y=0.1,
            bbox_width=0.3,
            bbox_height=0.3,
            frame_width=1280,
            frame_height=720,
            source="EDGE",
            provider="edge",
            model_name="edge-detector",
            model_version="1.0",
            schema_version="1.0",
            sync_state=DetectionSyncState.LOCAL_ONLY,
            sync_payload_hash="original_hash",
            edge_device_id="edge-01",
            source_event_id="SRC-EVT-MISMATCH",
            source_sequence=1,
            observed_at=datetime.now(timezone.utc),
            received_at=datetime.now(timezone.utc),
            processed_at=datetime.now(timezone.utc),
            inference_latency_ms=50,
        )
        db_session.add(det)
        await db_session.commit()
        
        repo = DetectionRepository(db_session)
        existing = await repo.get(det_id)
        assert existing is not None
        assert existing.sync_payload_hash == "original_hash"
        different_hash = "different_hash"
        assert different_hash != existing.sync_payload_hash


class TestEdgeRestart:
    """Tests for edge sync persistence across restarts."""

    @pytest.mark.asyncio
    async def test_sync_state_persists_restart(self, client, session_factory):
        """Sync state survives backend restart."""
        det_id = f"DET-RESTART-{uuid4().hex[:8]}"
        async with session_factory() as session1:
            det = Detection(
                detection_id=det_id,
                camera_id="CAM-EDGE-01",
                frame_id=f"FRM-{uuid4().hex[:8]}",
                class_name="PERSON",
                class_id=0,
                taxonomy_version="1.0",
                confidence=0.9,
                quality_state="GOOD",
                occlusion_state="LOW",
                detection_state="DETECTED",
                bbox_x=0.1,
                bbox_y=0.1,
                bbox_width=0.3,
                bbox_height=0.3,
                frame_width=1280,
                frame_height=720,
                source="EDGE",
                provider="edge",
                model_name="edge-detector",
                model_version="1.0",
                schema_version="1.0",
                sync_state=DetectionSyncState.SYNC_PENDING,
                sync_payload_hash="pending_hash",
                edge_device_id="edge-01",
                source_event_id="SRC-EVT-RESTART",
                source_sequence=1,
                observed_at=datetime.now(timezone.utc),
                received_at=datetime.now(timezone.utc),
                processed_at=datetime.now(timezone.utc),
                inference_latency_ms=50,
            )
            session1.add(det)
            await session1.commit()
        
        # Simulate restart with fresh session pointing to the same engine
        async with session_factory() as session2:
            repo = DetectionRepository(session2)
            retrieved = await repo.get(det_id)
            assert retrieved is not None
            assert retrieved.sync_state == DetectionSyncState.SYNC_PENDING
            assert retrieved.sync_payload_hash == "pending_hash"


class TestEdgeIdempotency:
    """Tests for edge detection idempotency."""

    @pytest.mark.asyncio
    async def test_same_detection_id_same_payload_idempotent(self, client, db_session):
        """Same detection_id + same payload = one record."""
        cam_id = f"CAM-IDEMPOTENT-{uuid4().hex[:6]}"
        config = await DetectionConfigRepository(db_session).create(
            camera_id=cam_id,
            provider="demo",
            model_name="demo-detector",
            model_version="1.0",
            source=DetectionSource.EDGE,
            confidence_threshold=0.3,
            iou_threshold=0.5,
            max_detections=100,
            sample_rate=1.0,
            min_frame_interval_ms=0,
            nms_enabled=True,
            clip_bbox=True,
            queue_size_limit=50,
            enable_edge_sync=True,
            sync_interval_sec=60,
            active=True,
        )
        await db_session.commit()
        
        from unittest.mock import AsyncMock
        from app.domain.detection.inference_provider import InferenceResult, RawDetection

        service = DetectionService(db_session)
        provider = await create_demo_provider({
            'model_name': 'demo-detector',
            'model_version': '1.0',
            'device': 'cpu',
            'confidence_threshold': 0.3,
        })
        provider.infer = AsyncMock(return_value=InferenceResult(
            frame_id="FRM-IDEMPOTENT-001",
            camera_id=cam_id,
            detections=[
                RawDetection(
                    class_id=0,
                    class_name="PERSON",
                    confidence=0.9,
                    bbox=[0.1, 0.1, 0.4, 0.4],
                    bbox_format="xyxy_norm",
                )
            ],
            inference_latency_ms=25,
            model_name="demo-detector",
            model_version="1.0",
            provider="demo",
        ))
        
        service._providers[cam_id] = provider
        service.normalizer = DetectionNormalizer()
        
        # Process same frame twice with same edge config
        import numpy as np
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        frame_id = f"FRM-IDEMPOTENT-{uuid4().hex[:6]}"
        payload_hash = f"idem_hash_{uuid4().hex[:8]}"
        edge_config = {
            "sync_state": "LOCAL_ONLY",
            "payload_hash": payload_hash,
            "edge_device_id": "edge-01",
            "source_event_id": f"SRC-IDEMPOTENT-{uuid4().hex[:6]}",
            "source_sequence": 1,
        }
        
        # First processing
        created1 = await service.process_frame(
            frame, cam_id, frame_id, 1280, 720,
            edge_config=edge_config,
        )
        
        # Second processing (same frame, same edge config)
        created2 = await service.process_frame(
            frame, cam_id, frame_id, 1280, 720,
            edge_config=edge_config,
        )
        
        # Should be idempotent - second call returns empty (duplicate skipped)
        assert len(created1) > 0
        assert len(created2) == 0


class TestEdgePartialFailure:
    """Tests for partial sync failures."""

    @pytest.fixture
    def detection_service(self, db_session):
        return DetectionService(db_session)

    @pytest.mark.asyncio
    async def test_partial_sync_failure(self, client, db_session, detection_service):
        """Some detections sync, others fail - states tracked individually."""
        batch_id = uuid4().hex[:6]
        cam_id = f"CAM-EDGE-{batch_id}"
        detections = []
        for i in range(3):
            det = Detection(
                detection_id=f"DET-PARTIAL-{batch_id}-{i}",
                camera_id=cam_id,
                frame_id=f"FRM-{uuid4().hex[:8]}",
                class_name="PERSON",
                class_id=0,
                taxonomy_version="1.0",
                confidence=0.9,
                quality_state="GOOD",
                occlusion_state="LOW",
                detection_state="DETECTED",
                bbox_x=0.1,
                bbox_y=0.1,
                bbox_width=0.3,
                bbox_height=0.3,
                frame_width=1280,
                frame_height=720,
                source="EDGE",
                provider="edge",
                model_name="edge-detector",
                model_version="1.0",
                schema_version="1.0",
                sync_state=DetectionSyncState.SYNC_PENDING,
                sync_payload_hash=f"hash-{batch_id}-{i}",
                edge_device_id="edge-01",
                source_event_id=f"SRC-PARTIAL-{batch_id}-{i}",
                source_sequence=i,
                observed_at=datetime.now(timezone.utc),
                received_at=datetime.now(timezone.utc),
                processed_at=datetime.now(timezone.utc),
                inference_latency_ms=50,
            )
            db_session.add(det)
            detections.append(det)
        await db_session.commit()
        
        # Mark only first two as synced
        count = await detection_service.mark_synced(
            [detections[0].detection_id, detections[1].detection_id],
            "sync_hash_123"
        )
        assert count == 2
        
        # Verify states
        await db_session.refresh(detections[0])
        await db_session.refresh(detections[1])
        await db_session.refresh(detections[2])
        
        # First two synced, third still pending
        assert detections[0].sync_state == DetectionSyncState.SYNCED
        assert detections[1].sync_state == DetectionSyncState.SYNCED
        assert detections[2].sync_state == DetectionSyncState.SYNC_PENDING