// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 4 — correlation service entrypoint
//
// Mode decides the provider: DEMO serves isolated fixtures; REAL calls the live
// /api/v1 backend. There is NO silent fallback — a REAL provider surfaces
// failures as "EVENT/CORRELATION DATA UNAVAILABLE" and never shows demo
// signals in REAL mode (§63). No component imports mock fixtures directly
// except demo/test infrastructure.
// ─────────────────────────────────────────────────────────────────────────────

import { mockCorrelationService } from './mockCorrelationService'
import { realCorrelationService } from './RealCorrelationService'
import type { IEventCorrelationService } from './IEventCorrelationService'

// Determine mode from environment - defaults to DEMO for development.
// Set VITE_CORRELATION_MODE=REAL to point the workspace at the live backend.
const isRealMode = import.meta.env.VITE_CORRELATION_MODE === 'REAL'

export const correlationService: IEventCorrelationService = isRealMode ? realCorrelationService : mockCorrelationService
export type { IEventCorrelationService } from './IEventCorrelationService'