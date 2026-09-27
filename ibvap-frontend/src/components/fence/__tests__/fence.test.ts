// ─────────────────────────────────────────────────────────────────────────────
// Component 1 — Fence & Polygon Validation Unit Tests
// ─────────────────────────────────────────────────────────────────────────────

import { describe, it, expect } from 'vitest'
import {
  validateZonePolygon,
  computePolygonArea,
  doSegmentsIntersect,
  formatActiveTimeWindow,
  formatMonitoredObjects,
  formatZoneRuleSummary,
} from '../polygonValidation'
import type { ZonePoint } from '@/types'

describe('Component 1 — Polygon Geometry Validation', () => {
  it('approves a valid triangle in normalized coordinate space', () => {
    const triangle: ZonePoint[] = [
      { x: 0.1, y: 0.1 },
      { x: 0.5, y: 0.1 },
      { x: 0.3, y: 0.5 },
    ]
    const res = validateZonePolygon(triangle)
    expect(res.valid).toBe(true)
    expect(res.reason).toBeUndefined()
  })

  it('approves a valid convex quadrilateral', () => {
    const quad: ZonePoint[] = [
      { x: 0.1, y: 0.1 },
      { x: 0.8, y: 0.1 },
      { x: 0.8, y: 0.8 },
      { x: 0.1, y: 0.8 },
    ]
    const res = validateZonePolygon(quad)
    expect(res.valid).toBe(true)
    expect(computePolygonArea(quad)).toBeCloseTo(0.49, 2)
  })

  it('rejects fewer than 3 vertices with clear reason', () => {
    const points: ZonePoint[] = [
      { x: 0.1, y: 0.1 },
      { x: 0.5, y: 0.5 },
    ]
    const res = validateZonePolygon(points)
    expect(res.valid).toBe(false)
    expect(res.reason).toContain('At least 3 points required')
  })

  it('rejects out of bounds coordinates', () => {
    const invalidPts: ZonePoint[] = [
      { x: -0.05, y: 0.1 },
      { x: 0.5, y: 0.1 },
      { x: 0.3, y: 0.5 },
    ]
    const res = validateZonePolygon(invalidPts)
    expect(res.valid).toBe(false)
    expect(res.reason).toContain('exceeds camera boundary')
  })

  it('rejects degenerate collinear vertices with zero area', () => {
    const collinear: ZonePoint[] = [
      { x: 0.1, y: 0.1 },
      { x: 0.3, y: 0.3 },
      { x: 0.5, y: 0.5 },
    ]
    const res = validateZonePolygon(collinear)
    expect(res.valid).toBe(false)
    expect(res.reason).toContain('too small or vertices are collinear')
  })

  it('rejects self-intersecting polygon (bow-tie shape)', () => {
    const bowtie: ZonePoint[] = [
      { x: 0.1, y: 0.1 },
      { x: 0.9, y: 0.9 },
      { x: 0.9, y: 0.2 },
      { x: 0.1, y: 0.6 },
    ]
    const res = validateZonePolygon(bowtie)
    expect(res.valid).toBe(false)
    expect(res.reason).toContain('self-intersect')
  })

  it('detects intersecting line segments properly', () => {
    const p1 = { x: 0, y: 0 }
    const q1 = { x: 1, y: 1 }
    const p2 = { x: 0, y: 1 }
    const q2 = { x: 1, y: 0 }
    expect(doSegmentsIntersect(p1, q1, p2, q2)).toBe(true)

    // Parallel segments
    const p3 = { x: 0, y: 0 }
    const q3 = { x: 1, y: 0 }
    const p4 = { x: 0, y: 0.5 }
    const q4 = { x: 1, y: 0.5 }
    expect(doSegmentsIntersect(p3, q3, p4, q4)).toBe(false)
  })
})

describe('Component 1 — Zone Rules & Time Window Formatting', () => {
  it('formats active time window crossing midnight', () => {
    const window = formatActiveTimeWindow('22:00', '05:00')
    expect(window).toContain('22:00–05:00')
    expect(window).toContain('Night Window')
  })

  it('formats day active time window', () => {
    const window = formatActiveTimeWindow('06:00', '18:00')
    expect(window).toContain('06:00–18:00')
    expect(window).toContain('Day Window')
  })

  it('handles always active 24/7 window', () => {
    expect(formatActiveTimeWindow()).toBe('24/7 Always Active')
    expect(formatActiveTimeWindow('00:00', '00:00')).toBe('24/7 Active')
  })

  it('formats monitored objects clearly', () => {
    expect(formatMonitoredObjects()).toBe('All Objects Monitored')
    expect(formatMonitoredObjects([])).toBe('All Objects Monitored')
    expect(formatMonitoredObjects(['HUMAN', 'VEHICLE'])).toBe('Humans, Vehicles')
    expect(formatMonitoredObjects(['ANIMAL'])).toBe('Animals')
  })

  it('formats full zone rule summary', () => {
    const summary = formatZoneRuleSummary({
      active_start: '22:00',
      active_end: '05:00',
      allowed_object_types: ['HUMAN'],
    })
    expect(summary).toContain('22:00–05:00')
    expect(summary).toContain('Humans')
  })
})
