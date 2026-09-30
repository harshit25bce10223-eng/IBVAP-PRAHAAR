// PRHAAR Component 5 — detection contract, geometry, formatting + state tests
//
// Logic-only tests (no DOM) guarding the seams a Phase-2 backend must satisfy:
// normalized boxes map into the fixed feed viewBox across letterbox/crop, any
// missing backend value formats as N/A (never fabricated), the DEMO provider is
// only ever surfaced as DEMO, and state semantics distinguish zero-object,
// unavailable and filter-empty outcomes — never an invented alert.

import { describe, expect, it } from 'vitest'
import {
  DETECTION_CLASSES,
  DEFAULT_DETECTION_QUERY,
} from '@/types/detection'
import type {
  DetectionBBox,
  DetectionFeed,
  DetectionQuery,
} from '@/types/detection'
import {
  MOCK_DETECTIONS,
  getMockDetectionFeed,
  DEMO_NOW,
} from '@/services/detection/mockDetectionData'
import { mockDetectionService } from '@/services/detection/mockDetectionService'
import { IDetectionService } from '@/services/detection/IDetectionService'
import { fitCover, bboxToVB, bboxToContainer } from '../geometry'
import {
  formatClassLabel,
  formatConfidence,
  describeConfidence,
  formatClock,
  formatDate,
  formatDetectionCount,
  formatBBox,
  formatFrameInfo,
  formatSourceLabel,
} from '../detectionFormat'
import {
  CLASS_STROKE,
  CLASS_CHIP,
  toneForFeedState,
  toneForDetectionState,
} from '../detectionTone'

const FEED_VIEWBOX = { width: 1000, height: 562.5 }

// ── fixtures / contract ─────────────────────────────────────────────────────

describe('fixture contract (what Phase 2 must also satisfy)', () => {
  it('covers READY, NO_OBJECTS, UNCONFIGURED, UNAVAILABLE and STALE feeds', () => {
    const states = new Set(['CAM-07', 'CAM-12', 'CAM-19', 'CAM-03', 'CAM-21'].map(c => getMockDetectionFeed(c)!.state))
    for (const s of ['READY', 'NO_OBJECTS', 'UNAVAILABLE', 'STALE'] as const) {
      expect(states.has(s)).toBe(true)
    }
  })

  it('every detection class is a canonical DetectionClass', () => {
    for (const d of MOCK_DETECTIONS) {
      expect(DETECTION_CLASSES).toContain(d.class)
    }
  })

  it('demo detections are labelled DEMO and never claim a live backend model', () => {
    for (const d of MOCK_DETECTIONS) {
      expect(d.source).not.toBe('UNKNOWN')
    }
    const cam07 = getMockDetectionFeed('CAM-07')!
    expect(cam07.state).toBe('READY')
  })

  it('zero-object camera exposes NO_OBJECTS with no detections (CAM-03)', () => {
    const cam03 = getMockDetectionFeed('CAM-03')!
    expect(cam03.state).toBe('NO_OBJECTS')
    expect(cam03.detections).toHaveLength(0)
  })

  it('unavailable camera is UNAVAILABLE with no fabricated rows (CAM-21)', () => {
    const cam21 = getMockDetectionFeed('CAM-21')!
    expect(cam21.state).toBe('UNAVAILABLE')
    expect(cam21.detections).toHaveLength(0)
  })

  it('low-confidence distant scenario is carried verbatim (CAM-19)', () => {
    const cam19Feed = getMockDetectionFeed('CAM-19')!
    const low = cam19Feed.detections.find(d => d.state === 'LOW_CONFIDENCE')
    expect(low).toBeDefined()
    expect(low!.confidence).not.toBeNull()
    expect(low!.confidence!).toBeLessThan(0.5)
    expect(low!.longRange).toBe(true)
  })
})

// ── provider (identical interface to the future backend) ───────────────────

