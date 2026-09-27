// ─────────────────────────────────────────────────────────────────────────────
// useFieldResilience — Field Intelligence & Resilience data hook.
//
// Architecture: UI → hook/store/service → prototype data now, real API later.
// ─────────────────────────────────────────────────────────────────────────────

import { useEffect } from 'react'
import { useFieldResilienceStore } from '@/store'

export function useFieldResilience() {
  const data = useFieldResilienceStore(s => s.data)
  const loadState = useFieldResilienceStore(s => s.loadState)
  const fetch = useFieldResilienceStore(s => s.fetch)

  useEffect(() => {
    if (useFieldResilienceStore.getState().loadState === 'idle') {
      fetch().catch(() => {})
    }
  }, [fetch])

  return { data, loadState, refetch: fetch }
}