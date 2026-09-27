// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 5 — detection color tones (restrained, PRHAAR-native)
//
// Class colors are deliberately NEUTRAL and slightly desaturated: a class is an
// observation, never a severity. Emphasis (cyan accent) is reserved for the
// selected box and feed readiness; warn tones are reserved for low-confidence /
// stale / unavailable states — LOW_CONFIDENCE is a subtle warning, never a
// critical incident.
// ─────────────────────────────────────────────────────────────────────────────

import type { DetectionClass, DetectionFeedState, DetectionQuality, DetectionState } from '@/types/detection'

/**
 * Class → neutral stroke color. All tonally similar; distinct enough to tell
 * PERSON from ANIMAL at a glance without implying threat (Component spec
 * §180: ANIMAL must stay visually distinct from PERSON without threat color).
 */
export const CLASS_STROKE: Record<DetectionClass, string> = {
  PERSON: '#7fb2d0',
  VEHICLE: '#c9b27a',
  ANIMAL: '#8fc49b',
  OBJECT: '#aab4c4',
  UNKNOWN: '#b8a6c9',
}

/** Class short label on the overlay chip. */
export const CLASS_CHIP: Record<DetectionClass, string> = {
  PERSON: 'PE',
  VEHICLE: 'VE',
  ANIMAL: 'AN',
  OBJECT: 'OB',
  UNKNOWN: 'UK',
}

export type DetectionTone = 'accent' | 'info' | 'warning' | 'critical' | 'neutral' | 'danger'

const TONE_TEXT: Record<DetectionTone, string> = {
  accent: 'text-cyan-400',
  info: 'text-sky-400',
  warning: 'text-amber-400',
  critical: 'text-amber-400',
  neutral: 'text-slate-400',
  danger: 'text-red-400',
}

const TONE_DOT: Record<DetectionTone, string> = {
  accent: 'bg-cyan-400',
  info: 'bg-sky-400',
  warning: 'bg-amber-400',
  critical: 'bg-amber-400',
  neutral: 'bg-slate-400',
  danger: 'bg-red-400',
}

const TONE_BADGE: Record<DetectionTone, 'info' | 'warning' | 'offline' | 'cyan' | 'critical' | 'default'> = {
  accent: 'cyan',
  info: 'info',
  warning: 'warning',
  critical: 'warning',
  neutral: 'default',
  danger: 'critical',
}

/** Expects a Badge variant (as used by <Badge>). */
export function badgeTone(tone: DetectionTone): 'info' | 'warning' | 'offline' | 'cyan' | 'critical' | 'default' {
  return TONE_BADGE[tone]
}

export function textTone(tone: DetectionTone): string {
  return TONE_TEXT[tone]
}

export function dotTone(tone: DetectionTone): string {
  return TONE_DOT[tone]
}

/**
 * Feed availability tone.
 * READY itself is accent (not "warning"); NO_OBJECTS is neutral info;
 * UNAVAILABLE/OFFLINE are danger; STALE is a warning (data delayed, not dead).
 */
export function toneForFeedState(state: DetectionFeedState): DetectionTone {
  switch (state) {
    case 'READY':
      return 'accent'
    case 'NO_OBJECTS':
      return 'info'
    case 'UNCONFIGURED':
    case 'STALE':
      return 'warning'
    case 'UNAVAILABLE':
    case 'OFFLINE':
      return 'danger'
    default:
      return 'neutral'
  }
}

/**
 * Single-box state tone. LOW_CONFIDENCE and OCCLUDED are subtle warnings —
 * never critical. INVALID is the only state that claims the box is unusable.
 */
export function toneForDetectionState(state: DetectionState): DetectionTone {
  switch (state) {
    case 'DETECTED':
      return 'accent'
    case 'LOW_CONFIDENCE':
    case 'PARTIAL':
    case 'OCCLUDED':
      return 'warning'
    case 'INVALID':
      return 'danger'
    case 'UNKNOWN':
    default:
      return 'neutral'
  }
}

/** Quality tone: poor → danger, limited → warning, good → info, unknown → neutral. */
export function toneForQuality(q: DetectionQuality): DetectionTone {
  switch (q) {
    case 'GOOD':
      return 'info'
    case 'LIMITED':
      return 'warning'
    case 'POOR':
      return 'danger'
    default:
      return 'neutral'
  }
}