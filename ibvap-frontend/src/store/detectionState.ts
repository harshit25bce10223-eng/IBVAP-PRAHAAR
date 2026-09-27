// ─────────────────────────────────────────────────────────────────────────────
// detectionState — normalized detection feed/list state (Component 5)
//
// One feed entry per camera id; the Camera Wall, Single Camera, Dashboard and
// Incident Detail all read the same cache so one provider response feeds every
// surface. List queries are API-ready params with single-flight per query key.
// Selection is per-detection so the Inspector is bounded (one record), never
// the whole stream. Everything here renders provider output — it never
// computes risk, correlation, identity or threat from detections.
// ─────────────────────────────────────────────────────────────────────────────

import { create } from 'zustand'
import { detectionService } from '@/services/detection'
import { DEFAULT_DETECTION_QUERY } from '@/types/detection'
import type {
  DetectionFeed,
  DetectionQuery,
  DetectionResult,
  DetectionResultPage,
} from '@/types/detection'

export type DetectionListState = 'idle' | 'loading' | 'ready' | 'error'
export type DetectionLoadState = 'idle' | 'loading' | 'ready' | 'error'

export interface DetectionFeedEntry {
  feed: DetectionFeed | null
  state: DetectionLoadState
  error: string | null
}

interface DetectionStore {
  /** Normalized per-camera feeds. */
  feeds: Record<string, DetectionFeedEntry>

  query: DetectionQuery
  page: DetectionResultPage | null
  listState: DetectionListState
  listError: string | null

  /** Selected detection for the Inspector (single bounded record). */
  selected: DetectionResult | null
  selectedCameraId: string | null

  setQuery: (patch: Partial<DetectionQuery>) => void
  fetchFeed: (cameraId: string) => Promise<void>
  fetchList: () => Promise<void>
  selectDetection: (detection: DetectionResult | null, cameraId: string | null) => void
  resetList: () => void
}

const feedFlight = new Map<string, Promise<void>>()
const listFlight = new Map<string, Promise<void>>()

function queryKey(q: DetectionQuery): string {
  return JSON.stringify(q)
}

export const useDetectionStore = create<DetectionStore>((set, get) => ({
  feeds: {},

  query: { ...DEFAULT_DETECTION_QUERY },
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
        patch.confidenceMin !== undefined ||
        patch.quality !== undefined ||
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
        const feed = await detectionService.getFeed(cameraId)
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
              error: err instanceof Error ? err.message : 'Detection data could not be loaded.',
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
        const page = await detectionService.listDetections(get().query)
        set({ page, listState: 'ready' })
      } catch (err) {
        set({
          listState: 'error',
          listError: err instanceof Error ? err.message : 'Detection data could not be loaded.',
        })
      } finally {
        listFlight.delete(key)
      }
    })()
    listFlight.set(key, task)
    return task
  },

  selectDetection: (detection, cameraId) => set({ selected: detection, selectedCameraId: cameraId }),

  resetList: () => set({ query: { ...DEFAULT_DETECTION_QUERY }, page: null, listState: 'idle', listError: null }),
}))

export function detectionFeedEntry(entries: Record<string, DetectionFeedEntry>, cameraId: string): DetectionFeedEntry {
  const EMPTY: DetectionFeedEntry = { feed: null, state: 'idle', error: null }
  return entries[cameraId] ?? EMPTY
}