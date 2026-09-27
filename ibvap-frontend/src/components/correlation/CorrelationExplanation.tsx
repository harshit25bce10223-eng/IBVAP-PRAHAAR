import { clsx } from 'clsx'
import { CORRELATION_BLURB, toneForCorrelation, TONE } from './correlationTone'
import type { CorrelationExplanation, CorrelationGroup } from '@/types/eventCorrelation'

const FACET_LABEL: Record<CorrelationExplanation['facet'], string> = {
  TEMPORAL: 'Temporal',
  SPATIAL: 'Spatial',
  ENTITY: 'Entity',
  SEQUENCE: 'Sequence',
  CAMERA: 'Camera',
  ZONE: 'Zone',
  CONTEXTUAL: 'Context',
}

/**
 * Structured "why" panel (§96–97). Never a single paragraph: each facet is a
 * scannable row. Heading reflects the state — related, uncertain, or not
 * related — and never claims causality (§81).
 */
export function CorrelationExplanation({ group }: { group: CorrelationGroup }) {
  const tone = toneForCorrelation(group.status)
  const heading =
    group.status === 'UNCERTAIN'
      ? 'Why uncertain'
      : group.status === 'DISSOLVED'
        ? 'Why not sustained'
        : group.status === 'STANDALONE'
          ? 'Why not related'
          : 'Why related'

  const fallback: CorrelationExplanation[] =
    group.status === 'STANDALONE'
      ? [{ facet: 'CONTEXTUAL', label: 'no support', detail: 'No sufficient relationship evidence.' }]
      : group.status === 'UNCERTAIN'
        ? [{ facet: 'CONTEXTUAL', label: 'partial', detail: CORRELATION_BLURB.UNCERTAIN }]
        : [{ facet: 'CONTEXTUAL', label: 'sustained', detail: CORRELATION_BLURB.CORRELATED }]

  const facets = group.explanation.length > 0 ? group.explanation : fallback

  return (
    <section className="rounded-xl border border-[#1e2d40] bg-[#0d1117] p-4" aria-label={heading}>
      <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-200">
        <span className={clsx('h-2 w-2 rounded-full', TONE[tone].dot)} aria-hidden />
        {heading}
      </h3>
      <dl className="mt-3 space-y-2">
        {facets.map((f, i) => (
          <div key={`${f.facet}-${i}`} className="grid grid-cols-[4.5rem_1fr] gap-2 items-baseline">
            <dt className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
              {FACET_LABEL[f.facet]}
            </dt>
            <dd className="text-xs text-slate-300">
              <span className="font-medium">{f.label}</span>
              {f.detail && <span className="text-slate-500"> — {f.detail}</span>}
            </dd>
          </div>
        ))}
      </dl>
    </section>
  )
}