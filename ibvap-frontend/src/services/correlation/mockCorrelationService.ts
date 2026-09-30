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
import { MOCK_GROUPS, MOCK_GROUP_BY_ID, MOCK_TIME_ANCHOR_MS } from './mockCorrelationData'
import { compareCorrelationGroups, matchesCorrelationQuery } from './correlationFilter'

const PROVIDER_DELAY_MS = 250

function delay(ms: number) {
  return new Promise<void>(resolve => setTimeout(resolve, ms))
}

/** Same filter/sort semantics as the Event Log; fixtures pinned to the demo anchor. */
function matchesQuery(g: CorrelationGroup, q: EventLogQuery): boolean {
  return matchesCorrelationQuery(g, q, MOCK_TIME_ANCHOR_MS)
}

function compareGroups(a: CorrelationGroup, b: CorrelationGroup, q: EventLogQuery): number {
  return compareCorrelationGroups(a, b, q)
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