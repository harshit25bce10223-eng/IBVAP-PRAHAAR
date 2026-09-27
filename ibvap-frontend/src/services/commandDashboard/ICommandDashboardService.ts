// ─────────────────────────────────────────────────────────────────────────────
// CommandDashboardService — Interface Contract
//
// The ONLY thing the Command Center UI depends on for its operational picture.
// Swap the implementation (MockCommandDashboardService → RealCommandDashboardService)
// without touching any dashboard component.
//
// Future API equivalents:
//   GET /dashboard/summary
//   GET /incidents/active
//   GET /cameras
//   GET /system/health
//   GET /map/context
// ─────────────────────────────────────────────────────────────────────────────

import type { CommandDashboardData } from '@/types'

export interface ICommandDashboardService {
  /** Full unified operational picture for the Command Center. */
  getDashboard(): Promise<CommandDashboardData>
}