// ─────────────────────────────────────────────────────────────────────────────
// MockIncidentIntelligenceService — local-dev implementation (DEMO ONLY).
//
// Isolates prototype investigation state so a real API can replace it later
// without rewriting the Incident Intelligence components.
// ─────────────────────────────────────────────────────────────────────────────

import type { IncidentIntelligenceData } from '@/types'
import type { IIncidentIntelligenceService } from './IIncidentIntelligenceService'
import { INCIDENT_INTELLIGENCE_DEMO } from './mockIncidentIntelligenceData'

const LATENCY_MS = 200

export class MockIncidentIntelligenceService implements IIncidentIntelligenceService {
  async getIncidentIntelligence(): Promise<IncidentIntelligenceData> {
    await new Promise(resolve => setTimeout(resolve, LATENCY_MS))
    return structuredClone(INCIDENT_INTELLIGENCE_DEMO)
  }
}