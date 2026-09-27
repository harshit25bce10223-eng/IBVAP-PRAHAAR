// ─────────────────────────────────────────────────────────────────────────────
// trackingState — normalized tracking feed/list state (Component 6)
//
// One feed entry per camera id; Camera Wall, Single Camera, Dashboard and
// Incident Detail all read the same cache so one provider response feeds every
// surface. List queries are API-ready params with single-flight per query key.
// Selection is per-track so the Inspector is bounded (one record), never
// the whole stream. Everything here renders provider output — it never
// computes risk, correlation, identity or threat from tracks.
// ─────────────────────────────────────────────────────────────────────────────

import { create } from 'zustand'
import { trackingService } from '@/services/tracking'
import { DEFAULT_TRACK_QUERY } from '@/types/tracking'
import type {
  Track,
  TrackingFeed,
  TrackObservation,
  TrackQuery,
  TrackResultPage,
  TrackSummary,
} from '@/types/tracking'

export type TrackListState = 'idle' | 'loading' | 'ready' | 'error'
export type TrackingLoadState = 'idle' | 'loading' | 'ready' | 'error'
export type TrackHistoryState = 'idle' | 'loading' | 'ready' | 'error'
export type TrackSummaryState = 'idle' | 'loading' | 'ready' | 'error'

export interface TrackingFeedEntry {
  feed: TrackingFeed | null
  state: TrackingLoadState
  error: string | null
}

export interface TrackHistoryEntry {
  observations: TrackObservation[]
  state: TrackHistoryState
  error: string | null
}

export interface TrackSummaryEntry {
  summary: TrackSummary | null
  state: TrackSummaryState
  error: string | null
}

interface TrackingStore {
  /** Normalized per-camera tracking feeds. */
  feeds: Record<string, TrackingFeedEntry>

  /** Per-track observation history cache (lazy-loaded on selection). */
  histories: Record<string, TrackHistoryEntry>

  /** Per-camera structural track summary cache. */
  summaries: Record<string, TrackSummaryEntry>

  query: TrackQuery
  page: TrackResultPage | null
  listState: TrackListState
  listError: string | null

  /** Selected track for the Inspector (single bounded record). */
  selected: Track | null
  selectedCameraId: string | null

  setQuery: (patch: Partial<TrackQuery>) => void
  fetchFeed: (cameraId: string) => Promise<void>
  fetchList: () => Promise<void>
  fetchTrackHistory: (trackId: string) => Promise<void>
  fetchSummary: (cameraId: string) => Promise<void>
  selectTrack: (track: Track | null, cameraId: string | null) => void
  resetList: () => void
}

const feedFlight = new Map<string, Promise<void>>()
const listFlight = new Map<string, Promise<void>>()
const historyFlight = new Map<string, Promise<void>>()
const summaryFlight = new Map<string, Promise<void>>()

function queryKey(q: TrackQuery): string {
  return JSON.stringify(q)
}

