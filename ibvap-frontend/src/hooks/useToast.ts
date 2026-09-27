// ─────────────────────────────────────────────────────────────────────────────
// useToast — tiny wrapper around uiStore
// ─────────────────────────────────────────────────────────────────────────────

import { useUIStore } from '@/store'

export function useToast() {
  const { addToast, removeToast, toasts } = useUIStore()
  return { toasts, addToast, removeToast }
}