// ─────────────────────────────────────────────────────────────────────────────
// correlationState — normalized correlation group/event state (Component 4)
//
// One canonical row per correlation group id. The Event Log, Dashboard feed,
// Single Camera context and Incident Detail all read from the same normalized
// cache, so no group object is duplicated across surfaces. List queries are
// API-ready params with single-flight per query key; detail is per-group
// single-flight; relationships are fetched lazily when a group is inspected.
// Nothing here computes correlation, risk or severity — it renders provider
// output (fixtures today, backend later).
// ─────────────────────────────────────────────────────────────────────────────

import { create } from 'zustand'
import { correlationService } from '@/services/correlation'
import { DEFAULT_CORRELATION_QUERY } from '@/types/eventCorrelation'
import type { CorrelationGroup, CorrelationGroupPage, CorrelationRelationship, EventLogQuery } from '@/types/eventCorrelation'

export type CorrelationListState = 'idle' | 'loading' | 'ready' | 'error'
export type CorrelationDetailState = 'idle' | 'loading' | 'ready' | 'error'

export interface CameraCorrelationContext {
  groups: CorrelationGroup[]
  state: CorrelationListState
  error: string | null
}

interface CorrelationStore {
  query: EventLogQuery
  page: CorrelationGroupPage | null
  listState: CorrelationListState
  listError: string | null

  /** Normalized cache — one entry per correlation id. */
  groups: Record<string, CorrelationGroup>
  /** Groups collapsed/expanded in the log. Preserved across pagination. */
  expandedIds: string[]

  /** Dashboard recent feed. */
  recent: CorrelationGroup[]
  recentState: CorrelationListState
  recentError: string | null

  /** Single Camera related-events context. */
  cameraContext: Record<string, CameraCorrelationContext>

  /** Lazy-loadable relationship maps per group. */
  relationships: Record<string, CorrelationRelationship[]>
  relationshipStates: Record<string, CorrelationListState>

  selectedId: string | null
  detailState: CorrelationDetailState
  detailError: string | null

  setQuery: (patch: Partial<EventLogQuery>) => void
  fetchList: () => Promise<void>
  fetchRecent: (limit: number) => Promise<void>
  fetchCameraContext: (cameraId: string, limit?: number) => Promise<void>
  fetchGroup: (correlationId: string) => Promise<void>
  fetchRelationships: (correlationId: string) => Promise<void>
  selectGroup: (correlationId: string | null) => void
  toggleExpanded: (correlationId: string) => void
  resetList: () => void
}

const listFlight = new Map<string, Promise<void>>()
const detailFlight = new Map<string, Promise<void>>()
const relationshipFlight = new Map<string, Promise<void>>()
const cameraFlight = new Map<string, Promise<void>>()

function queryKey(q: EventLogQuery): string {
  return JSON.stringify(q)
}

