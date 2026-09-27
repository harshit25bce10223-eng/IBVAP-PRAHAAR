# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 5 — Detection Provider Tests
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import pytest
import asyncio
import numpy as np
from unittest.mock import AsyncMock, MagicMock, patch

from app.domain.detection.inference_provider import (
    DetectionInferenceProvider,
    ProviderHealth,
    InferenceResult,
    RawDetection,
    create_provider,
)
from app.domain.detection.providers.demo import DemoInferenceProvider, create_demo_provider


class TestProviderHealth:
    """Tests for ProviderHealth dataclass."""

    def test_default_health(self):
        """Default health state is UNAVAILABLE."""
        health = ProviderHealth()
        assert health.state == "UNAVAILABLE"
        assert health.recent_failures == 0
        assert health.queue_depth == 0
        assert health.avg_latency_ms == 0.0
        assert health.model_name is None
        assert health.model_version is None
        assert health.device is None
        assert health.details is None

    def test_health_state_update(self):
        """Health state can be updated."""
        health = ProviderHealth()
        health.state = "READY"
        health.model_name = "test-model"
        health.model_version = "1.0"
        health.device = "cuda:0"
        
        assert health.state == "READY"
        assert health.model_name == "test-model"
        assert health.model_version == "1.0"
        assert health.device == "cuda:0"


class TestRawDetection:
    """Tests for RawDetection dataclass."""

    def test_required_fields(self):
        """Required fields only."""
        detection = RawDetection(
            class_id=0,
            class_name="PERSON",
            confidence=0.9,
            bbox=[0.1, 0.2, 0.3, 0.4],
            bbox_format="xyxy_norm",
        )
        assert detection.class_id == 0
        assert detection.class_name == "PERSON"
        assert detection.confidence == 0.9
        assert detection.bbox == [0.1, 0.2, 0.3, 0.4]
        assert detection.bbox_format == "xyxy_norm"
        assert detection.occlusion is None
        assert detection.quality is None
        assert detection.metadata is None

    def test_all_fields(self):
        """All fields populated."""
        detection = RawDetection(
            class_id=0,
            class_name="PERSON",
            confidence=0.95,
            bbox=[100, 100, 200, 200],
            bbox_format="xyxy",
            occlusion=0.1,
            quality="GOOD",
            metadata={"demo": True},
        )
        assert detection.occlusion == 0.1
        assert detection.quality == "GOOD"
        assert detection.metadata == {"demo": True}


class TestInferenceResult:
    """Tests for InferenceResult dataclass."""

    def test_required_fields(self):
        """Required fields only."""
        result = InferenceResult(
            frame_id="FRM-001",
            camera_id="CAM-01",
            detections=[],
            inference_latency_ms=45,
            model_name="yolo-v8",
            model_version="1.0",
            provider="demo",
        )
        assert result.frame_id == "FRM-001"
        assert result.camera_id == "CAM-01"
        assert result.detections == []
        assert result.inference_latency_ms == 45
        assert result.model_name == "yolo-v8"
        assert result.model_version == "1.0"
        assert result.provider == "demo"
        assert result.device is None
        assert result.runtime_version is None
        assert result.timestamp is None

    def test_all_fields(self):
        """All fields populated."""
        from app.domain.detection.inference_provider import RawDetection
        
        result = InferenceResult(
            frame_id="FRM-001",
            camera_id="CAM-01",
            detections=[
                RawDetection(
                    class_id=0,
                    class_name="PERSON",
                    confidence=0.9,
                    bbox=[0.1, 0.2, 0.3, 0.4],
                    bbox_format="xyxy_norm",
                )
            ],
            inference_latency_ms=45,
            model_name="yolo-v8",
            model_version="1.0",
            provider="local_cpu",
            device="cuda:0",
            runtime_version="onnx-1.15",
            timestamp="2026-01-15T10:30:00+00:00",
        )
        assert result.device == "cuda:0"
        assert result.runtime_version == "onnx-1.15"
        assert result.timestamp == "2026-01-15T10:30:00+00:00"


