// ─────────────────────────────────────────────────────────────────────────────
// Component 1 — Zone Polygon & Rules Validation Utilities
// Mirrors backend domain rules: points in [0,1], >=3 points, non-degenerate area,
// and rejection of self-intersecting polygons with clear operator feedback.
// ─────────────────────────────────────────────────────────────────────────────

import type { ZonePoint, ZoneRules, ObjectType } from '@/types'

export interface PolygonValidationResult {
  valid: boolean
  reason?: string
}

function orientation(a: ZonePoint, b: ZonePoint, c: ZonePoint): number {
  const val = (b.y - a.y) * (c.x - b.x) - (b.x - a.x) * (c.y - b.y)
  if (Math.abs(val) < 1e-9) return 0
  return val > 0 ? 1 : 2
}

function onSegment(p: ZonePoint, q: ZonePoint, r: ZonePoint): boolean {
  return (
    q.x <= Math.max(p.x, r.x) &&
    q.x >= Math.min(p.x, r.x) &&
    q.y <= Math.max(p.y, r.y) &&
    q.y >= Math.min(p.y, r.y)
  )
}

export function doSegmentsIntersect(
  p1: ZonePoint,
  q1: ZonePoint,
  p2: ZonePoint,
  q2: ZonePoint
): boolean {
  const o1 = orientation(p1, q1, p2)
  const o2 = orientation(p1, q1, q2)
  const o3 = orientation(p2, q2, p1)
  const o4 = orientation(p2, q2, q1)

  // General case
  if (o1 !== o2 && o3 !== o4) return true

  // Special collinear cases
  if (o1 === 0 && onSegment(p1, p2, q1)) return true
  if (o2 === 0 && onSegment(p1, q2, q1)) return true
  if (o3 === 0 && onSegment(p2, p1, q2)) return true
  if (o4 === 0 && onSegment(p2, q1, q2)) return true

  return false
}

/**
 * Calculates polygon area using shoelace formula (normalized coordinate units [0, 1]).
 */
export function computePolygonArea(polygon: ZonePoint[]): number {
  const n = polygon.length
  if (n < 3) return 0
  let sum = 0
  let j = n - 1
  for (let i = 0; i < n; i++) {
    sum += polygon[j].x * polygon[i].y - polygon[i].x * polygon[j].y
    j = i
  }
  return Math.abs(sum) / 2
}

/**
 * Validates a polygon draft against PRHAAR geometric rules.
 * Returns structured result with operator-facing explanation.
 */
export function validateZonePolygon(points: ZonePoint[]): PolygonValidationResult {
  if (!points || points.length === 0) {
    return { valid: false, reason: 'No vertices placed. Click feed to place points.' }
  }

  if (points.length < 3) {
    return {
      valid: false,
      reason: `At least 3 points required (currently ${points.length}).`,
    }
  }

  if (points.length > 100) {
    return {
      valid: false,
      reason: `Maximum 100 vertices allowed (currently ${points.length}).`,
    }
  }

  for (let i = 0; i < points.length; i++) {
    const p = points[i]
    if (typeof p.x !== 'number' || typeof p.y !== 'number' || isNaN(p.x) || isNaN(p.y)) {
      return { valid: false, reason: `Vertex ${i + 1} has invalid coordinates.` }
    }
    if (p.x < 0 || p.x > 1 || p.y < 0 || p.y > 1) {
      return { valid: false, reason: `Vertex ${i + 1} exceeds camera boundary [0, 1].` }
    }
    // Consecutive duplicates check
    const next = points[(i + 1) % points.length]
    const distSq = (p.x - next.x) ** 2 + (p.y - next.y) ** 2
    if (distSq < 1e-8 && points.length > 3) {
      return { valid: false, reason: `Vertices ${i + 1} and ${i + 2} are identical.` }
    }
  }

  const area = computePolygonArea(points)
  if (area < 0.0001) {
    return {
      valid: false,
      reason: 'Zone area is too small or vertices are collinear.',
    }
  }

  // Self-intersection check among non-adjacent edges
  const n = points.length
  for (let i = 0; i < n; i++) {
    const p1 = points[i]
    const p2 = points[(i + 1) % n]
    for (let j = i + 1; j < n; j++) {
      // Skip adjacent segments (they legitimately share a vertex)
      if (j === i || j === (i - 1 + n) % n || j === (i + 1) % n) {
        continue
      }
      const p3 = points[j]
      const p4 = points[(j + 1) % n]
      if (doSegmentsIntersect(p1, p2, p3, p4)) {
        return {
          valid: false,
          reason: 'Polygon edges self-intersect. Adjust vertices to form a simple shape.',
        }
      }
    }
  }

  return { valid: true }
}

/**
 * Formats monitored object types as human-readable label.
 */
export function formatMonitoredObjects(types?: ObjectType[]): string {
  if (!types || types.length === 0) return 'All Objects Monitored'
  const names = types.map(t => {
    switch (t) {
      case 'HUMAN': return 'Humans'
      case 'VEHICLE': return 'Vehicles'
      case 'ANIMAL': return 'Animals'
      default: return t
    }
  })
  return names.join(', ')
}

/**
 * Formats zone active window as human-readable statement.
 */
export function formatActiveTimeWindow(start?: string, end?: string): string {
  if (!start || !end) return '24/7 Always Active'
  if (start === end) return '24/7 Active'
  const isNight = start > end || start >= '18:00' || end <= '06:00'
  return `${start}–${end}${isNight ? ' (Night Window)' : ' (Day Window)'}`
}

/**
 * Formats full zone rules into a concise operational summary.
 */
export function formatZoneRuleSummary(rules: ZoneRules): string {
  const windowStr = formatActiveTimeWindow(rules.active_start, rules.active_end)
  const objectsStr = formatMonitoredObjects(rules.allowed_object_types)
  return `${windowStr} · ${objectsStr}`
}