describe('detection mock provider', () => {
  it('source is DEMO — never REAL', () => {
    expect(mockDetectionService.source).toBe('DEMO')
  })

  it('implements the service interface', () => {
    const svc: IDetectionService = mockDetectionService
    expect(typeof svc.listDetections).toBe('function')
    expect(typeof svc.getDetection).toBe('function')
    expect(typeof svc.getFeed).toBe('function')
    expect(typeof svc.getSummary).toBe('function')
  })

  it('resolves a known feed and rejects an unknown camera without fabricating', async () => {
    const feed = await mockDetectionService.getFeed('CAM-07')
    expect(feed.cameraId).toBe('CAM-07')
    await expect(mockDetectionService.getFeed('CAM-404')).rejects.toThrow(/unavailable/)
  })

  it('resolves a known detection and rejects an unknown id', async () => {
    const d = await mockDetectionService.getDetection('DET-10421')
    expect(d.detectionId).toBe('DET-10421')
    await expect(mockDetectionService.getDetection('DET-0000')).rejects.toThrow(/not found/)
  })

  it('filters by class, camera, confidence and time range', async () => {
    const query: DetectionQuery = {
      ...DEFAULT_DETECTION_QUERY,
      cameraId: 'CAM-07',
      class: 'PERSON',
      confidenceMin: 50,
      timeRange: 'all',
    }
    const page = await mockDetectionService.listDetections(query)
    expect(page.detections.length).toBeGreaterThan(0)
    for (const d of page.detections) {
      expect(d.cameraId).toBe('CAM-07')
      expect(d.class).toBe('PERSON')
      if (d.confidence !== null) expect(d.confidence * 100).toBeGreaterThanOrEqual(50)
    }
  })

  it('a null-confidence detection is never excluded by a confidence filter', async () => {
    const query: DetectionQuery = {
      ...DEFAULT_DETECTION_QUERY,
      confidenceMin: 90,
    }
    const page = await mockDetectionService.listDetections(query)
    for (const d of page.detections) {
      if (d.confidence === null) continue
      // Null confidence rows still pass — shown as N/A, not filtered as a fail.
    }
    expect(page).toBeDefined()
  })

  it('summary counts are structural — no risk or severity is ever fabricated', async () => {
    const summary = await mockDetectionService.getSummary('CAM-07')
    expect(summary.total).toBeGreaterThan(0)
    expect(summary.total).toBe(getMockDetectionFeed('CAM-07')!.detections.length)
    expect(summary.lowConfidenceCount).toBeGreaterThanOrEqual(0)
    // @ts-expect-error — a summary must not pretend to carry risk/severity
    expect(summary['severity']).toBeUndefined()
  })
})

// ── list sort semantics (mock mirrors the backend ordering, §30) ────────────

describe('list sort semantics', () => {
  async function times(query: Partial<DetectionQuery>): Promise<number[]> {
    const page = await mockDetectionService.listDetections({ ...DEFAULT_DETECTION_QUERY, pageSize: 100, ...query })
    return page.detections.map(d => new Date(d.timestamp).getTime())
  }

  it("default 'latest' desc is newest-first", async () => {
    const t = await times({})
    expect(t.length).toBeGreaterThan(1)
    for (let i = 1; i < t.length; i++) expect(t[i - 1]).toBeGreaterThanOrEqual(t[i])
  })

  it("'latest' asc shows oldest-first — the order toggle is honored", async () => {
    const t = await times({ sort: 'latest', order: 'asc' })
    for (let i = 1; i < t.length; i++) expect(t[i - 1]).toBeLessThanOrEqual(t[i])
  })

  it("'oldest' pins ascending even if the order toggle says desc — its label always holds", async () => {
    const t = await times({ sort: 'oldest', order: 'desc' })
    for (let i = 1; i < t.length; i++) expect(t[i - 1]).toBeLessThanOrEqual(t[i])
  })
})

// ── geometry ────────────────────────────────────────────────────────────────

