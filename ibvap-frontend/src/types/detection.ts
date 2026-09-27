// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 5 — AI Detection domain types (canonical, render-only)
//
// The AI Detector (model, inference, tracking, ANPR, face, Re-ID) is a backend
// capability that does not exist in this frontend task. This module is the
// single canonical frontend model that renders its output. The backend (Phase
// 2) is authoritative for every semantic field: class, confidence, quality,
// occlusion, source, model/version and track/event/incident/evidence links.
//
// The frontend MUST NOT compute risk, severity, correlation, tracking IDs,
// identity, ANPR results or face matches, and it never fabricates a confidence,
// accuracy, model name or live timestamp. Polarity rule: DETECTION ≠ TRACKING
// ≠ IDENTITY ≠ CORRELATION ≠ RISK ≠ THREAT. A "PERSON" is an observation,
// not a threat.
//
// Coordinates are normalized [0,1] image-space (top-left origin) and are
// transformed into the rendered viewport by the overlay using the same viewBox
// as the existing camera feed — never hard-coded 1080p assumptions.
// ─────────────────────────────────────────────────────────────────────────────

/** Object class emitted by the detector. Class is NEVER a severity signal. */
export type DetectionClass = 'PERSON' | 'VEHICLE' | 'ANIMAL' | 'OBJECT' | 'UNKNOWN'
export const DETECTION_CLASSES: DetectionClass[] = ['PERSON', 'VEHICLE', 'ANIMAL', 'OBJECT', 'UNKNOWN']

/**
 * Observation quality reported by the provider. Quality is about the frame /
 * box, never a threat or risk value.
 */
export type DetectionQuality = 'GOOD' | 'LIMITED' | 'POOR' | 'UNKNOWN'

/** Occlusion severity — only ever shown verbatim, never inferred from motion. */
export type DetectionOcclusion = 'LOW' | 'MEDIUM' | 'HIGH'

/**
 * Detector-placement context. Not a health signal by itself; the camera
 * health interface owns camera health.
 */
export type DetectionSource = 'EDGE' | 'CENTRAL' | 'UNKNOWN'

/** Detector validity state of a single detection box (provider-supplied). */
export type DetectionState =
  | 'DETECTED'
  | 'LOW_CONFIDENCE'
  | 'PARTIAL'
  | 'OCCLUDED'
  | 'UNKNOWN'
  | 'INVALID'

/**
 * Feed-level availability. Deliberately distinct values:
 *   READY       → detector answered and produced >= 0 boxes
 *   NO_OBJECTS  → detector answered, zero objects (NOT unavailable)
 *   UNCONFIGURED→ detection not configured on this camera
 *   UNAVAILABLE → inference could not produce output (≠ zero objects)
 *   STALE       → last known output is delayed (older than expected)
 *   OFFLINE     → camera/edge link offline; no fresh output possible
 */
export type DetectionFeedState =
  | 'READY'
  | 'NO_OBJECTS'
  | 'UNCONFIGURED'
  | 'UNAVAILABLE'
  | 'STALE'
  | 'OFFLINE'

/** Detector runtime health — shown only when the provider reports it. */
export type InferenceState = 'READY' | 'PROCESSING' | 'DEGRADED' | 'UNAVAILABLE' | 'OFFLINE' | 'UNKNOWN'

/** Normalized bounding box in image-space coordinates, top-left origin. */
export interface DetectionBBox {
  x: number // 0..1
  y: number // 0..1
  width: number // 0..1
  height: number // 0..1
}

/** Camera-health context attached to a detection only when the backend flags it. */
export interface DetectionCameraHealthContext {
  cameraId: string
  /** Source reliability — reported separately from detector confidence. */
  reliability: 'HIGH' | 'MEDIUM' | 'LOW' | 'UNKNOWN'
  /** Backend only: viewpoint change invalidates geometry review in progress. */
  viewpointShift: boolean
  note: string | null
}

