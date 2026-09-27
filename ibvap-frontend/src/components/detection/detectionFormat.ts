// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 5 — pure display formatting for detections (no logic)
//
// Confidence, quality, source and geometry formatting only. Nothing here
// interprets a detection as risk, identity or threat; a class is displayed
// verbatim and a missing backend value is shown as N/A, never invented.
// ─────────────────────────────────────────────────────────────────────────────

import type { DetectionClass, DetectionSource } from '@/types/detection'
import { DETECTION_CLASSES } from '@/types/detection'

/** Class label: 'PERSON' → 'Person', 'UNKNOWN' → 'Unknown'. Null-safe. */
export function formatClassLabel(cls: DetectionClass | null | undefined): string {
  if (!cls || !DETECTION_CLASSES.includes(cls)) return 'Unknown'
  return cls.charAt(0) + cls.slice(1).toLowerCase()
}

/**
 * Confidence as a percent label. Accepts a 0–1 ratio (detector convention) or
 * a 0–100 value, matching the correlation formatter's tolerance. Human
 * precision only (no 5-decimal noise). Null → 'N/A'.
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

/** Generic count: '3 detections' / '1 detection'. */
export function formatDetectionCount(n: number): string {
  return `${n} detection${n === 1 ? '' : 's'}`
}

/** Bounding box as compact technical text — used only in the Inspector. */
export function formatBBox(x: number | null | undefined, y: number | null | undefined, width: number | null | undefined, height: number | null | undefined): string {
  const parts = [x, y, width, height]
  if (parts.some(p => p === null || p === undefined)) return 'N/A'
  return [x, y, width, height].map(p => (p as number).toFixed(3)).join(' · ')
}

/** Frame identity label: '# 1,284,221 · 25 fps'. Missing parts are omitted. */
export function formatFrameInfo(frameNumber: number | null | undefined, fps: number | null | undefined): string {
  const parts: string[] = []
  if (frameNumber !== null && frameNumber !== undefined) {
    parts.push(`# ${frameNumber.toLocaleString('en-US')}`)
  }
  if (fps !== null && fps !== undefined) {
    parts.push(`${fps} fps`)
  }
  return parts.join(' · ') || 'Frame data N/A'
}

/** Source label for visibility/context fields. */
export function formatSourceLabel(source: DetectionSource | null | undefined): string {
  if (!source || source === 'UNKNOWN') return 'Unknown'
  return source.charAt(0) + source.slice(1).toLowerCase()
}

/** Screen-reader-friendly detection description (used by the overlay). */
export function describeDetection(cls: DetectionClass, confidence: number | null, cameraId: string, timeIso: string): string {
  return `${formatClassLabel(cls)} detection, ${describeConfidence(confidence)}, camera ${cameraId}, ${formatClock(timeIso)}.`
}