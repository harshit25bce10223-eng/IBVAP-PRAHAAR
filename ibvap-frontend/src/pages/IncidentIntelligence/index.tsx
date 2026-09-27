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
    <div className="h-full flex flex-col gap-3 overflow-hidden p-4">
      {/* Page identity */}
      <header className="flex items-start justify-between flex-shrink-0">
        <div>
          <h1 className="text-lg font-semibold tracking-[0.12em] text-ssb-white uppercase">
            Incident Intelligence
          </h1>
          <p className="text-[11px] text-ssb-text-muted mt-0.5 tracking-wide">
            Correlated Events · Explainable Risk · Evidence Integrity
          </p>
        </div>
        <div className="text-right">
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