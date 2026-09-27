// ─────────────────────────────────────────────────────────────────────────────
// MockShellService — local-dev implementation of IShellService (DEMO ONLY).
//
// Prototype state is isolated here so a real API can replace it later without
// rewriting any shell component. A short latency keeps the same async shape
// as the future backend.
// ─────────────────────────────────────────────────────────────────────────────

import type { CommandNotification, SystemStatusInfo } from '@/types'
import type { IShellService } from './IShellService'
import { SHELL_DEMO_NOTIFICATIONS, SHELL_DEMO_STATUS } from './mockShellData'

const LATENCY_MS = 200

export class MockShellService implements IShellService {
  async getSystemStatus(): Promise<SystemStatusInfo> {
    await new Promise(resolve => setTimeout(resolve, LATENCY_MS))
    return { ...SHELL_DEMO_STATUS }
  }

  async getNotifications(): Promise<CommandNotification[]> {
    await new Promise(resolve => setTimeout(resolve, LATENCY_MS))
    return SHELL_DEMO_NOTIFICATIONS.map(n => ({ ...n }))
  }
}