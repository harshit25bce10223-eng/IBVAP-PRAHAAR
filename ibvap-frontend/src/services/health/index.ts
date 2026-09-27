// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 2 — health service entrypoint
//
// Phase 2 swap: replace the singleton below with the real API-backed
// implementation of IHealthService. No caller changes required.
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

export const healthService: IHealthService = mockHealthService

