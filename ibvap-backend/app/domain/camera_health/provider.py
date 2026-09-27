# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — Camera Health Provider Interface (Component 1 Integration)
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any

from app.domain.camera_health.analyzer import CameraHealthAnalyzer


class CameraHealthProvider(ABC):
    """
    Interface for Component 1 to consume Camera Health context.
    
    Component 1 (Virtual Fence + Risk Engine) depends on this interface
    rather than directly on database models or Camera Health internals.
    This keeps components decoupled and allows Camera Health to evolve
    independently.
    """

    @abstractmethod
    async def get_latest_health_context(self, camera_id: str) -> dict[str, Any] | None:
        """
        Get the latest health context for a camera.
        
        Returns dict with keys expected by Component 1:
        - viewpoint_shift_detected: bool
        - fence_confidence_override: "DEGRADED" | None
        - background_stability: str | None
        - reliability: "HIGH" | "MEDIUM" | "LOW" | "UNKNOWN" | None
        - geometry_confidence: "HIGH" | "MEDIUM" | "LOW" | "DEGRADED"
        - uncertainty_margin: float
        - last_updated: ISO timestamp string | None
        """
        ...

    @abstractmethod
    async def get_health_context_batch(self, camera_ids: list[str]) -> dict[str, dict[str, Any] | None]:
        """Get health context for multiple cameras."""
        ...


class CameraHealthProviderImpl(CameraHealthProvider):
    """Implementation using the CameraHealthAnalyzer."""

    def __init__(self, analyzer: CameraHealthAnalyzer):
        self.analyzer = analyzer

    async def get_latest_health_context(self, camera_id: str) -> dict[str, Any] | None:
        return self.analyzer.get_health_context_for_component1(camera_id)

    async def get_health_context_batch(self, camera_ids: list[str]) -> dict[str, dict[str, Any] | None]:
        result = {}
        for cam_id in camera_ids:
            result[cam_id] = self.analyzer.get_health_context_for_component1(cam_id)
        return result


# Global provider instance (set during app startup)
_camera_health_provider: CameraHealthProvider | None = None


def get_camera_health_provider() -> CameraHealthProvider | None:
    """Get the current Camera Health provider."""
    return _camera_health_provider


def set_camera_health_provider(provider: CameraHealthProvider) -> None:
    """Set the Camera Health provider (called during app startup)."""
    global _camera_health_provider
    _camera_health_provider = provider