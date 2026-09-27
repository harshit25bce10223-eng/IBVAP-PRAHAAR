// ─────────────────────────────────────────────────────────────────────────────
// authStore — Zustand slice for authentication state
// ─────────────────────────────────────────────────────────────────────────────

import { create } from 'zustand'
import { persist, createJSONStorage } from 'zustand/middleware'
import { authService } from '@/services/auth'
import { AuthError } from '@/services/auth/IAuthService'
import type { User, AuthToken, AuthStatus, LoginCredentials } from '@/types'

interface AuthStore {
  // ── State ──────────────────────────────────────────────────────────────
  status: AuthStatus
  user: User | null
  token: AuthToken | null
  error: string | null

  // ── Actions ────────────────────────────────────────────────────────────
  login: (credentials: LoginCredentials) => Promise<void>
  logout: () => Promise<void>
  restoreSession: () => Promise<void>
  clearError: () => void
  markSessionExpired: () => void
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      status: 'idle',
      user:   null,
      token:  null,
      error:  null,

      // ── login ──────────────────────────────────────────────────────────
      login: async (credentials) => {
        set({ status: 'loading', error: null })
        try {
          const { user, token } = await authService.login(credentials)
          set({ status: 'authenticated', user, token, error: null })
        } catch (err) {
          const message =
            err instanceof AuthError
              ? err.message
              : 'An unexpected error occurred. Please try again.'
          set({ status: 'error', error: message, user: null, token: null })
        }
      },

      // ── logout ─────────────────────────────────────────────────────────
      logout: async () => {
        const { token } = get()
        set({ status: 'unauthenticated', user: null, token: null, error: null })
        if (token?.accessToken) {
          // fire-and-forget; don't block UI on logout
          authService.logout(token.accessToken).catch(() => {})
        }
      },

      // ── restoreSession ─────────────────────────────────────────────────
      restoreSession: async () => {
        const { token } = get()
        if (!token?.accessToken) {
          set({ status: 'unauthenticated' })
          return
        }
        // Check token expiry locally first
        if (Date.now() > token.expiresAt) {
          set({ status: 'session_expired', user: null, token: null })
          return
        }
        set({ status: 'loading' })
        try {
          const user = await authService.validateSession(token.accessToken)
          if (user) {
            set({ status: 'authenticated', user })
          } else {
            set({ status: 'session_expired', user: null, token: null })
          }
        } catch {
          set({ status: 'session_expired', user: null, token: null })
        }
      },

      // ── helpers ────────────────────────────────────────────────────────
      clearError:          () => set({ error: null }),
      markSessionExpired:  () => set({ status: 'session_expired', user: null, token: null }),
    }),
    {
      name:    'ibvap-auth',
      storage: createJSONStorage(() => sessionStorage),
      // Only persist token; user is re-fetched on restore
      partialize: state => ({ token: state.token }),
    }
  )
)
