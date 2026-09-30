// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 5 — backend payload → canonical detection mappers
//
// Pure, defensive translation of the live FastAPI responses (§22 REAL mode)
// into the canonical contract in `@/types/detection`. Every function is total:
// unknown enum members collapse to UNKNOWN, absent identifiers become null,
// and a row without a detection id is dropped — never fabricated. Nothing here
// computes risk, severity, correlation, tracking, identity or ANPR; it only
// renames and validates fields the backend actually sent.
//
// Field-name contract (verified against app/schemas/detection/schemas.py):
//   DetectionSummary/Detail → detection_id, camera_id, frame_id, class_name,
//   confidence, bbox{x,y,width,height}, frame_width, frame_height,
//   quality_state, occlusion_state, detection_state, source, provider,
//   observed_at, received_at, processed_at, track_id, event_id, incident_id,
//   evidence_id, camera_health_context{state,reliability,viewpoint_shift},
//   provider_metadata{model_name,model_version}; detail adds anpr_ref,
//   region_profile, provider_class and top-level model_name/model_version.
//   DetectionPage → {detections, total, page, page_size}
//   DetectionFeedResponse → {camera_id, state, inference, last_updated_at,
//   detections[]}
//   CameraDetectionSummary → {camera_id, total_detections, by_class,
//   low_confidence_count, quality_summary, last_observed_at}
// ─────────────────────────────────────────────────────────────────────────────

import type {
  DetectionBBox,
  DetectionCameraHealthContext,
  DetectionClass,
  DetectionFeed,
  DetectionFeedState,
  DetectionOcclusion,
  DetectionQuality,
  DetectionQuery,
  DetectionResult,
  DetectionResultPage,
  DetectionSource,
  DetectionState,
  DetectionSummary,
  InferenceState,
} from '@/types/detection'
import { DETECTION_CLASSES } from '@/types/detection'

// ── primitive guards ────────────────────────────────────────────────────────

function isRecord(v: unknown): v is Record<string, unknown> {
  return typeof v === 'object' && v !== null && !Array.isArray(v)
}

function asString(v: unknown): string | null {
  return typeof v === 'string' && v.trim() !== '' ? v : null
}

function asNumber(v: unknown): number | null {
  return typeof v === 'number' && Number.isFinite(v) ? v : null
}

function asBool(v: unknown): boolean {
  return v === true
}

// ── enum canonicalization ───────────────────────────────────────────────────

const CLASS_SET = new Set<string>(DETECTION_CLASSES)
const QUALITY_SET = new Set<string>(['GOOD', 'LIMITED', 'POOR', 'UNKNOWN'])
const STATE_SET = new Set<string>(['DETECTED', 'LOW_CONFIDENCE', 'PARTIAL', 'OCCLUDED', 'UNKNOWN', 'INVALID'])
const SOURCE_SET = new Set<string>(['EDGE', 'CENTRAL', 'REMOTE', 'DEMO', 'UNKNOWN'])

/** Provider class token → canonical class; anything else is UNKNOWN. */
export function mapDetectionClass(v: unknown): DetectionClass {
  const s = asString(v)?.toUpperCase()
  return s !== undefined && CLASS_SET.has(s) ? (s as DetectionClass) : 'UNKNOWN'
}

export function mapQuality(v: unknown): DetectionQuality {
  const s = asString(v)?.toUpperCase()
  return s !== undefined && QUALITY_SET.has(s) ? (s as DetectionQuality) : 'UNKNOWN'
}

/** Backend may send UNKNOWN occlusion — the frontend hides it rather than inventing one. */
export function mapOcclusion(v: unknown): DetectionOcclusion | null {
  const s = asString(v)?.toUpperCase()
  return s === 'LOW' || s === 'MEDIUM' || s === 'HIGH' ? s : null
}

export function mapDetectionState(v: unknown): DetectionState {
  const s = asString(v)?.toUpperCase()
  return s !== undefined && STATE_SET.has(s) ? (s as DetectionState) : 'UNKNOWN'
}

/**
 * Detector placement. REMOTE and DEMO are real backend values (provider run on
 * a remote host / demo provider) — they are surfaced verbatim, never remapped.
 */
export function mapSource(v: unknown): DetectionSource {
  const s = asString(v)?.toUpperCase()
  return s !== undefined && SOURCE_SET.has(s) ? (s as DetectionSource) : 'UNKNOWN'
}

/**
 * Feed availability. PROCESSING/DEGRADED mean output exists but is delayed —
 * STALE is the honest frontend state ("last known, delayed"). UNKNOWN and any
 * malformed value become UNAVAILABLE, never READY (§22/§28: an API problem is
 * never presented as a healthy detector).
 */
export function mapFeedState(v: unknown): DetectionFeedState {
  const s = asString(v)?.toUpperCase()
  switch (s) {
    case 'READY':
      return 'READY'
    case 'NO_OBJECTS':
      return 'NO_OBJECTS'
    case 'UNCONFIGURED':
      return 'UNCONFIGURED'
    case 'STALE':
    case 'PROCESSING':
    case 'DEGRADED':
      return 'STALE'
    case 'OFFLINE':
      return 'OFFLINE'
    case 'UNAVAILABLE':
    default:
      return 'UNAVAILABLE'
  }
}

