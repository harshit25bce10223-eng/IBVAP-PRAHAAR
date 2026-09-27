import { clsx } from 'clsx'
import { CORRELATION_BLURB, CORRELATION_LABEL, toneForCorrelation, TONE } from './correlationTone'
import type { CorrelationGroup } from '@/types/eventCorrelation'

/**
 * Uncertainty panel (§39/§70/§179). Correlation and reliability uncertainty are
 * always visible — never hidden because the dashboard would look less tidy.
 */
export function CorrelationUncertainty({ group }: { group: CorrelationGroup }) {
  const tone = toneForCorrelation(group.status)
  return (
    <section className="rounded-xl border border-[#1e2d40] bg-[#0d1117] p-4" aria-label="Relationship uncertainty">
      <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-200">
        <span className={clsx('h-2 w-2 rounded-full', TONE[tone].dot)} aria-hidden />
        Relationship uncertainty
      </h3>
      <div className="mt-2 space-y-1.5">
        <div className="flex items-center justify-between text-xs">
          <dt className="text-slate-500">Correlation state</dt>
          <dd className={clsx('font-mono text-xs font-medium', TONE[tone].text)}>
            {CORRELATION_LABEL[group.status]}
          </dd>
        </div>
        <div className="flex items-center justify-between text-xs">
          <dt className="text-slate-500">Reliability</dt>
          <dd className={clsx('font-mono text-xs', reliabilityTone(group.uncertainty.reliability))}>
            {group.uncertainty.reliability}
          </dd>
        </div>
      </div>
      {group.uncertainty.note && (
        <p className="mt-2 rounded-md border border-white/5 bg-white/[0.03] px-2 py-1.5 text-[11px] text-slate-400">
          {group.uncertainty.note}
        </p>
      )}
      <p className="mt-2 text-[10px] text-slate-600">{CORRELATION_BLURB[group.status]}</p>
    </section>
  )
}

function reliabilityTone(r: CorrelationGroup['uncertainty']['reliability']): string {
  switch (r) {
    case 'HIGH': return 'text-prhaar-good'
    case 'MEDIUM': return 'text-prhaar-degraded'
    case 'LOW': return 'text-prhaar-failed'
    default: return 'text-slate-400'
  }
}