// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 5 — mock detection fixtures (DEMO ONLY)
//
// Isolated, hand-written fixtures that exercise every detection surface and
// every distinct empty/unavailable state. All values are authoritative demo
// outputs — this module never computes risk, severity, correlation, tracking,
// identity, ANPR or face matches. Only demo/test infrastructure imports this
// file; components consume the service interface.
//
// Demo timestamps use a fixed fictional date (2026-09-07) so behaviour is
// deterministic. Frame numbers are plausible demo counters, not real streams,
// and are never presented as live. All detection ids are DET-*, always
// distinct from TRK/EV/COR/INC/EVD ids.
// ─────────────────────────────────────────────────────────────────────────────

import type {
  DetectionBBox,
  DetectionCameraHealthContext,
  DetectionClass,
  DetectionFeed,
  DetectionFeedState,
  DetectionOcclusion,
  DetectionQuality,
  DetectionResult,
  InferenceState,
} from '@/types/detection'

const D = '2026-09-07'
/** Deterministic demo reference clock for relative time-range filters. */
export const DEMO_NOW = `${D}T04:00:00Z`

const CAM07_FOOTHILL = 'INDO-NEPAL / FOOTHILL'
const CAM12_FOREST = 'INDO-BHUTAN / HILLY-FOREST'
const CAM19_FRINGE = 'INDO-NEPAL / RURAL FRINGE'

/**
 * Demo model identity. Only mock data carries a name — a REAL provider would
 * surface backend model/version, never this constant (§175).
 */
const DEMO_PROVIDER = 'DEMO DETECTOR'
const DEMO_MODEL = 'DEMO'
const DEMO_VERSION = 'demo'

interface DetectionInput {
  id: string
  cameraId: string
  class: DetectionClass
  confidence: number | null
  bbox: DetectionBBox
  at: string
  quality?: DetectionQuality
  occlusion?: DetectionOcclusion
  state?: DetectionResult['state']
  partial?: boolean
  frameEdge?: boolean
  smallTarget?: boolean
  longRange?: boolean
  source?: DetectionResult['source']
  model?: string | null
  provider?: string | null
  modelVersion?: string | null
  trackId?: string | null
  eventId?: string | null
  incidentId?: string | null
  evidenceId?: string | null
  correlationId?: string | null
  cameraHealth?: DetectionCameraHealthContext | null
  regionProfile?: string | null
  visibility?: DetectionResult['visibility']
  frameNumber?: number | null
  fps?: number | null
  receivedAt?: string | null
  subclass?: string | null
}

function detection(ii: DetectionInput): DetectionResult {
  return {
    detectionId: ii.id,
    cameraId: ii.cameraId,
    class: ii.class,
    subclass: ii.subclass ?? null,
    confidence: ii.confidence,
    bbox: ii.bbox,
    timestamp: ii.at,
    receivedAt: ii.receivedAt ?? ii.at,
    updatedAt: ii.receivedAt ?? ii.at,
    frameNumber: ii.frameNumber ?? null,
    fps: ii.fps ?? null,
    frameWidth: null,
    frameHeight: null,
    quality: ii.quality ?? (ii.confidence === null ? 'UNKNOWN' : 'GOOD'),
    occlusion: ii.occlusion ?? null,
    state: ii.state ?? 'DETECTED',
    partial: ii.partial ?? false,
    frameEdge: ii.frameEdge ?? false,
    smallTarget: ii.smallTarget ?? false,
    longRange: ii.longRange ?? false,
    source: ii.source ?? 'EDGE',
    model: ii.model ?? DEMO_MODEL,
    provider: ii.provider ?? DEMO_PROVIDER,
    modelVersion: ii.modelVersion ?? DEMO_VERSION,
    trackId: ii.trackId ?? null,
    eventId: ii.eventId ?? null,
    incidentId: ii.incidentId ?? null,
    evidenceId: ii.evidenceId ?? null,
    correlationId: ii.correlationId ?? null,
    cameraHealth: ii.cameraHealth ?? null,
    regionProfile: ii.regionProfile ?? null,
    visibility: ii.visibility ?? null,
  }
}

