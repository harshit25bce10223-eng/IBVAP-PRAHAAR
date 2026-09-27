# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 4 — Event Correlation Schemas
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


# ── Enums ─────────────────────────────────────────────────────────────────────

CorrelationStatus = Literal[
    "STANDALONE",
    "RELATED",
    "CORRELATED",
    "UNCERTAIN",
    "DISSOLVED",
    "UNKNOWN",
]

CorrelationGroupState = Literal[
    "OPEN",
    "ACTIVE",
    "STABLE",
    "RESOLVED",
    "DISSOLVED",
    "UNKNOWN",
]

CorrelationCompleteness = Literal["COMPLETE", "PARTIAL", "UNKNOWN"]

CorrelationSource = Literal[
    "VIRTUAL_FENCE",
    "DETECTION",
    "TRACKING",
    "ANPR",
    "AUDIO",
    "SURFACE_ANOMALY",
    "SUSPICIOUS_ACTIVITY",
    "RE_ID",
    "CAMERA_HEALTH",
    "SYSTEM",
    "UNKNOWN",
]

CorrelationRelationType = Literal[
    "TEMPORAL",
    "SPATIAL",
    "ENTITY",
    "CAMERA",
    "ZONE",
    "SEQUENCE",
    "SUPPORTING",
    "CONTEXTUAL",
]

CorrelationEventKind = Literal[
    "DETECTION",
    "ZONE_ENTRY",
    "ZONE_EXIT",
    "ANPR_READ",
    "AUDIO_ANOMALY",
    "SURFACE_ANOMALY",
    "SUSPICIOUS_ACTIVITY",
    "REID_CANDIDATE",
    "TRACK",
    "CAMERA_CONTEXT",
    "SYSTEM",
    "UNKNOWN",
]

CorrelationModality = Literal[
    "VIDEO",
    "ANPR",
    "AUDIO",
    "RF",
    "THERMAL",
    "SYSTEM",
    "UNKNOWN",
]

Reliability = Literal["HIGH", "MEDIUM", "LOW", "UNKNOWN"]
Connectivity = Literal["LIVE", "DELAYED", "LAST_SYNCED", "UNKNOWN"]
IncidentState = Literal["NEW", "REVIEWED", "CLOSED", "UNKNOWN"]


# ── Nested Models ─────────────────────────────────────────────────────────────

class CorrelationExplanation(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True)
    facet: Literal[
        "TEMPORAL", "SPATIAL", "ENTITY", "SEQUENCE", "CAMERA", "ZONE", "CONTEXTUAL"
    ]
    label: str
    detail: str


class CorrelationEventMember(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True)
    eventId: str
    kind: CorrelationEventKind
    source: CorrelationSource
    modality: CorrelationModality
    cameraId: str
    zoneId: str | None = None
    sectorId: str | None = None
    regionProfile: str | None = None
    trackId: str | None = None
    timestamp: str
    severity: str
    reliability: Reliability | None = None
    confidence: float | None = None
    evidenceIds: list[str] = []
    healthContext: dict | None = None


class CorrelationRelationship(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True)
    fromEventId: str
    toEventId: str
    type: CorrelationRelationType
    strength: int | None = None
    explanation: str


class CorrelationConfidence(BaseModel):
    model_config = ConfigDict(extra="allow")
    value: int
    note: str


class CorrelationUncertainty(BaseModel):
    model_config = ConfigDict(extra="allow")
    reliability: Reliability
    note: str | None = None


class CorrelationRisk(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True)
    score: int | None = None
    severity: str | None = None


class TrackCandidate(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True)
    trackId: str
    confidence: float | None = None
    label: str


class CorrelationTransition(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True)
    status: CorrelationStatus
    at: str
    note: str | None = None


class CorrelationHistory(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True)
    createdAt: str
    updatedAt: str
    transitions: list[CorrelationTransition] = []


# ── Main Response Models ──────────────────────────────────────────────────────

class CorrelationGroupBase(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True)
    correlationId: str
    incidentId: str | None = None
    incidentState: str | None = None
    status: CorrelationStatus
    state: CorrelationGroupState
    startedAt: str
    endedAt: str | None = None
    eventCount: int
    cameraCount: int
    zoneCount: int = 0
    sourceCount: int = 1
    confidence: int | None = None
    completeness: CorrelationCompleteness | None = None
    uncertainty: dict | None = None
    trackCandidate: dict | None = None
    cameraChain: list[str] | None = None
    modalities: list[CorrelationModality] = []
    sectorId: str | None = None
    regionProfile: str | None = None
    evidenceCount: int = 0
    connectivity: Connectivity
    duplicatedOrSuppressed: bool = False
    history: dict
    updatedAt: str
    createdAt: str | None = None