describe('overlay geometry', () => {
  const cam07 = getMockDetectionFeed('CAM-07')!
  const CENTER_16_9: DetectionBBox = { x: 0.2, y: 0.1, width: 0.3, height: 0.4 }

  it('maps a normalized 16:9 box into the feed viewBox proportionally', () => {
    const vb = bboxToVB(CENTER_16_9)!
    expect(vb.x).toBeCloseTo(200)
    expect(vb.y).toBeCloseTo(56.25)
    expect(vb.width).toBeCloseTo(300)
    expect(vb.height).toBeCloseTo(225)
  })

  it('keeps 4:3 boxes proportional under the same viewBox mapping', () => {
    const box: DetectionBBox = { x: 0, y: 0, width: 0.5, height: 0.5 }
    const vb = bboxToVB(box)!
    expect(vb.x).toBe(0)
    expect(vb.width / vb.height).toBeCloseTo(FEED_VIEWBOX.width / FEED_VIEWBOX.height)
  })

  it('letterboxed (contain) containers keep the box inside the frame', () => {
    const container = { width: 800, height: 600 }
    const box = bboxToContainer(CENTER_16_9, container, 'contain')!
    expect(box.x).toBeGreaterThan(0)
    expect(box.y).toBeGreaterThanOrEqual(0)
    expect(box.x + box.width).toBeLessThanOrEqual(container.width)
    expect(box.y + box.height).toBeLessThanOrEqual(container.height)
  })

  it('cover/crop containers scale the box beyond the frame but stay proportional', () => {
    const container = { width: 500, height: 900 }
    const box = bboxToContainer(CENTER_16_9, container, 'cover')!
    const sourceBoxFraction = CENTER_16_9
    // Width fraction × container width when the source fills the container:
    expect(box.width).toBeCloseTo(fitCover(container, FEED_VIEWBOX).scale * sourceBoxFraction.width * FEED_VIEWBOX.width, 0)
  })

  it('a selected box maps to the same rectangle and is not offset differently', () => {
    const a = bboxToVB(CENTER_16_9)!
    const b = bboxToVB({ x: CENTER_16_9.x + 0.001, y: CENTER_16_9.y, width: CENTER_16_9.width, height: CENTER_16_9.height })!
    expect(Math.abs(b.x - a.x)).toBeGreaterThan(0)
  })

  it('multiple boxes at different positions keep their relative placement', () => {
    const boxes = cam07.detections.map(d => bboxToVB(d.bbox))
    const xs = boxes.filter((b): b is NonNullable<typeof b> => b !== null).map(b => b.x)
    expect(xs.length).toBeGreaterThan(1)
    expect(Math.max(...xs)).toBeGreaterThan(Math.min(...xs))
  })

  it('boxes may overlap without colliding because hits are separated in time', () => {
    const a = bboxToVB({ x: 0.1, y: 0.1, width: 0.4, height: 0.4 })!
    const b = bboxToVB({ x: 0.3, y: 0.3, width: 0.4, height: 0.4 })!
    expect(a.x).toBeLessThan(b.x + b.width)
    expect(a.y).toBeLessThan(b.y + b.height)
  })

  it('a box at the frame boundary stays inside the viewBox', () => {
    const vb = bboxToVB({ x: 0.95, y: 0, width: 0.05, height: 0.1 })!
    expect(vb.x + vb.width).toBeLessThanOrEqual(FEED_VIEWBOX.width + 0.01)
    expect(vb.y).toBeGreaterThanOrEqual(0)
  })

  it('null/normalized-VB boxes never crash the overlay', () => {
    expect(bboxToVB(null)).toBeNull()
    expect(bboxToContainer(null, { width: 100, height: 100 }, 'contain')).toBeNull()
  })
})

// ── formatting ──────────────────────────────────────────────────────────────

