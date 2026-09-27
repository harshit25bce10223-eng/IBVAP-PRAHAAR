// ─────────────────────────────────────────────────────────────────────────────
// incidentIntelligenceState — Zustand slice for the Incident Intelligence view.
//
// UI → hook → store → (Mock)IncidentIntelligenceService → prototype data now,
// real API later.
// ─────────────────────────────────────────────────────────────────────────────

import { create } from 'zustand'
import { incidentIntelligenceService } from '@/services/incidentIntelligence'
import type { IncidentIntelligenceData } from '@/types'

export type IncidentIntelligenceLoadState = 'idle' | 'loading' | 'ready' | 'error'

export interface IncidentIntelligenceState {
  data: IncidentIntelligenceData | null
  loadState: IncidentIntelligenceLoadState

  fetch: () => Promise<void>
}

export const useIncidentIntelligenceStore = create<IncidentIntelligenceState>(set => ({
  data: null,
  loadState: 'idle',

  fetch: async () => {
    set({ loadState: 'loading' })
    try {
      const data = await incidentIntelligenceService.getIncidentIntelligence()
      set({ data, loadState: 'ready' })
    } catch {
      set({ loadState: 'error' })
    }
  },
}))