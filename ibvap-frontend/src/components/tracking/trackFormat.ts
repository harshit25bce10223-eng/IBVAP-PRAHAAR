// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 6 — pure display formatting for tracks (no logic)
//
// Confidence, quality, source, velocity, duration and geometry formatting only.
// Nothing here interprets a track as risk, identity or threat; a class is
// displayed verbatim and a missing backend value is shown as N/A, never invented.
// ─────────────────────────────────────────────────────────────────────────────

import type { DetectionClass, DetectionQuality, TrackStatus, TrackSource, TrackContinuityQuality } from '@/types/tracking'

const DETECTION_CLASSES: readonly DetectionClass[] = ['PERSON', 'VEHICLE', 'ANIMAL', 'OBJECT', 'UNKNOWN']

/** Class label: 'PERSON' → 'Person', 'UNKNOWN' → 'Unknown'. Null-safe. */
export function formatTrackClassLabel(cls: DetectionClass | null | undefined): string {
  if (!cls || !DETECTION_CLASSES.includes(cls)) return 'Unknown'
  return cls.charAt(0) + cls.slice(1).toLowerCase()
}

/**
 * Confidence as a percent label. Accepts a 0–1 ratio (tracker convention) or
 * a 0–100 value. Human precision only (no 5-decimal noise). Null → 'N/A'.
 */
export function formatConfidence(value: number | null | undefined | false): string {
  if (value === null || value === undefined || value === false) return 'N/A'
  const pct = value <= 1 ? value * 100 : value
  return `${Math.round(pct)}%`
}

/** Confidence as an unambiguous one-line description for screen readers. */
export function describeConfidence(value: number | null | undefined | false): string {
  if (value === null || value === undefined || value === false) return 'confidence not provided'
  const pct = value <= 1 ? value * 100 : value
  return `${Math.round(pct)} percent confidence`
}

/** ISO timestamp → '02:14:11'. Invalid → '—'. */
export function formatClock(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

/** ISO timestamp → '07 Sep'. Invalid → '—'. */
export function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString([], { day: '2-digit', month: 'short' })
}

/** Milliseconds → '18s', '2m 30s', '1h 15m'. */
export function formatDuration(ms: number | null | undefined): string {
  if (ms === null || ms === undefined || !Number.isFinite(ms)) return '—'
  const sec = Math.round(ms / 1000)
  if (sec < 60) return `${sec}s`
  const min = Math.floor(sec / 60)
  const remSec = sec % 60
  if (min < 60) return remSec > 0 ? `${min}m ${remSec}s` : `${min}m`
  const hr = Math.floor(min / 60)
  const remMin = min % 60
  return remMin > 0 ? `${hr}h ${remMin}m` : `${hr}h`
}

/** Speed in m/s → '1.4 m/s'. Null → 'N/A'. */
export function formatSpeed(ms: number | null | undefined): string {
  if (ms === null || ms === undefined || !Number.isFinite(ms)) return 'N/A'
  return `${ms.toFixed(1)} m/s`
}

/** Velocity with units (m/s) and direction: '1.4 m/s NE'. */
export function formatVelocity(velocity: number | null | undefined, direction: string | null | undefined): string {
  const speedStr = formatSpeed(velocity)
  if (direction) return `${speedStr} ${direction}`
  return speedStr
}

/** Generic count: '9 observations'. */
export function formatObservationCount(n: number): string {
  return `${n} observation${n === 1 ? '' : 's'}`
}

/** Bounding box as compact technical text — used only in the Inspector. */
export function formatBBox(x: number | null | undefined, y: number | null | undefined, width: number | null | undefined, height: number | null | undefined): string {
  const parts = [x, y, width, height]
  if (parts.some(p => p === null || p === undefined)) return 'N/A'
  return [x, y, width, height].map(p => (p as number).toFixed(3)).join(' · ')
}

/** Source label for visibility/context fields. */
export function formatSourceLabel(source: TrackSource | null | undefined): string {
  if (!source || source === 'UNKNOWN') return 'Unknown'
  return source.charAt(0) + source.slice(1).toLowerCase()
}

/** Track status as display label. */
export function formatTrackStatus(status: TrackStatus | null | undefined): string {
  if (!status) return 'Unknown'
  const labels: Record<TrackStatus, string> = {
    ACTIVE: 'Active',
    TENTATIVE: 'Tentative',
    LOST: 'Lost',
    REACQUIRED: 'Reacquired',
    ENDED: 'Ended',
    STALE: 'Stale',
    INVALID: 'Invalid',
    UNKNOWN: 'Unknown',
  }
  return labels[status] ?? status
}

/** Continuity quality as display label. */
export function formatContinuityQuality(quality: TrackContinuityQuality | null | undefined): string {
  if (!quality || quality === 'UNKNOWN') return 'Unknown'
  return quality.charAt(0) + quality.slice(1).toLowerCase()
}

/** Screen-reader-friendly track description (used by the overlay). */
export function describeTrack(
  trackId: string,
  cls: DetectionClass,
  status: TrackStatus,
  confidence: number | null,
  cameraId: string,
  timeIso: string
): string {
  return `Track ${trackId}, ${formatTrackClassLabel(cls)}, ${formatTrackStatus(status).toLowerCase()}, ${describeConfidence(confidence)}, camera ${cameraId}, ${formatClock(timeIso)}.`
}