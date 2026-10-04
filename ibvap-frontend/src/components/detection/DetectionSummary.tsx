import { clsx } from 'clsx'
import type { DetectionSummary as DetectionSummaryModel } from '@/types/detection'
import { formatDetectionCount } from './detectionFormat'

interface DetectionSummaryProps {
  summary: DetectionSummaryModel | null
  /** Show a DEMO/SIMULATED provenance tag (from the mock feed). */
  demo?: boolean
  /** Heading override, e.g. 'Page composition' when composing filtered results. */
  title?: string
  /**
   * Honest scope line rendered verbatim under the heading (e.g.
   * 'Page 1 of 3 · 24 matching'). Required when the card composes a filtered
   * page instead of a whole feed so counts are never read as a fleet total.
   */
  scopeNote?: string
  className?: string
}

/**
 * Compact structural summary — counts only, never risk/severity (§116).
 * Total detections, a per-class breakdown, a low-confidence count and a
 * limited/poor-quality count are the extent of what this component reports.
 */
export function DetectionSummary({ summary, demo = false, title = 'Active detections', scopeNote, className }: DetectionSummaryProps) {
  if (!summary) {
    return (
      <div className={clsx('rounded-xl border border-border bg-surface p-4', className)} role="status">
        <p className="text-[11px] text-slate-500">Detection summary unavailable.</p>
      </div>
    )
  }

  const classes: { label: string; value: number }[] = (['PERSON', 'VEHICLE', 'ANIMAL', 'OBJECT', 'UNKNOWN'] as const)
    .map(c => ({ label: c.charAt(0) + c.slice(1).toLowerCase(), value: summary.byClass[c] ?? 0 }))
    .filter(e => e.value > 0)

  // Observation quality is reported with §37 vocabulary — 'Limited / poor
  // quality', never 'false', 'failed' or 'wrong'. A limited observation is a
  // data-quality signal, not a threat judgement.
  const limitedQuality = (summary.qualitySummary.LIMITED ?? 0) + (summary.qualitySummary.POOR ?? 0)

  return (
    <div className={clsx('rounded-xl border border-border bg-surface p-4', className)} aria-label={title}>
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-200">{title}</h3>
        <span className="font-mono text-xs text-slate-400">{formatDetectionCount(summary.total)}</span>
      </div>
      {scopeNote && <p className="mt-0.5 font-mono text-[10px] text-slate-500">{scopeNote}</p>}

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
          {limitedQuality > 0 && (
            <div className="flex items-center justify-between text-[11px] col-span-2">
              <dt className="text-amber-400/90">Limited / poor quality</dt>
              <dd className="font-mono text-amber-300 tabular-nums">{limitedQuality}</dd>
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