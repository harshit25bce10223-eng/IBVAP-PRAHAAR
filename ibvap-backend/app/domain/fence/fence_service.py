# ─────────────────────────────────────────────────────────────────────────────
# IBVAP — Fence Service
# ─────────────────────────────────────────────────────────────────────────────
# Orchestrates geometry + rules to decide a track's membership in a zone and
# whether the configured rule passed (i.e. the object is allowed in that zone).
#
# Key distinction maintained throughout:
#   is_inside   — geometric containment of the representative point.
#   rule_passed — whether the configured rule ALLOWS this object in this zone
#                 (object-type gate), within the active time window.
#
# These two booleans are NEVER collapsed into one.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime, time, timedelta, timezone
from typing import Any

from app.domain.geometry.bbox import (
    get_representative_point,
    is_bbox_inside_zone,
)
from app.domain.geometry.point_in_polygon import check_point_in_polygon


def is_active_time_window(
    rules: dict[str, Any],
    current: datetime,
    tz: timezone = timezone.utc,
) -> bool:
    """Evaluate a zone's active time window.

    Supports windows that cross midnight, e.g. 18:00 -> 06:00.
    Endpoints are INCLUSIVE.

    A zone with no active window configured is considered always active.
    """
    start_s = rules.get("active_start")
    end_s = rules.get("active_end")
    if start_s is None or end_s is None:
        return True

    try:
        start = time.fromisoformat(str(start_s))
        end = time.fromisoformat(str(end_s))
    except ValueError:
        # Malformed window -> treat as always inactive rather than silently active.
        return False

    local = current.astimezone(tz)
    now = local.time()

    if start <= end:
        # Single-day window (no midnight crossing).
        return start <= now <= end

    # Crosses midnight: active from start until 23:59:59.999999, then 00:00 until end.
    if now >= start or now <= end:
        return True

    return now >= start or now <= end


def normalize_rules(rules: dict[str, Any] | None) -> dict[str, Any]:
    return rules if isinstance(rules, dict) else {}


def allowed_object_types(rules: dict[str, Any]) -> list[str] | None:
    """Return the allowed object-type list, or None if unrestricted."""
    raw = rules.get("allowed_object_types")
    if raw in (None, [], ""):
        return None
    if isinstance(raw, list):
        return [str(o).upper() for o in raw if o]
    return None


def object_allowed(rules: dict[str, Any], object_type: str, current: datetime) -> bool:
    """Check object-type gate AND active time window.

    Returns True when the configured rule explicitly allows this object and the
    current time is inside the active window.
    """
    allowed = allowed_object_types(rules)
    if allowed is not None and object_type.upper() not in allowed:
        return False
    return is_active_time_window(rules, current)


class ZoneMembershipResult:
    __slots__ = ("is_inside", "rule_passed")

    def __init__(self, is_inside: bool, rule_passed: bool) -> None:
        self.is_inside = is_inside
        self.rule_passed = rule_passed

    def to_dict(self) -> dict[str, bool]:
        return {"is_inside": self.is_inside, "rule_passed": self.rule_passed}


def evaluate_membership(
    bbox: dict[str, float],
    polygon: list[dict[str, float]],
    rules: dict[str, Any],
    object_type: str,
    current: datetime,
) -> ZoneMembershipResult:
    """Determine geometric membership and rule-pass status for a single bbox."""
    is_inside = is_bbox_inside_zone(bbox, polygon)
    rule_passed = object_allowed(rules, object_type, current)
    return ZoneMembershipResult(is_inside=is_inside, rule_passed=rule_passed)