/**
 * Detector runtime state. LOADING/WARMING are start-up phases of PROCESSING;
 * FAILED maps to UNAVAILABLE (inference could not produce output).
 */
export function mapInferenceState(v: unknown): InferenceState {
  const s = asString(v)?.toUpperCase()
  switch (s) {
    case 'READY':
      return 'READY'
    case 'PROCESSING':
    case 'LOADING':
    case 'WARMING':
      return 'PROCESSING'
    case 'DEGRADED':
      return 'DEGRADED'
    case 'OFFLINE':
      return 'OFFLINE'
    case 'FAILED':
    case 'UNAVAILABLE':
      return 'UNAVAILABLE'
    default:
      return 'UNKNOWN'
  }
}

// ── composite fields ────────────────────────────────────────────────────────

function mapBBox(v: unknown): DetectionBBox | null {
  if (!isRecord(v)) return null
  const x = asNumber(v.x)
  const y = asNumber(v.y)
  const width = asNumber(v.width)
  const height = asNumber(v.height)
  if (x === null || y === null || width === null || height === null) return null
  return { x, y, width, height }
}

/**
 * Detector confidence as a 0–1 ratio. The backend contract is 0–1; a value in
 * (1, 100] is a provider percent that is normalized by 100. Anything else is
 * dropped (N/A) — a confidence is never invented or clamped into range.
 */
export function normalizeConfidence(v: unknown): number | null {
  const n = asNumber(v)
  if (n === null || n < 0) return null
  if (n <= 1) return n
  if (n <= 100) return n / 100
  return null
}

/**
 * Camera-health context attached to a detection. Only surfaces when the
 * backend actually flagged something (reliability, viewpoint shift or note) —
 * otherwise it is noise and stays null.
 */
function mapCameraHealthContext(v: unknown, cameraId: string): DetectionCameraHealthContext | null {
  if (!isRecord(v)) return null
  const raw = asString(v.reliability)?.toUpperCase()
  const reliability =
    raw === 'HIGH' || raw === 'MEDIUM' || raw === 'LOW' ? (raw as 'HIGH' | 'MEDIUM' | 'LOW') : 'UNKNOWN'
  const viewpointShift = asBool(v.viewpoint_shift)
  const note = asString(v.note)
  if (reliability === 'UNKNOWN' && !viewpointShift && note === null) return null
  return { cameraId, reliability, viewpointShift, note }
}

/** Model identity: top-level detail fields win, provider_metadata is the fallback. */
function provenanceOf(raw: Record<string, unknown>): { model: string | null; modelVersion: string | null } {
  const meta = isRecord(raw.provider_metadata) ? raw.provider_metadata : null
  return {
    model: asString(raw.model_name) ?? (meta ? asString(meta.model_name) : null),
    modelVersion: asString(raw.model_version) ?? (meta ? asString(meta.model_version) : null),
  }
}

// ── record mappers ──────────────────────────────────────────────────────────

/**
 * One backend detection row → canonical DetectionResult. Shared by the list
 * and detail endpoints because both use the same snake_case contract; detail
 * rows simply carry extra fields (anpr_ref, region_profile, top-level model).
 * Returns null when the row has no detection id — identity is never invented.
 */
export function mapDetection(raw: unknown): DetectionResult | null {
  if (!isRecord(raw)) return null
  const detectionId = asString(raw.detection_id)
  const cameraId = asString(raw.camera_id)
  if (detectionId === null || cameraId === null) return null

  const observedAt = asString(raw.observed_at)
  const receivedAt = asString(raw.received_at)
  const { model, modelVersion } = provenanceOf(raw)

  return {
    detectionId,
    cameraId,
    class: mapDetectionClass(raw.class_name),
    subclass: asString(raw.provider_class),
    confidence: normalizeConfidence(raw.confidence),
    bbox: mapBBox(raw.bbox),
    // '' renders as '—' — a missing observation time is shown as absent,
    // never replaced by "now".
    timestamp: observedAt ?? receivedAt ?? '',
    receivedAt,
    updatedAt: asString(raw.processed_at) ?? receivedAt,
    frameId: asString(raw.frame_id),
    frameNumber: null,
    fps: null,
    frameWidth: asNumber(raw.frame_width),
    frameHeight: asNumber(raw.frame_height),
    quality: mapQuality(raw.quality_state),
    occlusion: mapOcclusion(raw.occlusion_state),
    state: mapDetectionState(raw.detection_state),
    // The live backend contract carries no geometry flags — they are not
    // inferred from motion or position.
    partial: false,
    frameEdge: false,
    smallTarget: false,
    longRange: false,
    source: mapSource(raw.source),
    model,
    provider: asString(raw.provider),
    modelVersion,
    trackId: asString(raw.track_id),
    eventId: asString(raw.event_id),
    incidentId: asString(raw.incident_id),
    evidenceId: asString(raw.evidence_id),
    correlationId: asString(raw.correlation_id),
    cameraHealth: mapCameraHealthContext(raw.camera_health_context, cameraId),
    regionProfile: asString(raw.region_profile),
    visibility: null,
    anprRef: asString(raw.anpr_ref),
  }
}

