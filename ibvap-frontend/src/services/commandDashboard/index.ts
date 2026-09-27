// ─────────────────────────────────────────────────────────────────────────────
// Command Center service entrypoint — used by the dashboard store.
//
// Local-dev implementation backed by MockCommandDashboardService (प्रहार
// prototype state). Swap the singleton for a RealCommandDashboardService
// without touching callers.
// ─────────────────────────────────────────────────────────────────────────────

import { MockCommandDashboardService } from './MockCommandDashboardService'

export const commandDashboardService = new MockCommandDashboardService()