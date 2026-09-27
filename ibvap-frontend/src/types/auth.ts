// ─────────────────────────────────────────────────────────────────────────────
// IBVAP Domain Types — Auth & User
// ─────────────────────────────────────────────────────────────────────────────

export type Role = 'officer' | 'commander' | 'admin' | 'auditor'

export interface Permission {
  resource: string
  actions: ('read' | 'write' | 'delete' | 'export')[]
}

export interface GeoZone {
  id: string
  name: string
  code: string        // e.g. "ZONE-A", "SECTOR-7"
  type: 'zone' | 'sector' | 'district' | 'national'
  parentId?: string
}

export interface DeviceCertificate {
  deviceId: string
  fingerprint: string
  issuedAt: string   // ISO-8601
  expiresAt: string  // ISO-8601
  status: 'valid' | 'expiring_soon' | 'expired' | 'revoked' | 'unknown'
  issuerCN: string
}

export interface User {
  id: string
  email: string
  displayName: string
  role: Role
  avatarUrl?: string
  badge?: string           // officer badge / employee ID
  assignedZone?: GeoZone   // null → full-sector access
  deviceCert?: DeviceCertificate
  lastLogin?: string       // ISO-8601
  mfaEnabled: boolean
}

// ─── Auth payloads ───────────────────────────────────────────────────────────

export interface LoginCredentials {
  email: string
  password: string
  rememberDevice?: boolean
}

export interface AuthToken {
  accessToken: string
  refreshToken: string
  expiresAt: number  // unix epoch ms
}

export type AuthStatus =
  | 'idle'
  | 'loading'
  | 'authenticated'
  | 'unauthenticated'
  | 'session_expired'
  | 'error'

export interface AuthState {
  status: AuthStatus
  user: User | null
  token: AuthToken | null
  error: string | null
}

// ─── Role helpers ─────────────────────────────────────────────────────────────

export const ROLE_LABELS: Record<Role, string> = {
  officer:   'Field Officer',
  commander: 'Sector Commander',
  admin:     'System Administrator',
  auditor:   'Audit Reviewer',
}

export const ROLE_HIERARCHY: Record<Role, number> = {
  officer:   1,
  commander: 2,
  auditor:   2,
  admin:     3,
}

export function hasMinRole(userRole: Role, required: Role): boolean {
  return ROLE_HIERARCHY[userRole] >= ROLE_HIERARCHY[required]
}
