// ─────────────────────────────────────────────────────────────────────────────
// Incident Intelligence service entrypoint — used by the store.
//
// Local-dev implementation backed by the mock. Swap the singleton for a real
// implementation without touching callers.
// ─────────────────────────────────────────────────────────────────────────────

import { MockIncidentIntelligenceService } from './MockIncidentIntelligenceService'

export const incidentIntelligenceService = new MockIncidentIntelligenceService()