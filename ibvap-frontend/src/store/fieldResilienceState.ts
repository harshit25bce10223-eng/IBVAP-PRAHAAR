// ─────────────────────────────────────────────────────────────────────────────
// fieldResilienceState — Zustand slice for Field Intelligence & Resilience.
//
// UI → hook → store → (Mock)FieldResilienceService → prototype data now, real
// API later.
// ─────────────────────────────────────────────────────────────────────────────

import { create } from 'zustand'
import { fieldResilienceService } from '@/services/fieldResilience'
import type { FieldIntelligenceData } from '@/types'

export type FieldResilienceLoadState = 'idle' | 'loading' | 'ready' | 'error'

export interface FieldResilienceState {
  data: FieldIntelligenceData | null
  loadState: FieldResilienceLoadState

  fetch: () => Promise<void>
}

export const useFieldResilienceStore = create<FieldResilienceState>(set => ({
  data: null,
  loadState: 'idle',

  fetch: async () => {
    set({ loadState: 'loading' })
    try {
      const data = await fieldResilienceService.getFieldIntelligence()
      set({ data, loadState: 'ready' })
    } catch {
      set({ loadState: 'error' })
    }
  },
}))