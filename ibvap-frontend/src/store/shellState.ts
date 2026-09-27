// ─────────────────────────────────────────────────────────────────────────────
// shellState — Zustand slice for command-shell status + notifications.
//
// UI → hook → store → (Mock)ShellService → prototype data now, real API later.
// The status initially carries an OPERATIONAL fallback so the command header
// never renders blank while the first fetch resolves.
// ─────────────────────────────────────────────────────────────────────────────

import { create } from 'zustand'
import { shellService } from '@/services/shell'
import type { CommandNotification, SystemStatusInfo } from '@/types'

export type ShellLoadState = 'idle' | 'loading' | 'ready' | 'error'

interface ShellStore {
  status: SystemStatusInfo | null
  statusState: ShellLoadState
  notifications: CommandNotification[]
  notifState: ShellLoadState

  fetchSystemStatus: () => Promise<void>
  fetchNotifications: () => Promise<void>
  markAllNotificationsRead: () => void
}

export const useShellStore = create<ShellStore>(set => ({
  status: {
    state: 'OPERATIONAL',
    label: 'SYSTEM OPERATIONAL',
    detail: 'Initializing…',
  },
  statusState: 'idle',
  notifications: [],
  notifState: 'idle',

  fetchSystemStatus: async () => {
    set({ statusState: 'loading' })
    try {
      const status = await shellService.getSystemStatus()
      set({ status, statusState: 'ready' })
    } catch {
      set({
        status: {
          state: 'OFFLINE',
          label: 'SYSTEM OFFLINE',
          detail: 'Status feed unavailable',
        },
        statusState: 'error',
      })
    }
  },

  fetchNotifications: async () => {
    set({ notifState: 'loading' })
    try {
      const notifications = await shellService.getNotifications()
      set({ notifications, notifState: 'ready' })
    } catch {
      set({ notifState: 'error' })
    }
  },

  markAllNotificationsRead: () =>
    set(s => ({
      notifications: s.notifications.map(n => ({ ...n, read: true })),
    })),
}))