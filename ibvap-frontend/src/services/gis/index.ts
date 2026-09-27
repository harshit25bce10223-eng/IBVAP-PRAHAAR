// ─────────────────────────────────────────────────────────────────────────────
// GIS service entrypoint — used by the GIS store.
//
// Local-dev implementation backed by MockGisService (प्रहार prototype map).
// Swap the singleton for a RealGisService without touching callers.
// ─────────────────────────────────────────────────────────────────────────────

import { MockGisService } from './MockGisService'

export const gisService = new MockGisService()