// ─────────────────────────────────────────────────────────────────────────────
// healthState — normalized per-camera health cache (Component 2)
//
// One entry per camera id; multiple surfaces (dashboard, rail, wall, twin)
// read the same entry, so one provider response feeds every consumer.
// Single-flight per camera prevents duplicate requests. No polling here —
// Phase 2 can drive `refreshHealth` from SSE/WebSocket without touching UI.
// ─────────────────────────────────────────────────────────────────────────────

import { create } from 'zustand'
import { healthService } from '@/services/health'
import type { CameraHealth } from '@/types/cameraHealth'

export type HealthEntryState = 'idle' | 'loading' | 'ready' | 'error' | 'last-known'

export interface HealthEntry {
  data: CameraHealth | null
  state: HealthEntryState
  error: string | null
  /** Local fetch time (ms epoch). Null until the first attempt resolves. */
  fetchedAt: number | null
}

interface HealthStore {
  entries: Record<string, HealthEntry>
  fetchHealth: (cameraId: string) => Promise<void>
  fetchAll: (cameraIds: string[]) => Promise<void>
  refreshHealth: (cameraId: string) => Promise<void>
}

const EMPTY: HealthEntry = { data: null, state: 'idle', error: null, fetchedAt: null }

/** In-flight promises keyed by camera — one request per camera at a time. */
const inFlight = new Map<string, Promise<void>>()

export const useHealthStore = create<HealthStore>((set, get) => ({
  entries: {},

  fetchHealth: cameraId => {
    const existing = inFlight.get(cameraId)
    if (existing) return existing
    const current = get().entries[cameraId]
    if (current && (current.state === 'loading' || current.state === 'ready')) {
      return Promise.resolve()
    }

    const task = (async () => {
      set(s => ({
        entries: {
          ...s.entries,
          [cameraId]: {
            data: current?.data ?? null,
            state: 'loading',
            error: null,
            fetchedAt: current?.fetchedAt ?? null,
          },
        },
      }))
      try {
        const data = await healthService.get(cameraId)
        set(s => ({
          entries: {
            ...s.entries,
            [cameraId]: { data, state: 'ready', error: null, fetchedAt: Date.now() },
          },
        }))
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Health telemetry could not be retrieved.'
        const cached = get().entries[cameraId]?.data
        set(s => ({
          entries: {
            ...s.entries,
            [cameraId]: {
              data: cached ?? null,
              // A cached record stays visible but is explicitly last-known.
              state: cached ? 'last-known' : 'error',
              error: message,
              fetchedAt: get().entries[cameraId]?.fetchedAt ?? null,
            },
          },
        }))
      } finally {
        inFlight.delete(cameraId)
      }
    })()
    inFlight.set(cameraId, task)
    return task
  },

  fetchAll: cameraIds => Promise.all(cameraIds.map(id => get().fetchHealth(id))).then(() => {}),

  refreshHealth: async cameraId => {
    inFlight.delete(cameraId)
    set(s => ({
      entries: { ...s.entries, [cameraId]: s.entries[cameraId] ?? { ...EMPTY } },
    }))
    // Force a fresh attempt even when a ready record exists.
    const current = get().entries[cameraId]
    if (current.state === 'ready') {
      set(s => ({
        entries: {
          ...s.entries,
          [cameraId]: { ...current, state: 'loading', error: null },
        },
      }))
      try {
        const data = await healthService.get(cameraId)
        set(s => ({
          entries: {
            ...s.entries,
            [cameraId]: { data, state: 'ready', error: null, fetchedAt: Date.now() },
          },
        }))
      } catch (err) {
        const message = err instanceof Error ? err.message : 'Health telemetry could not be retrieved.'
        set(s => ({
          entries: {
            ...s.entries,
            [cameraId]: { ...current, state: 'last-known', error: message },
          },
        }))
      }
      return
    }
    return get().fetchHealth(cameraId)
  },
}))

export function healthEntry(entries: Record<string, HealthEntry>, cameraId: string): HealthEntry {
  return entries[cameraId] ?? EMPTY
}
