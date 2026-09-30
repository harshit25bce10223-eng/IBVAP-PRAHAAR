// PRHAAR Component 5 — REAL-mode mapper tests (§22)
//
// The live backend is the authority for every semantic field. These tests pin
// the seams that guarantee the frontend never upgrades a backend answer:
// unknown vocabularies collapse to UNKNOWN/UNAVAILABLE, a malformed payload is
// never READY, an absent id drops the row, and a percent confidence is
// normalized without being invented or clamped. Query translation is pinned to
// the exact backend parameter names (sort/order/min_confidence/from_time).

import { describe, expect, it } from 'vitest'
import {
  mapDetectionClass,
  mapQuality,
  mapOcclusion,
  mapDetectionState,
  mapSource,
  mapFeedState,
  mapInferenceState,
  normalizeConfidence,
  mapDetection,
  mapDetectionPage,
  mapDetectionFeed,
  mapCameraDetectionSummary,
  sortToBackendParams,
  confidencePercentToRatioParam,
  timeRangeFromIso,
} from '../mapDetection'

// A realistic DetectionDetailResponse row (snake_case, as the backend sends it).
function backendRow(overrides: Record<string, unknown> = {}): Record<string, unknown> {
  return {
    detection_id: 'DET-90001',
    camera_id: 'CAM-07',
    frame_id: 'FRM-1284221',
    class_name: 'PERSON',
    class_id: 0,
    confidence: 0.94,
    bbox: { x: 0.1, y: 0.2, width: 0.3, height: 0.4 },
    frame_width: 1920,
    frame_height: 1080,
    quality_state: 'GOOD',
    occlusion_state: 'LOW',
    detection_state: 'DETECTED',
    source: 'EDGE',
    provider: 'demo-inference',
    observed_at: '2026-09-07T04:00:00Z',
    received_at: '2026-09-07T04:00:01Z',
    processed_at: '2026-09-07T04:00:02Z',
    track_id: 'TRK-1042',
    event_id: null,
    incident_id: null,
    evidence_id: null,
    anpr_ref: 'SIGHT-22017',
    region_profile: 'PUNJAB-BORDER-A',
    provider_class: 'PEDESTRIAN',
    camera_health_context: null,
    provider_metadata: { model_name: 'meta-model', model_version: 'meta-v9' },
    ...overrides,
  }
}

// ── enum canonicalization ───────────────────────────────────────────────────

