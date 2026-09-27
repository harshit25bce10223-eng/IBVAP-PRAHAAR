# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 5 — Demo Inference Provider (for testing/development)
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import asyncio
import random
import time
from typing import Any

import numpy as np

from app.domain.detection.inference_provider import (
    DetectionInferenceProvider,
    ProviderHealth,
    InferenceResult,
    RawDetection,
)


class DemoInferenceProvider(DetectionInferenceProvider):
    """
    Demo inference provider that generates realistic fake detections.
    Only for development/testing - never use in production.
    """
    
    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.config = config
        self.model_name = config.get("model_name", "demo-detector")
        self.model_version = config.get("model_version", "1.0.0")
        self.device = config.get("device", "cpu")
        self.runtime_version = config.get("runtime_version", "demo-1.0")
        self._loaded = False
        self._warm = False
        self._fail_next = False
        self._frame_count = 0
        self._classes = ["PERSON", "VEHICLE", "ANIMAL", "OBJECT"]
        self._detection_enabled = config.get("detection_enabled", True)
        
    async def load(self) -> None:
        """Simulate model loading."""
        await asyncio.sleep(0.1)  # Simulate loading time
        self._loaded = True
        self._health = ProviderHealth(
            state="READY",
            model_name=self.model_name,
            model_version=self.model_version,
            device=self.device,
        )
    
    async def warmup(self) -> None:
        """Simulate warmup."""
        if not self._loaded:
            raise RuntimeError("Provider not loaded")
        await asyncio.sleep(0.05)
        self._warm = True
        self._health.state = "READY"
    
    async def infer(self, frame: np.ndarray, frame_id: str, camera_id: str) -> InferenceResult:
        """Generate fake detections based on frame content."""
        if not self._loaded:
            raise RuntimeError("Provider not loaded")
        if not self._warm:
            raise RuntimeError("Provider not warmed up")
        if self._fail_next:
            self._fail_next = False
            self._health.state = "FAILED"
            self._health.recent_failures += 1
            raise RuntimeError("Simulated provider failure")
        
        start_time = time.perf_counter()
        
        # Simulate inference latency
        await asyncio.sleep(random.uniform(0.01, 0.05))
        
        detections = []
        if self._detection_enabled:
            # Generate 0-5 detections based on frame properties
            h, w = frame.shape[:2]
            num_detections = random.randint(0, 5)
            
            for _ in range(num_detections):
                class_name = random.choice(self._classes)
                class_id = self._classes.index(class_name)
                
                # Generate normalized bbox
                box_w = random.uniform(0.05, 0.3)
                box_h = random.uniform(0.05, 0.3)
                x = random.uniform(0, 1 - box_w)
                y = random.uniform(0, 1 - box_h)
                
                confidence = random.uniform(0.3, 0.99)
                
                detections.append(RawDetection(
                    class_id=class_id,
                    class_name=class_name,
                    confidence=confidence,
                    bbox=[x, y, x + box_w, y + box_h],
                    bbox_format="xyxy_norm",
                    occlusion=random.uniform(0, 0.5),
                    quality=random.choice(["GOOD", "LIMITED", "POOR"]),
                    metadata={"demo": True}
                ))
        
        self._frame_count += 1
        latency_ms = int((time.perf_counter() - start_time) * 1000)
        
        self._health.last_successful_inference = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        self._health.avg_latency_ms = (self._health.avg_latency_ms * 0.9 + latency_ms * 0.1)
        self._health.state = "READY"
        
        return InferenceResult(
            frame_id=frame_id,
            camera_id=camera_id,
            detections=detections,
            inference_latency_ms=latency_ms,
            model_name=self.model_name,
            model_version=self.model_version,
            provider="demo",
            device=self.device,
            runtime_version=self.runtime_version,
            timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        )
    
    async def infer_batch(self, frames: list[np.ndarray], frame_ids: list[str], camera_id: str) -> list[InferenceResult]:
        """Process batch sequentially for demo."""
        results = []
        for frame, fid in zip(frames, frame_ids):
            result = await self.infer(frame, fid, camera_id)
            results.append(result)
        return results
    
    async def health(self) -> ProviderHealth:
        return self._health
    
    async def metadata(self) -> dict[str, Any]:
        return {
            "model_name": self.model_name,
            "model_version": self.model_version,
            "provider": "demo",
            "device": self.device,
            "runtime_version": self.runtime_version,
            "supported_classes": self._classes,
            "input_format": "BGR",
            "max_batch_size": 16,
        }
    
    async def shutdown(self) -> None:
        self._loaded = False
        self._warm = False
        self._health.state = "UNAVAILABLE"
    
    def simulate_failure(self) -> None:
        """Inject a failure for testing."""
        self._fail_next = True
    
    def set_detection_enabled(self, enabled: bool) -> None:
        self._detection_enabled = enabled


async def create_demo_provider(config: dict[str, Any]) -> DemoInferenceProvider:
    """Factory function for demo provider."""
    provider = DemoInferenceProvider(config)
    await provider.load()
    await provider.warmup()
    return provider