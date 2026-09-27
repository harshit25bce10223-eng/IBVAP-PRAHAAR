# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 4 — Event Type Compatibility Matrix
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from typing import Any


# Event source types
EventSource = str

# Default compatibility matrix
# Values: 0 (incompatible) to 100 (strongly compatible)
DEFAULT_COMPATIBILITY_MATRIX: dict[str, dict[str, int]] = {
    "VIRTUAL_FENCE": {
        "VIRTUAL_FENCE": 100,
        "DETECTION": 80,
        "TRACKING": 70,
        "ANPR": 50,
        "AUDIO": 30,
        "SURFACE_ANOMALY": 30,
        "SUSPICIOUS_ACTIVITY": 70,
        "RE_ID": 40,
        "CAMERA_HEALTH": 10,
        "SYSTEM": 20,
        "UNKNOWN": 20,
    },
    "DETECTION": {
        "VIRTUAL_FENCE": 80,
        "DETECTION": 90,
        "TRACKING": 95,
        "ANPR": 60,
        "AUDIO": 40,
        "SURFACE_ANOMALY": 40,
        "SUSPICIOUS_ACTIVITY": 80,
        "RE_ID": 50,
        "CAMERA_HEALTH": 10,
        "SYSTEM": 20,
        "UNKNOWN": 20,
    },
    "TRACKING": {
        "VIRTUAL_FENCE": 70,
        "DETECTION": 95,
        "TRACKING": 100,
        "ANPR": 60,
        "AUDIO": 40,
        "SURFACE_ANOMALY": 40,
        "SUSPICIOUS_ACTIVITY": 80,
        "RE_ID": 70,
        "CAMERA_HEALTH": 10,
        "SYSTEM": 20,
        "UNKNOWN": 20,
    },
    "ANPR": {
        "VIRTUAL_FENCE": 50,
        "DETECTION": 60,
        "TRACKING": 60,
        "ANPR": 90,
        "AUDIO": 30,
        "SURFACE_ANOMALY": 30,
        "SUSPICIOUS_ACTIVITY": 50,
        "RE_ID": 40,
        "CAMERA_HEALTH": 10,
        "SYSTEM": 20,
        "UNKNOWN": 20,
    },
    "AUDIO": {
        "VIRTUAL_FENCE": 30,
        "DETECTION": 40,
        "TRACKING": 40,
        "ANPR": 30,
        "AUDIO": 100,
        "SURFACE_ANOMALY": 50,
        "SUSPICIOUS_ACTIVITY": 50,
        "RE_ID": 30,
        "CAMERA_HEALTH": 10,
        "SYSTEM": 20,
        "UNKNOWN": 20,
    },
    "SURFACE_ANOMALY": {
        "VIRTUAL_FENCE": 30,
        "DETECTION": 40,
        "TRACKING": 40,
        "ANPR": 30,
        "AUDIO": 50,
        "SURFACE_ANOMALY": 90,
        "SUSPICIOUS_ACTIVITY": 40,
        "RE_ID": 30,
        "CAMERA_HEALTH": 10,
        "SYSTEM": 20,
        "UNKNOWN": 20,
    },
    "SUSPICIOUS_ACTIVITY": {
        "VIRTUAL_FENCE": 70,
        "DETECTION": 80,
        "TRACKING": 80,
        "ANPR": 50,
        "AUDIO": 50,
        "SURFACE_ANOMALY": 40,
        "SUSPICIOUS_ACTIVITY": 100,
        "RE_ID": 50,
        "CAMERA_HEALTH": 10,
        "SYSTEM": 20,
        "UNKNOWN": 20,
    },
    "RE_ID": {
        "VIRTUAL_FENCE": 40,
        "DETECTION": 50,
        "TRACKING": 70,
        "ANPR": 40,
        "AUDIO": 30,
        "SURFACE_ANOMALY": 30,
        "SUSPICIOUS_ACTIVITY": 50,
        "RE_ID": 100,
        "CAMERA_HEALTH": 10,
        "SYSTEM": 20,
        "UNKNOWN": 20,
    },
    "CAMERA_HEALTH": {
        "VIRTUAL_FENCE": 10,
        "DETECTION": 10,
        "TRACKING": 10,
        "ANPR": 10,
        "AUDIO": 10,
        "SURFACE_ANOMALY": 10,
        "SUSPICIOUS_ACTIVITY": 10,
        "RE_ID": 10,
        "CAMERA_HEALTH": 100,
        "SYSTEM": 50,
        "UNKNOWN": 20,
    },
    "SYSTEM": {
        "VIRTUAL_FENCE": 20,
        "DETECTION": 20,
        "TRACKING": 20,
        "ANPR": 20,
        "AUDIO": 20,
        "SURFACE_ANOMALY": 20,
        "SUSPICIOUS_ACTIVITY": 20,
        "RE_ID": 20,
        "CAMERA_HEALTH": 50,
        "SYSTEM": 100,
        "UNKNOWN": 20,
    },
    "UNKNOWN": {
        "VIRTUAL_FENCE": 20,
        "DETECTION": 20,
        "TRACKING": 20,
        "ANPR": 20,
        "AUDIO": 20,
        "SURFACE_ANOMALY": 20,
        "SUSPICIOUS_ACTIVITY": 20,
        "RE_ID": 20,
        "CAMERA_HEALTH": 20,
        "SYSTEM": 20,
        "UNKNOWN": 50,
    },
}


def get_compatibility(source_a: str, source_b: str) -> int:
    """Get compatibility score between two event sources."""
    return DEFAULT_COMPATIBILITY_MATRIX.get(source_a, {}).get(source_b, 20)


def get_event_type_compatibility(event_type_a: str, event_type_b: str) -> int:
    """Get compatibility between event kinds (e.g., ZONE_ENTRY + DETECTION)."""
    # This would be a more granular matrix for event kinds
    # For now, use a simplified version
    strong_pairs = {
        ("ZONE_ENTRY", "DETECTION"),
        ("ZONE_ENTRY", "TRACKING"),
        ("ZONE_EXIT", "DETECTION"),
        ("ZONE_EXIT", "TRACKING"),
        ("ANPR_READ", "TRACKING"),
        ("ANPR_READ", "DETECTION"),
        ("AUDIO_ANOMALY", "SUSPICIOUS_ACTIVITY"),
        ("SURFACE_ANOMALY", "SUSPICIOUS_ACTIVITY"),
        ("REID_CANDIDATE", "TRACKING"),
        ("DETECTION", "TRACKING"),
    }
    
    if (event_type_a, event_type_b) in strong_pairs or (event_type_b, event_type_a) in strong_pairs:
        return 80
    return 30


def get_default_compatibility_matrix() -> dict[str, dict[str, int]]:
    """Return a copy of the default compatibility matrix."""
    return {k: v.copy() for k, v in DEFAULT_COMPATIBILITY_MATRIX.items()}