import { create } from 'zustand'

// Intentionally not persisted: a fresh portal visit starts in judge-friendly demo mode.
export const useExperienceStore = create<{
  mode: 'demo' | 'real'
  setMode: (mode: 'demo' | 'real') => void
}>(set => ({ mode: 'demo', setMode: mode => set({ mode }) }))
