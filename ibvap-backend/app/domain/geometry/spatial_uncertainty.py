# ─────────────────────────────────────────────────────────────────────────────
# IBVAP — Spatial Uncertainty Engine
# ─────────────────────────────────────────────────────────────────────────────
# Replaces naive binary INSIDE/OUTSIDE with a three-state model:
#
#   DEFINITELY_OUTSIDE  — representative point is beyond the uncertainty margin
#   BOUNDARY_UNCERTAIN  — representative point is within the margin of the fence
#   DEFINITELY_INSIDE   — representative point is clearly inside
#
# Sources of uncertainty:
#   - Detection localization error (bbox jitter)
#   - Finite image resolution
#   - Camera calibration error (if applicable)
#   - Tracking instability
#
# DESIGN RULE:
#   A BOUNDARY_UNCERTAIN event must NOT immediately produce a confirmed-intrusion
#   incident. It requires temporal confirmation (see temporal_state.py).
#
# The margin is configurable per deployment. A margin of 0 collapses back to
# the binary model (maintaining backward compatibility).
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from enum import Enum
from typing import Any

from app.domain.geometry.point_in_polygon import check_point_in_polygon
from app.domain.geometry.calibration import CalibrationQuality


class SpatialZone(str, Enum):
    DEFINITELY_OUTSIDE  = "DEFINITELY_OUTSIDE"
    BOUNDARY_UNCERTAIN  = "BOUNDARY_UNCERTAIN"
    DEFINITELY_INSIDE   = "DEFINITELY_INSIDE"


class GeometryConfidence(str, Enum):
    HIGH     = "HIGH"     # stable camera, good calibration, low jitter
    MEDIUM   = "MEDIUM"   # minor uncertainty in one dimension
    LOW      = "LOW"      # multiple uncertainty sources active
    DEGRADED = "DEGRADED" # camera viewpoint shift or invalid calibration


def classify_spatial_zone(
    point: dict[str, float],
    polygon: list[dict[str, float]],
    uncertainty_margin: float = 0.0,
) -> SpatialZone:
    """
    Three-state spatial classification.

    Args:
        point: {x, y} normalized [0,1] representative point
        polygon: normalized fence polygon
        uncertainty_margin: distance margin (normalized units) around the fence
                            within which membership is UNCERTAIN.
                            0 = binary INSIDE/OUTSIDE (backward compatible).

    Returns:
        SpatialZone enum value
    """
    if uncertainty_margin <= 0.0:
        inside = check_point_in_polygon(point, polygon)
        return SpatialZone.DEFINITELY_INSIDE if inside else SpatialZone.DEFINITELY_OUTSIDE

    # Primary check
    inside = check_point_in_polygon(point, polygon)

    if inside:
        # Check if we're within the margin of the boundary (near edge inside)
        if _near_boundary(point, polygon, uncertainty_margin):
            return SpatialZone.BOUNDARY_UNCERTAIN
        return SpatialZone.DEFINITELY_INSIDE
    else:
        # Outside — check proximity to boundary
        if _near_boundary(point, polygon, uncertainty_margin):
            return SpatialZone.BOUNDARY_UNCERTAIN
        return SpatialZone.DEFINITELY_OUTSIDE


def _near_boundary(
    point: dict[str, float],
    polygon: list[dict[str, float]],
    margin: float,
) -> bool:
    """Return True if point is within `margin` normalized units of any polygon edge."""
    px, py = point["x"], point["y"]
    n = len(polygon)
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]["x"], polygon[i]["y"]
        xj, yj = polygon[j]["x"], polygon[j]["y"]
        dist = _point_to_segment_distance(px, py, xi, yi, xj, yj)
        if dist <= margin:
            return True
        j = i
    return False


def _point_to_segment_distance(
    px: float, py: float,
    ax: float, ay: float,
    bx: float, by: float,
) -> float:
    """Euclidean distance from point P to line segment AB in normalized space."""
    dx, dy = bx - ax, by - ay
    len_sq = dx*dx + dy*dy
    if len_sq < 1e-12:
        # Degenerate segment (A == B) — return distance to A
        return ((px - ax)**2 + (py - ay)**2) ** 0.5
    t = max(0.0, min(1.0, ((px - ax)*dx + (py - ay)*dy) / len_sq))
    closest_x = ax + t * dx
    closest_y = ay + t * dy
    return ((px - closest_x)**2 + (py - closest_y)**2) ** 0.5


def compute_geometry_confidence(
    viewpoint_shift_detected: bool,
    calibration_quality: CalibrationQuality,
    detection_confidence: float,
    fence_confidence_override: str | None = None,
) -> GeometryConfidence:
    """
    Aggregate camera/calibration/detection signals into a geometry confidence level.

    This is used to qualify intrusion evidence:
      - HIGH: stable camera, good calibration, decent detection
      - MEDIUM: minor issues in one dimension
      - LOW: multiple issues
      - DEGRADED: camera viewpoint shifted or calibration invalid

    Never silently trusts geometry when the camera itself is unstable.
    """
    # Hard overrides first
    if fence_confidence_override == "INVALID":
        return GeometryConfidence.DEGRADED
    if viewpoint_shift_detected:
        return GeometryConfidence.DEGRADED

    if calibration_quality == CalibrationQuality.INVALID:
        # No calibration — image-space only, but camera is stable
        calib_score = 0
    elif calibration_quality == CalibrationQuality.LOW:
        calib_score = 1
    elif calibration_quality == CalibrationQuality.MEDIUM:
        calib_score = 0
    else:  # HIGH
        calib_score = 0

    det_score = 0 if detection_confidence >= 0.7 else (1 if detection_confidence >= 0.4 else 2)

    total = calib_score + det_score

    if fence_confidence_override == "DEGRADED":
        return GeometryConfidence.LOW

    if total == 0:
        return GeometryConfidence.HIGH
    elif total == 1:
        return GeometryConfidence.MEDIUM
    else:
        return GeometryConfidence.LOW