const CAM12_CONTEXT: DetectionCameraHealthContext = {
  cameraId: 'CAM-12',
  reliability: 'LOW',
  viewpointShift: true,
  note: 'Camera viewpoint changed; detection geometry may require review.',
}

// ── S1 — CAM-07 multiple detections, high confidence ────────────────────────
const DET_CAM07_PERSON = detection({
  id: 'DET-10421', cameraId: 'CAM-07', class: 'PERSON', confidence: 0.94,
  bbox: { x: 0.42, y: 0.4, width: 0.1, height: 0.22 },
  at: `${D}T02:14:11Z`, quality: 'GOOD', occlusion: 'LOW',
  trackId: 'TRK-1042', eventId: 'EV-10421', incidentId: 'INC-1042',
  evidenceId: 'EVD-10481', correlationId: 'COR-1042',
  regionProfile: CAM07_FOOTHILL, frameNumber: 1284221, fps: 25,
})
const DET_CAM07_VEHICLE = detection({
  id: 'DET-10422', cameraId: 'CAM-07', class: 'VEHICLE', confidence: 0.89,
  bbox: { x: 0.58, y: 0.46, width: 0.14, height: 0.12 },
  at: `${D}T02:14:15Z`, quality: 'GOOD', occlusion: 'LOW',
  trackId: 'TRK-1042', eventId: 'EV-10422', incidentId: 'INC-1042',
  regionProfile: CAM07_FOOTHILL, frameNumber: 1284225, fps: 25,
})
const DET_CAM07_ANIMAL = detection({
  id: 'DET-10423', cameraId: 'CAM-07', class: 'ANIMAL', confidence: 0.81,
  bbox: { x: 0.2, y: 0.44, width: 0.08, height: 0.16 },
  at: `${D}T02:14:22Z`, quality: 'GOOD', occlusion: 'LOW',
  regionProfile: CAM07_FOOTHILL, frameNumber: 1284232, fps: 25,
})

// ── S7 — overlapping detections (label-collision exercise) ──────────────────
const DET_CAM07_OVERLAP_A = detection({
  id: 'DET-10424', cameraId: 'CAM-07', class: 'PERSON', confidence: 0.72,
  bbox: { x: 0.62, y: 0.42, width: 0.1, height: 0.2 },
  at: `${D}T02:18:05Z`, quality: 'LIMITED', occlusion: 'LOW',
  regionProfile: CAM07_FOOTHILL, frameNumber: 1284415, fps: 25,
})
const DET_CAM07_OVERLAP_B = detection({
  id: 'DET-10425', cameraId: 'CAM-07', class: 'PERSON', confidence: 0.68,
  bbox: { x: 0.66, y: 0.44, width: 0.12, height: 0.18 },
  at: `${D}T02:18:07Z`, quality: 'GOOD', occlusion: 'MEDIUM', state: 'OCCLUDED',
  regionProfile: CAM07_FOOTHILL, frameNumber: 1284417, fps: 25,
})

// ── S2 — CAM-12 degraded health + viewpoint shift (hilly forest) ────────────
const DET_CAM12_PERSON = detection({
  id: 'DET-10431', cameraId: 'CAM-12', class: 'PERSON', confidence: 0.71,
  bbox: { x: 0.34, y: 0.38, width: 0.09, height: 0.2 },
  at: `${D}T02:20:05Z`, quality: 'LIMITED', occlusion: 'MEDIUM', source: 'EDGE',
  cameraHealth: CAM12_CONTEXT, regionProfile: CAM12_FOREST,
  frameNumber: 902147, fps: 30,
})
const DET_CAM12_ANIMAL = detection({
  id: 'DET-10432', cameraId: 'CAM-12', class: 'ANIMAL', confidence: 0.64,
  bbox: { x: 0.48, y: 0.4, width: 0.06, height: 0.14 },
  at: `${D}T02:20:11Z`, quality: 'LIMITED', occlusion: 'HIGH', source: 'EDGE',
  cameraHealth: CAM12_CONTEXT, regionProfile: CAM12_FOREST,
  frameNumber: 902153, fps: 30,
})
const DET_CAM12_PARTIAL_VEHICLE = detection({
  id: 'DET-10433', cameraId: 'CAM-12', class: 'VEHICLE', confidence: 0.77,
  bbox: { x: 0.9, y: 0.44, width: 0.1, height: 0.1 },
  at: `${D}T02:21:40Z`, quality: 'GOOD', occlusion: 'LOW', source: 'EDGE',
  state: 'PARTIAL', partial: true, frameEdge: true,
  cameraHealth: CAM12_CONTEXT, regionProfile: CAM12_FOREST,
  frameNumber: 902260, fps: 30,
})

