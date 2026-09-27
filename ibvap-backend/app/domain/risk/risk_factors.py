# ─────────────────────────────────────────────────────────────────────────────
# IBVAP — Risk Factor Catalog
# ─────────────────────────────────────────────────────────────────────────────
# Central source for every explainable risk factor. Values come from Settings so
# they remain configurable without editing code, and are surfaced verbatim in the
# incident's factor breakdown for explainability.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from app.core.config import settings

OBJECT_TYPES = {"HUMAN", "VEHICLE", "ANIMAL"}
RELIABILITIES = {"HIGH", "MEDIUM", "LOW"}


def factor(
    code: str,
    label: str,
    points: int,
    evidence: str,
) -> dict:
    """Build a structured risk factor entry."""
    return {"code": code, "label": label, "points": points, "evidence": evidence}


def restricted_zone_crossing(is_animal: bool, evidence: str) -> dict:
    points = settings.RISK_RESTRICTED_ANIMAL if is_animal else settings.RISK_RESTRICTED_NON_ANIMAL
    return factor("RESTRICTED_ZONE_CROSSING", "Restricted zone crossing", points, evidence)


def night_time(evidence: str) -> dict:
    return factor("NIGHT_TIME", "Night-time movement", settings.RISK_NIGHT, evidence)


def multi_camera(evidence: str) -> dict:
    return factor("MULTI_CAMERA_CONFIRMATION", "Multi-camera confirmation", settings.RISK_MULTI_CAMERA, evidence)


def object_type(obj: str, evidence: str) -> dict:
    if obj == "HUMAN":
        code, label, pts = "OBJECT_HUMAN", "Human object type", settings.RISK_HUMAN
    elif obj == "VEHICLE":
        code, label, pts = "OBJECT_VEHICLE", "Vehicle object type", settings.RISK_VEHICLE
    else:
        # ANIMAL crossing is already counted; do NOT add object-type points for animals.
        return factor("OBJECT_ANIMAL", "Animal object type", 0, evidence)
    return factor(code, label, pts, evidence)


def detection_confidence(confidence: float) -> dict:
    pts = round(confidence * settings.RISK_CONFIDENCE_MULTIPLIER)
    return factor(
        "DETECTION_CONFIDENCE",
        "Detection confidence",
        pts,
        f"Confidence {confidence:.2f} x {settings.RISK_CONFIDENCE_MULTIPLIER}",
    )


def low_reliability(evidence: str) -> dict:
    return factor(
        "LOW_RELIABILITY",
        "Uncertainty penalty",
        settings.RISK_LOW_RELIABILITY_PENALTY,
        evidence,
    )
