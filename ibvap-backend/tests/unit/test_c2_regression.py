# ─────────────────────────────────────────────────────────────────────────────
# Component 2 — Camera Health State Machine & Precedence Regression Suite
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import pytest

from app.domain.camera_health.state_engine import (
    CameraHealthInput,
    CameraHealthState,
    CameraHealthStateEngine,
    HealthMetricStatus,
    ImageQualityMetrics,
    NetworkMetrics,
    NetworkStatus,
    StreamHealthMetrics,
    StreamState,
    ViewpointMetrics,
    ViewpointStatus,
)


@dataclass
class DummyConfig:
    camera_id: str = "CAM-01"
    expected_fps: float = 25.0
    stale_after_seconds: float = 30.0
    offline_after_seconds: float = 60.0
    viewpoint_shift_threshold: float = 0.35
    min_ransac_inlier_ratio: float = 0.30
    sharpness_degraded_threshold: float = 0.50
    brightness_low_threshold: float = 0.10
    brightness_high_threshold: float = 0.90


def test_state_precedence_offline_over_degraded():
    """
    OFFLINE must take precedence over DEGRADED even when image and viewpoint
    are simultaneously degraded.
    """
    engine = CameraHealthStateEngine()
    config = DummyConfig()
    now = datetime.now(timezone.utc)

    # Stream disconnected + severe image degradation
    inp = CameraHealthInput(
        camera_id="CAM-01",
        config=config,
        source_timestamp=now,
        received_at=now,
        stream=StreamHealthMetrics(connected=False),
        image=ImageQualityMetrics(sharpness=0.1, brightness=0.05),
        network=NetworkMetrics(latency_ms=300),
        viewpoint=ViewpointMetrics(shift_score=0.8, shift_confidence=0.9),
    )

    derived = engine.derive_state(inp)
    assert derived.overall_status == CameraHealthState.OFFLINE
    assert derived.stream_state == StreamState.DISCONNECTED
    assert derived.reliability == "LOW"


def test_state_precedence_frozen_over_degraded():
    """
    FROZEN must take precedence over DEGRADED when stream is frozen.
    """
    engine = CameraHealthStateEngine()
    config = DummyConfig()
    now = datetime.now(timezone.utc)

    # Explicit FROZEN stream status with degraded image metrics
    inp = CameraHealthInput(
        camera_id="CAM-01",
        config=config,
        source_timestamp=now,
        received_at=now,
        stream=StreamHealthMetrics(connected=True, observed_fps=0.0),
        image=ImageQualityMetrics(sharpness=0.2),
        network=NetworkMetrics(latency_ms=250),
    )

    # Let's test the state engine directly
    stream_derived = {
        "state": StreamState.FROZEN,
        "reason": "Frame similarity persisted above threshold",
        "fps": 0.0,
        "expected_fps": 25.0,
        "frame_drop_percent": 100.0,
        "stale_seconds": 15.0,
        "reconnect_count": 0,
    }
    image_derived = {"status": HealthMetricStatus.DEGRADED, "metrics": {}, "background_stability": "Degraded"}
    network_derived = {"status": NetworkStatus.DEGRADED, "reason": "High latency"}
    viewpoint_derived = {"status": ViewpointStatus.STABLE, "shift_score": 0.05, "shift_confidence": 0.8, "detected_at": None, "fence_confidence_note": None}

    overall = engine._determine_overall_state(
        stream_derived, image_derived, network_derived, viewpoint_derived, config
    )
    assert overall["status"] == CameraHealthState.FROZEN
    assert "Frozen stream" in overall["reason"] or "Frame similarity" in overall["reason"]


def test_state_precedence_stale_over_degraded():
    """
    STALE must take precedence over DEGRADED when frame age exceeds stale threshold.
    """
    engine = CameraHealthStateEngine()
    config = DummyConfig(stale_after_seconds=30.0)

    stream_derived = {
        "state": StreamState.STALE,
        "reason": "No fresh frames for 45s",
        "fps": 5.0,
        "expected_fps": 25.0,
        "frame_drop_percent": 80.0,
        "stale_seconds": 45.0,
        "reconnect_count": 1,
    }
    image_derived = {"status": HealthMetricStatus.DEGRADED, "metrics": {}, "background_stability": "Degraded"}
    network_derived = {"status": NetworkStatus.DEGRADED, "reason": "High latency"}
    viewpoint_derived = {"status": ViewpointStatus.STABLE, "shift_score": 0.05, "shift_confidence": 0.8, "detected_at": None, "fence_confidence_note": None}

    overall = engine._determine_overall_state(
        stream_derived, image_derived, network_derived, viewpoint_derived, config
    )
    assert overall["status"] == CameraHealthState.STALE


