# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — Camera Health Schemas (Pydantic v2)
# ─────────────────────────────────────────────────────────────────────────────
from datetime import datetime
from typing import Any, Literal
from pydantic import BaseModel, Field, ConfigDict


# ── Enums ────────────────────────────────────────────────────────────────────

CameraHealthStatus = Literal[
    "ONLINE", "DEGRADED", "OFFLINE", "STALE", "FROZEN", "MAINTENANCE", "UNKNOWN"
]

StreamState = Literal[
    "CONNECTED", "RECONNECTING", "DISCONNECTED", "STALE", "FROZEN", "UNKNOWN"
]

HealthMetricStatus = Literal["GOOD", "DEGRADED", "FAILED", "UNKNOWN"]

NetworkStatus = Literal["STABLE", "DEGRADED", "OFFLINE", "UNKNOWN"]

ViewpointStatus = Literal["STABLE", "SHIFT_DETECTED", "SEVERE_SHIFT", "UNKNOWN"]

TrendDirection = Literal["IMPROVING", "STABLE", "DEGRADING", "UNKNOWN"]

CoverageState = Literal["NORMAL", "DEGRADED", "COMPROMISED", "UNKNOWN"]

ImpactLevel = Literal["NONE", "MINOR", "DEGRADED", "COMPROMISED", "UNKNOWN"]

HealthDataSource = Literal["LIVE", "LAST_KNOWN", "DEMO", "UNAVAILABLE"]


# ── Nested Models ────────────────────────────────────────────────────────────

class RegionProfile(BaseModel):
    model_config = ConfigDict(extra="allow")
    configured: bool = True
    region: str | None = None
    terrain: str | None = None
    location: str | None = None


class StreamHealth(BaseModel):
    model_config = ConfigDict(extra="allow")
    state: StreamState
    fps: float | None = None
    expectedFps: float | None = None
    frameDropPercent: float | None = None
    staleSeconds: float | None = None
    reconnectCount: int | None = None


class HealthMetric(BaseModel):
    model_config = ConfigDict(extra="allow")
    metric: str
    label: str
    value: float | str | None = None
    unit: str | None = None
    status: HealthMetricStatus
    reason: str | None = None


class ImageHealth(BaseModel):
    model_config = ConfigDict(extra="allow")
    status: HealthMetricStatus
    metrics: list[HealthMetric]
    backgroundStability: str | None = None


class NetworkHealth(BaseModel):
    model_config = ConfigDict(extra="allow")
    status: NetworkStatus
    latencyMs: float | None = None
    latencyVarianceMs: float | None = None
    packetLossPercent: float | None = None
    heartbeatAgeSec: float | None = None


class ViewpointHealth(BaseModel):
    model_config = ConfigDict(extra="allow")
    status: ViewpointStatus
    shiftScore: float | None = None
    detectedAt: str | None = None
    shiftDetected: bool = False
    fenceConfidenceNote: str | None = None


class HealthTrend(BaseModel):
    model_config = ConfigDict(extra="allow")
    metric: str
    label: str
    direction: TrendDirection
    deltaPercent: float | None = None
    window: str | None = None
    persistence: str | None = None
    series: list[float] = []


class HealthIssue(BaseModel):
    model_config = ConfigDict(extra="allow")
    issueId: str
    title: str
    impact: Literal["HIGH", "MEDIUM", "LOW"]
    firstSeen: str | None = None
    lastSeen: str | None = None
    count: int
    durationLabel: str | None = None
    impactNote: str | None = None
    affectedModules: list[str] = []


class OperationalImpact(BaseModel):
    model_config = ConfigDict(extra="allow")
    level: ImpactLevel
    coverage: CoverageState
    affectedModules: list[str] = []
    message: str | None = None


class MaintenanceState(BaseModel):
    model_config = ConfigDict(extra="allow")
    recommended: bool = False
    reason: str | None = None
    durationLabel: str | None = None
    impactNote: str | None = None


class LastKnown(BaseModel):
    model_config = ConfigDict(extra="allow")
    status: CameraHealthStatus
    at: str | None = None


# ── Main Response ────────────────────────────────────────────────────────────

class CameraHealthResponse(BaseModel):
    """Canonical response for GET /api/v1/cameras/{id}/health"""
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    cameraId: str
    status: CameraHealthStatus
    statusReason: str | None = None
    lastUpdated: str | None = None
    source: HealthDataSource
    regionProfile: RegionProfile

    stream: StreamHealth
    image: ImageHealth
    network: NetworkHealth
    viewpoint: ViewpointHealth
    trends: list[HealthTrend] = []
    issues: list[HealthIssue] = []
    operationalImpact: OperationalImpact
    maintenance: MaintenanceState | None = None
    lastKnown: LastKnown | None = None


# ── List Response ────────────────────────────────────────────────────────────

class CameraHealthSummary(BaseModel):
    """Compact representation for GET /api/v1/cameras/health"""
    model_config = ConfigDict(extra="allow")

    cameraId: str
    status: CameraHealthStatus
    statusReason: str | None = None
    lastUpdated: str | None = None
    source: HealthDataSource
    regionProfile: RegionProfile

    stream: StreamHealth
    image: ImageHealth
    network: NetworkHealth
    viewpoint: ViewpointHealth
    operationalImpact: OperationalImpact
    lastKnown: LastKnown | None = None


# ── History Request/Response ────────────────────────────────────────────────

class HealthHistoryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    from_ts: datetime | None = Field(default=None, alias="from")
    to_ts: datetime | None = Field(default=None, alias="to")
    metrics: list[str] | None = None
    resolution: Literal["1m", "5m", "15m", "1h", "6h", "1d"] = "5m"
    limit: int = Field(default=1000, ge=1, le=10000)


class HealthHistoryPoint(BaseModel):
    model_config = ConfigDict(extra="allow")
    timestamp: datetime
    metrics: dict[str, float | str | None]


class HealthHistoryResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    cameraId: str
    resolution: str
    points: list[HealthHistoryPoint]


# ── Issues Response ────────────────────────────────────────────────────────

class HealthIssueResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    cameraId: str
    issues: list[HealthIssue]


# ── Ingestion Request ──────────────────────────────────────────────────────

class StreamTelemetry(BaseModel):
    model_config = ConfigDict(extra="allow")
    streamConnected: bool = True
    sequenceNumber: int | None = None
    expectedFps: float | None = None
    observedFps: float | None = None
    frameDropRate: float | None = None
    frameAgeMs: float | None = None
    reconnectCount: int | None = None


class NetworkTelemetry(BaseModel):
    model_config = ConfigDict(extra="allow")
    latencyMs: float | None = None
    latencyVarianceMs: float | None = None
    packetLossPercent: float | None = None
    heartbeatAgeSec: float | None = None


class ImageMetrics(BaseModel):
    model_config = ConfigDict(extra="allow")
    sharpness: float | None = None
    brightness: float | None = None
    exposure: Literal["NORMAL", "UNDEREXPOSED", "OVEREXPOSED", "UNKNOWN"] | None = None
    contrast: float | None = None
    noise: float | None = None


class ViewpointTelemetry(BaseModel):
    model_config = ConfigDict(extra="allow")
    shiftScore: float | None = None
    shiftConfidence: float | None = None
    referenceFeaturesCount: int | None = None
    inlierRatio: float | None = None


class HealthObservationIngest(BaseModel):
    """POST /api/v1/internal/cameras/{camera_id}/health/observations"""
    model_config = ConfigDict(extra="allow")

    sourceTimestamp: datetime
    receivedTimestamp: datetime | None = None
    sourceSequence: int | None = None
    stream: StreamTelemetry | None = None
    network: NetworkTelemetry | None = None
    image: ImageMetrics | None = None
    viewpoint: ViewpointTelemetry | None = None
    algorithmVersion: str | None = None


class HealthObservationIngestResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    accepted: bool
    observationId: int | None = None
    currentStatus: CameraHealthStatus | None = None


# ── Config Schemas ─────────────────────────────────────────────────────────

class CameraHealthConfigCreate(BaseModel):
    model_config = ConfigDict(extra="allow")
    cameraId: str
    expectedFps: float = 25.0
    staleAfterSeconds: int = 30
    offlineAfterSeconds: int = 120
    freezeWindowSeconds: int = 10
    healthSamplingIntervalSeconds: int = 5
    regionProfile: str = "MIXED_BORDER_SECTOR"
    terrainProfile: str | None = None
    illuminationMode: str = "DAY"
    timezone: str = "UTC"
    viewpointShiftThreshold: float = 0.3
    minFeatureMatches: int = 10
    minRansacInlierRatio: float = 0.5
    sharpnessDegradedThreshold: float | None = None
    brightnessLowThreshold: float | None = None
    brightnessHighThreshold: float | None = None
    trendWindowDays: int = 7
    trendPersistenceDays: int = 3
    baselineAdaptationRate: float = 0.1
    observationRetentionDays: int = 30
    eventRetentionDays: int = 90


class CameraHealthConfigUpdate(BaseModel):
    model_config = ConfigDict(extra="allow")
    expectedFps: float | None = None
    staleAfterSeconds: int | None = None
    offlineAfterSeconds: int | None = None
    freezeWindowSeconds: int | None = None
    healthSamplingIntervalSeconds: int | None = None
    regionProfile: str | None = None
    terrainProfile: str | None = None
    illuminationMode: str | None = None
    timezone: str | None = None
    viewpointShiftThreshold: float | None = None
    minFeatureMatches: int | None = None
    minRansacInlierRatio: float | None = None
    sharpnessDegradedThreshold: float | None = None
    brightnessLowThreshold: float | None = None
    brightnessHighThreshold: float | None = None
    trendWindowDays: int | None = None
    trendPersistenceDays: int | None = None
    baselineAdaptationRate: float | None = None
    observationRetentionDays: int | None = None
    eventRetentionDays: int | None = None
    active: bool | None = None


class CameraHealthConfigResponse(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True)
    cameraId: str
    expectedFps: float
    staleAfterSeconds: int
    offlineAfterSeconds: int
    freezeWindowSeconds: int
    healthSamplingIntervalSeconds: int
    regionProfile: str
    terrainProfile: str | None
    illuminationMode: str
    timezone: str
    viewpointShiftThreshold: float
    minFeatureMatches: int
    minRansacInlierRatio: float
    sharpnessDegradedThreshold: float | None
    brightnessLowThreshold: float | None
    brightnessHighThreshold: float | None
    trendWindowDays: int
    trendPersistenceDays: int
    baselineAdaptationRate: float
    observationRetentionDays: int
    eventRetentionDays: int
    active: bool
    createdAt: datetime
    updatedAt: datetime