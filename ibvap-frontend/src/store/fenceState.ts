// ─────────────────────────────────────────────────────────────────────────────
// fenceState — virtual fence editing + zone management
// ─────────────────────────────────────────────────────────────────────────────

import { create } from 'zustand'
import type { Zone, ZonePoint } from '@/types'

export type FenceMode = 'view' | 'draw' | 'edit'

interface FenceStore {
  zones: Zone[]
  mode: FenceMode
  /** zone_id being edited (or 'draft' for a brand-new zone) */
  editingId: string | null
  draftPoints: ZonePoint[]
  /** true while a persisted operation is in flight */
  saving: boolean
  error: string | null

  setZones: (zones: Zone[]) => void
  setMode: (mode: FenceMode) => void
  beginDrawing: () => void
  beginEdit: (zoneId: string, polygon: ZonePoint[]) => void
  addDraftPoint: (p: ZonePoint) => void
  removeDraftPoint: (index: number) => void
  updateDraftPoint: (index: number, p: ZonePoint) => void
  clearDraft: () => void
  setSaving: (v: boolean) => void
  setError: (msg: string | null) => void
}

export const useFenceStore = create<FenceStore>(set => ({
  zones: [],
  mode: 'view',
  editingId: null,
  draftPoints: [],
  saving: false,
  error: null,

  setZones: zones => set({ zones }),
  setMode: mode => set({ mode }),

  beginDrawing: () =>
    set({ mode: 'draw', editingId: null, draftPoints: [], error: null }),

  beginEdit: (zoneId, polygon) =>
    set({ mode: 'edit', editingId: zoneId, draftPoints: [...polygon], error: null }),

  addDraftPoint: p =>
    set(s => ({ draftPoints: [...s.draftPoints, p] })),

  removeDraftPoint: index =>
    set(s => ({
      draftPoints: s.draftPoints.filter((_, i) => i !== index),
    })),

  updateDraftPoint: (index, p) =>
    set(s => ({
      draftPoints: s.draftPoints.map((point, i) => (i === index ? p : point)),
    })),

  clearDraft: () => set({ draftPoints: [], editingId: null, mode: 'view', error: null }),
  setSaving: v => set({ saving: v }),
  setError: msg => set({ error: msg }),
}))