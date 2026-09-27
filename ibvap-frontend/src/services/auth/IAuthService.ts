// ─────────────────────────────────────────────────────────────────────────────
// AuthService — Interface Contract
//
// This interface is the ONLY thing the UI depends on for authentication.
// Swap the implementation (MockAuthService → RealAuthService) without
// touching any page or component.
// ─────────────────────────────────────────────────────────────────────────────

import type { LoginCredentials, AuthToken, User } from '@/types'

export interface IAuthService {
  /**
   * Authenticate a user with email + password.
   * Returns the user profile and JWT tokens on success.
   * Throws an AuthError on failure.
   */
  login(credentials: LoginCredentials): Promise<{ user: User; token: AuthToken }>

  /**
   * Silently refresh an access token using the stored refresh token.
   * Returns new AuthToken or throws if refresh is invalid/expired.
   */
  refreshToken(refreshToken: string): Promise<AuthToken>

  /**
   * Invalidate the session server-side and clear local state.
   */
  logout(accessToken: string): Promise<void>

  /**
   * Validate a stored token and return the user profile.
   * Used on app startup to restore a session.
   * Returns null if the token is invalid or expired.
   */
  validateSession(accessToken: string): Promise<User | null>
}

// ─── Typed error ─────────────────────────────────────────────────────────────

export type AuthErrorCode =
  | 'INVALID_CREDENTIALS'
  | 'ACCOUNT_LOCKED'
  | 'SESSION_EXPIRED'
  | 'NETWORK_ERROR'
  | 'DEVICE_NOT_TRUSTED'
  | 'MFA_REQUIRED'
  | 'UNKNOWN'

export class AuthError extends Error {
  constructor(
    public readonly code: AuthErrorCode,
    message: string
  ) {
    super(message)
    this.name = 'AuthError'
  }
}
