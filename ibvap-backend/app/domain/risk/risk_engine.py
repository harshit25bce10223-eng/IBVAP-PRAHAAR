# ─────────────────────────────────────────────────────────────────────────────
# IBVAP — Risk Engine
# ─────────────────────────────────────────────────────────────────────────────
# Pure, deterministic scoring. Given a request and the membership facts, builds
# an EXPLAINABLE factor list, a raw score, a clamped final score, and severity.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.core.config import settings
from app.core.errors import InvalidConfidenceError, InvalidObjectTypeError, InvalidBBoxError
from app.domain.risk import risk_factors
from app.domain.risk.severity import Severity, severity_for_score

VALID_RELIABILITIES = {"HIGH", "MEDIUM", "LOW"}


@dataclass
class RiskResult:
    risk_score: int
    severity: Severity
    factors: list[dict[str, Any]] = field(default_factory=list)
    raw_score: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "risk_score": self.risk_score,
            "severity": self.severity,
            "factors": self.factors,
        }


def _validate_object_type(obj: str) -> None:
    if not isinstance(obj, str) or obj.upper() not in risk_factors.OBJECT_TYPES:
        raise InvalidObjectTypeError(str(obj))


def _validate_confidence(confidence: float) -> None:
    if (
        not isinstance(confidence, (int, float))
        or isinstance(confidence, bool)
        or confidence != confidence  # NaN
        or confidence in (float("inf"), float("-inf"))
        or not (0.0 <= confidence <= 1.0)
    ):
        raise InvalidConfidenceError(confidence)


def _validate_bbox(bbox: dict[str, Any]) -> None:
    if (
        not isinstance(bbox, dict)
        or not all(k in bbox for k in ("x", "y", "width", "height"))
        or not all(isinstance(bbox[k], (int, float)) and isinstance(bbox[k], (int, float)) for k in ("x", "y", "width", "height"))
    ):
        raise InvalidBBoxError("bbox must contain numeric x, y, width, height.")
    for k in ("x", "y"):
        if not (0.0 <= bbox[k] <= 1.0):
            raise InvalidBBoxError(f"bbox '{k}' must be in range [0, 1].")
    for k in ("width", "height"):
        if bbox[k] <= 0.0:
            raise InvalidBBoxError(f"bbox '{k}' must be positive.")


def _validate_reliability(reliability: str) -> None:
    if not isinstance(reliability, str) or reliability.upper() not in VALID_RELIABILITIES:
        raise InvalidObjectTypeError(f"Unknown reliability '{reliability}'. Allowed: HIGH, MEDIUM, LOW.")


def calculate_risk(
    *,
    object_type: str,
    zone_crossed: bool,
    is_night: bool,
    multi_camera_confirmed: bool,
    confidence: float,
    reliability: str,
    evidence: str | None = None,
) -> RiskResult:
    """Deterministic risk calculation.

    zone_crossed is expected True only when an ENTRY was detected AND the zone rule
    passed. Evidence is a human-readable string attached to the crossing factor.
    """
    obj = str(object_type).upper()
    _validate_object_type(obj)
    _validate_confidence(confidence)
    rel = str(reliability).upper()
    _validate_reliability(rel)

    evidence = evidence or "Track entered restricted zone."

    factors: list[dict[str, Any]] = []
    total = 0

    is_animal = obj == "ANIMAL"

    # Restricted zone crossing
    crossing = risk_factors.restricted_zone_crossing(is_animal, evidence)
    factors.append(crossing)
    total += crossing["points"]

    # Night-time movement
    if is_night:
        night = risk_factors.night_time("Movement occurred during night hours.")
        factors.append(night)
        total += night["points"]

    # Multi-camera confirmation
    if multi_camera_confirmed:
        mc = risk_factors.multi_camera("Object confirmed by multiple cameras.")
        factors.append(mc)
        total += mc["points"]

    # Object type (never applies to ANIMAL — already counted via crossing factor)
    ot = risk_factors.object_type(obj, f"Detected object type: {obj}.")
    factors.append(ot)
    total += ot["points"]

    # Detection confidence
    conf = risk_factors.detection_confidence(confidence)
    factors.append(conf)
    total += conf["points"]

    # Low reliability penalty
    if rel == "LOW":
        pen = risk_factors.low_reliability("Uncertainty engine reported LOW reliability.")
        factors.append(pen)
        total += pen["points"]

    # Bounded final score; raw preserved for debugging/explainability.
    raw = total
    final = max(settings.RISK_SCORE_MIN, min(settings.RISK_SCORE_MAX, raw))

    return RiskResult(
        risk_score=final,
        severity=severity_for_score(final),
        factors=factors,
        raw_score=raw,
    )