describe('enum canonicalization (unknown backend vocabulary → canonical, never guessed)', () => {
  it('classes: canonical passes, other/garbage collapses to UNKNOWN', () => {
    expect(mapDetectionClass('PERSON')).toBe('PERSON')
    expect(mapDetectionClass('person')).toBe('PERSON')
    expect(mapDetectionClass('TRUCK')).toBe('UNKNOWN')
    expect(mapDetectionClass(null)).toBe('UNKNOWN')
    expect(mapDetectionClass(42)).toBe('UNKNOWN')
  })

  it('quality: canonical passes, unknown collapses to UNKNOWN', () => {
    expect(mapQuality('GOOD')).toBe('GOOD')
    expect(mapQuality('limited')).toBe('LIMITED')
    expect(mapQuality('EXCELLENT')).toBe('UNKNOWN')
    expect(mapQuality(undefined)).toBe('UNKNOWN')
  })

  it('occlusion: only LOW/MEDIUM/HIGH survive; UNKNOWN hides (null), never invents one', () => {
    expect(mapOcclusion('HIGH')).toBe('HIGH')
    expect(mapOcclusion('UNKNOWN')).toBeNull()
    expect(mapOcclusion('NONE')).toBeNull()
    expect(mapOcclusion(null)).toBeNull()
  })

  it('detection state: canonical passes, backend-only or garbage collapses to UNKNOWN', () => {
    expect(mapDetectionState('LOW_CONFIDENCE')).toBe('LOW_CONFIDENCE')
    expect(mapDetectionState('OCCLUDED')).toBe('OCCLUDED')
    expect(mapDetectionState('STALE')).toBe('UNKNOWN')
    expect(mapDetectionState('')).toBe('UNKNOWN')
  })

  it('source: EDGE/CENTRAL/REMOTE/DEMO pass verbatim, garbage collapses to UNKNOWN', () => {
    expect(mapSource('EDGE')).toBe('EDGE')
    expect(mapSource('REMOTE')).toBe('REMOTE')
    expect(mapSource('DEMO')).toBe('DEMO')
    expect(mapSource('SATELLITE')).toBe('UNKNOWN')
  })

  it('feed state: PROCESSING/DEGRADED → STALE (delayed, not fresh); UNKNOWN/garbage → UNAVAILABLE', () => {
    expect(mapFeedState('READY')).toBe('READY')
    expect(mapFeedState('NO_OBJECTS')).toBe('NO_OBJECTS')
    expect(mapFeedState('UNCONFIGURED')).toBe('UNCONFIGURED')
    expect(mapFeedState('STALE')).toBe('STALE')
    expect(mapFeedState('PROCESSING')).toBe('STALE')
    expect(mapFeedState('DEGRADED')).toBe('STALE')
    expect(mapFeedState('OFFLINE')).toBe('OFFLINE')
    expect(mapFeedState('UNKNOWN')).toBe('UNAVAILABLE')
    expect(mapFeedState('WHATEVER')).toBe('UNAVAILABLE')
    expect(mapFeedState(null)).toBe('UNAVAILABLE')
  })

  it('inference state: LOADING/WARMING → PROCESSING; FAILED → UNAVAILABLE; garbage → UNKNOWN', () => {
    expect(mapInferenceState('READY')).toBe('READY')
    expect(mapInferenceState('LOADING')).toBe('PROCESSING')
    expect(mapInferenceState('WARMING')).toBe('PROCESSING')
    expect(mapInferenceState('DEGRADED')).toBe('DEGRADED')
    expect(mapInferenceState('OFFLINE')).toBe('OFFLINE')
    expect(mapInferenceState('FAILED')).toBe('UNAVAILABLE')
    expect(mapInferenceState('UNAVAILABLE')).toBe('UNAVAILABLE')
    expect(mapInferenceState('???')).toBe('UNKNOWN')
  })
})

// ── confidence ──────────────────────────────────────────────────────────────

describe('confidence normalization (0–1 ratio out; never invented, never clamped)', () => {
  it('accepts a ratio as-is and converts a percent by /100', () => {
    expect(normalizeConfidence(0.94)).toBeCloseTo(0.94)
    expect(normalizeConfidence(94)).toBeCloseTo(0.94)
    expect(normalizeConfidence(1)).toBe(1)
    expect(normalizeConfidence(100)).toBe(1)
    expect(normalizeConfidence(0)).toBe(0)
  })

  it('drops out-of-range and non-numeric values to null (N/A)', () => {
    expect(normalizeConfidence(-0.1)).toBeNull()
    expect(normalizeConfidence(101)).toBeNull()
    expect(normalizeConfidence(null)).toBeNull()
    expect(normalizeConfidence('0.9')).toBeNull()
    expect(normalizeConfidence(NaN)).toBeNull()
    expect(normalizeConfidence(Infinity)).toBeNull()
  })
})

// ── mapDetection ────────────────────────────────────────────────────────────

