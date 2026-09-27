# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 5 — Inference Provider Abstraction
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class ProviderHealth:
    state: str = "UNAVAILABLE"  # READY, LOADING, WARMING, DEGRADED, FAILED, UNAVAILABLE, UNKNOWN
    last_successful_inference: str | None = None  # ISO timestamp
    recent_failures: int = 0
    queue_depth: int = 0
    avg_latency_ms: float = 0.0
    model_name: str | None = None
    model_version: str | None = None
    device: str | None = None
    details: dict[str, Any] | None = None


@dataclass
class RawDetection:
    class_id: int
    class_name: str
    confidence: float
    bbox: list[float]  # [x1, y1, x2, y2] or [x, y, w, h] depending on provider
    bbox_format: str  # "xyxy", "xywh", "xyxy_norm", "xywh_norm"
    occlusion: float | None = None
    quality: str | None = None
    metadata: dict[str, Any] | None = None


@dataclass
class InferenceResult:
    frame_id: str
    camera_id: str
    detections: list[RawDetection]
    inference_latency_ms: int
    model_name: str
    model_version: str
    provider: str
    device: str | None = None
    runtime_version: str | None = None
    timestamp: str | None = None  # ISO timestamp when inference completed


class DetectionInferenceProvider(ABC):
    """
    Abstract base class for detection inference providers.
    
    Implementations must provide model-agnostic inference capabilities.
    Supported providers: LocalCPU, LocalGPU, ONNX, TensorRT, Remote, Edge.
    """
    
    def __init__(self, config: dict[str, Any]):
        self.config = config
        self._health = ProviderHealth(state="UNAVAILABLE")
    
    @abstractmethod
    async def load(self) -> None:
        """
        Load the model and initialize the provider.
        Must be called before any inference.
        """
        pass
    
    @abstractmethod
    async def warmup(self) -> None:
        """
        Warm up the model with dummy inference.
        Should be called after load() before processing real frames.
        """
        pass
    
    @abstractmethod
    async def infer(self, frame: np.ndarray, frame_id: str, camera_id: str) -> InferenceResult:
        """
        Run inference on a single frame.
        
        Args:
            frame: Input frame as numpy array (H, W, C) in BGR or RGB format
            frame_id: Unique identifier for this frame
            camera_id: Camera identifier
            
        Returns:
            InferenceResult with detections and metadata
        """
        pass
    
    @abstractmethod
    async def infer_batch(self, frames: list[np.ndarray], frame_ids: list[str], camera_id: str) -> list[InferenceResult]:
        """
        Run inference on a batch of frames.
        
        Args:
            frames: List of input frames
            frame_ids: List of frame identifiers
            camera_id: Camera identifier (same for all frames in batch)
            
        Returns:
            List of InferenceResult, one per frame
        """
        pass
    
    @abstractmethod
    async def health(self) -> ProviderHealth:
        """
        Get current provider health status.
        """
        pass
    
    @abstractmethod
    async def metadata(self) -> dict[str, Any]:
        """
        Get provider metadata (model name, version, supported classes, etc.)
        """
        pass
    
    @abstractmethod
    async def shutdown(self) -> None:
        """
        Gracefully shutdown the provider and release resources.
        """
        pass
    
    @property
    def health_state(self) -> ProviderHealth:
        return self._health
    
    def _update_health(self, **kwargs) -> None:
        for key, value in kwargs.items():
            if hasattr(self._health, key):
                setattr(self._health, key, value)


# Factory function for creating providers
async def create_provider(provider_type: str, config: dict[str, Any]) -> DetectionInferenceProvider:
    """
    Factory function to create inference provider instances.
    
    Args:
        provider_type: Type of provider ("local_cpu", "local_gpu", "onnx", "tensorrt", "remote", "edge", "demo")
        config: Provider-specific configuration
        
    Returns:
        Initialized provider instance
    """
    if provider_type == "local_cpu":
        from app.domain.detection.providers.local_cpu import LocalCPUProvider
        return LocalCPUProvider(config)
    elif provider_type == "local_gpu":
        from app.domain.detection.providers.local_gpu import LocalGPUProvider
        return LocalGPUProvider(config)
    elif provider_type == "onnx":
        from app.domain.detection.providers.onnx import ONNXProvider
        return ONNXProvider(config)
    elif provider_type == "tensorrt":
        from app.domain.detection.providers.tensorrt import TensorRTProvider
        return TensorRTProvider(config)
    elif provider_type == "remote":
        from app.domain.detection.providers.remote import RemoteInferenceProvider
        return RemoteInferenceProvider(config)
    elif provider_type == "edge":
        from app.domain.detection.providers.edge import EdgeInferenceProvider
        return EdgeInferenceProvider(config)
    elif provider_type == "demo":
        from app.domain.detection.providers.demo import create_demo_provider
        return await create_demo_provider(config)
    else:
        raise ValueError(f"Unknown provider type: {provider_type}")