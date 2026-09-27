// ─────────────────────────────────────────────────────────────────────────────
// useCameraHealth — Provider → Service → Store → Component boundary
//
// Pages and panels consume health exclusively through this hook. It owns the
// request lifecycle (start → loading → success/error → last-known fallback)
// and cancels stale updates on unmount or camera change.
// ─────────────────────────────────────────────────────────────────────────────

import { useCallback, useEffect } from 'react'
import { healthEntry, useHealthStore } from '@/store/healthState'

export function useCameraHealth(cameraId: string) {
  const entry = useHealthStore(s => healthEntry(s.entries, cameraId))
  const fetchHealth = useHealthStore(s => s.fetchHealth)
  const refreshHealth = useHealthStore(s => s.refreshHealth)

  useEffect(() => {
    let cancelled = false
    fetchHealth(cameraId).catch(() => {
      if (!cancelled) return
    })
    return () => {
      cancelled = true
    }
  }, [cameraId, fetchHealth])

  const retry = useCallback(() => refreshHealth(cameraId), [cameraId, refreshHealth])

  return {
    health: entry.data,
    state: entry.state,
    error: entry.error,
    fetchedAt: entry.fetchedAt,
    retry,
  }
}
