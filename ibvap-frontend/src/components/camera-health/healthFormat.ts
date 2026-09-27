// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 2 — pure display formatting (no business logic)
//
// Durations and ages only. Status interpretation always comes from the
// backend record; nothing here classifies health.
// ─────────────────────────────────────────────────────────────────────────────

/** Whole seconds between `fromMs` and `nowMs` (never negative). */
export function ageSec(fromMs: number, nowMs: number): number {
  return Math.max(0, Math.round((nowMs - fromMs) / 1000))
}

/** Operator age label for telemetry timestamps. Null input → 'Unknown'. */
export function formatAge(iso: string | null, nowMs: number): string {
  if (!iso) return 'Unknown'
  const ms = new Date(iso).getTime()
  if (Number.isNaN(ms)) return 'Unknown'
  const s = ageSec(ms, nowMs)
  if (s < 5) return 'just now'
  if (s < 60) return `${s} sec ago`
  const m = Math.floor(s / 60)
  if (m < 60) return `${m} min ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ${m % 60}m ago`
  return new Date(ms).toLocaleDateString([], { day: '2-digit', month: 'short' })
}

/** Clock label (HH:MM:SS) for an ISO timestamp. Invalid → '—'. */
export function formatClock(iso: string | null): string {
  if (!iso) return '—'
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return '—'
  return d.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
}

/** Metric value rendering. Null/undefined → 'N/A' (never zero). */
export function formatMetricValue(value: number | string | null | undefined, unit: string | null): string {
  if (value === null || value === undefined) return 'N/A'
  if (typeof value === 'string') return value
  if (unit === '%') return `${round1(value)}%`
  if (unit === 'ratio') return value.toFixed(2)
  if (unit === 'ms') return `${Math.round(value)} ms`
  if (unit === 'fps') return `${round1(value)} fps`
  return String(value)
}

function round1(n: number): string {
  return (Math.round(n * 10) / 10).toString()
}
