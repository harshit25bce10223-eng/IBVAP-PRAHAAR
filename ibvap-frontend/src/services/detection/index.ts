// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 5 — detection service entrypoint
//
// Phase 2 swap: replace the singleton below with the real API-backed
// implementation of IDetectionService. No caller changes required. A REAL
// provider must surface failures as DETECTION DATA UNAVAILABLE — it must never
// silently fall back to mock fixtures.
// No component imports mock fixtures directly except demo/test infrastructure.
// ─────────────────────────────────────────────────────────────────────────────

import { mockDetectionService } from './mockDetectionService'
import { realDetectionService } from './RealDetectionService'
import type { IDetectionService } from './IDetectionService'

// Determine mode from environment - defaults to DEMO for development
const isRealMode = import.meta.env.VITE_DETECTION_MODE === 'REAL'

export const detectionService: IDetectionService = isRealMode ? realDetectionService : mockDetectionService
export type { IDetectionService } from './IDetectionService'