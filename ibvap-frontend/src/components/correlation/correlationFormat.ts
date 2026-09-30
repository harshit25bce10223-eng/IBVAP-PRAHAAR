// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 4 — pure display formatting (no business logic)
//
// Durations, ranges and labels only. Correlation/risk/severity interpretation
// always comes from the backend record; nothing here groups or scores.
// ─────────────────────────────────────────────────────────────────────────────

/** Clock label (HH:MM:SS) for an ISO timestamp. Invalid → '—'. */
export function formatClock(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

/** Short clock (HH:MM) for the dashboard feed. */
export function formatClockShort(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit' })
}

/** Date label (e.g. '07 Sep') for detail headers. Invalid → '—'. */
export function formatDate(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleDateString([], { day: '2-digit', month: 'short' })
}

/** Whole seconds between two ISO timestamps. Invalid → null. */
export function diffSec(fromIso: string, toIso: string): number | null {
  const a = new Date(fromIso).getTime()
  const b = new Date(toIso).getTime()
  if (Number.isNaN(a) || Number.isNaN(b)) return null
  return Math.max(0, Math.round((b - a) / 1000))
}

/** Duration label from a seconds value. Null → '—'. */
export function formatSec(sec: number | null | undefined): string {
  if (sec === null || sec === undefined) return '—'
  if (sec < 60) return `${sec} sec`
  const m = Math.floor(sec / 60)
  const s = sec % 60
  return s === 0 ? `${m}m` : `${m}m ${s}s`
}

/**
 * Window label for a group: '02:14:11 – 02:14:43 · 32 sec'.
 * Null end → single time. Never infers an instant from demo data.
 */
export function formatWindow(startedAt: string, endedAt: string | null): string {
  const start = formatClock(startedAt)
  if (!endedAt) return start
  const end = formatClock(endedAt)
  const sec = diffSec(startedAt, endedAt)
  return `${start} – ${end}${sec !== null ? ` · ${formatSec(sec)}` : ''}`
}

/** Count label: '5 signals' / '1 signal' (never fabricated zeros). */
export function formatSignalCount(n: number): string {
  return `${n} signal${n === 1 ? '' : 's'}`
}

/** Count label: '2 cameras' / '1 camera'. */
export function formatCameraCount(n: number): string {
  return `${n} camera${n === 1 ? '' : 's'}`
}

/** Count label for grouped rows in the log: '8 groups' / '1 group'. */
export function formatGroupCount(n: number): string {
  return `${n} group${n === 1 ? '' : 's'}`
}

/** Camera list label from a camera chain or member cameras. */
export function formatCameraList(chain: string[] | null, memberCameras: string[]): string {
  const list = chain && chain.length > 0 ? chain : memberCameras
  const unique = [...new Set(list)]
  return unique.length === 0 ? 'CAMERA UNKNOWN' : unique.join(' / ')
}

/**
 * Confidence is only displayed when the backend supplies it (§95). Accepts
 * either a 0–1 ratio (member/track confidence) or a 0–100 value (group
 * confidence) — a pure unit conversion, never a computed score.
 */
export function formatConfidence(value: number): string {
  const pct = value <= 1 ? value * 100 : value
  return `${Math.round(pct)}%`
}

/** Modality list — e.g. 'VIDEO · ANPR · AUDIO'. */
export function formatModalities(modalities: string[]): string {
  return modalities.length === 0 ? '—' : modalities.join(' · ')
}

/**
 * Chronological comparator on event observed time (§60). Ties are broken by
 * eventId so the visual timeline never depends on array or insertion order.
 * Unparseable timestamps sort last rather than silently landing anywhere.
 */
export function compareByObservedTime(
  a: { timestamp: string; eventId: string },
  b: { timestamp: string; eventId: string }
): number {
  const ta = new Date(a.timestamp).getTime()
  const tb = new Date(b.timestamp).getTime()
  const aInvalid = Number.isNaN(ta)
  const bInvalid = Number.isNaN(tb)
  if (aInvalid !== bInvalid) return aInvalid ? 1 : -1
  if (!aInvalid && ta !== tb) return ta - tb
  return a.eventId.localeCompare(b.eventId)
}