export function mapDetectionPage(raw: unknown): DetectionResultPage {
  if (!isRecord(raw)) return { detections: [], total: 0 }
  const detections = Array.isArray(raw.detections)
    ? raw.detections.map(mapDetection).filter((d): d is DetectionResult => d !== null)
    : []
  const total = asNumber(raw.total)
  return { detections, total: total !== null ? total : detections.length }
}

/**
 * Composed camera feed. A malformed payload becomes UNAVAILABLE with zero
 * rows — the UI then shows "detection unavailable", never an empty success.
 */
export function mapDetectionFeed(raw: unknown, cameraId: string): DetectionFeed {
  if (!isRecord(raw)) {
    return { cameraId, state: 'UNAVAILABLE', inference: 'UNKNOWN', lastUpdatedAt: null, detections: [] }
  }
  const detections = Array.isArray(raw.detections)
    ? raw.detections.map(mapDetection).filter((d): d is DetectionResult => d !== null)
    : []
  return {
    cameraId: asString(raw.camera_id) ?? cameraId,
    state: mapFeedState(raw.state),
    inference: mapInferenceState(raw.inference),
    lastUpdatedAt: asString(raw.last_updated_at),
    detections,
  }
}

/**
 * Camera aggregate summary. Returns null when the backend did not report a
 * total — a summary is never fabricated from nothing. Class/quality keys are
 * narrowed to the canonical sets so unknown backend vocabularies cannot leak
 * into the UI.
 */
export function mapCameraDetectionSummary(raw: unknown, cameraId: string): DetectionSummary | null {
  if (!isRecord(raw)) return null
  const total = asNumber(raw.total_detections)
  if (total === null) return null

  const byClass: Partial<Record<DetectionClass, number>> = {}
  if (isRecord(raw.by_class)) {
    for (const [k, v] of Object.entries(raw.by_class)) {
      const key = k.toUpperCase()
      const n = asNumber(v)
      if (n !== null && CLASS_SET.has(key)) byClass[key as DetectionClass] = n
    }
  }
  const qualitySummary: Partial<Record<DetectionQuality, number>> = {}
  if (isRecord(raw.quality_summary)) {
    for (const [k, v] of Object.entries(raw.quality_summary)) {
      const key = k.toUpperCase()
      const n = asNumber(v)
      if (n !== null && QUALITY_SET.has(key)) qualitySummary[key as DetectionQuality] = n
    }
  }

  return {
    cameraId: asString(raw.camera_id) ?? cameraId,
    total,
    byClass,
    lowConfidenceCount: asNumber(raw.low_confidence_count) ?? 0,
    qualitySummary,
    lastUpdatedAt: asString(raw.last_observed_at),
  }
}

// ── query translation (frontend query → backend parameters) ─────────────────

/**
 * Sort mapping. 'latest' honors the order toggle (desc = newest first,
 * matching the toggle label and the backend's observed_at semantics); 'oldest'
 * pins ascending so its label always holds. Non-time sorts pass the toggle
 * through on their own backend field.
 */
export function sortToBackendParams(
  sort: DetectionQuery['sort'],
  order: DetectionQuery['order']
): { sort: 'observed_at' | 'confidence' | 'class_name' | 'camera_id'; order: 'asc' | 'desc' } {
  switch (sort) {
    case 'oldest':
      return { sort: 'observed_at', order: 'asc' }
    case 'confidence':
      return { sort: 'confidence', order }
    case 'class':
      return { sort: 'class_name', order }
    case 'camera':
      return { sort: 'camera_id', order }
    case 'latest':
    default:
      return { sort: 'observed_at', order }
  }
}

/**
 * Display confidence cutoff (percent 0..100) → backend `min_confidence` ratio
 * string (0..1). Clamped so a stray value can never produce a 422.
 */
export function confidencePercentToRatioParam(percent: number): string {
  const clamped = Math.min(100, Math.max(0, percent))
  return String(Math.round(clamped) / 100)
}

/**
 * Relative time range → absolute `from_time` ISO anchor. 'today' anchors to
 * local midnight (the operator's day), matching how the UI labels it. 'all'
 * returns null (no parameter).
 */
export function timeRangeFromIso(range: DetectionQuery['timeRange'], now: Date): string | null {
  switch (range) {
    case '15m':
      return new Date(now.getTime() - 15 * 60_000).toISOString()
    case '1h':
      return new Date(now.getTime() - 60 * 60_000).toISOString()
    case 'today': {
      const midnight = new Date(now)
      midnight.setHours(0, 0, 0, 0)
      return midnight.toISOString()
    }
    case 'all':
    default:
      return null
  }
}
