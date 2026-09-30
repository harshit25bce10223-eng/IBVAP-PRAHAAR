// ─────────────────────────────────────────────────────────────────────────────
// IncidentIntelligence — INCIDENT INTELLIGENCE (SIH screenshot 5)
//
// Three operational columns that prove the alert→meaning flow:
//   Multiple signals → correlated incident → explainable risk → evidence →
//   blockchain integrity. Deliberately a different composition from the
//   Command Center (no KPI strip / map grid).
// ─────────────────────────────────────────────────────────────────────────────

import { useIncidentIntelligence } from '@/hooks'
import {
  TimelineColumn,
  RiskColumn,
  EvidenceColumn,
  IncidentIntelSkeleton,
} from '@/components/incident-intelligence'

export function IncidentIntelligence() {
  const { data, loadState, refetch } = useIncidentIntelligence()

  if (loadState === 'error' && !data) {
    return (
      <div className="h-full flex items-center justify-center">
        <button
          onClick={() => refetch().catch(() => {})}
          className="text-xs text-ssb-amber-bright underline underline-offset-2"
        >
          Failed to load incident intelligence — try again
        </button>
      </div>
    )
  }

  if (!data) {
    return <IncidentIntelSkeleton />
  }

  const correlationIndex = 3 // steps[3] is the cross-camera candidate match

  return (
    <div className="h-full flex flex-col gap-3 overflow-y-auto p-4">
      {/* Page identity */}
      <header className="flex items-start justify-between flex-shrink-0">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-lg font-semibold tracking-[0.12em] text-ssb-white uppercase">
              SUTRA · Correlated Incident Intelligence
            </h1>
            <span className="rounded border border-purple-500/30 bg-purple-500/10 px-2 py-0.5 font-mono text-[9px] text-purple-400 uppercase tracking-wider font-semibold">
              सूत्र
            </span>
          </div>
          <p className="text-[11px] text-ssb-text-muted mt-0.5 tracking-wide">
            From Scattered Multi-Camera Alerts to One Complete Story · Explainable Risk &amp; Integrity
          </p>
        </div>
        <div className="text-right flex flex-col items-end gap-1">
          {/* Prototype data badge — mock service until the real API phase. */}
          <span className="rounded border border-cyan-500/30 bg-cyan-500/10 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider text-cyan-400">
            Demo mode
          </span>
          <span className="block text-[9px] font-mono tracking-[0.2em] text-ssb-text-muted/60 uppercase">
            Primary Incident · {data.incidentId}
          </span>
          <span className="block text-[10px] font-mono text-ssb-red-bright mt-0.5">
            {data.riskScore} / 100 · {data.band}
          </span>
        </div>
      </header>

      {/* Three operational columns */}
      <div className="flex-1 min-h-0 grid grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)_minmax(0,1.1fr)] gap-3">
        <TimelineColumn timeline={data.timeline} correlationIndex={correlationIndex} />
        <RiskColumn data={data} />
        <EvidenceColumn data={data} />
      </div>
    </div>
  )
}