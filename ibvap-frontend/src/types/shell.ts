// ─────────────────────────────────────────────────────────────────────────────
// प्रहार — Application Shell types (Main Command Dashboard, Sub-Component 1)
//
// Canonical contracts for the command shell: system status, command
// notifications and the operational-section context. These mirror the
//  prototype → real-API seam: the UI only ever depends on these types,
//  never on hardcoded display strings inside JSX.
// ─────────────────────────────────────────────────────────────────────────────

export type SystemOperationState =
  | 'OPERATIONAL'
  | 'DEGRADED'
  | 'CRITICAL'
  | 'OFFLINE'

export interface SystemStatusInfo {
  state: SystemOperationState
  /** Display label such as "SYSTEM OPERATIONAL" (never colour-only). */
  label: string
  /** Optional explanatory copy for health/detail panels. */
  detail?: string
  /** ISO-8601 timestamp of the last status report. */
  updatedAt?: string
}

export type CommandNotificationSeverity = 'critical' | 'warning' | 'info'

export interface CommandNotification {
  id: string
  severity: CommandNotificationSeverity
  title: string
  /** Secondary context line, e.g. "CAM-01 · Risk 82 · HIGH". */
  meta?: string
  /** ISO-8601 timestamp when the alert was raised. */
  occurredAt: string
  read: boolean
}

// ─── Command display context (navigation/header/breadcrumb) ─────────────────

export interface CommandSectionContext {
  /** Operational section, e.g. "COMMAND CENTER". */
  section: string
  /** Resolved page label, e.g. "Live Camera Wall". */
  label: string
  /** Breadcrumb leaf, e.g. "OVERVIEW". */
  sub: string
}