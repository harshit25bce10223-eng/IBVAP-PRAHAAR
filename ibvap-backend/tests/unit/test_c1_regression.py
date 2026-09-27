# ─────────────────────────────────────────────────────────────────────────────
# Component 1 — Virtual Fence + Risk Engine Regression Test Suite
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime, timezone
import pytest

from app.core.errors import ZoneGeometryError
from app.domain.fence.fence_service import is_active_time_window, object_allowed
from app.domain.fence.membership import validate_polygon, polygon_area
from app.domain.risk.risk_engine import calculate_risk
from app.domain.risk.severity import severity_for_score


def test_polygon_validation_rules():
    # Valid triangle
    valid_triangle = [{"x": 0.1, "y": 0.1}, {"x": 0.5, "y": 0.1}, {"x": 0.3, "y": 0.5}]
    validate_polygon(valid_triangle)
    assert polygon_area(valid_triangle) > 0.0

    # Less than 3 points
    with pytest.raises(ZoneGeometryError, match="at least 3 points"):
        validate_polygon([{"x": 0.1, "y": 0.1}, {"x": 0.2, "y": 0.2}])

    # Out of bounds
    with pytest.raises(ZoneGeometryError, match="must be in range"):
        validate_polygon([{"x": -0.1, "y": 0.1}, {"x": 0.5, "y": 0.1}, {"x": 0.3, "y": 0.5}])

    # Degenerate collinear (zero area)
    collinear = [
        {"x": 0.1, "y": 0.1},
        {"x": 0.3, "y": 0.3},
        {"x": 0.5, "y": 0.5},
    ]
    with pytest.raises(ZoneGeometryError, match="zero area"):
        validate_polygon(collinear)

    # Self-intersecting polygon
    self_intersecting = [
        {"x": 0.1, "y": 0.1},
        {"x": 0.9, "y": 0.9},
        {"x": 0.9, "y": 0.2},
        {"x": 0.1, "y": 0.6},
    ]
    with pytest.raises(ZoneGeometryError, match="self-intersecting"):
        validate_polygon(self_intersecting)


def test_active_time_window_across_midnight():
    rules = {"active_start": "22:00", "active_end": "05:00"}
    
    # 23:30 UTC -> inside
    t1 = datetime(2026, 9, 23, 23, 30, tzinfo=timezone.utc)
    assert is_active_time_window(rules, t1) is True
    assert object_allowed(rules, "HUMAN", t1) is True

    # 03:15 UTC -> inside
    t2 = datetime(2026, 9, 23, 3, 15, tzinfo=timezone.utc)
    assert is_active_time_window(rules, t2) is True
    assert object_allowed(rules, "HUMAN", t2) is True

    # 12:00 UTC -> outside
    t3 = datetime(2026, 9, 23, 12, 0, tzinfo=timezone.utc)
    assert is_active_time_window(rules, t3) is False
    assert object_allowed(rules, "HUMAN", t3) is False


def test_active_time_window_daytime():
    rules = {"active_start": "08:00", "active_end": "17:00"}
    
    t_inside = datetime(2026, 9, 23, 12, 0, tzinfo=timezone.utc)
    assert is_active_time_window(rules, t_inside) is True

    t_outside = datetime(2026, 9, 23, 19, 0, tzinfo=timezone.utc)
    assert is_active_time_window(rules, t_outside) is False


def test_risk_engine_explainability_and_mitigation():
    # Human crossing at night with multi-camera and low reliability penalty
    res = calculate_risk(
        object_type="HUMAN",
        zone_crossed=True,
        is_night=True,
        multi_camera_confirmed=True,
        confidence=0.9,
        reliability="LOW",
    )
    # Expected factors:
    # RESTRICTED_ZONE_CROSSING (+25)
    # NIGHT_TIME (+20)
    # MULTI_CAMERA_CONFIRMATION (+15)
    # OBJECT_HUMAN (+15)
    # DETECTION_CONFIDENCE (0.9 * 20 = +18)
    # LOW_RELIABILITY (-15)
    # Total raw: 25 + 20 + 15 + 15 + 18 - 15 = 78 (HIGH)
    assert res.raw_score == 78
    assert res.risk_score == 78
    assert res.severity == "HIGH"
    
    # Check factor codes
    codes = [f["code"] for f in res.factors]
    assert "RESTRICTED_ZONE_CROSSING" in codes
    assert "NIGHT_TIME" in codes
    assert "MULTI_CAMERA_CONFIRMATION" in codes
    assert "OBJECT_HUMAN" in codes
    assert "DETECTION_CONFIDENCE" in codes
    assert "LOW_RELIABILITY" in codes

    # Low reliability penalty is negative points (mitigating)
    low_rel_factor = next(f for f in res.factors if f["code"] == "LOW_RELIABILITY")
    assert low_rel_factor["points"] == -15


def test_severity_thresholds():
    assert severity_for_score(0) == "LOW"
    assert severity_for_score(39) == "LOW"
    assert severity_for_score(40) == "MEDIUM"
    assert severity_for_score(64) == "MEDIUM"
    assert severity_for_score(65) == "HIGH"
    assert severity_for_score(84) == "HIGH"
    assert severity_for_score(85) == "CRITICAL"
    assert severity_for_score(100) == "CRITICAL"