// ── S3 — CAM-19 long-range small distant PERSON, low confidence (edge post) ─
const DET_CAM19_LONG_RANGE = detection({
  id: 'DET-10441', cameraId: 'CAM-19', class: 'PERSON', confidence: 0.42,
  bbox: { x: 0.49, y: 0.38, width: 0.02, height: 0.05 },
  at: `${D}T02:33:12Z`, quality: 'POOR', occlusion: 'LOW', source: 'EDGE',
  state: 'LOW_CONFIDENCE', smallTarget: true, longRange: true,
  visibility: 'NIGHT', regionProfile: CAM19_FRINGE,
  frameNumber: 764093, fps: 25,
})

// ── S8 — future tracking compatibility reference (no tracking implemented) ──
// DET-10421 already carries trackId TRK-1042; it is a fixture-only reference
// for a FUTURE tracking module and must never create a track here.
const TRACK_REFERENCE_DETECTION_ID = 'DET-10421'

/** Camera feeds by camera id — the canonical fixture table for this module. */
const MOCK_FEEDS: Record<string, { state: DetectionFeedState; inference: InferenceState; lastUpdatedAt: string; detections: DetectionResult[] }> = {
  // S1/S7 — CAM-07: multiple high-confidence detections incl. overlap
  'CAM-07': {
    state: 'READY',
    inference: 'READY',
    lastUpdatedAt: `${D}T02:18:10Z`,
    detections: [
      DET_CAM07_PERSON,
      DET_CAM07_VEHICLE,
      DET_CAM07_ANIMAL,
      DET_CAM07_OVERLAP_A,
      DET_CAM07_OVERLAP_B,
    ],
  },
  // S2 — CAM-12: degraded health, viewpoint shift, partial/edge vehicle
  'CAM-12': {
    state: 'READY',
    inference: 'READY',
    lastUpdatedAt: `${D}T02:21:42Z`,
    detections: [DET_CAM12_PERSON, DET_CAM12_ANIMAL, DET_CAM12_PARTIAL_VEHICLE],
  },
  // S3 — CAM-19: offline edge post, STALE last-known long-range detection
  'CAM-19': {
    state: 'STALE',
    inference: 'DEGRADED',
    lastUpdatedAt: `${D}T02:33:12Z`,
    detections: [DET_CAM19_LONG_RANGE],
  },
  // S4 — CAM-03: detector ready, ZERO objects (distinct from unavailable)
  'CAM-03': {
    state: 'NO_OBJECTS',
    inference: 'READY',
    lastUpdatedAt: `${D}T02:40:00Z`,
    detections: [],
  },
  // S5 — CAM-21: inference unavailable (not a zero-object report)
  'CAM-21': {
    state: 'UNAVAILABLE',
    inference: 'UNAVAILABLE',
    lastUpdatedAt: `${D}T02:45:00Z`,
    detections: [],
  },
}

export const MOCK_DETECTION_CAMERAS = Object.keys(MOCK_FEEDS)
export const MOCK_DETECTIONS: DetectionResult[] = Object.values(MOCK_FEEDS).flatMap(f => f.detections)

export function getMockDetectionFeed(cameraId: string): DetectionFeed | null {
  const entry = MOCK_FEEDS[cameraId]
  if (!entry) return null
  return {
    cameraId,
    state: entry.state,
    inference: entry.inference,
    lastUpdatedAt: entry.lastUpdatedAt,
    detections: entry.detections,
  }
}

export function getMockDetectionById(detectionId: string): DetectionResult | null {
  return MOCK_DETECTIONS.find(d => d.detectionId === detectionId) ?? null
}

export const TRACK_REFERENCE_FIXTURE_ID = TRACK_REFERENCE_DETECTION_ID