// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 4 — correlation service entrypoint
//
// Phase 2 swap: replace the singleton below with the real API-backed
// implementation of IEventCorrelationService. No caller changes required.
// No component imports mock fixtures directly except demo/test infrastructure.
// ─────────────────────────────────────────────────────────────────────────────

import { mockCorrelationService } from './mockCorrelationService'
import type { IEventCorrelationService } from './IEventCorrelationService'

export const correlationService: IEventCorrelationService = mockCorrelationService
export type { IEventCorrelationService } from './IEventCorrelationService'