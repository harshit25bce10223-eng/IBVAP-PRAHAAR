// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 2 — Camera Health domain types (canonical, render-only)
//
// The backend (Phase 2) is authoritative for every semantic field below:
// status, metric statuses, trends, viewpoint, impact. The frontend renders
// authoritative fields verbatim and MUST NOT derive thresholds, tamper
// verdicts, maintenance conditions, risk or severity from raw values.
// ─────────────────────────────────────────────────────────────────────────────

/** Overall camera health as classified by the backend. */
export type CameraHealthStatus =
  | 'ONLINE'
  | 'DEGRADED'
  | 'OFFLINE'
  | 'STALE'
  | 'FROZEN'
  | 'MAINTENANCE'
  | 'UNKNOWN'

/** Stream connectivity as reported by the backend. Connection alive does NOT
 *  imply a usable feed — freshness/freeze are separate fields. */
export type StreamState =
  | 'CONNECTED'
  | 'DEGRADED'
  | 'RECONNECTING'
  | 'DISCONNECTED'
  | 'STALE'
  | 'FROZEN'
  | 'UNKNOWN'

/** Per-metric condition as classified by the backend. */
export type HealthMetricStatus = 'GOOD' | 'DEGRADED' | 'FAILED' | 'UNKNOWN'

export type NetworkStatus = 'STABLE' | 'DEGRADED' | 'OFFLINE' | 'UNKNOWN'

export type ViewpointStatus =
  | 'STABLE'
  | 'SHIFT_DETECTED'
  | 'SEVERE_SHIFT'
  | 'UNKNOWN'

export type TrendDirection =
  | 'IMPROVING'
  | 'STABLE'
  | 'DEGRADING'
  | 'UNKNOWN'

export type CoverageState = 'NORMAL' | 'DEGRADED' | 'COMPROMISED' | 'UNKNOWN'

export type ImpactLevel = 'NONE' | 'MINOR' | 'DEGRADED' | 'COMPROMISED' | 'UNKNOWN'

/** Where the displayed data came from. Never claim LIVE for demo fixtures. */
export type HealthDataSource = 'LIVE' | 'LAST_KNOWN' | 'DEMO' | 'UNAVAILABLE'

/** One backend-classified metric. `value: null` means unavailable → N/A. */
export interface HealthMetric {
  metric: string
  label: string
  /** Raw value exactly as provided (ratio 0–1, ms, %, fps …). Null = N/A. */
  value: number | string | null
  /** Display unit: 'fps' | 'ms' | '%' | 'ratio' | null. */
  unit: string | null
  status: HealthMetricStatus
  reason: string | null
}

/** Backend-provided trend envelope. `series` holds pre-computed points
 *  (oldest → newest) for sparkline rendering only — never derived here. */
export interface HealthTrend {
  metric: string
  label: string
  direction: TrendDirection
  /** Signed percent change over the window, e.g. -7.2. Null = not provided. */
  deltaPercent: number | null
  /** Observation window label, e.g. '15 MIN' | '1 HR' | '24 HR' | '7 DAYS'. */
  window: string | null
  /** How long the condition has persisted, e.g. '8 days'. */
  persistence: string | null
  series: number[]
}

/** One deduplicated health issue for presentation. The backend owns identity;
 *  repeated observations collapse into firstSeen/lastSeen/count here. */
export interface HealthIssue {
  issueId: string
  title: string
  /** Operational impact of this issue (NOT a camera severity score). */
  impact: 'HIGH' | 'MEDIUM' | 'LOW'
  firstSeen: string | null
  lastSeen: string | null
  /** Number of backend observations collapsed into this record. */
  count: number
  durationLabel: string | null
  impactNote: string | null
  affectedModules: string[]
}

export interface OperationalImpact {
  level: ImpactLevel
  coverage: CoverageState
  affectedModules: string[]
  message: string | null
}

export interface MaintenanceState {
  recommended: boolean
  reason: string | null
  durationLabel: string | null
  impactNote: string | null
}

/** Deployment context from configuration — never fabricated telemetry. */
export interface RegionProfile {
  configured: boolean
  region: string | null
  terrain: string | null
  location: string | null
}

/**
 * Canonical camera-health record. Field-for-field compatible with the planned
 * Phase-2 response `GET /api/v1/cameras/{id}/health` (see IHealthService).
 * Component 1 compatibility: `viewpoint.shiftDetected`,
 * `viewpoint.fenceConfidenceNote` and `backgroundStability` are the
 * forward-compatible signals the fence-confidence path will consume.
 */
export interface CameraHealth {
  cameraId: string
  status: CameraHealthStatus
  statusReason: string | null
  /** ISO-8601 telemetry time. Null = never received. */
  lastUpdated: string | null
  source: HealthDataSource
  regionProfile: RegionProfile

  stream: {
    state: StreamState
    fps: number | null
    expectedFps: number | null
    /** Frame-drop rate in percent, e.g. 0.8. Null = unavailable. */
    frameDropPercent: number | null
    /** Seconds since the last usable frame. Null = unavailable. */
    staleSeconds: number | null
    reconnectCount: number | null
  }

  image: {
    status: HealthMetricStatus
    metrics: HealthMetric[]
    /** Slow-baseline stability note (vegetation/season context), if provided. */
    backgroundStability: string | null
  }

  network: {
    status: NetworkStatus
    latencyMs: number | null
    latencyVarianceMs: number | null
    packetLossPercent: number | null
    heartbeatAgeSec: number | null
  }

  viewpoint: {
    status: ViewpointStatus
    /** Backend shift score 0–1. Null = not provided. */
    shiftScore: number | null
    detectedAt: string | null
    /** Forward-compatible fence signal for Component 1. */
    shiftDetected: boolean
    /** e.g. 'Fence confidence reduced until officer review'. Null if none. */
    fenceConfidenceNote: string | null
  }

  trends: HealthTrend[]
  issues: HealthIssue[]
  operationalImpact: OperationalImpact
  maintenance: MaintenanceState | null

  /** Last good record when current telemetry is missing/stale. */
  lastKnown: {
    status: CameraHealthStatus
    at: string | null
  } | null
}

export const HEALTH_STATUSES: CameraHealthStatus[] = [
  'ONLINE',
  'DEGRADED',
  'OFFLINE',
  'STALE',
  'FROZEN',
  'MAINTENANCE',
  'UNKNOWN',
]
