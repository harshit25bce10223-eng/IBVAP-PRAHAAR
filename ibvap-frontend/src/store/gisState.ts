// ─────────────────────────────────────────────────────────────────────────────
// gisState — Zustand slice for the GIS / Digital Twin map.
//
// UI → hook → store → (Mock)GisService → prototype data now, real GIS later.
// Layer toggles and the selected map entity stay as page-local UI state — only
// the dataset is shared through the store.
// ─────────────────────────────────────────────────────────────────────────────

import { create } from 'zustand'
import { gisService } from '@/services/gis'
import type { GisData } from '@/types'

export type GisLoadState = 'idle' | 'loading' | 'ready' | 'error'

export interface GisState {
  data: GisData | null
  loadState: GisLoadState

  fetch: () => Promise<void>
}

export const useGisStore = create<GisState>(set => ({
  data: null,
  loadState: 'idle',

  fetch: async () => {
    set({ loadState: 'loading' })
    try {
      const data = await gisService.getGisData()
      set({ data, loadState: 'ready' })
    } catch {
      set({ loadState: 'error' })
    }
  },
}))