describe('mapDetection (snake_case row → canonical DetectionResult)', () => {
  it('renames every field the Inspector consumes', () => {
    const d = mapDetection(backendRow())!
    expect(d.detectionId).toBe('DET-90001')
    expect(d.cameraId).toBe('CAM-07')
    expect(d.frameId).toBe('FRM-1284221')
    expect(d.class).toBe('PERSON')
    expect(d.subclass).toBe('PEDESTRIAN')
    expect(d.confidence).toBeCloseTo(0.94)
    expect(d.bbox).toEqual({ x: 0.1, y: 0.2, width: 0.3, height: 0.4 })
    expect(d.timestamp).toBe('2026-09-07T04:00:00Z')
    expect(d.receivedAt).toBe('2026-09-07T04:00:01Z')
    expect(d.updatedAt).toBe('2026-09-07T04:00:02Z')
    expect(d.frameWidth).toBe(1920)
    expect(d.frameHeight).toBe(1080)
    expect(d.quality).toBe('GOOD')
    expect(d.occlusion).toBe('LOW')
    expect(d.state).toBe('DETECTED')
    expect(d.source).toBe('EDGE')
    expect(d.trackId).toBe('TRK-1042')
    expect(d.anprRef).toBe('SIGHT-22017')
    expect(d.regionProfile).toBe('PUNJAB-BORDER-A')
  })

  it('model identity: top-level detail fields win, provider_metadata is the fallback', () => {
    const withTop = mapDetection(backendRow({ model_name: 'live-model', model_version: 'live-v3' }))!
    expect(withTop.model).toBe('live-model')
    expect(withTop.modelVersion).toBe('live-v3')
    const metaOnly = mapDetection(backendRow())!
    expect(metaOnly.model).toBe('meta-model')
    expect(metaOnly.modelVersion).toBe('meta-v9')
    const neither = mapDetection(backendRow({ provider_metadata: null }))!
    expect(neither.model).toBeNull()
    expect(neither.modelVersion).toBeNull()
  })

  it('missing observation time becomes empty string (renders —), never "now"', () => {
    const d = mapDetection(backendRow({ observed_at: null, received_at: null }))!
    expect(d.timestamp).toBe('')
    expect(d.receivedAt).toBeNull()
  })

  it('updatedAt falls back to receivedAt when processed_at is absent', () => {
    const d = mapDetection(backendRow({ processed_at: null }))!
    expect(d.updatedAt).toBe('2026-09-07T04:00:01Z')
  })

  it('rows without a detection id or camera id are dropped — identity is never invented', () => {
    expect(mapDetection(backendRow({ detection_id: null }))).toBeNull()
    expect(mapDetection(backendRow({ detection_id: '' }))).toBeNull()
    expect(mapDetection(backendRow({ camera_id: null }))).toBeNull()
    expect(mapDetection(null)).toBeNull()
    expect(mapDetection('row')).toBeNull()
  })

  it('malformed bbox degrades to null rather than partial coordinates', () => {
    expect(mapDetection(backendRow({ bbox: { x: 0.1, y: 0.2 } }))!.bbox).toBeNull()
    expect(mapDetection(backendRow({ bbox: null }))!.bbox).toBeNull()
  })

  it('geometry flags are never inferred from the live payload', () => {
    const d = mapDetection(backendRow())!
    expect(d.partial || d.frameEdge || d.smallTarget || d.longRange).toBe(false)
  })

  it('camera health context stays null unless the backend flagged something', () => {
    expect(mapDetection(backendRow())!.cameraHealth).toBeNull()
    const flagged = mapDetection(
      backendRow({ camera_health_context: { state: 'DEGRADED', reliability: 'LOW', viewpoint_shift: true } })
    )!
    expect(flagged.cameraHealth).toEqual({
      cameraId: 'CAM-07',
      reliability: 'LOW',
      viewpointShift: true,
      note: null,
    })
  })
})

// ── page / feed / summary ───────────────────────────────────────────────────

describe('mapDetectionPage', () => {
  it('maps rows and keeps the backend total', () => {
    const page = mapDetectionPage({ detections: [backendRow(), backendRow({ detection_id: 'DET-90002' })], total: 57 })
    expect(page.detections).toHaveLength(2)
    expect(page.total).toBe(57)
  })

  it('falls back to the mapped length when total is absent and drops malformed rows', () => {
    const page = mapDetectionPage({ detections: [backendRow({ detection_id: null }), backendRow()] })
    expect(page.detections).toHaveLength(1)
    expect(page.total).toBe(1)
  })

  it('a malformed page is empty, never a crash', () => {
    expect(mapDetectionPage(null)).toEqual({ detections: [], total: 0 })
    expect(mapDetectionPage({ detections: 'nope' }).detections).toEqual([])
  })
})

describe('mapDetectionFeed', () => {
  it('maps the feed envelope and canonicalizes both states', () => {
    const feed = mapDetectionFeed(
      { camera_id: 'CAM-07', state: 'PROCESSING', inference: 'WARMING', last_updated_at: '2026-09-07T04:00:00Z', detections: [backendRow()] },
      'CAM-07'
    )
    expect(feed.cameraId).toBe('CAM-07')
    expect(feed.state).toBe('STALE')
    expect(feed.inference).toBe('PROCESSING')
    expect(feed.lastUpdatedAt).toBe('2026-09-07T04:00:00Z')
    expect(feed.detections).toHaveLength(1)
  })

  it('a malformed payload is UNAVAILABLE with zero rows — never an empty success', () => {
    const feed = mapDetectionFeed(undefined, 'CAM-21')
    expect(feed.state).toBe('UNAVAILABLE')
    expect(feed.detections).toEqual([])
    expect(feed.cameraId).toBe('CAM-21')
  })
})

