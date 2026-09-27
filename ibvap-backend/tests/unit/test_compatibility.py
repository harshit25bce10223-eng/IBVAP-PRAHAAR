"""Component 4 — Compatibility Matrix Tests."""

from __future__ import annotations

import pytest

from app.domain.event_correlation.compatibility import (
    get_compatibility,
    get_event_type_compatibility,
    DEFAULT_COMPATIBILITY_MATRIX,
)


class TestCompatibilityMatrix:
    """Tests for event type compatibility matrix."""

    def test_default_matrix_exists(self):
        """Default matrix is defined."""
        assert DEFAULT_COMPATIBILITY_MATRIX is not None
        assert isinstance(DEFAULT_COMPATIBILITY_MATRIX, dict)
        assert "VIRTUAL_FENCE" in DEFAULT_COMPATIBILITY_MATRIX

    def test_virtual_fence_detection_compatible(self):
        """VIRTUAL_FENCE and DETECTION are compatible."""
        score = get_compatibility("VIRTUAL_FENCE", "DETECTION")
        assert score == 80

    def test_detection_tracking_strong(self):
        """DETECTION and TRACKING are strongly compatible."""
        score = get_compatibility("DETECTION", "TRACKING")
        assert score == 95

    def test_anpr_detection_compatible(self):
        """ANPR and DETECTION are compatible."""
        score = get_compatibility("ANPR", "DETECTION")
        assert score == 60

    def test_audio_anomaly_low_compatibility(self):
        """AUDIO_ANOMALY has low compatibility with visual events."""
        score = get_compatibility("AUDIO", "DETECTION")
        assert score == 40

    def test_same_type_high_compatibility(self):
        """Same event type has high compatibility."""
        score = get_compatibility("DETECTION", "DETECTION")
        assert score == 90

    def test_symmetric(self):
        """Compatibility is symmetric."""
        score1 = get_compatibility("DETECTION", "TRACKING")
        score2 = get_compatibility("TRACKING", "DETECTION")
        assert score1 == score2

    def test_unknown_type_defaults(self):
        """Unknown types return default low compatibility."""
        score = get_compatibility("UNKNOWN_TYPE", "DETECTION")
        assert score == 20


class TestEventTypeCompatibility:
    """Tests for get_event_type_compatibility."""

    def test_returns_int(self):
        """Returns integer score."""
        result = get_event_type_compatibility("DETECTION", "ZONE_ENTRY")
        assert isinstance(result, int)

    def test_strong_pairs(self):
        """Strong pairs return 80."""
        score = get_event_type_compatibility("ZONE_ENTRY", "DETECTION")
        assert score == 80

    def test_weak_pairs(self):
        """Weak pairs return 30."""
        score = get_event_type_compatibility("ZONE_ENTRY", "AUDIO_ANOMALY")
        assert score == 30

    def test_symmetric(self):
        """Event type compatibility is symmetric."""
        score1 = get_event_type_compatibility("ZONE_ENTRY", "DETECTION")
        score2 = get_event_type_compatibility("DETECTION", "ZONE_ENTRY")
        assert score1 == score2