export const useCorrelationStore = create<CorrelationStore>((set, get) => ({
  query: { ...DEFAULT_CORRELATION_QUERY },
  page: null,
  listState: 'idle',
  listError: null,

  groups: {},
  expandedIds: [],

  recent: [],
  recentState: 'idle',
  recentError: null,

  cameraContext: {},

  relationships: {},
  relationshipStates: {},

  selectedId: null,
  detailState: 'idle',
  detailError: null,

  setQuery: patch =>
    set(s => {
      const resetsPage =
        patch.search !== undefined ||
        patch.correlation !== undefined ||
        patch.severity !== undefined ||
        patch.cameraId !== undefined ||
        patch.sectorId !== undefined ||
        patch.source !== undefined ||
        patch.connectivity !== undefined ||
        patch.timeRange !== undefined
      return {
        query: {
          ...s.query,
          ...patch,
          page: patch.page ?? (resetsPage ? 1 : s.query.page),
        },
      }
    }),

  fetchList: () => {
    const key = queryKey(get().query)
    const existing = listFlight.get(key)
    if (existing) return existing
    set({ listState: 'loading', listError: null })
    const task = (async () => {
      try {
        const page = await correlationService.listGroups(get().query)
        const merged = { ...get().groups }
        for (const g of page.groups) merged[g.correlationId] = g
        set({ page, groups: merged, listState: 'ready' })
      } catch (err) {
        set({
          listState: 'error',
          listError: err instanceof Error ? err.message : 'Correlation data could not be loaded.',
        })
      } finally {
        listFlight.delete(key)
      }
    })()
    listFlight.set(key, task)
    return task
  },

  fetchRecent: limit => {
    if (get().recentState === 'loading') return Promise.resolve()
    set(() => ({ recentState: 'loading', recentError: null }))
    const task = (async () => {
      try {
        const recent = await correlationService.listRecent(limit)
        const merged = { ...get().groups }
        for (const g of recent) merged[g.correlationId] = g
        set({ recent, groups: merged, recentState: 'ready' })
      } catch (err) {
        set({
          recentError: err instanceof Error ? err.message : 'Recent correlation data could not be loaded.',
          recentState: 'error',
        })
      }
    })()
    return task
  },

  fetchCameraContext: (cameraId, limit = 4) => {
    const existing = cameraFlight.get(cameraId)
    if (existing) return existing
    const current = get().cameraContext[cameraId]
    if (current && (current.state === 'loading' || current.state === 'ready')) return Promise.resolve()
    set(s => ({
      cameraContext: {
        ...s.cameraContext,
        [cameraId]: { groups: current?.groups ?? [], state: 'loading', error: null },
      },
    }))
    const task = (async () => {
      try {
        const groups = await correlationService.listForCamera(cameraId, limit)
        const merged = { ...get().groups }
        for (const g of groups) merged[g.correlationId] = g
        set(s => ({
          groups: merged,
          cameraContext: {
            ...s.cameraContext,
            [cameraId]: { groups, state: 'ready', error: null },
          },
        }))
      } catch (err) {
        set(s => ({
          cameraContext: {
            ...s.cameraContext,
            [cameraId]: {
              groups: current?.groups ?? [],
              state: 'error',
              error: err instanceof Error ? err.message : 'Related events could not be loaded.',
            },
          },
        }))
      } finally {
        cameraFlight.delete(cameraId)
      }
    })()
    cameraFlight.set(cameraId, task)
    return task
  },

  fetchGroup: correlationId => {
    if (get().groups[correlationId]) {
      set({ selectedId: correlationId, detailState: 'ready', detailError: null })
      return Promise.resolve()
    }
    const existing = detailFlight.get(correlationId)
    if (existing) return existing
    set({ selectedId: correlationId, detailState: 'loading', detailError: null })
    const task = (async () => {
      try {
        const group = await correlationService.getGroup(correlationId)
        set(s => ({
          groups: { ...s.groups, [correlationId]: group },
          detailState: 'ready',
        }))
      } catch (err) {
        set({
          detailState: 'error',
          detailError: err instanceof Error ? err.message : 'Correlation group could not be loaded.',
        })
      } finally {
        detailFlight.delete(correlationId)
      }
    })()
    detailFlight.set(correlationId, task)
    return task
  },

  fetchRelationships: correlationId => {
    if (get().relationships[correlationId] || get().relationshipStates[correlationId] === 'loading') {
      return Promise.resolve()
    }
    set(s => ({
      relationshipStates: { ...s.relationshipStates, [correlationId]: 'loading' },
    }))
    const task = (async () => {
      try {
        const relationships = await correlationService.getRelationships(correlationId)
        set(s => ({
          relationships: { ...s.relationships, [correlationId]: relationships },
          relationshipStates: { ...s.relationshipStates, [correlationId]: 'ready' },
        }))
      } catch {
        set(s => ({
          relationshipStates: { ...s.relationshipStates, [correlationId]: 'error' },
        }))
      }
    })()
    relationshipFlight.set(correlationId, task)
    return task
  },

  selectGroup: correlationId => set({ selectedId: correlationId }),

  toggleExpanded: correlationId =>
    set(s => ({
      expandedIds: s.expandedIds.includes(correlationId)
        ? s.expandedIds.filter(id => id !== correlationId)
        : [...s.expandedIds, correlationId],
    })),

  resetList: () => set({ query: { ...DEFAULT_CORRELATION_QUERY }, page: null, listState: 'idle', listError: null }),
}))

export function relationsFor(group: CorrelationGroup, relationships: Record<string, CorrelationRelationship[]>, state: CorrelationListState | undefined): CorrelationRelationship[] {
  if (state === 'error') return []
  return relationships[group.correlationId] ?? group.relationships
}