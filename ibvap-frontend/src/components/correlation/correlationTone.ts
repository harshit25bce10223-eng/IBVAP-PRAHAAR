// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 4 — single status → presentation map
//
// The ONLY place that maps a correlation/severity/reliability state to
// colors. Correlation is NOT a severity: correlation uses neutral/accent
// styling, severity keeps the existing risk semantics, and camera health
// keeps the Component 2 semantics. Colors reference the centralized
// `--prhaar-*` tokens (index.css) — no per-component shades.
// ─────────────────────────────────────────────────────────────────────────────

import type { Badge } from '@/components/ui'
import type { ComponentProps } from 'react'
import type {
  Connectivity,
  CorrelationGroupState,
  CorrelationStatus,
  IncidentState,
  Reliability,
} from '@/types/eventCorrelation'
import type { Severity } from '@/types/risk'

type BadgeVariant = ComponentProps<typeof Badge>['variant']

/** Tailwind classes built exclusively from centralized prhaar tokens. */
export const TONE = {
  good: { text: 'text-prhaar-good', dot: 'bg-prhaar-good', badge: 'safe' },
  degraded: { text: 'text-prhaar-degraded', dot: 'bg-prhaar-degraded', badge: 'warning' },
  failed: { text: 'text-prhaar-failed', dot: 'bg-prhaar-failed', badge: 'critical' },
  neutral: { text: 'text-slate-400', dot: 'bg-slate-500', badge: 'offline' },
  accent: { text: 'text-prhaar-accent', dot: 'bg-prhaar-accent', badge: 'cyan' },
} as const satisfies Record<string, { text: string; dot: string; badge: BadgeVariant }>

export type CorrelationTone = keyof typeof TONE

/**
 * Correlation is never a severity: CORRELATED uses accent/neutral styling
 * regardless of the underlying risk. DISSOLVED renders muted to signal the
 * history is preserved but no longer active; UNKNOWN is neutral.
 */
export function toneForCorrelation(status: CorrelationStatus): CorrelationTone {
  switch (status) {
    case 'CORRELATED':
    case 'RELATED': return 'accent'
    case 'UNCERTAIN': return 'degraded'
    case 'DISSOLVED': return 'neutral'
    case 'STANDALONE': return 'neutral'
    case 'UNKNOWN': return 'neutral'
  }
}

/** Correlation status → short human label (always text + color, §124/§153). */
export const CORRELATION_LABEL: Record<CorrelationStatus, string> = {
  CORRELATED: 'CORRELATED',
  RELATED: 'RELATED',
  STANDALONE: 'STANDALONE',
  UNCERTAIN: 'UNCERTAIN',
  DISSOLVED: 'DISSOLVED',
  UNKNOWN: 'UNKNOWN',
}

/** One-line operator explanation for each correlation state. */
export const CORRELATION_BLURB: Record<CorrelationStatus, string> = {
  CORRELATED: 'Signals were grouped into one combined situation.',
  RELATED: 'Signals show relationship evidence; grouping is in progress.',
  STANDALONE: 'No sufficient relationship evidence for grouping.',
  UNCERTAIN: 'Relationship evidence is partial or conflicting.',
  DISSOLVED: 'A previous correlation was not sustained.',
  UNKNOWN: 'Insufficient event relationship data.',
}

/** Group lifecycle uses neutral/amber semantics, not severity colors. */
export function toneForGroupState(state: CorrelationGroupState): CorrelationTone {
  switch (state) {
    case 'OPEN':
    case 'ACTIVE': return 'accent'
    case 'STABLE': return 'good'
    case 'RESOLVED': return 'good'
    case 'DISSOLVED': return 'neutral'
    case 'UNKNOWN': return 'neutral'
  }
}

export const GROUP_STATE_LABEL: Record<CorrelationGroupState, string> = {
  OPEN: 'OPEN',
  ACTIVE: 'ACTIVE',
  STABLE: 'STABLE',
  RESOLVED: 'RESOLVED',
  DISSOLVED: 'DISSOLVED',
  UNKNOWN: 'UNKNOWN',
}

/** Severity keeps the existing Component 1 risk semantics. */
export function toneForSeverity(severity: Severity): CorrelationTone {
  switch (severity) {
    case 'LOW': return 'good'
    case 'MEDIUM': return 'degraded'
    case 'HIGH': return 'failed'
    case 'CRITICAL': return 'failed'
  }
}

/** Reliability semantics mirror health: HIGH=good, MEDIUM=degraded, LOW=failed. */
export function toneForReliability(reliability: Reliability): CorrelationTone {
  switch (reliability) {
    case 'HIGH': return 'good'
    case 'MEDIUM': return 'degraded'
    case 'LOW': return 'failed'
    case 'UNKNOWN': return 'neutral'
  }
}

export const RELIABILITY_LABEL: Record<Reliability, string> = {
  HIGH: 'HIGH',
  MEDIUM: 'MEDIUM',
  LOW: 'LOW',
  UNKNOWN: 'UNKNOWN',
}

/** Connectivity: DELAYED is explicitly not real-time (§141). */
export function toneForConnectivity(connectivity: Connectivity): CorrelationTone {
  switch (connectivity) {
    case 'LIVE': return 'good'
    case 'DELAYED': return 'degraded'
    case 'LAST_SYNCED': return 'degraded'
    case 'UNKNOWN': return 'neutral'
  }
}

export const CONNECTIVITY_LABEL: Record<Connectivity, string> = {
  LIVE: 'LIVE',
  DELAYED: 'DELAYED',
  LAST_SYNCED: 'LAST SYNCED',
  UNKNOWN: 'UNKNOWN',
}

export function toneForIncidentState(state: IncidentState | null): CorrelationTone {
  switch (state) {
    case 'NEW': return 'degraded'
    case 'REVIEWED': return 'accent'
    case 'CLOSED': return 'neutral'
    case null:
    case 'UNKNOWN': return 'neutral'
  }
}

export const INCIDENT_STATE_LABEL: Record<IncidentState, string> = {
  NEW: 'NEW',
  REVIEWED: 'REVIEWED',
  CLOSED: 'CLOSED',
  UNKNOWN: 'UNKNOWN',
}