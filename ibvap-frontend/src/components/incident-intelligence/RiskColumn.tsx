// ─────────────────────────────────────────────────────────────────────────────
// RiskColumn — explainable risk (Incident Intelligence, centre).
//
// Shows WHY the incident reached its score: factor contribution bars, the
// project-wide band brackets (82 ⇒ HIGH, never CRITICAL), decision-support
// framing and human-in-the-loop review. No black-box explanation.
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'
import { RISK_BAND_STYLE } from '@/types/commandDashboard'
import type { IncidentIntelligenceData, RiskContributionTone } from '@/types'

interface Props {
  data: IncidentIntelligenceData
  className?: string
}

const TONE_COLOR: Record<RiskContributionTone, string> = {
  critical: '#D62828',
  warning: '#F4B942',
  info: '#22D3EE',
  safe: '#0B5D3B',
}

export function RiskColumn({ data, className }: Props) {
  const total = data.riskFactors.reduce((sum, f) => sum + f.points, 0)
  const style = RISK_BAND_STYLE[data.band]

  return (
    <div className={clsx('flex h-full min-h-0 flex-col rounded-md border border-ssb-border/70 bg-ssb-navy/60 p-3', className)}>
      <div className="flex items-start justify-between gap-2 flex-shrink-0">
        <div>
          <h2 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-ssb-white">
            Explainable Risk
          </h2>
          <p className="text-[9.5px] text-ssb-text-muted mt-0.5">
            Controllable factor contributions for {data.incidentId}
          </p>
        </div>
        <div className="text-right flex-shrink-0">
          <div className="flex items-baseline gap-1">
            <span className={clsx('text-2xl font-mono font-bold leading-none', style.text)}>{data.riskScore}</span>
            <span className="text-[10px] font-mono text-ssb-text-muted">/ 100</span>
          </div>
          <span className={clsx('mt-1 inline-block rounded px-1.5 py-0.5 text-[9px] font-bold tracking-wider', style.text, 'bg-ssb-navy-deep/60 border border-ssb-border/60')}>
            {data.band}
          </span>
        </div>
      </div>

      {/* Factor contribution bars */}
      <div className="mt-3 flex-1 min-h-0 flex flex-col gap-1.5">
        {data.riskFactors.map(factor => {
          const pct = Math.round((factor.points / total) * 100)
          return (
            <div key={factor.label} className="flex items-center gap-2">
              <span className="w-[150px] flex-shrink-0 text-right text-[10px] text-ssb-text">
                {factor.label}
              </span>
              <div className="h-2 flex-1 min-w-0 overflow-hidden rounded-sm bg-ssb-navy-deep/70 border border-ssb-border/40">
                <div
                  className="h-full rounded-sm"
                  style={{ width: `${pct}%`, backgroundColor: TONE_COLOR[factor.tone] }}
                />
              </div>
              <span
                className="w-9 flex-shrink-0 text-right text-[10px] font-mono font-semibold"
                style={{ color: TONE_COLOR[factor.tone] }}
              >
                +{factor.points}
              </span>
            </div>
          )
        })}

        {/* Total */}
        <div className="mt-1.5 flex items-center gap-2 border-t border-ssb-border/60 pt-1.5">
          <span className="w-[150px] flex-shrink-0 text-right text-[10px] font-semibold uppercase tracking-wider text-ssb-text-muted">
            Total
          </span>
          <div className="h-2 flex-1 min-w-0 overflow-hidden rounded-sm bg-ssb-navy-deep/70">
            <div className="h-full rounded-sm bg-ssb-red-bright/80" style={{ width: `${Math.round((total / 100) * 100)}%` }} />
          </div>
          <span className="w-9 flex-shrink-0 text-right text-[10px] font-mono font-bold text-ssb-white">
            {total}
          </span>
        </div>
      </div>

      {/* Band brackets */}
      <div className="mt-3 grid grid-cols-4 gap-1 flex-shrink-0">
        {data.bandBrackets.map(bracket => {
          const active = bracket.label === data.band
          return (
            <div
              key={bracket.label}
              className={clsx(
                'rounded border px-1.5 py-1 text-center',
                active ? 'border-ssb-amber-bright/70 bg-ssb-amber/15' : 'border-ssb-border/50 bg-ssb-navy-deep/40'
              )}
            >
              <span className={clsx('block text-[9px] font-bold tracking-wider', active ? 'text-ssb-amber-bright' : 'text-ssb-text-muted')}>
                {bracket.label}
              </span>
              <span className="block text-[8px] font-mono text-ssb-text-muted/70">{bracket.range}</span>
            </div>
          )
        })}
      </div>

      <p className="mt-2 flex-shrink-0 text-[9.5px] italic text-ssb-text-muted/80">
        {data.decisionNote}
      </p>

      {/* Human review */}
      <div className="mt-2 flex-shrink-0 rounded border border-ssb-border/60 bg-ssb-navy-deep/50 p-2">
        <div className="flex items-center gap-2">
          <span className="h-1.5 w-1.5 rounded-full bg-ssb-amber-bright" />
          <span className="text-[9.5px] font-semibold uppercase tracking-wider text-ssb-amber-bright">
            {data.review.title}
          </span>
        </div>
        <p className="mt-1 text-[9.5px] leading-snug text-ssb-text-muted">{data.review.note}</p>
      </div>
    </div>
  )
}