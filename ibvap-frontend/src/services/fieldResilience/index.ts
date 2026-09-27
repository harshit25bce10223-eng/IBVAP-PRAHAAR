// ─────────────────────────────────────────────────────────────────────────────
// Field Resilience service entrypoint — used by the store.
//
// Local-dev implementation backed by the mock. Swap the singleton for a real
// implementation without touching callers.
// ─────────────────────────────────────────────────────────────────────────────

import { MockFieldResilienceService } from './MockFieldResilienceService'

export const fieldResilienceService = new MockFieldResilienceService()