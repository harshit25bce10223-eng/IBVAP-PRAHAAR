# ─────────────────────────────────────────────────────────────────────────────
# Component 2 — Camera Health State Machine & Precedence Regression Suite
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import cv2
import numpy as np
import pytest

from app.domain.camera_health.analyzer import CameraHealthAnalyzer
from app.domain.camera_health.freeze import FreezeDetector
from app.domain.camera_health.provider import CameraHealthProviderImpl
from app.domain.camera_health.state_engine import (
    CameraHealthInput,
    CameraHealthState,
    CameraHealthStateEngine,
    FreezeMetrics,
    HealthMetricStatus,
    ImageQualityMetrics,
    NetworkMetrics,
    NetworkStatus,
    StreamHealthMetrics,
    StreamState,
    ViewpointMetrics,
    ViewpointStatus,
)
from app.domain.camera_health.trend_engine import TrendDirection, TrendEngine
from app.domain.camera_health.viewpoint import ViewpointDetector
from app.domain.geometry.calibration import CalibrationQuality
from app.domain.geometry.spatial_uncertainty import (
    GeometryConfidence,
    compute_geometry_confidence,
)
from app.domain.risk.risk_engine import calculate_risk


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


# ═════════════════════════════════════════════════════════════════════════════
# §41 Regression tests — one test block per repaired defect (F1–F13).
# These pin the repaired behaviour so it cannot silently regress.
# ═════════════════════════════════════════════════════════════════════════════


def _derived_bundle(
    *,
    stream_state: StreamState = StreamState.CONNECTED,
    image_status: HealthMetricStatus = HealthMetricStatus.GOOD,
    network_status: NetworkStatus = NetworkStatus.STABLE,
    viewpoint_status: ViewpointStatus = ViewpointStatus.STABLE,
    viewpoint_note: str | None = None,
):
    """Build the four dimension-derived dicts consumed by _determine_overall_state."""
    stream_derived = {
        "state": stream_state,
        "reason": None,
        "fps": 25.0,
        "expected_fps": 25.0,
        "frame_drop_percent": 0.0,
        "stale_seconds": 1.0,
        "reconnect_count": 0,
    }
    image_derived = {"status": image_status, "metrics": {}, "background_stability": "Stable"}
    network_derived = {"status": network_status, "reason": "High latency"}
    viewpoint_derived = {
        "status": viewpoint_status,
        "shift_score": 0.0,
        "shift_confidence": 0.0,
        "detected_at": None,
        "fence_confidence_note": viewpoint_note,
    }
    return stream_derived, image_derived, network_derived, viewpoint_derived


# ── F1/F9/F13: explicit state-precedence matrix (table-driven) ──────────────

@pytest.mark.parametrize(
    ("overrides", "expected_status", "expected_reliability", "reason_substrings"),
    [
        # Nominal
        ({}, CameraHealthState.ONLINE, "HIGH", ()),
        # Single self-degrading dimension → DEGRADED (F9 documented decision)
        ({"image_status": HealthMetricStatus.DEGRADED}, CameraHealthState.DEGRADED, "MEDIUM", ("image quality degraded",)),
        ({"image_status": HealthMetricStatus.FAILED}, CameraHealthState.DEGRADED, "MEDIUM", ("image quality failed",)),
        ({"network_status": NetworkStatus.DEGRADED}, CameraHealthState.DEGRADED, "MEDIUM", ("network degraded",)),
        ({"viewpoint_status": ViewpointStatus.SHIFT_DETECTED}, CameraHealthState.DEGRADED, "LOW", ("viewpoint shift detected",)),
        ({"viewpoint_status": ViewpointStatus.SEVERE_SHIFT}, CameraHealthState.DEGRADED, "LOW", ("severe viewpoint shift",)),
        # Single TRANSITORY stream dimension → UNKNOWN, never DEGRADED (F9)
        ({"stream_state": StreamState.DEGRADED}, CameraHealthState.UNKNOWN, "UNKNOWN", ("Insufficient telemetry",)),
        ({"stream_state": StreamState.RECONNECTING}, CameraHealthState.UNKNOWN, "UNKNOWN", ("Insufficient telemetry",)),
        # Volume precedence: OFFLINE > FROZEN > STALE > DEGRADED (F1/§38)
        ({"stream_state": StreamState.DISCONNECTED}, CameraHealthState.OFFLINE, "LOW", ()),
        ({"stream_state": StreamState.FROZEN}, CameraHealthState.FROZEN, None, ()),
        ({"stream_state": StreamState.STALE}, CameraHealthState.STALE, None, ()),
        # ≥2 degraded dimensions → DEGRADED with full reason list
        (
            {"image_status": HealthMetricStatus.DEGRADED, "network_status": NetworkStatus.DEGRADED},
            CameraHealthState.DEGRADED,
            "MEDIUM",
            ("image quality degraded", "network degraded"),
        ),
        # F13: viewpoint UNKNOWN must NOT block ONLINE (geometry confidence is
        # surfaced via fence_confidence_note, never auto-degraded)
        ({"viewpoint_status": ViewpointStatus.UNKNOWN}, CameraHealthState.ONLINE, "HIGH", ()),
    ],
)
def test_f9_f13_state_precedence_matrix(
    overrides, expected_status, expected_reliability, reason_substrings
):
    engine = CameraHealthStateEngine()
    config = DummyConfig()
    bundle = _derived_bundle(**overrides)

    result = engine._determine_overall_state(*bundle, config)

    # F1: the reason key must exist on EVERY path (KeyError:'reason' regression)
    for key in ("status", "reason", "reliability", "data_source"):
        assert key in result

    assert result["status"] == expected_status
    if expected_reliability is not None:
        assert result["reliability"] == expected_reliability
    for sub in reason_substrings:
        assert sub.lower() in (result["reason"] or "").lower()