describe('mapCameraDetectionSummary', () => {
  it('maps structural counts and narrows keys to the canonical sets', () => {
    const s = mapCameraDetectionSummary(
      {
        camera_id: 'CAM-07',
        total_detections: 12,
        by_class: { PERSON: 7, VEHICLE: 4, TRUCK: 1 },
        low_confidence_count: 3,
        quality_summary: { GOOD: 9, EXCELLENT: 3 },
        last_observed_at: '2026-09-07T03:59:00Z',
      },
      'CAM-07'
    )!
    expect(s.total).toBe(12)
    expect(s.byClass).toEqual({ PERSON: 7, VEHICLE: 4 }) // TRUCK is not a canonical class
    expect(s.qualitySummary).toEqual({ GOOD: 9 }) // EXCELLENT is not a canonical quality
    expect(s.lowConfidenceCount).toBe(3)
    expect(s.lastUpdatedAt).toBe('2026-09-07T03:59:00Z')
  })

  it('returns null when the backend did not report a total — a summary is never fabricated', () => {
    expect(mapCameraDetectionSummary({ camera_id: 'CAM-07' }, 'CAM-07')).toBeNull()
    expect(mapCameraDetectionSummary(null, 'CAM-07')).toBeNull()
  })

  it('an absent low-confidence count is 0, not a guess', () => {
    const s = mapCameraDetectionSummary({ camera_id: 'CAM-07', total_detections: 0 }, 'CAM-07')!
    expect(s.lowConfidenceCount).toBe(0)
    expect(s.total).toBe(0)
  })
})

// ── query translation ───────────────────────────────────────────────────────

describe('query → backend parameter translation', () => {
  it('latest honors the order toggle; oldest pins ascending so its label always holds', () => {
    expect(sortToBackendParams('latest', 'desc')).toEqual({ sort: 'observed_at', order: 'desc' })
    expect(sortToBackendParams('latest', 'asc')).toEqual({ sort: 'observed_at', order: 'asc' })
    expect(sortToBackendParams('oldest', 'desc')).toEqual({ sort: 'observed_at', order: 'asc' })
    expect(sortToBackendParams('oldest', 'asc')).toEqual({ sort: 'observed_at', order: 'asc' })
  })

  it('non-time sorts use the backend field names from ALLOWED_SORT_FIELDS', () => {
    expect(sortToBackendParams('confidence', 'desc')).toEqual({ sort: 'confidence', order: 'desc' })
    expect(sortToBackendParams('class', 'asc')).toEqual({ sort: 'class_name', order: 'asc' })
    expect(sortToBackendParams('camera', 'asc')).toEqual({ sort: 'camera_id', order: 'asc' })
  })

  it('percent cutoff → 0..1 ratio string, clamped (backend requires le=1.0)', () => {
    expect(confidencePercentToRatioParam(50)).toBe('0.5')
    expect(confidencePercentToRatioParam(0)).toBe('0')
    expect(confidencePercentToRatioParam(100)).toBe('1')
    expect(confidencePercentToRatioParam(150)).toBe('1')
    expect(confidencePercentToRatioParam(-5)).toBe('0')
  })

  it('time ranges anchor relative to the given now; all → null', () => {
    const now = new Date('2026-09-07T12:30:00Z')
    expect(timeRangeFromIso('15m', now)).toBe('2026-09-07T12:15:00.000Z')
    expect(timeRangeFromIso('1h', now)).toBe('2026-09-07T11:30:00.000Z')
    expect(timeRangeFromIso('all', now)).toBeNull()
  })

  it("'today' anchors to local midnight of the operator's day, not a rolling 24h window", () => {
    const noon = new Date(2026, 8, 7, 12, 30, 0) // local time
    const anchor = timeRangeFromIso('today', noon)!
    const midnight = new Date(noon)
    midnight.setHours(0, 0, 0, 0)
    expect(anchor).toBe(midnight.toISOString())
    expect(new Date(anchor).getHours()).toBe(0)
  })
})
