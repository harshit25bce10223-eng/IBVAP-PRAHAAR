# ─────────────────────────────────────────────────────────────────────────────
# IBVAP — Evaluation Schemas
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator

from app.core.errors import InvalidConfidenceError

ObjectType = Literal["HUMAN", "VEHICLE", "ANIMAL"]
Reliability = Literal["HIGH", "MEDIUM", "LOW"]


class BBoxModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x: float
    y: float
    width: float
    height: float

    @field_validator("x", "y")
    @classmethod
    def coord(cls, v: float) -> float:
        if v != v or v in (float("inf"), float("-inf")):
            raise ValueError("coordinates must be finite numbers")
        if not (0.0 <= v <= 1.0):
            raise ValueError("x/y must be in range [0, 1]")
        return v

    @field_validator("width", "height")
    @classmethod
    def size(cls, v: float) -> float:
        if v != v or v in (float("inf"), float("-inf")):
            raise ValueError("dimensions must be finite numbers")
        if v <= 0.0:
            raise ValueError("width/height must be positive")
        return v


class TrackEvaluateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    track_id: str
    camera_id: str
    object_type: ObjectType
    bbox: BBoxModel
    confidence: float
    is_night: bool = False
    multi_camera_confirmed: bool = False
    reliability: Reliability = "HIGH"
    timestamp: datetime | None = None

    @field_validator("track_id", "camera_id")
    @classmethod
    def non_empty(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("must be a non-empty string")
        return v.strip()

    @field_validator("confidence")
    @classmethod
    def validate_confidence(cls, v: float) -> float:
        # NaN / infinities
        if v != v or v in (float("inf"), float("-inf")):
            raise ValueError("Confidence must be between 0.0 and 1.0, got: nan/inf")
        if not (0.0 <= v <= 1.0):
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got: {v}")
        return v

    @field_validator("timestamp")
    @classmethod
    def ensure_tz(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            from datetime import timezone

            v = v.replace(tzinfo=timezone.utc)
        return v