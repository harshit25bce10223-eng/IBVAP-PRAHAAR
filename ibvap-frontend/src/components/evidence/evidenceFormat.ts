// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 3 — pure display formatting (no business logic)
// ─────────────────────────────────────────────────────────────────────────────

/** Truncated digest for table rows: first 8 … last 4 (e.g. a3f8c79d…91e2). */
export function truncateHash(hash: string): string {
  if (!hash) return 'HASH NOT AVAILABLE'
  if (hash.length <= 16) return hash
  return `${hash.slice(0, 8)}…${hash.slice(-4)}`
}

/** File-size label. Null → 'N/A' (never zero-filled). */
export function formatBytes(bytes: number | null): string {
  if (bytes === null || bytes === undefined) return 'N/A'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
  return `${(bytes / (1024 * 1024 * 1024)).toFixed(2)} GB`
}

/** Duration label for clips. Null → 'N/A'. */
export function formatDuration(sec: number | null): string {
  if (sec === null || sec === undefined) return 'N/A'
  if (sec < 60) return `${sec} s`
  const m = Math.floor(sec / 60)
  return `${m}m ${sec % 60}s`
}

/** Lowercase enum → 'Title case' for human labels (type/source/role). */
export function humanize(value: string): string {
  return value
    .toLowerCase()
    .split('_')
    .map(w => (w ? w[0].toUpperCase() + w.slice(1) : w))
    .join(' ')
}

/** 1,248-style count. */
export function formatCount(n: number): string {
  return n.toLocaleString('en-IN')
}
