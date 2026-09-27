// ─────────────────────────────────────────────────────────────────────────────
// useShell — command-shell data hooks.
//
// Architecture (spec §17):  UI → hook/store/service → prototype data now,
// real API later. Components never mutate the store or touch the service
// directly.
// ─────────────────────────────────────────────────────────────────────────────

import { useEffect } from 'react'
import { useShellStore } from '@/store'

export function useSystemStatus() {
  const status = useShellStore(s => s.status)
  const statusState = useShellStore(s => s.statusState)
  const fetchSystemStatus = useShellStore(s => s.fetchSystemStatus)

  return { status, statusState, refetch: fetchSystemStatus }
}

export function useNotifications() {
  const notifications = useShellStore(s => s.notifications)
  const notifState = useShellStore(s => s.notifState)
  const unreadCount = useShellStore(
    s => s.notifications.filter(n => !n.read).length
  )
  const fetchNotifications = useShellStore(s => s.fetchNotifications)
  const markAllRead = useShellStore(s => s.markAllNotificationsRead)

  /** Load notifications on mount when the store is not yet populated. */
  useEffect(() => {
    if (useShellStore.getState().notifState === 'idle') {
      fetchNotifications().catch(() => {})
    }
  }, [fetchNotifications])

  return { notifications, notifState, unreadCount, refetch: fetchNotifications, markAllRead }
}