// ─────────────────────────────────────────────────────────────────────────────
// cameraState — selected camera + live track visualization state
// ─────────────────────────────────────────────────────────────────────────────

import { create } from 'zustand'
import { DEFAULT_CAMERAS } from '@/types'
import type { CameraDetail, TrackVisual } from '@/types'

interface CameraStore {
  cameras: CameraDetail[]
  selectedCameraId: string
  tracks: TrackVisual[]
  isNight: boolean

  setSelectedCamera: (id: string) => void
  upsertTrack: (track: TrackVisual) => void
  clearTracks: () => void
  toggleNightMode: () => void
}

export const useCameraStore = create<CameraStore>((set, get) => ({
  cameras: DEFAULT_CAMERAS,
  selectedCameraId: DEFAULT_CAMERAS[0].id,
  tracks: [],
  isNight: true,

  setSelectedCamera: id => set({ selectedCameraId: id }),

  upsertTrack: track => {
    const existing = [...get().tracks]
    const idx = existing.findIndex(t => t.track_id === track.track_id)
    if (idx >= 0) existing[idx] = track
    else existing.push(track)

    // Keep a short history of recently-seen tracks.
    const cutoff = Date.now() - 4000
    set({ tracks: existing.filter(t => t.lastSeen >= cutoff) })
  },

  clearTracks: () => set({ tracks: [] }),
  toggleNightMode: () => set(s => ({ isNight: !s.isNight })),
}))