// ─────────────────────────────────────────────────────────────────────────────
// Auth service entrypoint — used by authStore during login/restore.
//
// Local-dev implementation backed by MockAuthService (PRHAAR demo profiles).
// Swap the singleton for a RealAuthService without touching callers.
// ─────────────────────────────────────────────────────────────────────────────

import { MockAuthService } from './MockAuthService'

export const authService = new MockAuthService()
