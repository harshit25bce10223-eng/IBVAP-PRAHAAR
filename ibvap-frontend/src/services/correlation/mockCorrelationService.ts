// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 4 — mock correlation provider (DEMO ONLY)
//
// Serves the isolated fixtures from `mockCorrelationData.ts`. Local filtering,
// sorting and pagination make the Event Log exercises async on a "service
// boundary" shape, but this module NEVER computes correlation, risk or
// severity — those values are fabricated nowhere and arrive from fixtures.
// Unknown correlation/event ids reject so the UI exercises error paths.
// ─────────────────────────────────────────────────────────────────────────────

import type {
  CorrelationEventMember,
  CorrelationGroup,
  CorrelationGroupPage,
  CorrelationRelationship,
  EventLogQuery,
} from '@/types/eventCorrelation'
import type { IEventCorrelationService } from './IEventCorrelationService'
import { MOCK_GROUPS, MOCK_GROUP_BY_ID } from './mockCorrelationData'

const PROVIDER_DELAY_MS = 250

function delay(ms: number) {
  return new Promise<void>(resolve => setTimeout(resolve, ms))
}

function matchesTimeRange(iso: string, range: EventLogQuery['timeRange']): boolean {
  if (range === 'all') return true
  const t = new Date(iso).getTime()
  const now = Date.now()
  const minutes = range === '15m' ? 15 : range === '1h' ? 60 : range === 'today' ? 24 * 60 : 0
  if (minutes === 0) return true
  return now - t <= minutes * 60_000
}

function matchesQuery(g: CorrelationGroup, q: EventLogQuery): boolean {
  const s = q.search.trim().toLowerCase()
  const searchHit =
    s === '' ||
    g.correlationId.toLowerCase().includes(s) ||
    (g.incidentId ?? '').toLowerCase().includes(s) ||
    g.memberEvents.some(m => m.eventId.toLowerCase().includes(s) || m.cameraId.toLowerCase().includes(s)) ||
    (g.trackCandidate?.trackId.toLowerCase().includes(s) ?? false)
  if (!searchHit) return false
  if (q.correlation !== 'ALL' && g.status !== q.correlation) return false
  if (q.severity !== 'ALL' && g.risk.severity !== q.severity) return false
  if (q.cameraId !== 'ALL' && !g.memberEvents.some(m => m.cameraId === q.cameraId)) return false
  if (q.sectorId !== 'ALL' && g.sectorId !== q.sectorId && !g.memberEvents.some(m => m.sectorId === q.sectorId)) return false
  if (q.source !== 'ALL' && !g.sources.includes(q.source)) return false
  if (q.connectivity !== 'ALL' && g.connectivity !== q.connectivity) return false
  if (!matchesTimeRange(g.startedAt, q.timeRange)) return false
  return true
}

function compareGroups(a: CorrelationGroup, b: CorrelationGroup, q: EventLogQuery): number {
  const dir = q.order === 'asc' ? 1 : -1
  switch (q.sort) {
    case 'signals':
      return (a.eventCount - b.eventCount) * dir
    case 'cameras':
      return (a.cameraCount - b.cameraCount) * dir
    case 'severity': {
      const rank = { LOW: 0, MEDIUM: 1, HIGH: 2, CRITICAL: 3 } as const
      const ra = a.risk.severity ? rank[a.risk.severity] : -1
      const rb = b.risk.severity ? rank[b.risk.severity] : -1
      return (ra - rb) * dir
    }
    case 'status':
      return a.status.localeCompare(b.status) * dir
    case 'time':
    default:
      return (new Date(a.startedAt).getTime() - new Date(b.startedAt).getTime()) * dir
  }
}

class MockCorrelationService implements IEventCorrelationService {
  readonly source = 'DEMO' as const

  async listGroups(query: EventLogQuery): Promise<CorrelationGroupPage> {
    await delay(PROVIDER_DELAY_MS)
    const filtered = MOCK_GROUPS.filter(g => matchesQuery(g, query)).sort((a, b) => compareGroups(a, b, query))
    const pageSize = query.pageSize
    const start = (query.page - 1) * pageSize
    return {
      groups: filtered.slice(start, start + pageSize),
      total: filtered.length,
    }
  }

  async listRecent(limit: number): Promise<CorrelationGroup[]> {
    await delay(PROVIDER_DELAY_MS)
    return [...MOCK_GROUPS]
      .sort((a, b) => new Date(b.startedAt).getTime() - new Date(a.startedAt).getTime())
      .slice(0, limit)
  }

  async listForCamera(cameraId: string, limit: number): Promise<CorrelationGroup[]> {
    await delay(PROVIDER_DELAY_MS)
    return MOCK_GROUPS.filter(g => g.memberEvents.some(m => m.cameraId === cameraId))
      .sort((a, b) => new Date(b.startedAt).getTime() - new Date(a.startedAt).getTime())
      .slice(0, limit)
  }

  async getGroup(correlationId: string): Promise<CorrelationGroup> {
    await delay(PROVIDER_DELAY_MS)
    const group = MOCK_GROUP_BY_ID[correlationId] || MOCK_GROUPS.find(g => g.incidentId === correlationId)
    if (!group) {
      throw new Error(`Correlation group ${correlationId} was not found.`)
    }
    return group
  }

  async getRelationships(correlationId: string): Promise<CorrelationRelationship[]> {
    await delay(PROVIDER_DELAY_MS)
    const group = MOCK_GROUP_BY_ID[correlationId] || MOCK_GROUPS.find(g => g.incidentId === correlationId)
    if (!group) {
      throw new Error(`Correlation group ${correlationId} was not found.`)
    }
    return group.relationships
  }

  async getMemberEvent(eventId: string): Promise<CorrelationEventMember> {
    await delay(PROVIDER_DELAY_MS)
    const member = MOCK_GROUPS.flatMap(g => g.memberEvents).find(m => m.eventId === eventId)
    if (!member) {
      throw new Error(`Event ${eventId} was not found.`)
    }
    return member
  }
}

export const mockCorrelationService = new MockCorrelationService()