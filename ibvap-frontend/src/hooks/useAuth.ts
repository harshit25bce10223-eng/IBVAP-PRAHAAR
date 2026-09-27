// ─────────────────────────────────────────────────────────────────────────────
// useAuth — simple mock for the demo (replaced by real auth in prod)
// ─────────────────────────────────────────────────────────────────────────────

import { useAuthStore } from '@/store'

/**
 * Fallback identity shown only when the store reports an authenticated
 * session without a hydrated user object (should be rare). Branding follows
 * the PRHAAR product identity; issuerCN stays technical.
 */
const MOCK_USER = {
  id: 'usr-001',
  email: 'commander@prhaar.local',
  displayName: 'Cmdr. Rivera',
  role: 'commander' as const,
  badge: 'PRHAAR-001',
  assignedZone: null,
  deviceCert: {
    deviceId: 'dev-console-01',
    fingerprint: 'a1:b2:c3:d4:e5:f6',
    issuedAt: '2026-01-15T08:00:00Z',
    expiresAt: '2027-01-15T08:00:00Z',
    status: 'valid' as const,
    issuerCN: 'PRHAAR Root CA',
  },
  lastLogin: new Date().toISOString(),
  mfaEnabled: true,
}

export function useAuth() {
  const { status, user, token, error, login, logout, restoreSession, clearError, markSessionExpired } =
    useAuthStore()

  return {
    status,
    user: user ?? MOCK_USER,
    token,
    error,
    isAuthenticated: status === 'authenticated',
    hasFullSectorAccess: (user ?? MOCK_USER).assignedZone === null,
    login,
    logout,
    restoreSession,
    clearError,
    markSessionExpired,
  }
}