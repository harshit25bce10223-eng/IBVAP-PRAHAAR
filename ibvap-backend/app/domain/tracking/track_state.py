# ─────────────────────────────────────────────────────────────────────────────
# IBVAP — Track State helpers
# ─────────────────────────────────────────────────────────────────────────────
# Pure helpers for the membership state machine. The DATABASE is the source of
# truth for persisted values; these functions only compute transitions from
# previous + current membership booleans.
#
#   OUTSIDE -> INSIDE  => ENTRY   (fires exactly once per crossing)
#   INSIDE  -> INSIDE  => STABLE  (no event, no duplicate incident)
#   INSIDE  -> OUTSIDE => EXIT
#
# Deduplication strategy:
#   ENTRY keys embed a GENERATION counter: camera|track|zone|ENTRY|<gen>.
#   gen = number of prior ENTRY events for that (camera, track, zone).
#   Re-entry therefore yields gen+1 and a NEW incident (spec §8), while repeated
#   frames within a single crossing yield the SAME key (spec §21), which the
#   unique DB constraint rejects.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime, timezone
import json
from typing import Any

from app.core.config import settings

Position = dict[str, Any]  # {"x": float, "y": float, "ts": str}

MAX_PATH = settings.TRACK_PATH_MAX_POSITIONS


def append_position(path: list[Position] | None, pos: Position) -> list[Position]:
    """Append a timestamped position, bounded to MAX_PATH entries (drop oldest)."""
    if path is None:
        path = []
    path = [dict(p) for p in path]  # defensive copy
    path.append(pos)
    if len(path) > MAX_PATH:
        path = path[-MAX_PATH:]
    return path


def membership_transition(prev_inside: bool | None, cur_inside: bool) -> str:
    """Return 'ENTRY', 'EXIT', 'STABLE_INSIDE', 'STABLE_OUTSIDE' or 'FIRST'."""
    if prev_inside is None:
        return "FIRST"
    if cur_inside and not prev_inside:
        return "ENTRY"
    if not cur_inside and prev_inside:
        return "EXIT"
    return "STABLE_INSIDE" if cur_inside else "STABLE_OUTSIDE"


def was_inside(prev: bool | None) -> bool:
    return bool(prev) if prev is not None else False


def parse_membership(json_str: str | None) -> dict[str, bool]:
    """Deserialize the persisted membership snapshot into {zone_id: bool}."""
    if not json_str:
        return {}
    try:
        raw = json.loads(json_str)
    except (ValueError, TypeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {str(k): bool(v) for k, v in raw.items()}


def parse_path(json_str: str | None) -> list[Position]:
    """Deserialize a persisted timestamped path."""
    if not json_str:
        return []
    try:
        raw = json.loads(json_str)
    except (ValueError, TypeError):
        return []
    if not isinstance(raw, list):
        return []
    out = []
    for item in raw:
        if isinstance(item, dict) and "x" in item and "y" in item:
            out.append(item)
    return out


def dedup_key(
    camera_id: str,
    track_id: str,
    zone_id: str,
    transition: str,
    generation: int = 0,
) -> str:
    """Stable idempotency key for a crossing.

    ENTRY: camera|track|zone|ENTRY|<generation of this crossing>
    EXIT:  camera|track|zone|EXIT|<generation>
    """
    kind = "ENTRY" if transition == "ENTRY" else "EXIT"
    return f"{camera_id}|{track_id}|{zone_id}|{kind}|{generation}"


def entry_generation_prefix(camera_id: str, track_id: str, zone_id: str) -> str:
    return f"{camera_id}|{track_id}|{zone_id}|ENTRY|"


def utcnow() -> datetime:
    return datetime.now(timezone.utc)