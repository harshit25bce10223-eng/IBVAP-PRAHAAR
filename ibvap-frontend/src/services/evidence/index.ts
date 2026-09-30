// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 3 — evidence service entrypoint
//
// Phase 2 swap: replace the singleton below with the real API-backed
// implementation of IEvidenceService. No caller changes required.
// ─────────────────────────────────────────────────────────────────────────────

import { mockEvidenceService } from './mockEvidenceService'
import { realEvidenceService } from './realEvidenceService'
import type { IEvidenceService } from './IEvidenceService'

// Determine mode from environment - defaults to DEMO for development fixtures
export const isRealEvidenceMode = import.meta.env.VITE_EVIDENCE_MODE === 'REAL'

export const evidenceService: IEvidenceService = isRealEvidenceMode ? realEvidenceService : mockEvidenceService
export { mockEvidenceService, realEvidenceService }
export type { IEvidenceService, IExportReceipt } from './IEvidenceService'
