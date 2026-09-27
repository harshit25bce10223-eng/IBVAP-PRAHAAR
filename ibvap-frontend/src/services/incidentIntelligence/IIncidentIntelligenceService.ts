// ─────────────────────────────────────────────────────────────────────────────
// IncidentIntelligenceService — Interface Contract
//
// The ONLY thing the Incident Intelligence screen depends on. Swap the mock for
// a real implementation without touching any component.
//
// Future API equivalents:
//   GET /incidents/:id/timeline
//   GET /incidents/:id/risk-explanation
//   GET /incidents/:id/evidence
//   GET /incidents/:id/reeid
// ─────────────────────────────────────────────────────────────────────────────

import type { IncidentIntelligenceData } from '@/types'

export interface IIncidentIntelligenceService {
  /** Full investigation dataset for the primary incident. */
  getIncidentIntelligence(): Promise<IncidentIntelligenceData>
}