def test_viewpoint_shift_and_severe_shift():
    """
    Tests viewpoint shift detection thresholding and severe shift.
    """
    engine = CameraHealthStateEngine()
    config = DummyConfig(viewpoint_shift_threshold=0.35, min_ransac_inlier_ratio=0.30)
    now = datetime.now(timezone.utc)

    # Moderate shift (0.45 >= 0.35, confidence 0.85 >= 0.30)
    inp_mod = CameraHealthInput(
        camera_id="CAM-01",
        config=config,
        source_timestamp=now,
        received_at=now,
        viewpoint=ViewpointMetrics(shift_score=0.45, shift_confidence=0.85),
    )
    res_mod = engine._derive_viewpoint(inp_mod, config)
    assert res_mod["status"] == ViewpointStatus.SHIFT_DETECTED
    assert "reduced until officer review" in res_mod["fence_confidence_note"]

    # Severe shift (0.78 >= 0.70)
    inp_sev = CameraHealthInput(
        camera_id="CAM-01",
        config=config,
        source_timestamp=now,
        received_at=now,
        viewpoint=ViewpointMetrics(shift_score=0.78, shift_confidence=0.90),
    )
    res_sev = engine._derive_viewpoint(inp_sev, config)
    assert res_sev["status"] == ViewpointStatus.SEVERE_SHIFT
    assert "severely reduced" in res_sev["fence_confidence_note"]


def test_degraded_dimensions_accounting():
    """
    Verifies that >= 2 degraded dimensions trigger DEGRADED status with detailed reason.
    """
    engine = CameraHealthStateEngine()
    config = DummyConfig()

    stream_derived = {
        "state": StreamState.CONNECTED,
        "reason": None,
        "fps": 25.0,
        "expected_fps": 25.0,
        "frame_drop_percent": 0.0,
        "stale_seconds": 1.0,
        "reconnect_count": 0,
    }
    # Dimension 1: image degraded
    image_derived = {"status": HealthMetricStatus.DEGRADED, "metrics": {}, "background_stability": "Degraded"}
    # Dimension 2: network degraded
    network_derived = {"status": NetworkStatus.DEGRADED, "reason": "High latency"}
    viewpoint_derived = {"status": ViewpointStatus.STABLE, "shift_score": 0.05, "shift_confidence": 0.8, "detected_at": None, "fence_confidence_note": None}

    overall = engine._determine_overall_state(
        stream_derived, image_derived, network_derived, viewpoint_derived, config
    )
    assert overall["status"] == CameraHealthState.DEGRADED
    assert "image quality degraded" in overall["reason"]
    assert "network degraded" in overall["reason"]


def test_nominal_online_state():
    """
    Verifies that fully healthy stream, image, and network result in ONLINE with HIGH reliability.
    """
    engine = CameraHealthStateEngine()
    config = DummyConfig()

    stream_derived = {
        "state": StreamState.CONNECTED,
        "reason": None,
        "fps": 25.0,
        "expected_fps": 25.0,
        "frame_drop_percent": 0.0,
        "stale_seconds": 1.0,
        "reconnect_count": 0,
    }
    image_derived = {"status": HealthMetricStatus.GOOD, "metrics": {}, "background_stability": "Stable"}
    network_derived = {"status": NetworkStatus.STABLE, "reason": None}
    viewpoint_derived = {"status": ViewpointStatus.STABLE, "shift_score": 0.02, "shift_confidence": 0.95, "detected_at": None, "fence_confidence_note": None}

    overall = engine._determine_overall_state(
        stream_derived, image_derived, network_derived, viewpoint_derived, config
    )
    assert overall["status"] == CameraHealthState.ONLINE
    assert overall["reliability"] == "HIGH"
    assert overall["reason"] is None


def test_camera_isolation():
    """
    Verifies that evaluating CAM-01 does not affect or mutate CAM-02 state.
    """
    engine = CameraHealthStateEngine()
    config1 = DummyConfig(camera_id="CAM-01")
    config2 = DummyConfig(camera_id="CAM-02")
    now = datetime.now(timezone.utc)

    inp1 = CameraHealthInput(
        camera_id="CAM-01",
        config=config1,
        source_timestamp=now,
        received_at=now,
        stream=StreamHealthMetrics(connected=False),
    )
    res1 = engine.derive_state(inp1)
    assert res1.overall_status == CameraHealthState.OFFLINE

    inp2 = CameraHealthInput(
        camera_id="CAM-02",
        config=config2,
        source_timestamp=now,
        received_at=now,
        stream=StreamHealthMetrics(connected=True, observed_fps=25.0),
        image=ImageQualityMetrics(sharpness=0.85, brightness=0.7),
        network=NetworkMetrics(latency_ms=25.0, packet_loss_percent=0.1),
        viewpoint=ViewpointMetrics(shift_score=0.01, shift_confidence=0.98),
    )
    res2 = engine.derive_state(inp2)
    assert res2.overall_status == CameraHealthState.ONLINE
    assert res1.overall_status == CameraHealthState.OFFLINE
