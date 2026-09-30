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

const DEFAULT_DEMO_USER: User = {
  id: 'usr-002',
  email: 'commander@prhaar.local',
  displayName: 'Col. Priya Sharma',
  role: 'commander',
  badge: 'CMD-0042',
  assignedZone: undefined,
  mfaEnabled: true,
  lastLogin: new Date().toISOString(),
  deviceCert: {
    deviceId: 'DEV-CMD-002',
    fingerprint: '11:22:33:44:55:66:77:88',
    issuedAt: new Date(Date.now() - 60 * 86_400_000).toISOString(),
    expiresAt: new Date(Date.now() + 5 * 86_400_000).toISOString(),
    status: 'valid',
    issuerCN: 'IBVAP-Root-CA',
  },
}

const DEFAULT_DEMO_TOKEN: AuthToken = {
  accessToken: 'demo-token-commander',
  refreshToken: 'demo-refresh-commander',
  expiresAt: Date.now() + 24 * 60 * 60 * 1000,
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      status: 'authenticated',
      user:   DEFAULT_DEMO_USER,
      token:  DEFAULT_DEMO_TOKEN,
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
          authService.logout(token.accessToken).catch(() => {})
        }
      },

      // ── restoreSession ─────────────────────────────────────────────────
      restoreSession: async () => {
        const { token } = get()
        if (!token?.accessToken) {
          set({ status: 'authenticated', user: DEFAULT_DEMO_USER, token: DEFAULT_DEMO_TOKEN })
          return
        }
        if (Date.now() > token.expiresAt) {
          set({ status: 'authenticated', user: DEFAULT_DEMO_USER, token: DEFAULT_DEMO_TOKEN })
          return
        }
        try {
          const user = await authService.validateSession(token.accessToken)
          if (user) {
            set({ status: 'authenticated', user })
          } else {
            set({ status: 'authenticated', user: DEFAULT_DEMO_USER, token: DEFAULT_DEMO_TOKEN })
          }
        } catch {
          set({ status: 'authenticated', user: DEFAULT_DEMO_USER, token: DEFAULT_DEMO_TOKEN })
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