class TestDemoInferenceProvider:
    """Tests for DemoInferenceProvider."""

    @pytest.fixture
    def provider_config(self):
        return {
            "model_name": "demo-detector",
            "model_version": "1.0.0",
            "device": "cpu",
            "runtime_version": "demo-1.0",
            "confidence_threshold": 0.3,
            "detection_enabled": True,
        }

    @pytest.fixture
    async def provider(self, provider_config):
        provider = DemoInferenceProvider(provider_config)
        await provider.load()
        await provider.warmup()
        yield provider
        await provider.shutdown()

    @pytest.mark.asyncio
    async def test_load(self, provider):
        """Provider loads and becomes READY."""
        assert provider._loaded is True
        assert provider._health.state == "READY"
        assert provider._health.model_name == "demo-detector"
        assert provider._health.model_version == "1.0.0"
        assert provider._health.device == "cpu"

    @pytest.mark.asyncio
    async def test_warmup(self, provider):
        """Provider warms up correctly."""
        assert provider._warm is True
        assert provider._health.state == "READY"

    @pytest.mark.asyncio
    async def test_infer_returns_result(self, provider):
        """infer returns InferenceResult with detections."""
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        frame_id = "FRM-TEST-001"
        camera_id = "CAM-01"
        
        result = await provider.infer(frame, frame_id, camera_id)
        
        assert isinstance(result, InferenceResult)
        assert result.frame_id == frame_id
        assert result.camera_id == camera_id
        assert isinstance(result.detections, list)
        assert result.inference_latency_ms > 0
        assert result.model_name == "demo-detector"
        assert result.model_version == "1.0.0"
        assert result.provider == "demo"
        assert result.device == "cpu"
        assert result.runtime_version == "demo-1.0"
        assert result.timestamp is not None

    @pytest.mark.asyncio
    async def test_infer_zero_detections_possible(self, provider):
        """Provider can return zero detections (healthy, no objects)."""
        provider.set_detection_enabled(False)
        
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        result = await provider.infer(np.zeros((720, 1280, 3), dtype=np.uint8), "FRM-001", "CAM-01")
        
        assert result.detections == []
        assert provider._health.state == "READY"

    @pytest.mark.asyncio
    async def test_infer_not_loaded_raises(self, provider_config):
        """Infer before load raises error."""
        provider = DemoInferenceProvider(provider_config)
        # Don't load
        
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        with pytest.raises(RuntimeError, match="not loaded"):
            await provider.infer(frame, "FRM-001", "CAM-01")

    @pytest.mark.asyncio
    async def test_infer_not_warmed_raises(self, provider_config):
        """Infer before warmup raises error."""
        provider = DemoInferenceProvider(provider_config)
        await provider.load()
        # Don't warmup
        
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        with pytest.raises(RuntimeError, match="not warmed up"):
            await provider.infer(frame, "FRM-001", "CAM-01")

    @pytest.mark.asyncio
    async def test_infer_batch(self, provider):
        """infer_batch processes multiple frames."""
        frames = [
            np.zeros((720, 1280, 3), dtype=np.uint8),
            np.zeros((720, 1280, 3), dtype=np.uint8),
        ]
        frame_ids = ["FRM-001", "FRM-002"]
        camera_id = "CAM-01"
        
        results = await provider.infer_batch(frames, frame_ids, camera_id)
        
        assert len(results) == 2
        for i, result in enumerate(results):
            assert isinstance(result, InferenceResult)
            assert result.frame_id == frame_ids[i]
            assert result.camera_id == camera_id

    @pytest.mark.asyncio
    async def test_health(self, provider):
        """health returns ProviderHealth."""
        health = await provider.health()
        
        assert isinstance(health, ProviderHealth)
        assert health.state == "READY"
        assert health.model_name == "demo-detector"
        assert health.model_version == "1.0.0"
        assert health.device == "cpu"

    @pytest.mark.asyncio
    async def test_metadata(self, provider):
        """metadata returns provider info."""
        meta = await provider.metadata()
        
        assert meta["model_name"] == "demo-detector"
        assert meta["model_version"] == "1.0.0"
        assert meta["provider"] == "demo"
        assert meta["device"] == "cpu"
        assert meta["runtime_version"] == "demo-1.0"
        assert meta["supported_classes"] == ["PERSON", "VEHICLE", "ANIMAL", "OBJECT"]
        assert meta["input_format"] == "BGR"
        assert meta["max_batch_size"] == 16

    @pytest.mark.asyncio
    async def test_shutdown(self, provider):
        """shutdown cleans up."""
        await provider.shutdown()
        
        assert provider._loaded is False
        assert provider._warm is False
        assert provider._health.state == "UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_simulate_failure(self, provider):
        """simulate_failure injects failure for next infer."""
        provider.simulate_failure()
        
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        with pytest.raises(RuntimeError, match="Simulated provider failure"):
            await provider.infer(np.zeros((720, 1280, 3), dtype=np.uint8), "FRM-001", "CAM-01")
        
        # Health should reflect failure
        health = await provider.health()
        assert health.state == "FAILED"
        assert health.recent_failures == 1

    @pytest.mark.asyncio
    async def test_set_detection_enabled(self, provider):
        """set_detection_enabled toggles detection generation."""
        provider.set_detection_enabled(False)
        
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        result = await provider.infer(np.zeros((720, 1280, 3), dtype=np.uint8), "FRM-001", "CAM-01")
        assert result.detections == []
        
        provider.set_detection_enabled(True)
        result = await provider.infer(np.zeros((720, 1280, 3), dtype=np.uint8), "FRM-001", "CAM-01")
        # With detection enabled, may have detections (random)
        assert isinstance(result.detections, list)


