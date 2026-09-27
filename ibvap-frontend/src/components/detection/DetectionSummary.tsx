import { clsx } from 'clsx'
import type { DetectionSummary as DetectionSummaryModel } from '@/types/detection'
import { formatDetectionCount } from './detectionFormat'

interface DetectionSummaryProps {
  summary: DetectionSummaryModel | null
  /** Show a DEMO/SIMULATED provenance tag (from the mock feed). */
  demo?: boolean
  className?: string
}

/**
 * Compact structural summary — counts only, never risk/severity (§116).
 * Total detections, a per-class breakdown, and a low-confidence count are the
 * extent of what this component reports.
 */
export function DetectionSummary({ summary, demo = false, className }: DetectionSummaryProps) {
  if (!summary) {
    return (
      <div className={clsx('rounded-xl border border-[#1e2d40] bg-[#0d1117] p-4', className)} role="status">
        <p className="text-[11px] text-slate-500">Detection summary unavailable.</p>
      </div>
    )
  }

  const classes: { label: string; value: number }[] = (['PERSON', 'VEHICLE', 'ANIMAL', 'OBJECT', 'UNKNOWN'] as const)
    .map(c => ({ label: c.charAt(0) + c.slice(1).toLowerCase(), value: summary.byClass[c] ?? 0 }))
    .filter(e => e.value > 0)

  return (
    <div className={clsx('rounded-xl border border-[#1e2d40] bg-[#0d1117] p-4', className)} aria-label="Active detections summary">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-200">Active detections</h3>
        <span className="font-mono text-xs text-slate-400">{formatDetectionCount(summary.total)}</span>
      </div>

      {summary.total === 0 ? (
        <p className="mt-2 text-[11px] text-slate-500">No objects detected in the current frame.</p>
      ) : (
        <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1.5">
          {classes.map(e => (
            <div key={e.label} className="flex items-center justify-between text-[11px]">
              <dt className="text-slate-500">{e.label}</dt>
              <dd className="font-mono text-slate-200 tabular-nums">{e.value}</dd>
            </div>
          ))}
          {summary.lowConfidenceCount > 0 && (
            <div className="flex items-center justify-between text-[11px] col-span-2">
              <dt className="text-amber-400/90">Low confidence</dt>
              <dd className="font-mono text-amber-300 tabular-nums">{summary.lowConfidenceCount}</dd>
            </div>
          )}
        </dl>
      )}

      {demo && (
        <p className="mt-3 flex items-center gap-1.5 font-mono text-[9px] uppercase tracking-wider text-slate-500">
          <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" aria-hidden />
          Demo / simulated detections
        </p>
      )}
    </div>
  )
}