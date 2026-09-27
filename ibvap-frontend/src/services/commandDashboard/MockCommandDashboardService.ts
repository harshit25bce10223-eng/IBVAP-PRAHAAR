// ─────────────────────────────────────────────────────────────────────────────
// MockCommandDashboardService — local-dev implementation (DEMO ONLY).
//
// Prototype state is isolated here so a real API can replace it later without
// rewriting any Command Center component. A short latency keeps the same async
// shape as the future backend.
// ─────────────────────────────────────────────────────────────────────────────

import type { CommandDashboardData } from '@/types'
import type { ICommandDashboardService } from './ICommandDashboardService'
import { COMMAND_DASHBOARD_DEMO } from './mockCommandDashboardData'

const LATENCY_MS = 200

export class MockCommandDashboardService implements ICommandDashboardService {
  async getDashboard(): Promise<CommandDashboardData> {
    await new Promise(resolve => setTimeout(resolve, LATENCY_MS))
    return structuredClone(COMMAND_DASHBOARD_DEMO)
  }
}