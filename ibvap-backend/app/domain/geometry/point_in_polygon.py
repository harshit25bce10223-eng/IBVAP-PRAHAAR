# ─────────────────────────────────────────────────────────────────────────────
# IBVAP — Point-in-Polygon (Ray Casting)
# ─────────────────────────────────────────────────────────────────────────────
# Baseline algorithm: ray casting (even-odd rule).
#
# BOUNDARY_POLICY:
#   Points lying exactly on a polygon edge are treated as INSIDE when the policy
#   is INCLUSIVE (the documented default). This gives deterministic, stable
#   alert behavior for objects resting on the fence line.
#
# The boundary policy is centralized here. Geometry abstractions (is_bbox_inside_zone,
# representative points) all route through this single authoritative function so the
# policy is never duplicated across modules.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from typing import Any

from app.core.config import settings

BOUNDARY_POLICY = settings.BOUNDARY_POLICY  # "INCLUSIVE" | "EXCLUSIVE"


def _on_segment(
    qx: float,
    qy: float,
    ax: float,
    ay: float,
    bx: float,
    by: float,
    eps: float = 1e-9,
) -> bool:
    """Return True if point Q lies on segment AB (within tolerance)."""
    cross = (bx - ax) * (qy - ay) - (by - ay) * (qx - ax)
    if abs(cross) > eps:
        return False
    if qx < min(ax, bx) - eps or qx > max(ax, bx) + eps:
        return False
    if qy < min(ay, by) - eps or qy > max(ay, by) + eps:
        return False
    return True


def check_point_in_polygon(point: dict[str, Any], polygon: list[dict[str, Any]]) -> bool:
    """Ray-casting hit test.

    Args:
        point: {"x": float, "y": float}
        polygon: [{"x": float, "y": float}, ...] — assumed closed implicitly.

    Returns:
        True if inside (respecting BOUNDARY_POLICY), False otherwise.
    """
    if not point or not polygon or len(polygon) < 3:
        return False

    px, py = float(point["x"]), float(point["y"])
    n = len(polygon)

    intersect_count = 0
    j = n - 1
    for i in range(n):
        xi, yi = float(polygon[i]["x"]), float(polygon[i]["y"])
        xj, yj = float(polygon[j]["x"]), float(polygon[j]["y"])

        # Boundary contact: point on edge => INSIDE when policy is INCLUSIVE (default).
        if BOUNDARY_POLICY == "INCLUSIVE" and _on_segment(px, py, xi, yi, xj, yj):
            return True

        # Ray-casting rule: upward / downward edge crossings.
        intersects = (yi > py) != (yj > py)
        if intersects:
            x_intersect = (xj - xi) * (py - yi) / (yj - yi) + xi
            if px < x_intersect:
                intersect_count += 1

        j = i

    return (intersect_count % 2) == 1
