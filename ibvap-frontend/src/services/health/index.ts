// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 2 — health service entrypoint
//
// Phase 2 swap: replace the singleton below with the real API-backed
// implementation of IHealthService. No caller changes required. A REAL
// provider must surface failures as CAMERA HEALTH DATA UNAVAILABLE — it must
// never silently fall back to mock fixtures.
// No component imports mock fixtures directly except demo/test infrastructure.
// ─────────────────────────────────────────────────────────────────────────────

import { mockHealthService } from './mockHealthService'
import { realHealthService } from './realHealthService'
import type { IHealthService } from './IHealthService'

export { mockHealthService } from './mockHealthService'
export { realHealthService } from './realHealthService'
export type { IHealthService }

export function getHealthService(mode: 'DEMO' | 'REAL'): IHealthService {
  return mode === 'REAL' ? realHealthService : mockHealthService
}

// Set VITE_HEALTH_MODE=REAL to point the health surfaces at the live backend.
// Defaults to DEMO for development. REAL failures surface as explicit errors
// (the store keeps last-known data labelled as such) — never demo values.
const isRealMode = import.meta.env.VITE_HEALTH_MODE === 'REAL'

export const healthService: IHealthService = isRealMode ? realHealthService : mockHealthService

