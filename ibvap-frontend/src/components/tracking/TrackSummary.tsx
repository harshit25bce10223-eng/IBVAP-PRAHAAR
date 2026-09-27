// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 6 — compact structural track summary (§128, §185, §186).
//
// Total active tracks, a per-class breakdown, and a per-status breakdown are
// the extent of what this component reports. Never risk/severity/threat counts.
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'
import type { TrackSummary } from '@/types/tracking'
import { formatTrackClassLabel, formatTrackStatus } from './trackFormat'
import { TRACK_STATUSES } from '@/types/tracking'

interface TrackSummaryProps {
  summary: TrackSummary | null
  /** Show a DEMO/SIMULATED provenance tag (from the mock feed). */
  demo?: boolean
  className?: string
}

/**
 * Compact structural summary — counts only, never risk/severity (§128, §185).
 * Active tracks, per-class breakdown, and per-status breakdown.
 */
export function TrackSummary({ summary, demo = false, className }: TrackSummaryProps) {
  if (!summary) {
    return (
      <div className={clsx('rounded-xl border border-[#1e2d40] bg-[#0d1117] p-4', className)} role="status">
        <p className="text-[11px] text-slate-500">Track summary unavailable.</p>
      </div>
    )
  }

  const classEntries: { label: string; value: number }[] = (['PERSON', 'VEHICLE', 'ANIMAL', 'OBJECT', 'UNKNOWN'] as const)
    .map(c => ({ label: formatTrackClassLabel(c), value: summary.byClass[c] ?? 0 }))
    .filter(e => e.value > 0)

  const statusEntries = TRACK_STATUSES
    .filter(s => (summary.byStatus[s] ?? 0) > 0)
    .map(s => ({ label: formatTrackStatus(s), value: summary.byStatus[s] ?? 0 }))

  return (
    <div className={clsx('rounded-xl border border-[#1e2d40] bg-[#0d1117] p-4', className)} aria-label="Active tracks summary">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-200">Active Tracks</h3>
        <span className="font-mono text-xs text-slate-400">{summary.totalActive}</span>
      </div>

      {summary.totalTracks === 0 ? (
        <p className="mt-2 text-[11px] text-slate-500">No active tracks in the current frame.</p>
      ) : (
        <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1.5">
          {classEntries.map(e => (
            <div key={e.label} className="flex items-center justify-between text-[11px]">
              <dt className="text-slate-500">{e.label}</dt>
              <dd className="font-mono text-slate-200 tabular-nums">{e.value}</dd>
            </div>
          ))}
          {statusEntries.map(e => (
            <div key={e.label} className="flex items-center justify-between text-[11px]">
              <dt className="text-slate-500">{e.label}</dt>
              <dd className="font-mono text-slate-200 tabular-nums">{e.value}</dd>
            </div>
          ))}
        </dl>
      )}

      {demo && (
        <p className="mt-3 flex items-center gap-1.5 font-mono text-[9px] uppercase tracking-wider text-slate-500">
          <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" aria-hidden />
          Demo / simulated tracks
        </p>
      )}
    </div>
  )
}