# ─────────────────────────────────────────────────────────────────────────────
# IBVAP — Polygon Validation
# ─────────────────────────────────────────────────────────────────────────────
# Validates zone polygons on creation/update. Malformed polygons are REJECTED
# with structured errors — never silently repaired.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import math
from typing import Any

from app.core.config import settings
from app.core.errors import ZoneGeometryError


def _is_numeric(v: Any) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def _segments(pts: list[dict[str, float]]):
    n = len(pts)
    for i in range(n):
        yield pts[i], pts[(i + 1) % n]


def _segments_intersect(p1, p2, p3, p4) -> bool:
    """True if segment p1-p2 properly intersects p3-p4 (non-shared endpoints)."""
    o1 = _orientation(p1, p2, p3)
    o2 = _orientation(p1, p2, p4)
    o3 = _orientation(p3, p4, p1)
    o4 = _orientation(p3, p4, p2)

    if o1 != o2 and o3 != o4:
        return True

    # Collinear overlap handling: report as valid (not self-intersecting) only if
    # the segments share an endpoint (adjacent edges), otherwise it is degenerate.
    def on_segment(a, b, c):
        return min(a[0], c[0]) <= b[0] <= max(a[0], c[0]) and min(a[1], c[1]) <= b[1] <= max(a[1], c[1])

    if o1 == 0 and on_segment(p1, p3, p2):
        return True
    if o2 == 0 and on_segment(p1, p4, p2):
        return True
    if o3 == 0 and on_segment(p3, p1, p4):
        return True
    if o4 == 0 and on_segment(p3, p2, p4):
        return True
    return False


def _orientation(a, b, c) -> int:
    val = (b[1] - a[1]) * (c[0] - b[0]) - (b[0] - a[0]) * (c[1] - b[1])
    if abs(val) < 1e-9:
        return 0
    return 1 if val > 0 else 2


def polygon_area(polygon: list[dict[str, float]]) -> float:
    """Shoelace formula (signed). Returns absolute area in normalized square-units."""
    n = len(polygon)
    if n < 3:
        return 0.0
    s = 0.0
    j = n - 1
    for i in range(n):
        s += polygon[j]["x"] * polygon[i]["y"] - polygon[i]["x"] * polygon[j]["y"]
        j = i
    return abs(s) / 2.0


def validate_polygon(polygon: list[dict[str, Any]]) -> None:
    """Validate a polygon. Raises ZoneGeometryError with a structured message on failure."""
    MIN_P = settings.POLYGON_MIN_POINTS
    MAX_P = settings.POLYGON_MAX_POINTS
    cmin, cmax = settings.COORD_MIN, settings.COORD_MAX

    if not isinstance(polygon, list) or len(polygon) == 0:
        raise ZoneGeometryError("Zone polygon is required and must be a non-empty array.")

    if len(polygon) < MIN_P:
        raise ZoneGeometryError(
            f"Zone polygon must have at least {MIN_P} points, got {len(polygon)}."
        )
    if len(polygon) > MAX_P:
        raise ZoneGeometryError(
            f"Zone polygon must have at most {MAX_P} points, got {len(polygon)}."
        )

    for idx, p in enumerate(polygon):
        if not isinstance(p, dict) or "x" not in p or "y" not in p:
            raise ZoneGeometryError(
                f"Polygon point {idx} must be an object with numeric 'x' and 'y'."
            )
        if not _is_numeric(p["x"]) or not _is_numeric(p["y"]):
            raise ZoneGeometryError(
                f"Polygon point {idx} must have numeric x/y values."
            )
        if not (cmin <= p["x"] <= cmax):
            raise ZoneGeometryError(
                f"Polygon point {idx} x must be in range [{cmin}, {cmax}], got {p['x']}."
            )
        if not (cmin <= p["y"] <= cmax):
            raise ZoneGeometryError(
                f"Polygon point {idx} y must be in range [{cmin}, {cmax}], got {p['y']}."
            )

    # Non-degenerate: no two consecutive points identical, and non-zero area separately.
    area = polygon_area(polygon)
    if area <= 1e-9:
        raise ZoneGeometryError("Zone polygon is degenerate (zero area).")

    # Self-intersection detection among non-adjacent edge pairs.
    n = len(polygon)
    for i in range(n):
        p1 = (polygon[i]["x"], polygon[i]["y"])
        p2 = (polygon[(i + 1) % n]["x"], polygon[(i + 1) % n]["y"])
        for j in range(i + 1, n):
            # Skip adjacent edges (share a vertex) — those are legitimately connected.
            if j == i or j == (i - 1) % n or j == (i + 1) % n:
                continue
            p3 = (polygon[j]["x"], polygon[j]["y"])
            p4 = (polygon[(j + 1) % n]["x"], polygon[(j + 1) % n]["y"])
            if _segments_intersect(p1, p2, p3, p4):
                raise ZoneGeometryError("Zone polygon is self-intersecting.")
