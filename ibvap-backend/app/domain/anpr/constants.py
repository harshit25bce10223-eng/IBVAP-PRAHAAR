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

# ── Vehicle color ─────────────────────────────────────────────────────────────
VehicleColor = Literal[
    "WHITE", "BLACK", "GREY", "SILVER", "RED", "BLUE",
    "GREEN", "YELLOW", "GREEN", "BROWN", "OTHER", "UNKNOWN",
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

# ── Search match types ────────────────────────────────────────────────────────
SearchMatchType = Literal[
    "EXACT_NORMALIZED_MATCH", "TOP_CANDIDATE_MATCH", "PARTIAL_MATCH", "RELATED_SIGHTING",
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