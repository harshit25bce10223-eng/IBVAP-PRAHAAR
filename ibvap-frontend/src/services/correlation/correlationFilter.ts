// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 4 — shared correlation group filter/sort (render-only)
//
// Deterministic filtering and ordering of backend-provided correlation groups
// for the Event Log. Nothing here computes correlation, risk or severity — it
// only narrows and orders groups that were correlated by the backend.
// ─────────────────────────────────────────────────────────────────────────────

import type { CorrelationGroup, EventLogQuery } from '@/types/eventCorrelation'

/** Time-window match against an explicit anchor (mock fixtures are pinned). */
export function matchesTimeRange(
  iso: string,
  range: EventLogQuery['timeRange'],
  nowMs: number = Date.now()
): boolean {
  if (range === 'all') return true
  const t = new Date(iso).getTime()
  if (Number.isNaN(t)) return false
  const minutes = range === '15m' ? 15 : range === '1h' ? 60 : range === 'today' ? 24 * 60 : 0
  if (minutes === 0) return true
  return nowMs - t <= minutes * 60_000
}

/** True when a group matches the full query (search + filters + time range). */
export function matchesCorrelationQuery(
  g: CorrelationGroup,
  q: EventLogQuery,
  nowMs: number = Date.now()
): boolean {
  const s = q.search.trim().toLowerCase()
  const searchHit =
    s === '' ||
    g.correlationId.toLowerCase().includes(s) ||
    (g.incidentId ?? '').toLowerCase().includes(s) ||
    g.memberEvents.some(
      m =>
        m.eventId.toLowerCase().includes(s) || m.cameraId.toLowerCase().includes(s)
    ) ||
    (g.trackCandidate?.trackId.toLowerCase().includes(s) ?? false)
  if (!searchHit) return false
  if (q.correlation !== 'ALL' && g.status !== q.correlation) return false
  if (q.severity !== 'ALL' && g.risk.severity !== q.severity) return false
  if (q.cameraId !== 'ALL' && !g.memberEvents.some(m => m.cameraId === q.cameraId)) return false
  if (q.sectorId !== 'ALL' && g.sectorId !== q.sectorId && !g.memberEvents.some(m => m.sectorId === q.sectorId)) return false
  if (q.source !== 'ALL' && !g.sources.includes(q.source)) return false
  if (q.connectivity !== 'ALL' && g.connectivity !== q.connectivity) return false
  if (!matchesTimeRange(g.startedAt, q.timeRange, nowMs)) return false
  return true
}

/**
 * Deterministic ordering for the Event Log; unknown/null severities sort last.
 * Ties fall back to correlationId so equal primary keys never reorder between
 * requests (stable paging, §60).
 */
export function compareCorrelationGroups(
  a: CorrelationGroup,
  b: CorrelationGroup,
  q: EventLogQuery
): number {
  const dir = q.order === 'asc' ? 1 : -1
  const primary = comparePrimary(a, b, q) * dir
  return primary !== 0 ? primary : a.correlationId.localeCompare(b.correlationId)
}

function comparePrimary(a: CorrelationGroup, b: CorrelationGroup, q: EventLogQuery): number {
  switch (q.sort) {
    case 'signals':
      return a.eventCount - b.eventCount
    case 'cameras':
      return a.cameraCount - b.cameraCount
    case 'severity': {
      const rank = { LOW: 0, MEDIUM: 1, HIGH: 2, CRITICAL: 3 } as const
      const ra = a.risk.severity ? rank[a.risk.severity] : -1
      const rb = b.risk.severity ? rank[b.risk.severity] : -1
      return ra - rb
    }
    case 'status':
      return a.status.localeCompare(b.status)
    case 'time':
    default: {
      const ta = new Date(a.startedAt).getTime()
      const tb = new Date(b.startedAt).getTime()
      if (Number.isNaN(ta) !== Number.isNaN(tb)) return Number.isNaN(ta) ? 1 : -1
      if (!Number.isNaN(ta) && ta !== tb) return ta - tb
      return 0
    }
  }
}