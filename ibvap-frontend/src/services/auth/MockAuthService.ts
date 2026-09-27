// ─────────────────────────────────────────────────────────────────────────────
// MockAuthService — Local-dev only implementation of IAuthService
//
// ⚠️  NEVER ship mock credentials to production.
//     Replace this with RealAuthService that calls your backend.
// ─────────────────────────────────────────────────────────────────────────────

import type { IAuthService } from './IAuthService'
import { AuthError } from './IAuthService'
import type { LoginCredentials, AuthToken, User, GeoZone } from '@/types'

// ─── Demo zones ──────────────────────────────────────────────────────────────

const ZONE_ALPHA: GeoZone = {
  id: 'zone-alpha',
  name: 'Zone Alpha — Northern Perimeter',
  code: 'ZONE-A',
  type: 'zone',
}

// ─── Demo users ──────────────────────────────────────────────────────────────
// Credentials only exist in dev. They are never sent to any server.

const MOCK_USERS: Record<string, { password: string; user: User }> = {
  'officer@prhaar.local': {
    password: 'Officer@123',
    user: {
      id: 'usr-001',
      email: 'officer@prhaar.local',
      displayName: 'Rajan Mehta',
      role: 'officer',
      badge: 'OFC-7721',
      assignedZone: ZONE_ALPHA,
      mfaEnabled: false,
      lastLogin: new Date(Date.now() - 86_400_000).toISOString(),
      deviceCert: {
        deviceId: 'DEV-OFC-001',
        fingerprint: 'aa:bb:cc:dd:ee:ff:00:11',
        issuedAt: new Date(Date.now() - 30 * 86_400_000).toISOString(),
        expiresAt: new Date(Date.now() + 60 * 86_400_000).toISOString(),
        status: 'valid',
        issuerCN: 'IBVAP-Root-CA',
      },
    },
  },
  'commander@prhaar.local': {
    password: 'Commander@123',
    user: {
      id: 'usr-002',
      email: 'commander@prhaar.local',
      displayName: 'Col. Priya Sharma',
      role: 'commander',
      badge: 'CMD-0042',
      // no assignedZone → full-sector access
      mfaEnabled: true,
      lastLogin: new Date(Date.now() - 3_600_000).toISOString(),
      deviceCert: {
        deviceId: 'DEV-CMD-002',
        fingerprint: '11:22:33:44:55:66:77:88',
        issuedAt: new Date(Date.now() - 60 * 86_400_000).toISOString(),
        expiresAt: new Date(Date.now() + 5 * 86_400_000).toISOString(), // expiring soon!
        status: 'expiring_soon',
        issuerCN: 'IBVAP-Root-CA',
      },
    },
  },
  'admin@prhaar.local': {
    password: 'Admin@123',
    user: {
      id: 'usr-003',
      email: 'admin@prhaar.local',
      displayName: 'Sysadmin PRHAAR',
      role: 'admin',
      badge: 'ADM-0001',
      mfaEnabled: true,
      lastLogin: new Date(Date.now() - 600_000).toISOString(),
      deviceCert: {
        deviceId: 'DEV-ADM-003',
        fingerprint: '99:88:77:66:55:44:33:22',
        issuedAt: new Date(Date.now() - 10 * 86_400_000).toISOString(),
        expiresAt: new Date(Date.now() - 86_400_000).toISOString(), // expired!
        status: 'expired',
        issuerCN: 'IBVAP-Root-CA',
      },
    },
  },
}

// ─── Token helpers ────────────────────────────────────────────────────────────

function makeToken(userId: string): AuthToken {
  return {
    accessToken:  `mock-access-${userId}-${Date.now()}`,
    refreshToken: `mock-refresh-${userId}-${Date.now()}`,
    expiresAt:    Date.now() + 8 * 60 * 60 * 1000, // 8 hours
  }
}

// ─── Implementation ───────────────────────────────────────────────────────────

export class MockAuthService implements IAuthService {
  private static readonly STORAGE_KEY = 'ibvap_mock_session'

  async login(credentials: LoginCredentials): Promise<{ user: User; token: AuthToken }> {
    // Simulate network delay
    await delay(600)

    const emailKey = credentials.email.toLowerCase()
    // Legacy `ibvap.local` credentials keep working; canonical domain is prhaar.local.
    const entry =
      MOCK_USERS[emailKey] ?? MOCK_USERS[emailKey.replace('@ibvap.local', '@prhaar.local')]

    if (!entry || entry.password !== credentials.password) {
      throw new AuthError('INVALID_CREDENTIALS', 'Invalid email or password.')
    }

    const token = makeToken(entry.user.id)
    const user  = { ...entry.user, lastLogin: new Date().toISOString() }

    // Persist for session restore
    sessionStorage.setItem(
      MockAuthService.STORAGE_KEY,
      JSON.stringify({ user, token })
    )

    return { user, token }
  }

  async refreshToken(refreshToken: string): Promise<AuthToken> {
    await delay(300)
    if (!refreshToken.startsWith('mock-refresh-')) {
      throw new AuthError('SESSION_EXPIRED', 'Refresh token is invalid.')
    }
    // Extract userId from token string
    const parts = refreshToken.split('-')
    const userId = parts[2]
    return makeToken(userId)
  }

  async logout(_accessToken: string): Promise<void> {
    await delay(200)
    sessionStorage.removeItem(MockAuthService.STORAGE_KEY)
  }

  async validateSession(_accessToken: string): Promise<User | null> {
    await delay(100)
    try {
      const raw = sessionStorage.getItem(MockAuthService.STORAGE_KEY)
      if (!raw) return null
      const session = JSON.parse(raw) as { user: User; token: AuthToken }
      if (Date.now() > session.token.expiresAt) {
        sessionStorage.removeItem(MockAuthService.STORAGE_KEY)
        return null
      }
      return session.user
    } catch {
      return null
    }
  }
}

function delay(ms: number) {
  return new Promise(r => setTimeout(r, ms))
}
