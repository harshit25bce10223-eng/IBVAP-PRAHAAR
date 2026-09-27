# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — Camera Health Analyzer (Main Orchestrator)
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

import numpy as np

from app.core.config import settings
from app.domain.camera_health.state_engine import (
    CameraHealthInput,
    CameraHealthDerived,
    CameraHealthStateEngine,
    StreamHealthMetrics,
    ImageQualityMetrics,
    NetworkMetrics,
    ViewpointMetrics,
)
from app.domain.camera_health.baseline_engine import BaselineEngine, IlluminationRegime
from app.domain.camera_health.trend_engine import TrendEngine, TrendDirection
from app.domain.camera_health.viewpoint import ViewpointDetector, ViewpointResult
from app.domain.camera_health.freeze import FreezeDetector, FreezeResult
from app.domain.camera_health.image_quality import ImageQualityAnalyzer, ImageQualityResult
from app.domain.camera_health.state_engine import CameraHealthState


@dataclass
class HealthAnalysisResult:
    """Complete health analysis result."""
    camera_id: str
    source_timestamp: datetime
    received_at: datetime

    # Derived state (for storage)
    overall_status: CameraHealthState
    status_reason: str | None
    reliability: str | None

    # Stream
    stream_state: str
    stream_reason: str | None
    fps: float | None
    expected_fps: float | None
    frame_drop_percent: float | None
    stale_seconds: float | None
    reconnect_count: int | None

    # Image
    image_status: str
    sharpness_value: float | None
    sharpness_status: str | None
    sharpness_reason: str | None
    brightness_value: float | None
    brightness_status: str | None
    brightness_reason: str | None
    exposure_status: str | None
    noise_status: str | None
    background_stability: str | None

    # Network
    network_status: str
    latency_ms: float | None
    latency_variance_ms: float | None
    packet_loss_percent: float | None
    heartbeat_age_sec: float | None

    # Viewpoint
    viewpoint_status: str
    shift_score: float | None
    shift_confidence: float | None
    shift_detected: bool
    shift_detected_at: datetime | None
    fence_confidence_note: str | None

    # Trends (JSON-serializable)
    trends_json: dict | None

    # Issues (JSON-serializable)
    issues_json: dict | None

    # Operational impact
    impact_level: str | None
    coverage: str | None
    affected_modules: dict | None
    impact_message: str | None

    # Maintenance
    maintenance_recommended: bool
    maintenance_reason: str | None
    maintenance_duration: str | None
    maintenance_impact_note: str | None

    # Data source
    data_source: str
    last_updated: datetime

    # Metadata
    algorithm_version: str


