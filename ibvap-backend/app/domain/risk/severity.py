# ─────────────────────────────────────────────────────────────────────────────
# IBVAP — Severity Engine
# ─────────────────────────────────────────────────────────────────────────────
# The ONE canonical severity function. All callers route through here so the
# bands are never duplicated across the codebase.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from app.core.config import settings

Severity = str  # "LOW" | "MEDIUM" | "HIGH" | "CRITICAL"

_LOW = "LOW"
_MED = "MEDIUM"
_HIGH = "HIGH"
_CRIT = "CRITICAL"


def severity_for_score(score: int) -> Severity:
    """Map a final score to a severity band.

    0–39  LOW
    40–64 MEDIUM
    65–84 HIGH
    85–100 CRITICAL

    The input is assumed already clamped; bounds are inclusive lower/upper.
    """
    if score < settings.SEVERITY_MEDIUM_THRESHOLD:  # < 40
        return _LOW
    if score < settings.SEVERITY_HIGH_THRESHOLD:   # < 65
        return _MED
    if score < settings.SEVERITY_CRITICAL_THRESHOLD:  # < 85
        return _HIGH
    return _CRIT


SEVERITY_ORDER: list[str] = [_LOW, _MED, _HIGH, _CRIT]
