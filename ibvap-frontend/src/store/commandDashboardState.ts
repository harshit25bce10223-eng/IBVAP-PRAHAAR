// ─────────────────────────────────────────────────────────────────────────────
// commandDashboardState — Zustand slice for the Command Center picture.
//
// UI → hook → store → (Mock)CommandDashboardService → prototype data now, real
// API later. The data carries a null fallback so the dashboard can render a
// skeleton while the first fetch resolves.
// ─────────────────────────────────────────────────────────────────────────────

import { create } from 'zustand'
import { commandDashboardService } from '@/services/commandDashboard'
import type { CommandDashboardData } from '@/types'

export type CommandDashboardLoadState = 'idle' | 'loading' | 'ready' | 'error'

export interface CommandDashboardState {
  data: CommandDashboardData | null
  loadState: CommandDashboardLoadState

  fetch: () => Promise<void>
}

export const useCommandDashboardStore = create<CommandDashboardState>(set => ({
  data: null,
  loadState: 'idle',

  fetch: async () => {
    set({ loadState: 'loading' })
    try {
      const data = await commandDashboardService.getDashboard()
      set({ data, loadState: 'ready' })
    } catch {
      set({ loadState: 'error' })
    }
  },
}))