export const useTrackingStore = create<TrackingStore>((set, get) => ({
  feeds: {},
  histories: {},
  summaries: {},

  query: { ...DEFAULT_TRACK_QUERY },
  page: null,
  listState: 'idle',
  listError: null,

  selected: null,
  selectedCameraId: null,

  setQuery: patch =>
    set(s => {
      const resetsPage =
        patch.search !== undefined ||
        patch.cameraId !== undefined ||
        patch.class !== undefined ||
        patch.status !== undefined ||
        patch.source !== undefined ||
        patch.timeRange !== undefined
      return {
        query: {
          ...s.query,
          ...patch,
          page: patch.page ?? (resetsPage ? 1 : s.query.page),
        },
      }
    }),

  fetchFeed: cameraId => {
    const existing = feedFlight.get(cameraId)
    if (existing) return existing
    const current = get().feeds[cameraId]
    if (current && (current.state === 'loading' || current.state === 'ready')) return Promise.resolve()

    set(s => ({
      feeds: {
        ...s.feeds,
        [cameraId]: { feed: current?.feed ?? null, state: 'loading', error: null },
      },
    }))
    const task = (async () => {
      try {
        const feed = await trackingService.getTrackFeed(cameraId)
        set(s => ({
          feeds: { ...s.feeds, [cameraId]: { feed, state: 'ready', error: null } },
        }))
      } catch (err) {
        set(s => ({
          feeds: {
            ...s.feeds,
            [cameraId]: {
              feed: current?.feed ?? null,
              state: 'error',
              error: err instanceof Error ? err.message : 'Tracking data could not be loaded.',
            },
          },
        }))
      } finally {
        feedFlight.delete(cameraId)
      }
    })()
    feedFlight.set(cameraId, task)
    return task
  },

  fetchList: () => {
    const key = queryKey(get().query)
    const existing = listFlight.get(key)
    if (existing) return existing
    set({ listState: 'loading', listError: null })
    const task = (async () => {
      try {
        const page = await trackingService.listTracks(get().query)
        set({ page, listState: 'ready' })
      } catch (err) {
        set({
          listState: 'error',
          listError: err instanceof Error ? err.message : 'Tracking data could not be loaded.',
        })
      } finally {
        listFlight.delete(key)
      }
    })()
    listFlight.set(key, task)
    return task
  },

  fetchTrackHistory: trackId => {
    const existing = historyFlight.get(trackId)
    if (existing) return existing
    const current = get().histories[trackId]
    if (current && (current.state === 'loading' || current.state === 'ready')) return Promise.resolve()

    set(s => ({
      histories: {
        ...s.histories,
        [trackId]: { observations: current?.observations ?? [], state: 'loading', error: null },
      },
    }))
    const task = (async () => {
      try {
        const observations = await trackingService.getTrackHistory(trackId)
        set(s => ({
          histories: { ...s.histories, [trackId]: { observations, state: 'ready', error: null } },
        }))
      } catch (err) {
        set(s => ({
          histories: {
            ...s.histories,
            [trackId]: {
              observations: current?.observations ?? [],
              state: 'error',
              error: err instanceof Error ? err.message : 'Track history could not be loaded.',
            },
          },
        }))
      } finally {
        historyFlight.delete(trackId)
      }
    })()
    historyFlight.set(trackId, task)
    return task
  },

  fetchSummary: cameraId => {
    const existing = summaryFlight.get(cameraId)
    if (existing) return existing
    const current = get().summaries[cameraId]
    if (current && (current.state === 'loading' || current.state === 'ready')) return Promise.resolve()

    set(s => ({
      summaries: {
        ...s.summaries,
        [cameraId]: { summary: current?.summary ?? null, state: 'loading', error: null },
      },
    }))
    const task = (async () => {
      try {
        const summary = await trackingService.getTrackSummary(cameraId)
        set(s => ({
          summaries: { ...s.summaries, [cameraId]: { summary, state: 'ready', error: null } },
        }))
      } catch (err) {
        set(s => ({
          summaries: {
            ...s.summaries,
            [cameraId]: {
              summary: current?.summary ?? null,
              state: 'error',
              error: err instanceof Error ? err.message : 'Track summary could not be loaded.',
            },
          },
        }))
      } finally {
        summaryFlight.delete(cameraId)
      }
    })()
    summaryFlight.set(cameraId, task)
    return task
  },

  selectTrack: (track, cameraId) => set({ selected: track, selectedCameraId: cameraId }),

  resetList: () => set({ query: { ...DEFAULT_TRACK_QUERY }, page: null, listState: 'idle', listError: null }),
}))

export function trackingFeedEntry(entries: Record<string, TrackingFeedEntry>, cameraId: string): TrackingFeedEntry {
  const EMPTY: TrackingFeedEntry = { feed: null, state: 'idle', error: null }
  return entries[cameraId] ?? EMPTY
}

export function trackingHistoryEntry(entries: Record<string, TrackHistoryEntry>, trackId: string): TrackHistoryEntry {
  const EMPTY: TrackHistoryEntry = { observations: [], state: 'idle', error: null }
  return entries[trackId] ?? EMPTY
}

export function trackingSummaryEntry(entries: Record<string, TrackSummaryEntry>, cameraId: string): TrackSummaryEntry {
  const EMPTY: TrackSummaryEntry = { summary: null, state: 'idle', error: null }
  return entries[cameraId] ?? EMPTY
}