class CorrelationGroup(CorrelationGroupBase):
    """Full correlation group model with all fields including relationships."""
    model_config = ConfigDict(extra="allow", from_attributes=True)
    memberEvents: list[CorrelationEventMember] = []
    relationships: list[CorrelationRelationship] = []
    explanation: list[CorrelationExplanation] = []
    confidence: CorrelationConfidence | None = None
    trackCandidate: TrackCandidate | None = None
    sources: list[CorrelationSource] = []
    healthContext: list[dict] = []


class CorrelationGroupSummary(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True)
    correlationId: str
    incidentId: str | None = None
    status: CorrelationStatus
    lastUpdated: str
    eventCount: int
    cameraCount: int
    primaryEventId: str | None = None
    startedAt: str
    endedAt: str | None = None
    zoneCount: int = 0
    sourceCount: int = 1
    confidence: int | None = None
    completeness: CorrelationCompleteness | None = None
    sectorId: str | None = None
    regionProfile: str | None = None
    sources: list[CorrelationSource] = []
    modalities: list[CorrelationModality] = []
    connectivity: Connectivity
    duplicatedOrSuppressed: bool = False


class CorrelationGroupPage(BaseModel):
    model_config = ConfigDict(extra="allow")
    groups: list[CorrelationGroupSummary]
    total: int


# ── Query/List ────────────────────────────────────────────────────────────────

class CorrelationQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    search: str = ""
    status: str = ""
    severity: str = ""
    cameraId: str = ""
    sectorId: str = ""
    zoneId: str = ""
    source: str = ""
    sort: str = "time"
    order: str = "desc"
    page: int = Field(default=1, ge=1)
    pageSize: int = Field(default=20, ge=1, le=100)
    timeRange: str = "all"


# ── Config ────────────────────────────────────────────────────────────────────

class CorrelationConfigBase(BaseModel):
    model_config = ConfigDict(extra="allow")
    config_id: str
    profile: str
    event_pair: str | None = None
    temporal_window_seconds: int
    spatial_window_meters: int | None = None
    camera_adjacency: list | None = None
    min_relationship_strength: int
    max_group_duration_seconds: int
    min_support_events: int
    compatibility_matrix: dict | None = None
    temporal_windows: dict | None = None
    spatial_windows: dict | None = None
    active: bool
    revision: int
    created_at: datetime
    updated_at: datetime
    activated_at: datetime | None = None


class CorrelationConfigCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile: str
    event_pair: str | None = None
    temporal_window_seconds: int = 300
    spatial_window_meters: int | None = None
    camera_adjacency: list | None = None
    min_relationship_strength: int = 50
    max_group_duration_seconds: int = 3600
    min_support_events: int = 2
    compatibility_matrix: dict | None = None
    temporal_windows: dict | None = None
    spatial_windows: dict | None = None
    active: bool = True


class CorrelationConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="allow")
    temporal_window_seconds: int | None = None
    spatial_window_meters: int | None = None
    camera_adjacency: list | None = None
    min_relationship_strength: int | None = None
    max_group_duration_seconds: int | None = None
    min_support_events: int | None = None
    compatibility_matrix: dict | None = None
    temporal_windows: dict | None = None
    spatial_windows: dict | None = None
    active: bool | None = None


class CorrelationConfigResponse(CorrelationConfigBase):
    pass


# ── Ingestion ─────────────────────────────────────────────────────────────────

class IngestEventRequest(BaseModel):
    model_config = ConfigDict(extra="allow")
    event_id: str | None = None
    event_type: str = "DETECTION"
    source: str = "SYSTEM"
    camera_id: str | None = None
    zone_id: str | None = None
    sector_id: str | None = None
    track_id: str | None = None
    event_time: datetime | None = None
    source_event_id: str | None = None
    source_sequence: int | None = None
    object_type: str | None = None
    bbox: list[float] | None = None
    confidence: float | None = None
    is_night: bool = False
    multi_camera_confirmed: bool = False
    reliability: Reliability = "HIGH"
    reid_candidate: str | None = None
    payload: dict | None = None


class IngestEventResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    correlation_id: str
    action: Literal["CREATED", "UPDATED", "DUPLICATE"]
    group_id: str
    score: int | None = None
    message: str | None = None