class TestCreateDemoProvider:
    """Tests for create_demo_provider factory."""

    @pytest.mark.asyncio
    async def test_factory_creates_and_initializes(self):
        """Factory creates, loads, and warms up provider."""
        provider = await create_demo_provider({
            "model_name": "test-model",
            "model_version": "2.0",
            "device": "cuda:0",
        })
        
        assert isinstance(provider, DemoInferenceProvider)
        assert provider._loaded is True
        assert provider._warm is True
        assert provider.model_name == "test-model"
        assert provider.model_version == "2.0"
        assert provider.device == "cuda:0"
        
        # Cleanup
        await provider.shutdown()


class TestProviderHealthTransitions:
    """Tests for provider health state transitions."""

    @pytest.fixture
    async def provider(self):
        provider = DemoInferenceProvider({
            "model_name": "test",
            "model_version": "1.0",
            "device": "cpu",
        })
        await provider.load()
        await provider.warmup()
        yield provider
        await provider.shutdown()

    @pytest.mark.asyncio
    async def test_ready_to_failed_transition(self, provider):
        """FAILED state on failure."""
        provider.simulate_failure()
        
        frame = np.zeros((720, 1280, 3), dtype=np.uint8)
        with pytest.raises(RuntimeError):
            await provider.infer(np.zeros((720, 1280, 3), dtype=np.uint8), "FRM-001", "CAM-01")
        
        health = await provider.health()
        assert health.state == "FAILED"
        assert health.recent_failures == 1

    @pytest.mark.asyncio
    async def test_shutdown_sets_unavailable(self, provider):
        """Shutdown sets UNAVAILABLE."""
        await provider.shutdown()
        
        health = await provider.health()
        assert health.state == "UNAVAILABLE"


class TestProviderFactory:
    """Tests for create_provider factory."""

    @pytest.mark.asyncio
    async def test_create_demo_provider(self):
        """Factory creates demo provider."""
        provider = await create_provider("demo", {
            "model_name": "test",
            "device": "cpu",
        })
        
        assert isinstance(provider, DemoInferenceProvider)
        assert provider._loaded is True
        
        await provider.shutdown()

    @pytest.mark.asyncio
    async def test_unknown_provider_raises(self):
        """Unknown provider type raises ValueError."""
        with pytest.raises(ValueError, match="Unknown provider type"):
            await create_provider("unknown_type", {})


# ─── Helper for running tests ────────────────────────────────────────────
if __name__ == "__main__":
    pytest.main([__file__, "-v"])