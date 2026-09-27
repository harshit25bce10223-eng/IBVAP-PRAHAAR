// ─────────────────────────────────────────────────────────────────────────────
// useIncidentIntelligence — Incident Intelligence data hook.
//
// Architecture: UI → hook/store/service → prototype data now, real API later.
// ─────────────────────────────────────────────────────────────────────────────

import { useEffect } from 'react'
import { useIncidentIntelligenceStore } from '@/store'

export function useIncidentIntelligence() {
  const data = useIncidentIntelligenceStore(s => s.data)
  const loadState = useIncidentIntelligenceStore(s => s.loadState)
  const fetch = useIncidentIntelligenceStore(s => s.fetch)

  useEffect(() => {
    if (useIncidentIntelligenceStore.getState().loadState === 'idle') {
      fetch().catch(() => {})
    }
  }, [fetch])

  return { data, loadState, refetch: fetch }
}