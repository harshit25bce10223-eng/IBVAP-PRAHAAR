// ─────────────────────────────────────────────────────────────────────────────
// mockShellData — isolated prototype (DEMO ONLY) fixtures for the shell.
//
// Replaceable by a real backend later; the UI never hardcodes these values.
// Timestamps are fixed ISO strings (no fabricated live "now") and are shown
// formatted as IST when rendered.
// ─────────────────────────────────────────────────────────────────────────────

import type { CommandNotification, SystemStatusInfo } from '@/types'

export const SHELL_DEMO_STATUS: SystemStatusInfo = {
  state: 'OPERATIONAL',
  label: 'SYSTEM OPERATIONAL',
  detail: 'All subsystems nominal',
  updatedAt: '2026-09-07T04:00:00Z',
}

export const SHELL_DEMO_NOTIFICATIONS: CommandNotification[] = [
  {
    id: 'n-001',
    severity: 'critical',
    title: 'HIGH-RISK INCIDENT — INC-024',
    meta: 'CAM-01 · TRK-014 · Risk 82 · HIGH',
    occurredAt: '2026-09-07T03:58:00Z',
    read: false,
  },
  {
    id: 'n-002',
    severity: 'warning',
    title: 'CAM-02 RE-ID MATCH DETECTED',
    meta: 'PATTERN REVIEW REQUIRED',
    occurredAt: '2026-09-07T03:52:00Z',
    read: false,
  },
  {
    id: 'n-003',
    severity: 'warning',
    title: 'CAM-07 NETWORK DEGRADED',
    meta: 'SECTOR LINK · CHECK HEALTH',
    occurredAt: '2026-09-07T03:41:00Z',
    read: false,
  },
]