class CameraHealthAnalyzer:
    """
    Main orchestrator for camera health analysis.
    
    Coordinates:
    - Image quality analysis
    - Viewpoint shift detection
    - Freeze detection
    - Baseline management
    - Trend analysis
    - State machine
    
    Produces complete health analysis ready for persistence and API response.
    """

    ALGORITHM_VERSION = "camera-health-v1.0"

    def __init__(self):
        self.state_engine = CameraHealthStateEngine()
        self.baseline_engine = BaselineEngine()
        self.trend_engine = TrendEngine()
        self.viewpoint_detector = ViewpointDetector()
        self.freeze_detector = FreezeDetector()
        self.image_quality_analyzer = ImageQualityAnalyzer()

        # Per-camera state
        self._last_analysis: dict[str, HealthAnalysisResult] = {}
        self._frame_buffers: dict[str, list] = {}

    def analyze_observation(
        self,
        camera_id: str,
        config: Any,
        source_timestamp: datetime,
        received_at: datetime,
        stream: StreamHealthMetrics | None = None,
        image: ImageQualityMetrics | None = None,
        network: NetworkMetrics | None = None,
        viewpoint: ViewpointMetrics | None = None,
        frame: np.ndarray | None = None,
        algorithm_version: str | None = None,
    ) -> HealthAnalysisResult:
        """
        Main analysis entry point.
        
        Accepts raw telemetry and optional frame, produces complete health analysis.
        """
        # Prepare input for state engine
        input_data = CameraHealthInput(
            camera_id=camera_id,
            config=config,
            source_timestamp=source_timestamp,
            received_at=received_at,
            stream=stream,
            image=image,
            network=network,
            viewpoint=viewpoint,
        )

        # Run enhanced analysis if frame provided
        if frame is not None:
            # Image quality
            iq_result = self.image_quality_analyzer.analyze(frame)
            if image is None:
                image = ImageQualityMetrics()
            image.sharpness = iq_result.sharpness
            image.brightness = iq_result.brightness
            image.exposure = iq_result.exposure
            image.contrast = iq_result.contrast
            image.noise = iq_result.noise

            # Update baseline with image quality metrics
            regime = iq_result.illumination_regime or IlluminationRegime.UNKNOWN
            self.baseline_engine.update(camera_id, "sharpness", iq_result.sharpness or 0, regime, is_healthy=True)
            self.baseline_engine.update(camera_id, "brightness", iq_result.brightness or 0, regime, is_healthy=True)

            # Viewpoint detection
            vp_result = self.viewpoint_detector.analyze(frame)
            if viewpoint is None:
                viewpoint = ViewpointMetrics()
            viewpoint.shift_score = vp_result.shift_score
            viewpoint.shift_confidence = vp_result.confidence
            viewpoint.reference_features = vp_result.inlier_ratio
            viewpoint.inlier_ratio = vp_result.inlier_ratio

            # Update baseline
            self.baseline_engine.update(camera_id, "viewpoint_shift", vp_result.shift_score, regime, is_healthy=not vp_result.shift_detected)

            # Freeze detection
            freeze_result = self.freeze_detector.analyze(frame, source_timestamp)
            # Freeze state is reflected in stream state by state engine

            # Add samples to trend engine
            self.trend_engine.add_sample("sharpness", source_timestamp, iq_result.sharpness or 0)
            self.trend_engine.add_sample("brightness", source_timestamp, iq_result.brightness or 0)
            if network and network.latency_ms:
                self.trend_engine.add_sample("latency", source_timestamp, network.latency_ms)

        # Run state machine
        derived = self.state_engine.derive_state(input_data)

        # Calculate trends
        trends = self._calculate_trends(camera_id)

        # Build issues from state
        issues = self._build_issues(camera_id, derived)

        # Determine operational impact
        impact = self._determine_operational_impact(derived)

        # Determine maintenance
        maintenance = self._determine_maintenance(camera_id, derived)

        # Determine data source
        data_source = self._determine_data_source(derived, source_timestamp)

        # Build result
        result = HealthAnalysisResult(
            camera_id=camera_id,
            source_timestamp=source_timestamp,
            received_at=received_at,
            overall_status=derived.overall_status,
            status_reason=derived.overall_reason,
            reliability=derived.reliability,
            stream_state=derived.stream_state.value,
            stream_reason=derived.stream_reason,
            fps=derived.fps,
            expected_fps=derived.expected_fps,
            frame_drop_percent=derived.frame_drop_percent,
            stale_seconds=derived.stale_seconds,
            reconnect_count=derived.reconnect_count,
            image_status=derived.image_status.value,
            sharpness_value=derived.image_metrics.get("sharpness", {}).get("value"),
            sharpness_status=derived.image_metrics.get("sharpness", {}).get("status"),
            sharpness_reason=derived.image_metrics.get("sharpness", {}).get("reason"),
            brightness_value=derived.image_metrics.get("brightness", {}).get("value"),
            brightness_status=derived.image_metrics.get("brightness", {}).get("status"),
            brightness_reason=derived.image_metrics.get("brightness", {}).get("reason"),
            exposure_status=derived.image_metrics.get("exposure", {}).get("status"),
            noise_status=derived.image_metrics.get("noise", {}).get("status"),
            background_stability=derived.background_stability,
            network_status=derived.network_status.value,
            network_reason=derived.network_reason,
            latency_ms=network.latency_ms if network else None,
            latency_variance_ms=network.latency_variance_ms if network else None,
            packet_loss_percent=network.packet_loss_percent if network else None,
            heartbeat_age_sec=network.heartbeat_age_sec if network else None,
            viewpoint_status=derived.viewpoint_status.value,
            shift_score=derived.shift_score,
            shift_confidence=derived.shift_confidence,
            shift_detected=derived.viewpoint_status in (CameraHealthState.VIEWPOINT_SHIFT_DETECTED, CameraHealthState.VIEWPOINT_SEVERE_SHIFT) if hasattr(CameraHealthState, 'VIEWPOINT_SHIFT_DETECTED') else False,
            shift_detected_at=derived.shift_detected_at,
            fence_confidence_note=derived.fence_confidence_note,
            trends_json=self._trends_to_json(trends),
            issues_json=self._issues_to_json(issues),
            impact_level=impact["level"],
            coverage=impact["coverage"],
            affected_modules=impact["affected_modules"],
            impact_message=impact["message"],
            maintenance_recommended=maintenance["recommended"],
            maintenance_reason=maintenance["reason"],
            maintenance_duration=maintenance["duration"],
            maintenance_impact_note=maintenance["impact_note"],
            data_source=derived.data_source,
            last_updated=datetime.now(),
            algorithm_version=algorithm_version or self.ALGORITHM_VERSION,
        )

        # Store for Component 1 integration
        self._last_analysis[camera_id] = result
        return result

    def _calculate_trends(self, camera_id: str) -> dict:
        """Calculate trends for all tracked metrics."""
        metrics = ["sharpness", "brightness", "latency"]
        trends = {}
        for metric in metrics:
            label = metric.capitalize()
            result = self.trend_engine.calculate_trend(metric, label)
            trends[metric] = {
                "metric": result.metric,
                "label": result.label,
                "direction": result.direction.value,
                "delta_percent": result.delta_percent,
                "window": result.window,
                "persistence": result.persistence,
                "series": result.series,
            }
        return trends

    def _trends_to_json(self, trends: dict) -> dict:
        return trends

    def _build_issues(self, camera_id: str, derived: Any) -> list[dict]:
        """Build deduplicated health issues from current state."""
        issues = []

        # Viewpoint shift issue
        if derived.viewpoint_status.value == "SHIFT_DETECTED":
            issues.append({
                "title": "Possible viewpoint shift",
                "impact": "HIGH",
                "reason": derived.fence_confidence_note or "Viewpoint shift detected",
                "affected_modules": ["Virtual Fence"],
            })
        elif derived.viewpoint_status.value == "SEVERE_SHIFT":
            issues.append({
                "title": "Severe viewpoint shift",
                "impact": "HIGH",
                "reason": derived.fence_confidence_note or "Severe viewpoint shift detected",
                "affected_modules": ["Virtual Fence"],
            })

        # Image quality degradation
        if derived.image_status.value in ("DEGRADED", "FAILED"):
            issues.append({
                "title": "Image sharpness degradation" if derived.sharpness_status == "DEGRADED" else "Image quality degraded",
                "impact": "MEDIUM",
                "reason": derived.sharpness_reason or "Image quality below baseline",
                "affected_modules": ["Detection", "Tracking"],
            })

        # Network degradation
        if derived.network_status.value == "DEGRADED":
            issues.append({
                "title": "Network degraded",
                "impact": "MEDIUM",
                "reason": derived.network_reason or "Network quality degraded",
                "affected_modules": ["Live visibility"],
            })

        # Stream issues
        if derived.stream_state.value in ("STALE", "FROZEN", "DISCONNECTED"):
            issues.append({
                "title": f"Stream {derived.stream_state.value.lower()}",
                "impact": "HIGH",
                "reason": derived.stream_reason or f"Stream {derived.stream_state.value.lower()}",
                "affected_modules": ["Virtual Fence", "Detection", "Live visibility"],
            })

        return issues

    def _issues_to_json(self, issues: list[dict]) -> dict:
        return {"issues": issues}

    def _determine_operational_impact(self, derived: Any) -> dict:
        """Determine operational impact from health state."""
        if derived.overall_status.value == "OFFLINE":
            return {
                "level": "COMPROMISED",
                "coverage": "COMPROMISED",
                "affected_modules": ["Virtual Fence", "Detection", "Live visibility"],
                "message": "Coverage compromised. Camera offline.",
            }
        elif derived.overall_status.value in ("FROZEN", "STALE"):
            return {
                "level": "DEGRADED",
                "coverage": "DEGRADED",
                "affected_modules": ["Virtual Fence", "Detection", "Live visibility"],
                "message": derived.overall_reason or "Camera feed unreliable.",
            }
        elif derived.overall_status.value == "DEGRADED":
            modules = []
            if derived.viewpoint_status.value in ("SHIFT_DETECTED", "SEVERE_SHIFT"):
                modules.append("Virtual Fence")
            if derived.image_status.value in ("DEGRADED", "FAILED"):
                modules.extend(["Detection", "Tracking"])
            if derived.network_status.value == "DEGRADED":
                modules.append("Live visibility")
            return {
                "level": "DEGRADED",
                "coverage": "DEGRADED",
                "affected_modules": list(set(modules)),
                "message": derived.overall_reason or "Camera health degraded.",
            }
        elif derived.overall_status.value == "ONLINE":
            return {
                "level": "NONE",
                "coverage": "NORMAL",
                "affected_modules": [],
                "message": "No current impact.",
            }
        else:
            return {
                "level": "UNKNOWN",
                "coverage": "UNKNOWN",
                "affected_modules": [],
                "message": "Health telemetry unavailable. State cannot be established.",
            }

    def _determine_maintenance(self, camera_id: str, derived: Any) -> dict:
        """Determine maintenance recommendation."""
        # Check trend engine for persistent degradation
        sharpness_trend = self.trend_engine.calculate_trend("sharpness", "Sharpness")
        if sharpness_trend.persistence_state.value == "MAINTENANCE_RECOMMENDED":
            return {
                "recommended": True,
                "reason": f"Sustained {sharpness_trend.metric} degradation over {sharpness_trend.persistence}",
                "duration": sharpness_trend.persistence,
                "impact_note": f"Lower {sharpness_trend.metric} quality for downstream analytics",
            }

        if derived.overall_status.value in ("OFFLINE", "FROZEN", "STALE"):
            return {
                "recommended": True,
                "reason": f"Camera {derived.overall_status.value.lower()}",
                "duration": "Unknown",
                "impact_note": "Coverage compromised until feed is restored",
            }

        return {"recommended": False}

    def _determine_data_source(self, derived: Any, source_ts: datetime) -> str:
        """Determine data source label."""
        now = datetime.now()
        age = (now - source_ts).total_seconds()
        if age > 60:
            return "LAST_KNOWN"
        return "LIVE"

    def get_latest_analysis(self, camera_id: str) -> Any:
        """Get latest analysis for Component 1 integration."""
        return self._last_analysis.get(camera_id)

    def get_health_context_for_component1(self, camera_id: str) -> dict | None:
        """
        Get health context for Component 1 integration.
        
        Returns the canonical signals that Component 1 expects:
        - viewpoint_shift_detected
        - fence_confidence_override
        - background_stability
        - reliability
        """
        analysis = self._last_analysis.get(camera_id)
        if not analysis:
            return None

        return {
            "camera_id": camera_id,
            "viewpoint_shift_detected": analysis.shift_detected,
            "fence_confidence_override": (
                "DEGRADED" if analysis.shift_detected else None
            ),
            "background_stability": analysis.background_stability,
            "reliability": analysis.reliability,
            "geometry_confidence": "LOW" if analysis.shift_detected else "HIGH",
            "uncertainty_margin": 0.05 if analysis.shift_detected else 0.02,
            "last_updated": analysis.last_updated.isoformat() if analysis.last_updated else None,
        }


# Global analyzer instance
camera_health_analyzer = CameraHealthAnalyzer()