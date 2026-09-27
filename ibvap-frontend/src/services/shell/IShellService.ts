// ─────────────────────────────────────────────────────────────────────────────
// ShellService — Interface Contract
//
// The ONLY thing the command shell UI depends on for system status and
// notifications. Swap the implementation (MockShellService → RealShellService)
// without touching any layout component.
// ─────────────────────────────────────────────────────────────────────────────

import type { CommandNotification, SystemStatusInfo } from '@/types'

export interface IShellService {
  /** Latest platform/system operational state. */
  getSystemStatus(): Promise<SystemStatusInfo>

  /** Command notifications for the current operator. */
  getNotifications(): Promise<CommandNotification[]>
}