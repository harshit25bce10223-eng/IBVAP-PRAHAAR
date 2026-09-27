# ─────────────────────────────────────────────────────────────────────────────
# IBVAP — Incident Schemas
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict


class RiskFactorOut(BaseModel):
    code: str
    label: str
    points: int
    evidence: str


class IncidentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    incident_id: str
    risk_score: int
    severity: str
    factors: list[dict[str, Any]]
    event_id: str
    camera_id: str
    track_id: str
    zone_id: str
    created_at: datetime


class EventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    event_id: str
    event_type: str
    camera_id: str
    track_id: str
    zone_id: str
    payload: dict[str, Any] | None
    ts: datetime


class TrackEvaluateResponse(BaseModel):
    track: dict[str, Any]
    evaluation: dict[str, Any]
    event: dict[str, Any]
    incident: dict[str, Any]