# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — Camera Health Analyzer (Main Orchestrator)
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from time import perf_counter
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
    ViewpointStatus,
    FreezeMetrics,
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
    network_reason: str | None
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

    # Freeze observability (§43)
    freeze_status: str | None = None
    freeze_confidence: float | None = None
    freeze_duration_sec: float | None = None

    # Observability (§43)
    analysis_duration_ms: float | None = None
    observation_id: int | None = None
    quality_flags: dict | None = None


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
        self.image_quality_analyzer = ImageQualityAnalyzer()

        # Per-camera detector state (F5): freeze persistence and the viewpoint
        # reference lifecycle are per camera. A single shared detector leaked
        # state across cameras and made reference handling global.
        self._freeze_detectors: dict[str, FreezeDetector] = {}
        self._viewpoint_detectors: dict[str, ViewpointDetector] = {}

        # Per-camera state
        self._last_analysis: dict[str, HealthAnalysisResult] = {}
        self._frame_buffers: dict[str, list] = {}

    # ── Per-camera detector access (F5) ────────────────────────────────────

    def _freeze_detector_for(self, camera_id: str) -> FreezeDetector:
        det = self._freeze_detectors.get(camera_id)
        if det is None:
            det = FreezeDetector()
            self._freeze_detectors[camera_id] = det
        return det

    def _viewpoint_detector_for(self, camera_id: str) -> ViewpointDetector:
        det = self._viewpoint_detectors.get(camera_id)
        if det is None:
            det = ViewpointDetector()
            self._viewpoint_detectors[camera_id] = det
        return det

    def refresh_viewpoint_reference(self, camera_id: str, frame: np.ndarray) -> bool:
        """Officer-confirmed viewpoint reference refresh (F5).

        This is the ONLY way an EXISTING reference is replaced. The production
        analyze path never auto-replaces a reference; if the field of view is
        confirmed re-aligned by an officer (e.g. after maintenance), they call
        this explicitly with a fresh frame. Returns True when the new
        reference was accepted (frame passed provisioning quality + feature
        gates).
        """
        det = self._viewpoint_detector_for(camera_id)
        iq = self.image_quality_analyzer.analyze(frame)
        if not self._reference_quality_ok(iq):
            return False
        ok = det.set_reference(frame)
        if ok:
            det._consecutive_shifts = 0
        return ok

    @staticmethod
    def _reference_quality_ok(iq: Any) -> bool:
        """Provisioning quality gate (F5): never seed a reference from an
        unusable frame (near-black / blown-out / broken exposure). Feature
        adequacy is enforced separately by ViewpointDetector.set_reference."""
        if iq is None:
            return True
        if iq.exposure is not None and str(getattr(iq.exposure, "value", iq.exposure)) not in ("NORMAL", "UNKNOWN"):
            return False
        if iq.brightness is not None and (iq.brightness < 0.1 or iq.brightness > 0.9):
            return False
        return True

    def _frame_viewpoint_metrics(
        self, camera_id: str, frame: np.ndarray, iq_result: Any
    ) -> ViewpointMetrics:
        """Frame-derived viewpoint metrics with the F5 reference lifecycle.

        Provisioning: while no reference exists, each observation attempts to
        establish one from a quality-validated frame. A missing reference is
        reported explicitly (reference_active=False, viewpoint UNKNOWN
        downstream) — never as a shift, and never auto-degrading the camera.
        """
        det = self._viewpoint_detector_for(camera_id)

        if not det.is_initialized():
            if not self._reference_quality_ok(iq_result):
                return ViewpointMetrics(
                    shift_score=0.0, shift_confidence=0.0, reference_active=False
                )
            if det.set_reference(frame):
                return ViewpointMetrics(
                    shift_score=0.0,
                    shift_confidence=0.0,
                    reference_features=det.reference_feature_count,
                    reference_active=True,
                )
            # Frame is quality-valid but feature-poor (low texture): reference
            # cannot be established. Report explicitly, never auto-degrade.
            return ViewpointMetrics(
                shift_score=0.0, shift_confidence=0.0, reference_active=False
            )

        vp = det.analyze(frame)
        return ViewpointMetrics(
            shift_score=vp.shift_score,
            shift_confidence=vp.confidence,
            reference_features=det.reference_feature_count,
            inlier_ratio=vp.inlier_ratio,
            reference_active=True,
        )

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
        t_start = perf_counter()

        # ── Frame-derived analysis FIRST (F3): the state engine must receive
        # the COMPLETE observation. Previously the state input was built from
        # caller telemetry BEFORE frame analysis and the frame-derived image
        # metrics / viewpoint / freeze signals were written afterwards — so
        # blurs, dark scenes and frozen feeds never reached the state machine.
        # Policy: caller telemetry wins where present; frame analysis fills
        # what is absent.
        iq_result = None
        freeze_metrics = None
        if frame is not None:
            # Image quality (also gates viewpoint reference provisioning, F5)
            iq_result = self.image_quality_analyzer.analyze(frame)
            if image is None:
                image = ImageQualityMetrics()
            if image.sharpness is None:
                image.sharpness = iq_result.sharpness
            if image.brightness is None:
                image.brightness = iq_result.brightness
            if image.exposure is None:
                image.exposure = iq_result.exposure
            if image.contrast is None:
                image.contrast = iq_result.contrast
            if image.noise is None:
                image.noise = iq_result.noise

            # Viewpoint: caller-provided shift evidence wins (e.g. edge node
            # computed it); otherwise derive from the frame through the F5
            # reference lifecycle.
            if viewpoint is None or viewpoint.shift_score is None:
                viewpoint = self._frame_viewpoint_metrics(camera_id, frame, iq_result)

            # Freeze: per-camera detector state, persistence across calls
            freeze_result = self._freeze_detector_for(camera_id).analyze(
                frame, source_timestamp
            )
            freeze_metrics = FreezeMetrics(
                frozen=bool(freeze_result.frozen),
                confidence=freeze_result.confidence,
                freeze_duration_sec=freeze_result.freeze_duration_sec,
                reason=freeze_result.reason,
            )

            # Baseline updates (observational records; no state decisions)
            regime = iq_result.illumination_regime or IlluminationRegime.UNKNOWN
            self.baseline_engine.update(
                camera_id, "sharpness", iq_result.sharpness or 0, regime, is_healthy=True
            )
            self.baseline_engine.update(
                camera_id, "brightness", iq_result.brightness or 0, regime, is_healthy=True
            )
            eff_score = viewpoint.shift_score if viewpoint.shift_score is not None else 0.0
            eff_conf = viewpoint.shift_confidence if viewpoint.shift_confidence is not None else 0.0
            shift_now = bool(
                viewpoint.reference_active is not False
                and eff_score >= getattr(config, "viewpoint_shift_threshold", 0.3)
                and eff_conf >= getattr(config, "min_ransac_inlier_ratio", 0.5)
            )
            self.baseline_engine.update(
                camera_id, "viewpoint_shift", eff_score, regime, is_healthy=not shift_now
            )

            # Trend samples (camera-keyed; F8 normalization happens in the
            # trend engine)
            self.trend_engine.add_sample(camera_id, "sharpness", source_timestamp, iq_result.sharpness or 0)
            self.trend_engine.add_sample(camera_id, "brightness", source_timestamp, iq_result.brightness or 0)
            if network and network.latency_ms is not None:
                self.trend_engine.add_sample(camera_id, "latency", source_timestamp, network.latency_ms)

        # Build the COMPLETE observation input for the state engine
        input_data = CameraHealthInput(
            camera_id=camera_id,
            config=config,
            source_timestamp=source_timestamp,
            received_at=received_at,
            stream=stream,
            image=image,
            network=network,
            viewpoint=viewpoint,
            freeze=freeze_metrics,
            algorithm_version=algorithm_version,
        )

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
            shift_detected=derived.viewpoint_status in (
                ViewpointStatus.SHIFT_DETECTED,
                ViewpointStatus.SEVERE_SHIFT,
            ),
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
            last_updated=datetime.now(timezone.utc),
            algorithm_version=algorithm_version or self.ALGORITHM_VERSION,
            freeze_status=(
                None if freeze_metrics is None
                else ("FROZEN" if freeze_metrics.frozen else "NOT_FROZEN")
            ),
            freeze_confidence=freeze_metrics.confidence if freeze_metrics else None,
            freeze_duration_sec=freeze_metrics.freeze_duration_sec if freeze_metrics else None,
            analysis_duration_ms=round((perf_counter() - t_start) * 1000, 3),
            quality_flags=self._build_quality_flags(derived),
        )

        # Store for Component 1 integration
        self._last_analysis[camera_id] = result
        return result

    def _calculate_trends(self, camera_id: str) -> dict:
        """Calculate trends for all tracked metrics (camera-keyed series)."""
        metrics = ["sharpness", "brightness", "latency"]
        trends = {}
        for metric in metrics:
            label = metric.capitalize()
            result = self.trend_engine.calculate_trend(camera_id, metric, label)
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

        # Image quality degradation (F7: canonical representation — read from
        # derived.image_metrics, the single source the state engine produces;
        # never from non-existent top-level derived attributes)
        if derived.image_status.value in ("DEGRADED", "FAILED"):
            degraded_metric = None
            degraded_reason = None
            for m_name, m_info in (derived.image_metrics or {}).items():
                m_status = getattr(m_info.get("status"), "value", m_info.get("status"))
                if m_status in ("DEGRADED", "FAILED"):
                    degraded_metric = m_name
                    degraded_reason = m_info.get("reason")
                    break
            issues.append({
                "title": (
                    f"Image {degraded_metric} degradation"
                    if degraded_metric else "Image quality degraded"
                ),
                "impact": "MEDIUM",
                "reason": degraded_reason or "Image quality below baseline",
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
        """Determine maintenance recommendation.

        F1: EVERY path returns the full contract
        {recommended, reason, duration, impact_note} — the previous fall-through
        path returned {"recommended": False} only and crashed the result
        builder with KeyError('reason') on every nominal sample.
        """
        # Check trend engine for persistent degradation
        sharpness_trend = self.trend_engine.calculate_trend(camera_id, "sharpness", "Sharpness")
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

        return {
            "recommended": False,
            "reason": None,
            "duration": None,
            "impact_note": None,
        }

    def _determine_data_source(self, derived: Any, source_ts: datetime | None) -> str:
        """Determine data source label.

        F8: one canonical time policy — aware-UTC internally; a naive
        timestamp is interpreted as UTC (same documented rule as
        CameraHealthStateEngine._as_utc). The previous naive local `now`
        made every age ~+5.5h on an IST host (always LAST_KNOWN).
        """
        if source_ts is None:
            return "UNKNOWN"
        ts = source_ts if source_ts.tzinfo is not None else source_ts.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - ts.astimezone(timezone.utc)).total_seconds()
        if age > 60:
            return "LAST_KNOWN"
        return "LIVE"

    @staticmethod
    def _build_quality_flags(derived: Any) -> dict:
        """Compact machine-readable quality flags for storage/API (§43)."""
        return {
            "stream_state": derived.stream_state.value,
            "image_status": derived.image_status.value,
            "network_status": derived.network_status.value,
            "viewpoint_status": derived.viewpoint_status.value,
            "background_stability": derived.background_stability,
            "shift_detected": derived.viewpoint_status in (
                ViewpointStatus.SHIFT_DETECTED,
                ViewpointStatus.SEVERE_SHIFT,
            ),
            "data_source": derived.data_source,
        }

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