# ── F5: viewpoint reference lifecycle ───────────────────────────────────────

class _StubIQ:
    """Minimal stand-in for ImageQualityResult for the provisioning gate."""

    def __init__(self, exposure=None, brightness=None):
        self.exposure = exposure
        self.brightness = brightness


def test_f5_reference_quality_gate_rejects_unusable_frames():
    analyzer = CameraHealthAnalyzer()
    assert analyzer._reference_quality_ok(_StubIQ(brightness=0.05)) is False  # near-black
    assert analyzer._reference_quality_ok(_StubIQ(brightness=0.95)) is False  # blown out
    assert analyzer._reference_quality_ok(_StubIQ(exposure="UNDEREXPOSED")) is False
    assert analyzer._reference_quality_ok(_StubIQ(exposure=None, brightness=None)) is True
    assert analyzer._reference_quality_ok(_StubIQ(exposure="NORMAL", brightness=0.5)) is True


def test_f5_low_texture_is_unknown_never_shift():
    """Flat scene: no reference can be seeded → UNKNOWN + note, never shift."""
    det = ViewpointDetector()
    flat = np.full((180, 320, 3), 128, dtype=np.uint8)
    assert det.set_reference(flat) is False
    assert det.is_initialized() is False

    engine = CameraHealthStateEngine()
    config = DummyConfig()
    now = datetime.now(timezone.utc)

    inp = CameraHealthInput(
        camera_id="CAM-01",
        config=config,
        source_timestamp=now,
        received_at=now,
        viewpoint=ViewpointMetrics(shift_score=0.0, shift_confidence=0.0, reference_active=False),
    )
    res = engine._derive_viewpoint(inp, config)
    assert res["status"] == ViewpointStatus.UNKNOWN
    assert "not initialized" in (res["fence_confidence_note"] or "")

    # And the overall verdict stays ONLINE — unknown geometry never auto-degrades
    bundle = _derived_bundle(viewpoint_status=ViewpointStatus.UNKNOWN, viewpoint_note=res["fence_confidence_note"])
    overall = engine._determine_overall_state(*bundle, config)
    assert overall["status"] == CameraHealthState.ONLINE


