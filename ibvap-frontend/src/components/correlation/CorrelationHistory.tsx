import { clsx } from 'clsx'
import { formatClock, formatDate } from './correlationFormat'
import { CORRELATION_LABEL, toneForCorrelation, TONE } from './correlationTone'
import type { CorrelationGroup } from '@/types/eventCorrelation'

/**
 * Correlation history (§45/§136–137). Preserves revisions — a DISSOLVED group
 * keeps its previous RELATED/CORRELATED states visible instead of silently
 * erasing them. Prepares for streaming systems where relationships change.
 */
export function CorrelationHistory({ group }: { group: CorrelationGroup }) {
  const transitions = [...group.history.transitions]
  return (
    <section className="rounded-xl border border-border bg-surface p-4" aria-label="Correlation history">
      <h3 className="text-sm font-semibold text-slate-200">Correlation history</h3>
      <p className="mt-0.5 font-mono text-[10px] text-slate-500">
        created {formatDate(group.history.createdAt)} {formatClock(group.history.createdAt)} · updated {formatClock(group.history.updatedAt)}
      </p>
      {transitions.length === 0 ? (
        <p className="mt-2 text-[11px] text-slate-500">No state transitions recorded.</p>
      ) : (
        <ol className="mt-2 space-y-2">
          {transitions.map((t, i) => {
            const isLast = i === transitions.length - 1
            const tone = toneForCorrelation(t.status)
            return (
              <li key={`${t.status}-${t.at}`} className="flex gap-3">
                <div className="flex flex-col items-center">
                  <span className={clsx('mt-1 h-2 w-2 rounded-full', TONE[tone].dot)} aria-hidden />
                  {!isLast && <span className="w-px flex-1 bg-border" aria-hidden />}
                </div>
                <div className="pb-2">
                  <p className={clsx('font-mono text-[11px] font-semibold uppercase tracking-wider', TONE[tone].text)}>
                    {CORRELATION_LABEL[t.status]}
                  </p>
                  <p className="font-mono text-[10px] text-slate-500">{formatClock(t.at)}</p>
                  {t.note && <p className="mt-1 text-[11px] text-slate-400">{t.note}</p>}
                </div>
              </li>
            )
          })}
        </ol>
      )}
    </section>
  )
}