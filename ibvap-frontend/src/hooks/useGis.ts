// ─────────────────────────────────────────────────────────────────────────────
// useGis — GIS / Digital Twin data hook.
//
// Architecture: UI → hook/store/service → prototype data now, real GIS later.
// Components never mutate the store or touch the service directly.
// ─────────────────────────────────────────────────────────────────────────────

import { useEffect } from 'react'
import { useGisStore } from '@/store'

export function useGis() {
  const data = useGisStore(s => s.data)
  const loadState = useGisStore(s => s.loadState)
  const fetch = useGisStore(s => s.fetch)

  useEffect(() => {
    if (useGisStore.getState().loadState === 'idle') {
      fetch().catch(() => {})
    }
  }, [fetch])

  return { data, loadState, refetch: fetch }
}