// ─────────────────────────────────────────────────────────────────────────────
// uiStore — sidebar collapse, mobile overlay, active section
// ─────────────────────────────────────────────────────────────────────────────

import { create } from 'zustand'

export type ToastSeverity = 'success' | 'error' | 'warning' | 'info'

export interface Toast {
  id: string
  message: string
  severity: ToastSeverity
  duration?: number  // ms; 0 = sticky
}

interface UIStore {
  sidebarCollapsed: boolean
  mobileMenuOpen: boolean
  toasts: Toast[]

  toggleSidebar: () => void
  setSidebarCollapsed: (v: boolean) => void
  setMobileMenuOpen: (v: boolean) => void

  addToast: (toast: Omit<Toast, 'id'>) => string
  removeToast: (id: string) => void
}

let toastCounter = 0

export const useUIStore = create<UIStore>(set => ({
  sidebarCollapsed: false,
  mobileMenuOpen:   false,
  toasts:           [],

  toggleSidebar:      () => set(s => ({ sidebarCollapsed: !s.sidebarCollapsed })),
  setSidebarCollapsed: v  => set({ sidebarCollapsed: v }),
  setMobileMenuOpen:   v  => set({ mobileMenuOpen: v }),

  addToast: toast => {
    const id = `toast-${++toastCounter}`
    set(s => ({ toasts: [...s.toasts, { ...toast, id }] }))
    const duration = toast.duration ?? 4000
    if (duration > 0) {
      setTimeout(() => {
        set(s => ({ toasts: s.toasts.filter(t => t.id !== id) }))
      }, duration)
    }
    return id
  },

  removeToast: id =>
    set(s => ({ toasts: s.toasts.filter(t => t.id !== id) })),
}))
