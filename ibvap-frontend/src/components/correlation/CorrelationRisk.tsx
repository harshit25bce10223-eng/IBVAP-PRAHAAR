import { SeverityBadge } from '@/components/risk/SeverityBadge'
import type { CorrelationRisk } from '@/types/eventCorrelation'

/**
 * Risk block — renders Component 1 backend output verbatim. The frontend
 * never computes the score, frame plays no part, and correlation cannot
 * change the number (§41/§129).
 */
export function CorrelationRisk({ risk }: { risk: CorrelationRisk }) {
  const referenced = risk.incidentIds
  const referenceLine = referenced.length > 0 && (
    <p className="mt-1 text-[10px] text-slate-500">
      Referenced incident{referenced.length === 1 ? '' : 's'}:{' '}
      <span className="font-mono">{referenced.join(', ')}</span>
    </p>
  )

  if (risk.score === null || risk.severity === null) {
    return (
      <section className="rounded-xl border border-[#1e2d40] bg-[#0d1117] p-4" aria-label="Risk assessment">
        <h3 className="text-sm font-semibold text-slate-200">Risk assessment</h3>
        <p className="mt-2 text-[11px] text-slate-500">No risk evaluation for this group yet.</p>
        {referenceLine}
      </section>
    )
  }
  return (
    <section className="rounded-xl border border-[#1e2d40] bg-[#0d1117] p-4" aria-label="Risk assessment">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-200">Risk assessment</h3>
        <SeverityBadge severity={risk.severity} score={risk.score} />
      </div>
      <p className="mt-2 text-[10px] text-slate-500">
        Scored by the Component 1 Risk Engine on the combined event.
      </p>
      {referenceLine}
    </section>
  )
}