def _textured_scene(seed: int) -> np.ndarray:
    """Deterministic textured 'scene' frame — passes the provisioning quality
    gate (mid brightness, NORMAL exposure) unlike full-range uniform noise,
    which the image-quality analyzer correctly classifies as OVEREXPOSED."""
    rng = np.random.default_rng(seed)
    yy, xx = np.mgrid[0:180, 0:320]
    block = 8 + (seed % 5) * 4
    f = np.zeros((180, 320, 3), dtype=np.uint8)
    f[:, :, 0] = ((xx // block + yy // block) % 2) * 150 + 60
    f[:, :, 1] = (xx % 64) * 2 + 40
    f[:, :, 2] = (yy % 64) * 2 + 40
    return np.clip(
        f.astype(np.int16) + rng.integers(-15, 15, (180, 320, 3)), 0, 255
    ).astype(np.uint8)


def test_f5_reference_not_auto_replaced_only_explicit_refresh():
    """The reference is seeded once and only replaced by explicit refresh."""
    analyzer = CameraHealthAnalyzer()
    config = DummyConfig()
    camera_id = "CAM-F5"
    now = datetime.now(timezone.utc)
    stream = StreamHealthMetrics(connected=True, observed_fps=25.0)

    frame_a = _textured_scene(11)
    frame_b = _textured_scene(22)  # different block size + noise → different scene

    analyzer.analyze_observation(camera_id, config, now, now, stream=stream, frame=frame_a)
    det = analyzer._viewpoint_detectors[camera_id]
    assert det.is_initialized() is True
    assert det.reference_feature_count >= 30
    ref_before = det._reference_frame.copy()

    # A very different second scene must NOT silently become the reference
    analyzer.analyze_observation(camera_id, config, now, now, stream=stream, frame=frame_b)
    assert np.array_equal(det._reference_frame, ref_before)

    # The only sanctioned replacement: the explicit officer-confirmed refresh
    accepted = analyzer.refresh_viewpoint_reference(camera_id, frame_b)
    assert accepted is True
    assert not np.array_equal(det._reference_frame, ref_before)
    assert det._consecutive_shifts == 0


# ── F8: canonical time policy (naive = UTC; host-independent verdicts) ──────

def test_f8_as_utc_naive_is_utc_aware_converts():
    engine = CameraHealthStateEngine()
    trend = TrendEngine()
    naive = datetime(2026, 1, 1, 12, 0, 0)
    aware_ist = datetime(2026, 1, 1, 17, 30, 0, tzinfo=timezone(timedelta(hours=5, minutes=30)))
    expected = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    assert engine._as_utc(naive) == expected
    assert engine._as_utc(aware_ist) == expected
    assert trend._as_utc(naive) == expected
    assert trend._as_utc(aware_ist) == expected


def test_f8_stream_staleness_is_host_independent():
    engine = CameraHealthStateEngine()
    config = DummyConfig(stale_after_seconds=30.0)
    now_utc = datetime.now(timezone.utc)
    ist = timezone(timedelta(hours=5, minutes=30))
    streak = StreamHealthMetrics(connected=True, observed_fps=25.0)

    def stream_state(source_ts):
        inp = CameraHealthInput(
            camera_id="CAM-01",
            config=config,
            source_timestamp=source_ts,
            received_at=now_utc,
            stream=streak,
        )
        return engine._derive_stream_health(inp, config)["state"]

    # A naive timestamp is interpreted as UTC: 45s old → STALE, 5s old → fresh.
    # (If naive were read as host-local time, the 5s case would be STALE on an
    #  IST host — that regression is what this test pins.)
    assert stream_state((now_utc - timedelta(seconds=45)).replace(tzinfo=None)) == StreamState.STALE
    assert stream_state((now_utc - timedelta(seconds=5)).replace(tzinfo=None)) == StreamState.CONNECTED
    # Aware-IST timestamps convert correctly regardless of host timezone
    assert stream_state((now_utc - timedelta(seconds=45)).astimezone(ist)) == StreamState.STALE
    assert stream_state((now_utc - timedelta(seconds=5)).astimezone(ist)) == StreamState.CONNECTED


def test_f8_data_source_live_vs_last_known():
    analyzer = CameraHealthAnalyzer()
    now_utc = datetime.now(timezone.utc)
    ist = timezone(timedelta(hours=5, minutes=30))

    assert analyzer._determine_data_source(None, (now_utc - timedelta(seconds=10)).replace(tzinfo=None)) == "LIVE"
    assert analyzer._determine_data_source(None, (now_utc - timedelta(seconds=120)).replace(tzinfo=None)) == "LAST_KNOWN"
    assert analyzer._determine_data_source(None, (now_utc - timedelta(seconds=10)).astimezone(ist)) == "LIVE"
    assert analyzer._determine_data_source(None, (now_utc - timedelta(seconds=120)).astimezone(ist)) == "LAST_KNOWN"
    assert analyzer._determine_data_source(None, None) == "UNKNOWN"


# ── F4/F11: freeze detector — frozen evidence vs quiet-but-healthy ──────────

def test_freeze_bit_exact_repeated_frames_confirmed():
    det = FreezeDetector(persistence_frames=3)
    frame = np.random.default_rng(5).integers(0, 256, (180, 320, 3), dtype=np.uint8)
    t0 = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

    results = [det.analyze(frame, t0 + timedelta(seconds=i)) for i in range(5)]
    assert results[0].frozen is False  # first frame (no comparison yet)
    assert results[1].frozen is False  # static content 1/3
    assert results[2].frozen is False  # static content 2/3
    assert results[3].frozen is True   # confirmed at persistence
    assert "Bit-exact" in results[3].reason
    assert results[3].freeze_duration_sec is not None


def test_freeze_quiet_scene_with_sensor_noise_not_frozen():
    """A quiet-but-alive scene: real sensor noise keeps activity above the
    floor → NOT frozen, even well past the persistence window (F4/F11)."""
    rng = np.random.default_rng(42)
    h, w = 180, 320
    base = np.zeros((h, w, 3), dtype=np.uint8)
    base[:, :, 0] = np.linspace(60, 180, w, dtype=np.uint8)[None, :]
    base[:, :, 1] = np.linspace(90, 150, h, dtype=np.uint8)[:, None]
    base[:, :, 2] = 110

    det = FreezeDetector()  # production defaults: persistence 10, floor 0.001
    t0 = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

    verdicts = []
    for i in range(14):
        noise = rng.integers(0, 7, (h, w, 1), dtype=np.uint8).astype(np.int16) - 3
        frame = np.clip(base.astype(np.int16) + noise, 0, 255).astype(np.uint8)
        verdicts.append(det.analyze(frame, t0 + timedelta(seconds=i)))

    assert all(v.frozen is False for v in verdicts)
    assert "Frame content active" in verdicts[-1].reason


def test_freeze_localized_movement_vetoes_freeze():
    """Small real movement inside ONE ROI cell must veto FROZEN even though
    the median activity across the grid stays at the floor (F4 movement guard)."""
    h, w = 180, 320
    det = FreezeDetector()
    t0 = datetime(2026, 1, 1, 10, 0, 0, tzinfo=timezone.utc)

    def frame_with_patch(x, y):
        f = np.full((h, w, 3), 128, dtype=np.uint8)
        f[y:y + 24, x:x + 24] = 255
        return f

    # Both patch positions sit fully inside the first ROI cell
    verdicts = [
        det.analyze(frame_with_patch(*(2, 2) if i % 2 == 0 else (4, 10)), t0 + timedelta(seconds=i))
        for i in range(14)
    ]
    assert all(v.frozen is False for v in verdicts)
    assert any("Localized movement" in (v.reason or "") for v in verdicts)


def test_freeze_signal_reaches_state_engine_via_input():
    """F3: a persisted freeze verdict must drive the overall state to FROZEN."""
    engine = CameraHealthStateEngine()
    config = DummyConfig()
    now = datetime.now(timezone.utc)

    inp = CameraHealthInput(
        camera_id="CAM-01",
        config=config,
        source_timestamp=now,
        received_at=now,
        stream=StreamHealthMetrics(connected=True, observed_fps=25.0),
        image=ImageQualityMetrics(sharpness=0.85, brightness=0.7),
        network=NetworkMetrics(latency_ms=25.0),
        viewpoint=ViewpointMetrics(shift_score=0.01, shift_confidence=0.98),
        freeze=FreezeMetrics(frozen=True, confidence=0.99, freeze_duration_sec=12.0, reason="test freeze"),
    )
    res = engine.derive_state(inp)
    assert res.overall_status == CameraHealthState.FROZEN
    assert res.stream_state == StreamState.FROZEN
    assert "test freeze" in (res.overall_reason or "") or "Frozen stream" in (res.overall_reason or "")


# ── F3/F7: analyzer contract — frame signals reach the state engine ─────────

def test_f3_f7_blurred_frame_reaches_state_engine():
    import cv2

    analyzer = CameraHealthAnalyzer()
    config = DummyConfig()
    now = datetime.now(timezone.utc)

    sharp_frame = np.random.default_rng(13).integers(0, 256, (180, 320, 3), dtype=np.uint8)
    blurred = cv2.GaussianBlur(sharp_frame, (31, 31), 0)

    result = analyzer.analyze_observation(
        "CAM-BLUR",
        config,
        now,
        now,
        stream=StreamHealthMetrics(connected=True, observed_fps=25.0),
        network=NetworkMetrics(latency_ms=25.0),
        frame=blurred,
    )

    # F7: canonical sharpness fields populated (no field-name mismatch)
    assert result.sharpness_value is not None
    assert result.sharpness_value < config.sharpness_degraded_threshold
    sharpness_status = getattr(result.sharpness_status, "value", result.sharpness_status)
    assert sharpness_status in ("DEGRADED", "FAILED")

    # F3: the frame-derived degradation reached the state machine
    assert HealthMetricStatus(result.image_status) in (
        HealthMetricStatus.DEGRADED,
        HealthMetricStatus.FAILED,
    )
    assert result.overall_status == CameraHealthState.DEGRADED
    assert result.freeze_status == "NOT_FROZEN"


def test_freeze_end_to_end_through_analyzer():
    """Frozen feed through the full analyzer: freeze_status + overall FROZEN +
    F1 maintenance contract (all four keys populated)."""
    analyzer = CameraHealthAnalyzer()
    config = DummyConfig()
    camera_id = "CAM-FZ"
    frame = np.random.default_rng(3).integers(0, 256, (180, 320, 3), dtype=np.uint8)
    stream = StreamHealthMetrics(connected=True, observed_fps=25.0)
    network = NetworkMetrics(latency_ms=25.0, packet_loss_percent=0.1)
    now = datetime.now(timezone.utc)

    result = None
    for i in range(11):  # persistence (10) + first frame
        ts = now - timedelta(seconds=10 - i)
        result = analyzer.analyze_observation(
            camera_id, config, ts, now, stream=stream, network=network, frame=frame
        )

    assert result.freeze_status == "FROZEN"
    assert result.overall_status == CameraHealthState.FROZEN
    assert result.stream_state == StreamState.FROZEN
    assert result.freeze_duration_sec is not None

    # F1: maintenance contract — every key present and populated for FROZEN
    assert result.maintenance_recommended is True
    assert result.maintenance_reason is not None
    assert result.maintenance_duration is not None
    assert result.maintenance_impact_note is not None


# ── §43: observability fields on the analyzer result ────────────────────────

def test_43_observability_fields_present():
    analyzer = CameraHealthAnalyzer()
    config = DummyConfig()
    now = datetime.now(timezone.utc)
    frame = np.random.default_rng(9).integers(0, 256, (180, 320, 3), dtype=np.uint8)

    result = analyzer.analyze_observation(
        "CAM-OBS",
        config,
        now,
        now,
        stream=StreamHealthMetrics(connected=True, observed_fps=25.0),
        network=NetworkMetrics(latency_ms=25.0),
        frame=frame,
    )

    for field in (
        "camera_id",
        "observation_id",
        "overall_status",
        "image_status",
        "freeze_status",
        "viewpoint_status",
        "network_status",
        "analysis_duration_ms",
        "status_reason",
    ):
        assert hasattr(result, field)

    assert result.camera_id == "CAM-OBS"
    # observation_id is assigned by the API layer after the DB flush
    assert result.observation_id is None
    assert result.analysis_duration_ms is not None
    assert result.analysis_duration_ms >= 0.0


# ── F12: OpenCV dependency pinned for fresh-venv installs ───────────────────

def test_f12_requirements_pin_opencv_and_numpy():
    req = Path(__file__).resolve().parents[2] / "requirements.txt"
    text = req.read_text(encoding="utf-8")
    assert "opencv-python-headless==" in text
    assert "numpy==" in text


# ═════════════════════════════════════════════════════════════════════════════
# §16/§37 — C2 → C1 integration: health-context contract (C1 logic UNTOUCHED)
#
# §16 verbatim: "verify that C1 no longer receives viewpoint_shift_detected=False
#   during an actual shift. Do NOT directly modify C1 risk calculations."
# §37 verbatim: "Check that C1 receives the correct camera-health context.
#   Do not modify C1 risk logic."
#
# These tests exercise the EXISTING contract end-to-end: C2 analysis →
# get_health_context_for_component1 / CameraHealthProvider (the exact path C1
# services consume) → C1's own (unmodified) compute_geometry_confidence /
# calculate_risk consumers.
# ═════════════════════════════════════════════════════════════════════════════

_C1_CONTEXT_KEYS = {
    "camera_id",
    "viewpoint_shift_detected",
    "fence_confidence_override",
    "background_stability",
    "reliability",
    "geometry_confidence",
    "uncertainty_margin",
    "last_updated",
}


def _warp_viewpoint(img: np.ndarray, tx: float, ty: float, rot: float, zoom: float) -> np.ndarray:
    """Deterministic viewpoint change: rotate+zoom about center, then translate."""
    h, w = img.shape[:2]
    m = cv2.getRotationMatrix2D((w / 2.0, h / 2.0), rot, zoom)
    m[0, 2] += tx
    m[1, 2] += ty
    return cv2.warpAffine(img, m, (w, h), borderValue=(0, 0, 0))


def test_f6_frame_based_shift_reaches_c1_context():
    """§15/§16: a REAL frame-inferred viewpoint shift (warped scene, no injected
    telemetry) must reach C1 as viewpoint_shift_detected=True → DEGRADED geometry.
    F6 regression: the enum bug made this arrive as False during an actual shift."""
    analyzer = CameraHealthAnalyzer()
    provider = CameraHealthProviderImpl(analyzer)
    config = DummyConfig()
    camera_id = "CAM-F6-CHAIN"

    base = _textured_scene(11)
    frames = [base] + [_warp_viewpoint(base, 120.0, 4.0, 5.0, 1.15)] * 9
    now = datetime.now(timezone.utc)
    stream = StreamHealthMetrics(connected=True, observed_fps=25.0, frame_drop_rate=0.0)
    network = NetworkMetrics(
        latency_ms=25.0, latency_variance_ms=8.0, packet_loss_percent=0.1, heartbeat_age_sec=2.0
    )

    result = None
    for i, frame in enumerate(frames):
        cv2.setRNGSeed(4242 + i)  # pin ORB/RANSAC randomness for a stable verdict
        result = analyzer.analyze_observation(
            camera_id,
            config,
            now + timedelta(seconds=i),
            now + timedelta(seconds=i),
            stream=stream,
            network=network,
            frame=frame,
        )

    assert result.viewpoint_status == "SHIFT_DETECTED"
    assert result.shift_detected is True
    assert result.overall_status == CameraHealthState.DEGRADED
    assert result.reliability == "LOW"

    # CameraHealthProvider is the exact consumption path C1 services use.
    ctx = asyncio.run(provider.get_latest_health_context(camera_id))
    assert ctx is not None
    assert set(ctx) == _C1_CONTEXT_KEYS
    assert ctx["viewpoint_shift_detected"] is True
    assert ctx["fence_confidence_override"] == "DEGRADED"
    assert ctx["geometry_confidence"] == "LOW"
    assert ctx["uncertainty_margin"] == 0.05

    # C1's own (unmodified) consumer collapses the context to DEGRADED geometry:
    # an actual shift can no longer slip through as False.
    c1_confidence = compute_geometry_confidence(
        viewpoint_shift_detected=ctx["viewpoint_shift_detected"],
        calibration_quality=CalibrationQuality.HIGH,
        detection_confidence=0.9,
        fence_confidence_override=ctx["fence_confidence_override"],
    )
    assert c1_confidence == GeometryConfidence.DEGRADED


def test_f37_c1_context_four_scenarios():
    """§37: healthy / degraded / viewpoint-changed / offline — each must deliver
    the correct, complete context to C1 (verified via its unmodified consumers)."""
    config = DummyConfig()
    now = datetime.now(timezone.utc)
    healthy_stream = StreamHealthMetrics(connected=True, observed_fps=25.0)
    healthy_network = NetworkMetrics(latency_ms=25.0, packet_loss_percent=0.1)

    # ── Scenario 1: healthy camera → ONLINE, no false shift ──────────────────
    analyzer = CameraHealthAnalyzer()
    camera_id = "CAM-C1-HEALTHY"
    result = analyzer.analyze_observation(
        camera_id,
        config,
        now,
        now,
        stream=healthy_stream,
        network=healthy_network,
        frame=_textured_scene(31),
    )
    assert result.overall_status == CameraHealthState.ONLINE
    assert result.reliability == "HIGH"
    ctx = analyzer.get_health_context_for_component1(camera_id)
    assert set(ctx) == _C1_CONTEXT_KEYS
    assert ctx["viewpoint_shift_detected"] is False
    assert ctx["fence_confidence_override"] is None
    assert ctx["geometry_confidence"] == "HIGH"
    assert compute_geometry_confidence(False, CalibrationQuality.HIGH, 0.9, None) == (
        GeometryConfidence.HIGH
    )

    # ── Scenario 2: degraded camera (blur) → DEGRADED, reliability MEDIUM ────
    analyzer = CameraHealthAnalyzer()
    camera_id = "CAM-C1-DEGRADED"
    blurred = cv2.GaussianBlur(_textured_scene(11), (31, 31), 0)
    result = analyzer.analyze_observation(
        camera_id,
        config,
        now,
        now,
        stream=healthy_stream,
        network=healthy_network,
        frame=blurred,
    )
    assert result.overall_status == CameraHealthState.DEGRADED
    assert result.reliability == "MEDIUM"
    ctx = analyzer.get_health_context_for_component1(camera_id)
    assert set(ctx) == _C1_CONTEXT_KEYS
    assert ctx["viewpoint_shift_detected"] is False  # blur is NOT a viewpoint shift
    assert ctx["reliability"] == "MEDIUM"  # delivered to C1 for its own logic

    # ── Scenario 3: viewpoint changed → SHIFT_DETECTED → C1 DEGRADED ─────────
    analyzer = CameraHealthAnalyzer()
    camera_id = "CAM-C1-VIEWSHIFT"
    result = analyzer.analyze_observation(
        camera_id,
        config,
        now,
        now,
        stream=healthy_stream,
        network=healthy_network,
        viewpoint=ViewpointMetrics(
            shift_score=0.45, shift_confidence=0.8, inlier_ratio=0.8, reference_active=True
        ),
        frame=_textured_scene(11),
    )
    assert result.viewpoint_status == "SHIFT_DETECTED"
    assert result.shift_detected is True
    assert result.overall_status == CameraHealthState.DEGRADED
    ctx = analyzer.get_health_context_for_component1(camera_id)
    assert set(ctx) == _C1_CONTEXT_KEYS
    assert ctx["viewpoint_shift_detected"] is True
    assert ctx["fence_confidence_override"] == "DEGRADED"
    assert ctx["geometry_confidence"] == "LOW"
    assert ctx["uncertainty_margin"] == 0.05
    assert compute_geometry_confidence(True, CalibrationQuality.HIGH, 0.9, "DEGRADED") == (
        GeometryConfidence.DEGRADED
    )

    # ── Scenario 4: offline camera → OFFLINE; C1 consumes LOW reliability ────
    analyzer = CameraHealthAnalyzer()
    camera_id = "CAM-C1-OFFLINE"
    result = analyzer.analyze_observation(
        camera_id,
        config,
        now,
        now,
        stream=StreamHealthMetrics(connected=False),
    )
    assert result.overall_status == CameraHealthState.OFFLINE
    assert result.stream_state == StreamState.DISCONNECTED
    assert result.reliability == "LOW"
    ctx = analyzer.get_health_context_for_component1(camera_id)
    assert set(ctx) == _C1_CONTEXT_KEYS
    assert ctx["viewpoint_shift_detected"] is False
    assert ctx["reliability"] == "LOW"

    # C1's own (unmodified) risk engine consumes the C2 context value directly.
    risk = calculate_risk(
        object_type="HUMAN",
        zone_crossed=True,
        is_night=True,
        multi_camera_confirmed=False,
        confidence=0.9,
        reliability=ctx["reliability"],
    )
    low_rel = next(f for f in risk.factors if f["code"] == "LOW_RELIABILITY")
    assert low_rel["points"] == -15


# ─────────────────────────────────────────────────────────────────────────────
# §34 regression: real HTTP surface on a fresh (model-created) schema.
#
# Guards the clean-environment defects found during §34 API validation:
#   1. The ingest route persisted `shift_confidence` into camera_health_current
#      while neither the ORM model nor any migration defined that column →
#      every POST /health/observations answered HTTP 500
#      (SQLAlchemy CompileError: "Unconsumed column names: shift_confidence").
#   2. Config create/update/read passed camelCase schema fields straight to
#      the snake_case ORM (TypeError on create; silent no-op on update).
# The conftest `engine` fixture builds the schema from the ORM models, so a
# missing model column makes these tests fail the same way production did.
# ─────────────────────────────────────────────────────────────────────────────

_NORMAL_INGEST_BODY = {
    "sourceSequence": 1,
    "stream": {
        "streamConnected": True,
        "sequenceNumber": 1,
        "expectedFps": 25.0,
        "observedFps": 25.0,
        "frameDropRate": 0.0,
        "frameAgeMs": 1000.0,
        "reconnectCount": 0,
    },
    "network": {
        "latencyMs": 25.0,
        "latencyVarianceMs": 8.0,
        "packetLossPercent": 0.1,
        "heartbeatAgeSec": 2.0,
    },
    # measured evidence of benchmark sample C2-0001 (engine-level ONLINE)
    "image": {
        "sharpness": 0.76238,
        "brightness": 0.536535,
        "exposure": "NORMAL",
        "contrast": 0.599455,
        "noise": 0.651695,
    },
    "viewpoint": {
        "shiftScore": 0.01916,
        "shiftConfidence": 0.503145,
        "inlierRatio": 0.503145,
    },
    "algorithmVersion": "c2-regression-route",
}


def test_c2_ingest_route_roundtrip_on_fresh_schema(client):
    """Config create → ingest → GET /health must round-trip on a fresh DB."""
    cam = "C2TEST-INGEST"
    now = datetime.now(timezone.utc)

    # ENV=test does not auto-create configs on ingest — provision explicitly.
    r = client.post(f"/api/v1/cameras/{cam}/health/config", json={"cameraId": cam})
    assert r.status_code == 200, r.text
    assert r.json()["expectedFps"] == 25.0  # camelCase contract preserved

    body = dict(_NORMAL_INGEST_BODY, sourceTimestamp=now.isoformat())
    r = client.post(f"/api/v1/cameras/{cam}/health/observations", json=body)
    assert r.status_code == 200, r.text  # HTTP 500 before the shift_confidence fix
    j = r.json()
    assert j["accepted"] is True
    assert isinstance(j["observationId"], int) and j["observationId"] >= 1
    assert j["currentStatus"] == "ONLINE"

    h = client.get(f"/api/v1/cameras/{cam}/health")
    assert h.status_code == 200, h.text
    hj = h.json()
    assert hj["status"] == "ONLINE"
    assert hj["source"] == "LIVE"
    assert hj["lastUpdated"]  # timestamp round-trip present
    assert hj["stream"]["state"] == "CONNECTED"
    assert hj["image"]["status"] == "GOOD"
    assert hj["network"]["status"] == "STABLE"
    assert hj["viewpoint"]["status"] == "STABLE"
    assert hj["viewpoint"]["shiftDetected"] is False
    sharp = next(m for m in hj["image"]["metrics"] if m["metric"] == "sharpness")
    assert abs(sharp["value"] - 0.76238) < 1e-6  # telemetry echoed, not invented


def test_c2_ingest_duplicate_sequence_is_idempotent(client):
    """F17 (§35 browser QA): re-sending the same (camera_id, source_sequence)
    must not raise an unhandled UNIQUE-constraint 500. A duplicate sequence
    (adapter retry, camera reboot resetting the counter) updates the existing
    row, reports duplicate: true, and the derived state reflects the re-sent
    telemetry."""
    cam = "C2TEST-DUPSEQ"
    now = datetime.now(timezone.utc)

    r = client.post(f"/api/v1/cameras/{cam}/health/config", json={"cameraId": cam})
    assert r.status_code == 200, r.text

    body = dict(_NORMAL_INGEST_BODY, sourceTimestamp=now.isoformat())
    r1 = client.post(f"/api/v1/cameras/{cam}/health/observations", json=body)
    assert r1.status_code == 200, r1.text
    j1 = r1.json()
    assert j1["accepted"] is True
    assert j1["duplicate"] is False

    # Identical resend (retry after lost ACK): 200 + duplicate flag, same row.
    r2 = client.post(f"/api/v1/cameras/{cam}/health/observations", json=body)
    assert r2.status_code == 200, r2.text  # HTTP 500 before F17
    j2 = r2.json()
    assert j2["accepted"] is True
    assert j2["duplicate"] is True
    assert j2["observationId"] == j1["observationId"]

    # Sequence reuse carrying NEW telemetry (camera reboot): the row updates
    # and the current state must reflect the latest payload, not a stale one.
    blurred = {
        "sharpness": 0.200305, "brightness": 0.537587, "exposure": "NORMAL",
        "contrast": 0.566096, "noise": 0.931638,
    }
    body2 = dict(body, image=blurred)
    r3 = client.post(f"/api/v1/cameras/{cam}/health/observations", json=body2)
    assert r3.status_code == 200, r3.text
    assert r3.json()["duplicate"] is True
    assert r3.json()["currentStatus"] == "DEGRADED"

    h = client.get(f"/api/v1/cameras/{cam}/health")
    assert h.status_code == 200, h.text
    hj = h.json()
    assert hj["status"] == "DEGRADED"
    sharp = next(m for m in hj["image"]["metrics"] if m["metric"] == "sharpness")
    assert abs(sharp["value"] - 0.200305) < 1e-6  # updated row, not the old one


def test_c2_config_patch_persists_and_viewpoint_shift_snapshot(client):
    """PATCH config must persist; viewpoint shift must persist its lifecycle."""
    cam = "C2TEST-SHIFT"
    now = datetime.now(timezone.utc)

    r = client.post(f"/api/v1/cameras/{cam}/health/config", json={"cameraId": cam})
    assert r.status_code == 200, r.text

    r = client.patch(f"/api/v1/cameras/{cam}/health/config", json={"staleAfterSeconds": 45})
    assert r.status_code == 200, r.text
    assert r.json()["staleAfterSeconds"] == 45  # was a silent no-op before the fix
    r = client.get(f"/api/v1/cameras/{cam}/health/config")
    assert r.status_code == 200, r.text
    assert r.json()["staleAfterSeconds"] == 45  # persisted

    body = dict(_NORMAL_INGEST_BODY, sourceTimestamp=now.isoformat())
    # measured evidence of benchmark sample C2-0141 (VIEWPOINT_CHANGED)
    body["image"] = {
        "sharpness": 0.403431,
        "brightness": 0.447248,
        "exposure": "UNDEREXPOSED",
        "contrast": 0.862678,
        "noise": 0.723627,
    }
    body["viewpoint"] = {
        "shiftScore": 0.423052,
        "shiftConfidence": 0.631579,
        "inlierRatio": 0.631579,
    }
    r = client.post(f"/api/v1/cameras/{cam}/health/observations", json=body)
    assert r.status_code == 200, r.text
    assert r.json()["currentStatus"] == "DEGRADED"

    h = client.get(f"/api/v1/cameras/{cam}/health")
    assert h.status_code == 200, h.text
    vp = h.json()["viewpoint"]
    assert vp["status"] == "SHIFT_DETECTED"
    assert vp["shiftDetected"] is True
    assert vp["fenceConfidenceNote"]  # derived C1-facing context is persisted
    assert vp["detectedAt"]  # lifecycle timestamp persisted
    assert abs(vp["shiftScore"] - 0.423052) < 1e-6


def test_c2_history_buckets_utc_and_normalizes_offsets(client):
    """F8 write-side: an IST-offset sourceTimestamp must be persisted as the
    true UTC instant, appear in history within the default (to=now) window,
    and every emitted timestamp must carry an explicit UTC offset.

    §34 clean-environment defects: persisting the raw aware value stored the
    IST wall clock (SQLite drops tzinfo), shifting buckets +5:30 so they fell
    outside the to=now window; naive isoformat output broke recency checks.
    """
    cam = "C2TEST-HIST"
    ist = timezone(timedelta(hours=5, minutes=30))
    now_utc = datetime.now(timezone.utc)

    r = client.post(f"/api/v1/cameras/{cam}/health/config", json={"cameraId": cam})
    assert r.status_code == 200, r.text

    # Caller sends IST-local wall time (aware, +05:30) — same instant as now.
    body = dict(_NORMAL_INGEST_BODY, sourceTimestamp=now_utc.astimezone(ist).isoformat())
    r = client.post(f"/api/v1/cameras/{cam}/health/observations", json=body)
    assert r.status_code == 200, r.text

    # GET /health: lastUpdated must be explicit-UTC ISO and actually recent.
    h = client.get(f"/api/v1/cameras/{cam}/health")
    assert h.status_code == 200, h.text
    hj = h.json()
    assert hj["source"] == "LIVE"
    lu = datetime.fromisoformat(hj["lastUpdated"])
    assert lu.tzinfo is not None  # explicit offset, not a wall-clock string
    assert abs((now_utc - lu).total_seconds()) < 300

    # History default window (to=now): sample present, true UTC minute bucket.
    r = client.get(
        f"/api/v1/cameras/{cam}/health/history",
        params={"resolution": "1m", "limit": 10},
    )
    assert r.status_code == 200, r.text
    pts = r.json()["points"]
    assert pts, "observation missing from history (offset not normalized?)"
    pt = datetime.fromisoformat(pts[0]["timestamp"])
    assert pt.tzinfo is not None
    assert abs((now_utc - pt).total_seconds()) < 300

    # Mixed naive/aware range params must not raise (naive = UTC per F8).
    r = client.get(
        f"/api/v1/cameras/{cam}/health/history",
        params={"from": (now_utc - timedelta(hours=1)).replace(tzinfo=None).isoformat()},
    )
    assert r.status_code == 200, r.text
    r = client.get(
        f"/api/v1/cameras/{cam}/health/history",
        params={"to": now_utc.replace(tzinfo=None).isoformat()},
    )
    assert r.status_code == 200, r.text


# ── §42: TrendEngine slope cap — bounded cost, identical results <= cap ─────

def test_trend_engine_slope_cap_bit_identical_below_cap():
    """For k <= max_slope_samples the capped estimator must equal the all-pairs
    estimator (§33 digest safety: both benchmark corpora stay far below the
    cap). Two engines with different caps must produce identical results, and
    the exact delta for a known clean ramp must be the analytic value."""
    now = datetime(2026, 1, 10, 12, 0, 0, tzinfo=timezone.utc)

    def build(cap: int):
        engine = TrendEngine(max_slope_samples=cap)
        for i in range(40):
            engine.add_sample(
                "CAM-CAP", "sharpness",
                now - timedelta(hours=40 - i), 0.8 - i * 0.002,
            )
        return engine.calculate_trend("CAM-CAP", "sharpness", "Sharpness", now=now)

    a = build(100)   # cap far above k: no subsampling in effect
    b = build(1000)  # ditto
    assert a.delta_percent == b.delta_percent
    assert a.direction == b.direction
    assert a.direction == TrendDirection.DEGRADING
    assert a.series == b.series
    # Analytic check: -0.002 per hour on a first value of 0.8, extrapolated
    # over the 7-day window → -42.0 %.
    assert abs(a.delta_percent - (-42.0)) < 0.5


def test_trend_engine_slope_cap_engaged_is_deterministic_and_directional():
    """With k > cap the estimate comes from a uniform subsample: it must stay
    deterministic and preserve direction on a clean descending ramp."""
    now = datetime(2026, 1, 10, 12, 0, 0, tzinfo=timezone.utc)
    engine = TrendEngine(max_slope_samples=10)
    for i in range(100):
        engine.add_sample(
            "CAM-CAP2", "sharpness",
            now - timedelta(hours=100 - i), 0.9 - i * 0.009,
        )
    r1 = engine.calculate_trend("CAM-CAP2", "sharpness", "Sharpness", now=now)
    r2 = engine.calculate_trend("CAM-CAP2", "sharpness", "Sharpness", now=now)
    assert r1.direction == TrendDirection.DEGRADING
    assert r1.delta_percent == r2.delta_percent  # deterministic
    # Uniform subsampling of a linear ramp preserves the slope: same analytic
    # value as the uncapped estimator would give (0.9 → 0.009 ≈ -0.009/h).
    assert abs(r1.delta_percent - (-168.0)) < 1.0
    assert len(r1.series) == 50  # series still covers the full window