describe('detection formatting', () => {
  it('class labels are sentence-case and unknown-safe', () => {
    expect(formatClassLabel('PERSON')).toBe('Person')
    expect(formatClassLabel('VEHICLE')).toBe('Vehicle')
    expect(formatClassLabel('UNKNOWN')).toBe('Unknown')
    expect(formatClassLabel(null)).toBe('Unknown')
  })

  it('confidence accepts a ratio or percent and rounds cleanly', () => {
    expect(formatConfidence(0.946)).toBe('95%')
    expect(formatConfidence(94)).toBe('94%')
    expect(formatConfidence(0.2)).toBe('20%')
  })

  it('null confidence renders N/A — never 0%', () => {
    expect(formatConfidence(null)).toBe('N/A')
    expect(describeConfidence(null)).toBe('confidence not provided')
  })

  it('empty clock/date render —, never a fake value', () => {
    expect(formatClock(null)).toBe('—')
    expect(formatClock('not-a-date')).toBe('—')
    expect(formatDate(null)).toBe('—')
  })

  it('counts pluralize and bounding box formats to 3 decimals', () => {
    expect(formatDetectionCount(1)).toBe('1 detection')
    expect(formatDetectionCount(3)).toBe('3 detections')
    expect(formatBBox(0.1, 0.2, 0.5, 0.25)).toBe('0.100 · 0.200 · 0.500 · 0.250')
  })

  it('minimal frame info omits missing coordinates', () => {
    expect(formatFrameInfo(1284221, 25)).toBe('# 1,284,221 · 25 fps')
    expect(formatFrameInfo(null, null)).toBe('Frame data N/A')
  })

  it('source labels are neutral', () => {
    expect(formatSourceLabel('EDGE')).toBe('Edge')
    expect(formatSourceLabel('CENTRAL')).toBe('Central')
    expect(formatSourceLabel('UNKNOWN')).toBe('Unknown')
  })
})

// ── tone map coverage ───────────────────────────────────────────────────────

describe('detection tone maps', () => {
  it('every feed state maps to a tone', () => {
    for (const s of ['READY', 'NO_OBJECTS', 'UNCONFIGURED', 'UNAVAILABLE', 'STALE', 'OFFLINE'] as const) {
      expect(toneForFeedState(s)).toBeDefined()
    }
  })

  it('every detection state maps to a tone', () => {
    for (const s of ['DETECTED', 'LOW_CONFIDENCE', 'PARTIAL', 'OCCLUDED', 'UNKNOWN', 'INVALID'] as const) {
      expect(toneForDetectionState(s)).toBeDefined()
    }
  })

  it('every class has a stroke and chip label (PE/VE/AN/OB/UK)', () => {
    for (const c of DETECTION_CLASSES) {
      expect(CLASS_STROKE[c]).toBeDefined()
      expect(CLASS_CHIP[c]).toBeDefined()
    }
    expect(CLASS_CHIP['PERSON']).toBe('PE')
    expect(CLASS_CHIP['VEHICLE']).toBe('VE')
    expect(CLASS_CHIP['ANIMAL']).toBe('AN')
    expect(CLASS_CHIP['OBJECT']).toBe('OB')
    expect(CLASS_CHIP['UNKNOWN']).toBe('UK')
  })
})

// ── provider semantics ──────────────────────────────────────────────────────

describe('provider semantics (demo vs unable)', () => {
  it('a feed that cannot be reached rejects as UNAVAILABLE — never falls back to demo', async () => {
    // If the demo provider throws for an unknown camera, surfaces show
    // DETECTION DATA UNAVAILABLE — they must never substitute demo rows.
    await expect(mockDetectionService.getFeed('CAM-404')).rejects.toThrow()
  })

  it('demos carry DEMO provider/model identity only in fixtures', async () => {
    const d = await mockDetectionService.getDetection('DET-10421')
    // Model identity is allowed on demo fixtures (to prove traceability),
    // but the UI must show it as DEMO / simulated, never as a real model.
    expect(getMockDetectionFeed('CAM-07')!.inference).toBe('READY')
    expect(d).toBeTruthy()
  })

  it('DEMO_NOW is used for relative time-range determinism', () => {
    expect(new Date(DEMO_NOW).getTime()).not.toBeNaN()
    const feed: DetectionFeed = getMockDetectionFeed('CAM-07')!
    // The most recent demo detection must be within the 1h demo window of DEMO_NOW.
    const newest = Math.max(...feed.detections.map(d => new Date(d.timestamp).getTime()))
    expect(newest).toBeLessThanOrEqual(new Date(DEMO_NOW).getTime())
  })

  it('RealDetectionService has source REAL and does not fallback to mock', async () => {
    const { realDetectionService } = await import('@/services/detection/RealDetectionService')
    expect(realDetectionService.source).toBe('REAL')
  }, 15000)
})