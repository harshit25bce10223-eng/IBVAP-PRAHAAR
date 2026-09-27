// ─────────────────────────────────────────────────────────────────────────────
// useCommandDashboard — Command Center data hooks.
//
// Architecture (spec §25/%26): UI → hook/store/service → prototype data now,
// real API later. Components never mutate the store or touch the service
// directly.
// ─────────────────────────────────────────────────────────────────────────────

import { useEffect } from 'react'
import { useCommandDashboardStore } from '@/store'

export function useCommandDashboard() {
  const data = useCommandDashboardStore(s => s.data)
  const loadState = useCommandDashboardStore(s => s.loadState)
  const fetch = useCommandDashboardStore(s => s.fetch)

  /** Load the dashboard on mount when the store is not yet populated. */
  useEffect(() => {
    if (useCommandDashboardStore.getState().loadState === 'idle') {
      fetch().catch(() => {})
    }
  }, [fetch])

  return { data, loadState, refetch: fetch }
}