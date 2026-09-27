# ─────────────────────────────────────────────────────────────────────────────
# IBVAP — Zone Schemas
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from app.core.config import settings

POINT_MIN, POINT_MAX = settings.POLYGON_MIN_POINTS, settings.POLYGON_MAX_POINTS
COORD_MIN, COORD_MAX = settings.COORD_MIN, settings.COORD_MAX

TIME_HINT = "HH:MM in 24h format, e.g. '18:00'"


class PolygonPoint(BaseModel):
    x: float
    y: float

    @field_validator("x", "y")
    @classmethod
    def finite_only(cls, v: float) -> float:
        if v != v or v in (float("inf"), float("-inf")):
            raise ValueError("coordinates must be finite numbers")
        # Coordinate range [0, 1] is enforced by the domain-level validate_polygon
        # so it surfaces as a structured INVALID_ZONE_GEOMETRY error (spec §6/§7),
        # not a bare Pydantic 422.
        return v


class ZoneRules(BaseModel):
    """Zone rule set. All fields optional; empty rules mean 'always allowed'."""

    allowed_object_types: list[Literal["HUMAN", "VEHICLE", "ANIMAL"]] | None = None
    active_start: str | None = None
    active_end: str | None = None
    dwell_time_seconds: int | None = None

    @field_validator("active_start", "active_end")
    @classmethod
    def validate_time(cls, v: str | None) -> str | None:
        if v is None:
            return v
        try:
            parts = v.split(":")
            if len(parts) != 2:
                raise ValueError
            hh, mm = int(parts[0]), int(parts[1])
            if not (0 <= hh <= 23 and 0 <= mm <= 59):
                raise ValueError
        except ValueError:
            raise ValueError(f"time must be {TIME_HINT}") from None
        return f"{hh:02d}:{mm:02d}"

    @field_validator("dwell_time_seconds")
    @classmethod
    def validate_dwell(cls, v: int | None) -> int | None:
        if v is not None and v < 0:
            raise ValueError("dwell_time_seconds must be >= 0")
        return v

    @model_validator(mode="after")
    def start_end_pair(self) -> "ZoneRules":
        if (self.active_start is None) != (self.active_end is None):
            raise ValueError("active_start and active_end must be provided together")
        return self


class ZoneCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    zone_id: str | None = None
    camera_id: str
    name: str = "Restricted Zone"
    polygon: list[PolygonPoint]
    rules: ZoneRules | None = None
    active: bool = True

    @field_validator("zone_id")
    @classmethod
    def validate_zone_id(cls, v: str | None) -> str | None:
        if v is not None and (not v.strip() or len(v) > 64):
            raise ValueError("zone_id must be <= 64 non-empty characters")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v.strip() or len(v) > 255:
            raise ValueError("name must be 1-255 characters")
        return v.strip()

    @field_validator("polygon")
    @classmethod
    def validate_polygon_len(cls, polygon: list[PolygonPoint]) -> list[PolygonPoint]:
        n = len(polygon)
        if n < POINT_MIN:
            raise ValueError(f"polygon must have at least {POINT_MIN} points, got {n}")
        if n > POINT_MAX:
            raise ValueError(f"polygon must have at most {POINT_MAX} points, got {n}")
        return polygon


class ZoneUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = None
    polygon: list[PolygonPoint] | None = None
    rules: ZoneRules | None = None
    active: bool | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str | None) -> str | None:
        if v is not None and (not v.strip() or len(v) > 255):
            raise ValueError("name must be 1-255 characters")
        return v.strip() if v else v

    @field_validator("polygon")
    @classmethod
    def validate_polygon_len(cls, polygon: list[PolygonPoint] | None) -> list[PolygonPoint] | None:
        if polygon is None:
            return None
        n = len(polygon)
        if n < POINT_MIN:
            raise ValueError(f"polygon must have at least {POINT_MIN} points, got {n}")
        if n > POINT_MAX:
            raise ValueError(f"polygon must have at most {POINT_MAX} points, got {n}")
        return polygon


class ZoneOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    zone_id: str
    camera_id: str
    name: str
    polygon: list[dict[str, float]]
    rules: dict[str, Any]
    active: bool
    created_at: datetime
    updated_at: datetime