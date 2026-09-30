// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 5 — mock detection provider (DEMO ONLY)
//
// Serves the isolated fixtures from `mockDetectionData.ts`. Local filtering,
// sorting and pagination make the detection surfaces async on a "service
// boundary" shape, but this module NEVER computes risk, severity, correlation,
// identity or threat — those values are fabricated nowhere and arrive (if at
// all) from backend fields. Summary counts are structural only.
// Unknown detection ids reject so the UI exercises error paths, and a feed for
// an unknown camera throws so surfaces can show DETECTION DATA UNAVAILABLE
// rather than silently fabricating rows.
// ─────────────────────────────────────────────────────────────────────────────

import type {
  DetectionFeed,
  DetectionQuery,
  DetectionResult,
  DetectionResultPage,
  DetectionSummary,
} from '@/types/detection'
import { DETECTION_CLASSES } from '@/types/detection'
import type { IDetectionService } from './IDetectionService'
import {
  DEMO_NOW,
  getMockDetectionById,
  getMockDetectionFeed,
  MOCK_DETECTIONS,
} from './mockDetectionData'

const PROVIDER_DELAY_MS = 250

function delay(ms: number) {
  return new Promise<void>(resolve => setTimeout(resolve, ms))
}

function withinTimeRange(iso: string, range: DetectionQuery['timeRange']): boolean {
  if (range === 'all') return true
  const ref = new Date(DEMO_NOW).getTime()
  const t = new Date(iso).getTime()
  if (Number.isNaN(t)) return false
  // 'today' anchors to local midnight of the demo reference clock — the same
  // day-window the REAL service requests (timeRangeFromIso), not a rolling 24h.
  if (range === 'today') {
    const midnight = new Date(ref)
    midnight.setHours(0, 0, 0, 0)
    return t >= midnight.getTime()
  }
  const minutes = range === '15m' ? 15 : 60
  return ref - t <= minutes * 60_000
}

function matchesQuery(d: DetectionResult, q: DetectionQuery): boolean {
  const s = q.search.trim().toLowerCase()
  const searchHit =
    s === '' ||
    d.detectionId.toLowerCase().includes(s) ||
    d.cameraId.toLowerCase().includes(s) ||
    d.class.toLowerCase().includes(s) ||
    (d.trackId?.toLowerCase().includes(s) ?? false) ||
    (d.eventId?.toLowerCase().includes(s) ?? false) ||
    (d.incidentId?.toLowerCase().includes(s) ?? false) ||
    (d.evidenceId?.toLowerCase().includes(s) ?? false) ||
    (d.correlationId?.toLowerCase().includes(s) ?? false)
  if (!searchHit) return false
  if (q.cameraId !== 'ALL' && d.cameraId !== q.cameraId) return false
  if (q.class !== 'ALL') {
    const matchesClass = q.class === 'OTHER' ? (d.class === 'OBJECT' || d.class === 'UNKNOWN') : d.class === q.class
    if (!matchesClass) return false
  }
  // Display-only confidence cutoff (percent). Null confidence never excluded
  // by a confidence filter — absence is shown as N/A, not as a fail.
  if (q.confidenceMin !== null && d.confidence !== null && d.confidence * 100 < q.confidenceMin) return false
  if (q.quality !== 'ALL' && d.quality !== q.quality) return false
  if (q.source !== 'ALL' && d.source !== q.source) return false
  if (!withinTimeRange(d.timestamp, q.timeRange)) return false
  return true
}

function compareDetections(a: DetectionResult, b: DetectionResult, q: DetectionQuery): number {
  const dir = q.order === 'asc' ? 1 : -1
  switch (q.sort) {
    case 'confidence': {
      const ca = a.confidence ?? -1
      const cb = b.confidence ?? -1
      return (ca - cb) * dir
    }
    case 'class':
      return a.class.localeCompare(b.class) * dir
    case 'camera':
      return a.cameraId.localeCompare(b.cameraId) * dir
    // 'oldest' pins ascending; 'latest' honors the order toggle — desc (the
    // default) is newest first, matching the toggle label and the backend's
    // observed_at ordering (sortToBackendParams).
    case 'oldest':
      return new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
    case 'latest':
    default:
      return (new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()) * dir
  }
}

/** Structural summary only — counts, never risk/severity (§116). */
import { buildSummary } from './detectionSummary'

class MockDetectionService implements IDetectionService {
  readonly source = 'DEMO' as const

  async listDetections(query: DetectionQuery): Promise<DetectionResultPage> {
    await delay(PROVIDER_DELAY_MS)
    const filtered = MOCK_DETECTIONS.filter(d => matchesQuery(d, query)).sort((a, b) => compareDetections(a, b, query))
    const pageSize = query.pageSize
    const start = (query.page - 1) * pageSize
    return {
      detections: filtered.slice(start, start + pageSize),
      total: filtered.length,
    }
  }

  async getDetection(detectionId: string): Promise<DetectionResult> {
    await delay(PROVIDER_DELAY_MS)
    const detection = getMockDetectionById(detectionId)
    if (!detection) {
      throw new Error(`Detection ${detectionId} was not found.`)
    }
    return detection
  }

  async getFeed(cameraId: string): Promise<DetectionFeed> {
    await delay(PROVIDER_DELAY_MS)
    const feed = getMockDetectionFeed(cameraId)
    if (!feed) {
      throw new Error(`Detection data unavailable for camera ${cameraId}.`)
    }
    return feed
  }

  async getSummary(cameraId: string): Promise<DetectionSummary> {
    const feed = await this.getFeed(cameraId)
    return buildSummary(feed.cameraId, feed.detections, feed.lastUpdatedAt)
  }
}

export const mockDetectionService = new MockDetectionService()
export { DETECTION_CLASSES }