// ─────────────────────────────────────────────────────────────────────────────
// MockFieldResilienceService — local-dev implementation (DEMO ONLY).
//
// Isolates prototype field state so a real API can replace it later without
// rewriting the Field Intelligence & Resilience components.
// ─────────────────────────────────────────────────────────────────────────────

import type { FieldIntelligenceData } from '@/types'
import type { IFieldResilienceService } from './IFieldResilienceService'
import { FIELD_INTELLIGENCE_DEMO } from './mockFieldResilienceData'

const LATENCY_MS = 200

export class MockFieldResilienceService implements IFieldResilienceService {
  async getFieldIntelligence(): Promise<FieldIntelligenceData> {
    await new Promise(resolve => setTimeout(resolve, LATENCY_MS))
    return structuredClone(FIELD_INTELLIGENCE_DEMO)
  }
}