# ─────────────────────────────────────────────────────────────────────────────
# IBVAP — Bounding Box Geometry
# ─────────────────────────────────────────────────────────────────────────────
# Bounding boxes use normalized coordinates:
#   { x, y, width, height }  where x,y = top-left corner, all in [0, 1].
#
# Representative-point selection is abstracted here so the strategy can be
# changed centrally without touching the rest of the system. The default
# (bottom-center) approximates ground contact for people & vehicles.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from typing import Any, Literal

from app.core.errors import InvalidBBoxError

BBox = dict[str, float]

RepresentativeStrategy = Literal["bottom_center", "center", "bottom_left", "bottom_right"]

_SUPPORTED_STRATEGIES: set[str] = {"bottom_center", "center", "bottom_left", "bottom_right"}
DEFAULT_STRATEGY: str = "bottom_center"


def get_bbox_center(bbox: BBox) -> dict[str, float]:
    """Return the exact geometric center of a bbox: {"x", "y"}."""
    x, y, w, h = bbox["x"], bbox["y"], bbox["width"], bbox["height"]
    return {"x": round(x + w / 2.0, 6), "y": round(y + h / 2.0, 6)}


def get_representative_point(
    bbox: BBox,
    strategy: RepresentativeStrategy | str = DEFAULT_STRATEGY,
) -> dict[str, float]:
    """Pick a representative point for membership testing.

    bottom_center (default): center of the bottom edge — best ground-contact proxy.
    center:                 geometric center.
    bottom_left             / bottom_right: bottom corners.
    """
    if strategy not in _SUPPORTED_STRATEGIES:
        raise InvalidBBoxError(f"Unknown representative strategy: {strategy}")

    x, y, w, h = bbox["x"], bbox["y"], bbox["width"], bbox["height"]

    if strategy == "bottom_center":
        return {"x": round(x + w / 2.0, 6), "y": round(y + h, 6)}
    if strategy == "center":
        return get_bbox_center(bbox)
    if strategy == "bottom_left":
        return {"x": round(x, 6), "y": round(y + h, 6)}
    if strategy == "bottom_right":
        return {"x": round(x + w, 6), "y": round(y + h, 6)}
    raise InvalidBBoxError(f"Unknown representative strategy: {strategy}")


def is_bbox_inside_zone(bbox: BBox, polygon: list[dict[str, float]]) -> bool:
    """Membership test using the configured representative-point strategy."""
    from app.domain.geometry.point_in_polygon import check_point_in_polygon

    rep = get_representative_point(bbox, strategy=DEFAULT_STRATEGY)
    return check_point_in_polygon(rep, polygon)
