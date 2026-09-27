// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 6 — useTracking (Tracking Engine hooks)
//
// Surfaces consume tracking state exclusively through these hooks. Each hook
// owns its lifecycle (start → loading → success/error) and cleans up on unmount.
// Single-flight per camera / query key protects against effect loops and stale
// updates (§163, §196). No fetch occurs on every render.
// ─────────────────────────────────────────────────────────────────────────────

import { useCallback, useEffect, useState } from 'react'
import { trackingFeedEntry, useTrackingStore } from '@/store/trackingState'
import { trackingService } from '@/services/tracking'
import type { Track } from '@/types/tracking'

/**
 * Tracking feed for a specific camera (§177, §195).
 * Returns the normalized feed (tracks + provider availability).
 * Shows last known state while reloading; errors surface as TRACKING DATA UNAVAILABLE (§167).
 */
export function useCameraTracks(cameraId: string | undefined | null) {
  const feeds = useTrackingStore(s => s.feeds)
  const fetchFeed = useTrackingStore(s => s.fetchFeed)

  useEffect(() => {
    if (!cameraId) return
    let cancelled = false
    fetchFeed(cameraId).catch(() => {
      if (cancelled) return
    })
    return () => {
      cancelled = true
    }
  }, [cameraId, fetchFeed])

  const retry = useCallback(() => {
    if (cameraId) return fetchFeed(cameraId)
    return Promise.resolve()
  }, [cameraId, fetchFeed])

  const entry = cameraId
    ? trackingFeedEntry(feeds, cameraId)
    : { feed: null, state: 'idle' as const, error: null }

  return {
    feed: entry.feed,
    tracks: entry.feed?.tracks ?? [],
    state: entry.state,
    error: entry.error,
    retry,
  }
}

/**
 * Track Inspector selection — single bounded record, lazy-loaded observation history (§52, §194).
 */
export function useTrackSelection() {
  const selected = useTrackingStore(s => s.selected)
  const selectedCameraId = useTrackingStore(s => s.selectedCameraId)
  const selectTrack = useTrackingStore(s => s.selectTrack)
  const histories = useTrackingStore(s => s.histories)
  const fetchTrackHistory = useTrackingStore(s => s.fetchTrackHistory)

  const select = useCallback(
    (track: Track | null, cameraId: string | null = null) => {
      selectTrack(track, cameraId ?? track?.cameraId ?? null)
    },
    [selectTrack]
  )

  const historyEntry = selected?.trackId ? histories[selected.trackId] : undefined
  const observations = historyEntry?.observations ?? []
  const historyState = historyEntry?.state ?? 'idle'
  const historyError = historyEntry?.error ?? null

  const fetchHistory = useCallback(() => {
    if (selected?.trackId) {
      return fetchTrackHistory(selected.trackId)
    }
    return Promise.resolve()
  }, [fetchTrackHistory, selected?.trackId])

  return {
    selected,
    selectedCameraId,
    selectTrack: select,
    observations,
    historyState,
    historyError,
    fetchHistory,
  }
}

/**
 * Paginated, filtered track list query (§48, §49, §251).
 */
export function useTrackList() {
  const query = useTrackingStore(s => s.query)
  const page = useTrackingStore(s => s.page)
  const listState = useTrackingStore(s => s.listState)
  const listError = useTrackingStore(s => s.listError)
  const setQuery = useTrackingStore(s => s.setQuery)
  const fetchList = useTrackingStore(s => s.fetchList)
  const resetList = useTrackingStore(s => s.resetList)

  useEffect(() => {
    let cancelled = false
    fetchList().catch(() => {
      if (cancelled) return
    })
    return () => {
      cancelled = true
    }
  }, [fetchList, query])

  const retry = useCallback(() => fetchList(), [fetchList])

  return {
    query,
    page,
    listState,
    listError,
    setQuery,
    retry,
    resetList,
  }
}

/**
 * Per-camera structural summary hook (§185).
 */
export function useTrackSummary(cameraId: string | undefined | null) {
  const summaries = useTrackingStore(s => s.summaries)
  const fetchSummary = useTrackingStore(s => s.fetchSummary)

  useEffect(() => {
    if (!cameraId) return
    let cancelled = false
    fetchSummary(cameraId).catch(() => {
      if (cancelled) return
    })
    return () => {
      cancelled = true
    }
  }, [cameraId, fetchSummary])

  const entry = cameraId ? summaries[cameraId] : undefined
  const summary = entry?.summary ?? null
  const state = entry?.state ?? 'idle'
  const error = entry?.error ?? null

  const retry = useCallback(() => {
    if (cameraId) return fetchSummary(cameraId)
    return Promise.resolve()
  }, [cameraId, fetchSummary])

  return { summary, state, error, retry }
}

/**
 * All active tracks across sector cameras for Dashboard/Overview (§128).
 */
export function useActiveTracks() {
  const [activeTracks, setActiveTracks] = useState<Track[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const tracks = await trackingService.getActiveTracks()
      setActiveTracks(tracks)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Active tracks unavailable.')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    let cancelled = false
    refresh().catch(() => {
      if (cancelled) return
    })
    return () => {
      cancelled = true
    }
  }, [refresh])

  return { activeTracks, loading, error, refresh }
}
