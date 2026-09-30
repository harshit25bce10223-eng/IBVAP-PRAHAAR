# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 7 — ANPR Constants
#
# All canonical string literals used across the ANPR domain.
# Mirrors frontend types/anpr.ts
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from typing import Literal

# ── Plate quality ─────────────────────────────────────────────────────────────
PlateQuality = Literal[
    "GOOD", "FAIR", "POOR", "UNREADABLE", "PARTIAL",
    "GLARE", "MOTION_BLUR", "OCCLUDED", "EXTREME_ANGLE", "DIRTY", "LOW_LIGHT", "UNKNOWN",
]

PLATE_QUALITIES = ["GOOD", "FAIR", "POOR", "UNREADABLE", "PARTIAL", "GLARE", "MOTION_BLUR", "OCCLUDED", "EXTREME_ANGLE", "DIRTY", "LOW_LIGHT", "UNKNOWN"]

# ── Vehicle class ─────────────────────────────────────────────────────────────
VehicleClass = Literal[
    "PERSONAL_CAR", "SUV", "TRUCK", "BUS", "VAN",
    "MOTORCYCLE", "SCOOTER", "TRACTOR", "THREE_WHEELER", "UTILITY", "OTHER", "UNKNOWN",
]

VEHICLE_CLASSES = ["PERSONAL_CAR", "SUV", "TRUCK", "BUS", "VAN", "MOTORCYCLE", "SCOOTER", "TRACTOR", "THREE_WHEELER", "UTILITY", "OTHER", "UNKNOWN"]

# C7 §10 — preserve the canonical repository class taxonomy. Callers (edge
# sync, harnesses, other components) may send looser vocabulary ("CAR",
# "BIKE", …); normalize it at the persistence boundary instead of storing
# non-canonical values (same normalizer principle as C5 §20). Unmapped
# values become UNKNOWN — never stored raw.
_VEHICLE_CLASS_SET = set(VEHICLE_CLASSES)
_VEHICLE_CLASS_SYNONYMS = {
    "CAR": "PERSONAL_CAR",
    "SEDAN": "PERSONAL_CAR",
    "HATCHBACK": "PERSONAL_CAR",
    "MOTORBIKE": "MOTORCYCLE",
    "BIKE": "MOTORCYCLE",
    "LORRY": "TRUCK",
    "AUTO": "THREE_WHEELER",
    "AUTO_RICKSHAW": "THREE_WHEELER",
    "RICKSHAW": "THREE_WHEELER",
}


def normalize_vehicle_class(value: str | None) -> str:
    """Map caller vocabulary onto the canonical VEHICLE_CLASSES taxonomy."""
    token = (value or "").strip().upper()
    if token in _VEHICLE_CLASS_SET:
        return token
    return _VEHICLE_CLASS_SYNONYMS.get(token, "UNKNOWN")

# ── Vehicle color ─────────────────────────────────────────────────────────────
VehicleColor = Literal[
    "WHITE", "BLACK", "GREY", "SILVER", "RED", "BLUE",
    "GREEN", "YELLOW", "BROWN", "OTHER", "UNKNOWN",
]

VEHICLE_COLORS = ["WHITE", "BLACK", "GREY", "SILVER", "RED", "BLUE", "GREEN", "YELLOW", "BROWN", "OTHER", "UNKNOWN"]

# ── Vehicle direction ─────────────────────────────────────────────────────────
VehicleDirection = Literal[
    "NORTH", "SOUTH", "EAST", "WEST", "INBOUND", "OUTBOUND", "UNKNOWN",
]

VEHICLE_DIRECTIONS = ["NORTH", "SOUTH", "EAST", "WEST", "INBOUND", "OUTBOUND", "UNKNOWN"]

# ── Plate format status ───────────────────────────────────────────────────────
PlateFormatStatus = Literal[
    "VALID_FORMAT", "POSSIBLE_FORMAT", "INVALID_FORMAT", "UNKNOWN_FORMAT", "NOT_ENOUGH_DATA",
]

PLATE_FORMAT_STATUSES = ["VALID_FORMAT", "POSSIBLE_FORMAT", "INVALID_FORMAT", "UNKNOWN_FORMAT", "NOT_ENOUGH_DATA"]

# ── Watchlist status ──────────────────────────────────────────────────────────
WatchlistStatus = Literal[
    "WATCHLIST_MATCH", "NO_MATCH", "UNKNOWN", "NOT_CHECKED",
]

WATCHLIST_STATUSES = ["WATCHLIST_MATCH", "NO_MATCH", "UNKNOWN", "NOT_CHECKED"]

# ── ANPR sync states ──────────────────────────────────────────────────────────
ANPRSyncState = Literal[
    "LOCAL_ONLY", "SYNC_PENDING", "SYNCED", "SYNC_FAILED", "UNKNOWN",
]

# ── ANPR sources ──────────────────────────────────────────────────────────────
ANPRSource = Literal["LIVE", "EDGE", "CENTRAL", "DEMO", "UNKNOWN"]

# Export list of all source values
ANPR_SOURCES = ["LIVE", "EDGE", "CENTRAL", "DEMO", "UNKNOWN"]

# ── Search match types (spec §24 — five labels) ───────────────────────────────
SearchMatchType = Literal[
    "EXACT_NORMALIZED_MATCH", "PARTIAL_MATCH", "RAW_READ_MATCH",
    "CANDIDATE_MATCH", "RELATED_SIGHTING",
]

SEARCH_MATCH_TYPES = [
    "EXACT_NORMALIZED_MATCH", "PARTIAL_MATCH", "RAW_READ_MATCH",
    "CANDIDATE_MATCH", "RELATED_SIGHTING",
]

# ── Provider health states ────────────────────────────────────────────────────
ANPRProviderHealthState = Literal[
    "READY", "WARMING", "DEGRADED", "UNAVAILABLE", "OFFLINE", "UNKNOWN",
]

# ── Ingestion result types ────────────────────────────────────────────────────
IngestionResult = Literal[
    "CREATED", "DUPLICATE", "ERROR",
]

INGESTION_RESULTS = ["CREATED", "DUPLICATE", "ERROR"]

# ── Camera health states (shared with Component 2) ────────────────────────────
CameraHealthState = Literal["HEALTHY", "DEGRADED", "OFFLINE", "UNKNOWN"]
CameraHealthReliability = Literal["HIGH", "MEDIUM", "LOW", "UNKNOWN"]