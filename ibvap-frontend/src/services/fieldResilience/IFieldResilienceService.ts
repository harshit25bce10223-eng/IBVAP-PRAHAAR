// ─────────────────────────────────────────────────────────────────────────────
// FieldResilienceService — Interface Contract
//
// The ONLY thing the Field Intelligence & Resilience screen depends on. Swap
// the mock for a real implementation without touching any component.
//
// Future API equivalents:
//   GET /field/subjects            (classification confidence + outcome)
//   GET /field/resilience          (buffer / sync state machine)
//   GET /cameras/:id/health        (degraded edge coverage)
//   GET /field/bandwidth-adaptation
// ─────────────────────────────────────────────────────────────────────────────

import type { FieldIntelligenceData } from '@/types'

export interface IFieldResilienceService {
  /** Field capability dataset (human/animal + offline resilience). */
  getFieldIntelligence(): Promise<FieldIntelligenceData>
}