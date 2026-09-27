// ─────────────────────────────────────────────────────────────────────────────
// useDetection — Service → Store → Component boundary (Component 5)
//
// Surfaces consume detection state exclusively through these hooks. Each hook
// owns its request lifecycle (start → loading → success/error) and swallows
// post-unmount rejections. No fetch happens on every render. Nothing here
// interprets a detection as a threat, identity or correlation.
// ─────────────────────────────────────────────────────────────────────────────

import { useCallback, useEffect } from 'react'
import { detectionFeedEntry, useDetectionStore } from '@/store/detectionState'

/**
 * Detection feed for one camera. Returns the normalized feed (detections +
 * honest detector availability), never a fabricated stream. A feed stays
 * visible when reloading; errors surface as DETECTION DATA UNAVAILABLE.
 */
export function useCameraFeed(cameraId: string | undefined | null) {
  const feeds = useDetectionStore(s => s.feeds)
  const fetchFeed = useDetectionStore(s => s.fetchFeed)

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

  const entry = cameraId ? detectionFeedEntry(feeds, cameraId) : { feed: null, state: 'idle' as const, error: null }

  return {
    feed: entry.feed,
    state: entry.state,
    error: entry.error,
    retry,
  }
}

/**
 * Detection Inspector selection — a single bounded record, cleared on demand.
 */
export function useDetectionSelection() {
  const selected = useDetectionStore(s => s.selected)
  const selectedCameraId = useDetectionStore(s => s.selectedCameraId)
  const selectDetection = useDetectionStore(s => s.selectDetection)

  const select = useCallback(
    (detection: NonNullable<typeof selected> | null, cameraId: string | null) => selectDetection(detection, cameraId),
    [selectDetection]
  )

  return { selected, selectedCameraId, select }
}

/**
 * Paginated, filtered detection list (used by list surfaces that opt in).
 * One request per query key; filter/sort/page changes re-fetch.
 */
export function useDetectionList() {
  const query = useDetectionStore(s => s.query)
  const page = useDetectionStore(s => s.page)
  const listState = useDetectionStore(s => s.listState)
  const listError = useDetectionStore(s => s.listError)
  const setQuery = useDetectionStore(s => s.setQuery)
  const fetchList = useDetectionStore(s => s.fetchList)
  const resetList = useDetectionStore(s => s.resetList)

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

  return { query, page, listState, listError, setQuery, retry, resetList }
}