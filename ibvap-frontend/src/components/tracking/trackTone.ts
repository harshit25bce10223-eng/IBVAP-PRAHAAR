// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 6 — track tone/color mapping
//
// Track colors must NOT represent risk severity (§41, §121).
// Neutral tones by class; status tones for state badges only.
// ─────────────────────────────────────────────────────────────────────────────

import type { DetectionClass, TrackStatus, TrackContinuityQuality, TrackSource, TrackingFeedState } from '@/types/tracking'
import type { DetectionQuality } from '@/types/detection'

/** Neutral class stroke colors for track overlays. A class is an observation, never a severity (§41). */
export const TRACK_CLASS_STROKE: Record<DetectionClass, string> = {
  PERSON: '#22d3ee',    // sky/cyan
  VEHICLE: '#f59e0b',   // amber
  ANIMAL: '#34d399',    // emerald
  OBJECT: '#94a3b8',    // slate
  UNKNOWN: '#a855f7',   // purple
}

/** Compact class chip labels: PE / VE / AN / OB / UK. */
export const TRACK_CLASS_CHIP: Record<DetectionClass, string> = {
  PERSON: 'PE',
  VEHICLE: 'VE',
  ANIMAL: 'AN',
  OBJECT: 'OB',
  UNKNOWN: 'UK',
}

/** Track status → semantic tone for badges/dots. */
export type TrackTone = 'info' | 'warning' | 'critical' | 'default' | 'cyan' | 'emerald' | 'amber'

export const STATUS_TONE: Record<TrackStatus, TrackTone> = {
  ACTIVE: 'cyan',
  TENTATIVE: 'warning',
  LOST: 'warning',
  REACQUIRED: 'info',
  ENDED: 'default',
  STALE: 'default',
  INVALID: 'critical',
  UNKNOWN: 'default',
}

export const QUALITY_TONE: Record<TrackContinuityQuality, TrackTone> = {
  STRONG: 'cyan',
  MODERATE: 'warning',
  WEAK: 'critical',
  UNKNOWN: 'default',
}

export const FEED_STATE_TONE: Record<TrackingFeedState, TrackTone> = {
  READY: 'cyan',
  PROCESSING: 'cyan',
  DEGRADED: 'warning',
  UNAVAILABLE: 'critical',
  STALE: 'warning',
  OFFLINE: 'critical',
  UNKNOWN: 'default',
}

export const SOURCE_TONE: Record<TrackSource, TrackTone> = {
  LIVE: 'cyan',
  EDGE: 'emerald',
  CENTRAL: 'cyan',
  DEMO: 'amber',
  UNKNOWN: 'default',
}

export function toneForStatus(status: TrackStatus): TrackTone {
  return STATUS_TONE[status] ?? 'default'
}

export function toneForQuality(quality: TrackContinuityQuality): TrackTone {
  return QUALITY_TONE[quality] ?? 'default'
}

export function toneForFeedState(state: TrackingFeedState): TrackTone {
  return FEED_STATE_TONE[state] ?? 'default'
}

export function toneForSource(source: TrackSource): TrackTone {
  return SOURCE_TONE[source] ?? 'default'
}

/** Dot color helper for status indicators. */
export function dotTone(tone: TrackTone): string {
  const colors: Record<TrackTone, string> = {
    info: 'bg-sky-400',
    warning: 'bg-amber-400',
    critical: 'bg-red-400',
    default: 'bg-slate-500',
    cyan: 'bg-cyan-400',
    emerald: 'bg-emerald-400',
    amber: 'bg-amber-400',
  }
  return colors[tone] ?? 'bg-slate-500'
}

/** Text color helper for status labels. */
export function textTone(tone: TrackTone): string {
  const colors: Record<TrackTone, string> = {
    info: 'text-sky-400',
    warning: 'text-amber-400',
    critical: 'text-red-400',
    default: 'text-slate-400',
    cyan: 'text-cyan-400',
    emerald: 'text-emerald-400',
    amber: 'text-amber-400',
  }
  return colors[tone] ?? 'text-slate-400'
}

/** Badge variant helper for UI Badge component — maps TrackTone to valid BadgeVariant. */
export function badgeTone(tone: TrackTone): 'info' | 'warning' | 'critical' | 'default' | 'cyan' | 'safe' | 'offline' {
  // Map TrackTone to valid BadgeVariant
  switch (tone) {
    case 'emerald':
      return 'safe'
    case 'amber':
      return 'warning'
    case 'info':
      return 'info'
    case 'warning':
      return 'warning'
    case 'critical':
      return 'critical'
    case 'cyan':
      return 'cyan'
    case 'default':
    default:
      return 'default'
  }
}