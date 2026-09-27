// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 3 — single status → presentation map
//
// The ONLY place mapping evidence states to color/badge language. Reuses
// the shared Badge variants and centralized `--prhaar-*` tokens, so
// VERIFIED is green and MISMATCH is red on every surface.
// ─────────────────────────────────────────────────────────────────────────────

import type { Badge } from '@/components/ui'
import type { ComponentProps } from 'react'
import type {
  AnchorState,
  EvidenceSyncState,
  IntegrityState,
  LedgerStatus,
  RecordStatus,
} from '@/types/evidence'

type BadgeVariant = ComponentProps<typeof Badge>['variant']

export const TONE = {
  good: { text: 'text-prhaar-good', dot: 'bg-prhaar-good', badge: 'safe' },
  degraded: { text: 'text-prhaar-degraded', dot: 'bg-prhaar-degraded', badge: 'warning' },
  failed: { text: 'text-prhaar-failed', dot: 'bg-prhaar-failed', badge: 'critical' },
  neutral: { text: 'text-slate-400', dot: 'bg-slate-500', badge: 'offline' },
  accent: { text: 'text-prhaar-accent', dot: 'bg-prhaar-accent', badge: 'cyan' },
} as const satisfies Record<string, { text: string; dot: string; badge: BadgeVariant }>

export type EvidenceTone = keyof typeof TONE

export function toneForIntegrity(state: IntegrityState): EvidenceTone {
  switch (state) {
    case 'VERIFIED': return 'good'
    case 'HASHED':
    case 'UNVERIFIED':
    case 'PENDING': return 'degraded'
    case 'MISMATCH': return 'failed'
    case 'UNAVAILABLE':
    case 'UNKNOWN': return 'neutral'
  }
}

export function toneForAnchor(state: AnchorState): EvidenceTone {
  switch (state) {
    case 'ANCHORED': return 'good'
    case 'PENDING': return 'degraded'
    case 'FAILED': return 'failed'
    case 'UNAVAILABLE':
    case 'UNKNOWN': return 'neutral'
  }
}

export function toneForRecordStatus(status: RecordStatus): EvidenceTone {
  switch (status) {
    case 'VALID': return 'good'
    case 'UNDER_REVIEW': return 'degraded'
    case 'QUARANTINED': return 'failed'
    case 'UNKNOWN': return 'neutral'
  }
}

export function toneForLedger(status: LedgerStatus): EvidenceTone {
  switch (status) {
    case 'HEALTHY': return 'good'
    case 'DEGRADED':
    case 'VERIFYING': return 'degraded'
    case 'UNAVAILABLE': return 'failed'
    case 'UNKNOWN': return 'neutral'
  }
}

export function toneForSync(state: EvidenceSyncState): EvidenceTone {
  switch (state) {
    case 'SYNCED': return 'good'
    case 'LOCAL_ONLY':
    case 'SYNC_PENDING': return 'degraded'
    case 'SYNC_FAILED': return 'failed'
    case 'UNKNOWN': return 'neutral'
  }
}

export const INTEGRITY_BLURB: Record<IntegrityState, string> = {
  VERIFIED: 'Recomputed evidence hash matches the recorded hash.',
  UNVERIFIED: 'Recorded but not yet verified against the stored hash.',
  HASHED: 'SHA-256 digest computed and recorded; verification pending.',
  MISMATCH: 'Recomputed hash does not match the expected hash.',
  PENDING: 'Verification not yet performed or anchor pending.',
  UNAVAILABLE: 'Verifier service currently unavailable.',
  UNKNOWN: 'Insufficient information to establish integrity.',
}
