// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 2 — single status → presentation map
//
// The ONLY place that maps a backend status to color/badge language. Every
// health surface (wall tile, mini panel, rail, twin marker) imports from
// here, so DEGRADED is amber everywhere and OFFLINE is red everywhere.
// Colors reference the centralized `--prhaar-*` tokens (index.css), which
// are mapped to the existing PRHAAR palette — no per-component shades.
// ─────────────────────────────────────────────────────────────────────────────

import type { Badge } from '@/components/ui'
import type { ComponentProps } from 'react'
import type {
  CameraHealthStatus,
  HealthMetricStatus,
  NetworkStatus,
  StreamState,
  TrendDirection,
  ViewpointStatus,
} from '@/types/cameraHealth'

type BadgeVariant = ComponentProps<typeof Badge>['variant']

/** Tailwind classes built exclusively from centralized prhaar tokens. */
export const TONE = {
  good: { text: 'text-prhaar-good', dot: 'bg-prhaar-good', badge: 'safe' },
  degraded: { text: 'text-prhaar-degraded', dot: 'bg-prhaar-degraded', badge: 'warning' },
  failed: { text: 'text-prhaar-failed', dot: 'bg-prhaar-failed', badge: 'critical' },
  neutral: { text: 'text-slate-400', dot: 'bg-slate-500', badge: 'offline' },
  accent: { text: 'text-prhaar-accent', dot: 'bg-prhaar-accent', badge: 'cyan' },
} as const satisfies Record<string, { text: string; dot: string; badge: BadgeVariant }>

export type HealthTone = keyof typeof TONE

export function toneForStatus(status: CameraHealthStatus): HealthTone {
  switch (status) {
    case 'ONLINE': return 'good'
    case 'DEGRADED':
    case 'STALE':
    case 'FROZEN':
    case 'MAINTENANCE': return 'degraded'
    case 'OFFLINE': return 'failed'
    case 'UNKNOWN': return 'neutral'
  }
}

export function toneForMetricStatus(status: HealthMetricStatus): HealthTone {
  switch (status) {
    case 'GOOD': return 'good'
    case 'DEGRADED': return 'degraded'
    case 'FAILED': return 'failed'
    case 'UNKNOWN': return 'neutral'
  }
}

export function toneForTrend(direction: TrendDirection): HealthTone {
  switch (direction) {
    case 'IMPROVING': return 'good'
    case 'STABLE': return 'neutral'
    case 'DEGRADING': return 'degraded'
    case 'UNKNOWN': return 'neutral'
  }
}

export function toneForStream(state: StreamState): HealthTone {
  switch (state) {
    case 'CONNECTED': return 'good'
    case 'DEGRADED':
    case 'RECONNECTING':
    case 'STALE':
    case 'FROZEN': return 'degraded'
    case 'DISCONNECTED': return 'failed'
    case 'UNKNOWN': return 'neutral'
  }
}

export function toneForNetwork(status: NetworkStatus): HealthTone {
  switch (status) {
    case 'STABLE': return 'good'
    case 'DEGRADED': return 'degraded'
    case 'OFFLINE': return 'failed'
    case 'UNKNOWN': return 'neutral'
  }
}

export function toneForViewpoint(status: ViewpointStatus): HealthTone {
  switch (status) {
    case 'STABLE': return 'good'
    case 'SHIFT_DETECTED': return 'degraded'
    case 'SEVERE_SHIFT': return 'failed'
    case 'UNKNOWN': return 'neutral'
  }
}

export const STREAM_LABEL: Record<StreamState, string> = {
  CONNECTED: 'Connected',
  DEGRADED: 'Degraded',
  RECONNECTING: 'Reconnecting',
  DISCONNECTED: 'Disconnected',
  STALE: 'Stale',
  FROZEN: 'Frame frozen',
  UNKNOWN: 'Unknown',
}

export const VIEWPOINT_LABEL: Record<ViewpointStatus, string> = {
  STABLE: 'Stable',
  SHIFT_DETECTED: 'Shift detected',
  SEVERE_SHIFT: 'Severe shift',
  UNKNOWN: 'Unknown',
}