/**
 * Canonical Detector output. `confidence`, `bbox` and every reference field is
 * provider-supplied; all of them are optional in the generic contract because
 * the frontend must degrade gracefully when a backend omits them.
 */
export interface DetectionResult {
  /** Detector-owned id (DET-*). Always distinct from TRK/EV/COR/INC/EVD ids. */
  detectionId: string
  cameraId: string
  class: DetectionClass
  /** Optional subclass (e.g. 'CAR') when the detector provides one. */
  subclass: string | null
  /** Detector confidence as a 0–1 ratio. Null = "not provided", shown as N/A. */
  confidence: number | null
  bbox: DetectionBBox | null
  /** Frame-observation timestamp (DETECTED AT), provider-supplied. */
  timestamp: string
  /** When the row was received by us — may differ from `timestamp`. */
  receivedAt: string | null
  /** Last mutation, if the provider keeps updating the record. */
  updatedAt: string | null
  /** Frame identity within the camera stream (provider-supplied). */
  frameNumber: number | null
  fps: number | null
  frameWidth: number | null
  frameHeight: number | null
  quality: DetectionQuality
  occlusion: DetectionOcclusion | null
  state: DetectionState
  /** Geometry is partial (object cut by frame edge). Backend only. */
  partial: boolean
  /** Object touches the frame edge. Backend only. */
  frameEdge: boolean
  /** Small, distant target (long-range camera). Backend only. */
  smallTarget: boolean
  longRange: boolean
  source: DetectionSource
  /** Model/provider/version — never hard-coded; shown only when provided. */
  model: string | null
  provider: string | null
  modelVersion: string | null
  /** Optional references. Presence means an actual upstream link exists. */
  trackId: string | null
  eventId: string | null
  incidentId: string | null
  evidenceId: string | null
  /** Optional downstream link — e.g. IEventCorrelationService correlation id. */
  correlationId: string | null
  cameraHealth: DetectionCameraHealthContext | null
  regionProfile: string | null
  /** Day/night/low-light context when the source provides it. Never implied. */
  visibility: 'DAY' | 'NIGHT' | 'LOW_LIGHT' | 'UNKNOWN' | null
}

/** Camera feed = detections + honest availability of the detector itself. */
export interface DetectionFeed {
  cameraId: string
  state: DetectionFeedState
  inference: InferenceState
  /** Freshness of this feed. STALE/LIVE semantics never fabricated. */
  lastUpdatedAt: string | null
  detections: DetectionResult[]
}

/**
 * Aggregate detection summary. Contains structural counts only — never risk,
 * severity or threat values. `byClass` and `qualitySummary` are plain counts.
 */
export interface DetectionSummary {
  cameraId: string
  total: number
  byClass: Partial<Record<DetectionClass, number>>
  lowConfidenceCount: number
  qualitySummary: Partial<Record<DetectionQuality, number>>
  lastUpdatedAt: string | null
}

/** List query — pagination, sorting and DISPLAY filters only (no risk concept). */
export interface DetectionQuery {
  search: string
  cameraId: string // 'ALL' or a camera id
  class: DetectionClass | 'OTHER' | 'ALL'
  /** Display-only confidence cutoff in percent (0..100). Null = no filter. */
  confidenceMin: number | null
  quality: DetectionQuality | 'ALL'
  source: DetectionSource | 'ALL'
  timeRange: '15m' | '1h' | 'today' | 'all'
  sort: 'latest' | 'oldest' | 'confidence' | 'class' | 'camera'
  order: 'asc' | 'desc'
  page: number
  pageSize: number
}

export interface DetectionResultPage {
  detections: DetectionResult[]
  total: number
}

export const DEFAULT_DETECTION_QUERY: DetectionQuery = {
  search: '',
  cameraId: 'ALL',
  class: 'ALL',
  confidenceMin: null,
  quality: 'ALL',
  source: 'ALL',
  timeRange: 'all',
  sort: 'latest',
  order: 'desc',
  page: 1,
  pageSize: 10,
}