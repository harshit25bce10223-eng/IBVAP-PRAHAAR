// ─────────────────────────────────────────────────────────────────────────────
// ActiveIncidentPanel — right dominant panel (spec §16, §17).
//
// Shows active incidents ordered by risk (highest first). The Golden Incident
// (INC-024) is expanded to expose the 6-step chain. Severity language is
// strictly consistent: 85–100 = CRITICAL, 65–84 = HIGH, 40–64 = MEDIUM, 0–39 = LOW.
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'
import { AlertTriangle } from 'lucide-react'
import { Badge } from '@/components/ui'
import type { DashboardIncident, GoldenIncident } from '@/types'
import { riskBandFor, RISK_BAND_STYLE } from '@/types'

interface Props {
  incidents: DashboardIncident[]
  goldenIncident: GoldenIncident
  className?: string
}

export function ActiveIncidentPanel({ incidents, goldenIncident, className }: Props) {
  return (
    <div className={clsx('flex flex-col gap-2 min-h-0 overflow-hidden rounded-md border border-ssb-border/70 bg-ssb-navy-deep', className)}>
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-ssb-border/40 flex-shrink-0">
        <div className="flex items-center gap-2">
          <AlertTriangle size={13} className="text-ssb-amber-bright" aria-hidden />
          <span className="text-[10px] font-semibold tracking-[0.16em] text-ssb-text-muted uppercase">
            Active Incidents
          </span>
        </div>
        <Badge variant="warning" size="sm" className="font-mono">{String(incidents.length).padStart(2, '0')}</Badge>
      </div>

      {/* Incident list */}
      <div className="flex-1 overflow-y-auto px-2 space-y-1.5 pb-2">
        {incidents.map(inc => (
          <IncidentCard
            key={inc.id}
            incident={inc}
            isGolden={inc.isGolden}
            goldenSteps={inc.isGolden ? goldenIncident.steps : undefined}
          />
        ))}
      </div>
    </div>
  )
}

// ─── Incident card ──────────────────────────────────────────────────────────

function IncidentCard({
  incident,
  isGolden,
  goldenSteps,
}: {
  incident: DashboardIncident
  isGolden?: boolean
  goldenSteps?: GoldenIncident['steps']
}) {
  const band = riskBandFor(incident.riskScore)
  const style = RISK_BAND_STYLE[band]

  return (
    <div
      className={clsx(
        'rounded border px-2.5 py-2 transition-colors',
        isGolden
          ? 'border-ssb-red-bright/30 bg-ssb-red/5'
          : 'border-ssb-border/40 bg-ssb-navy/60 hover:bg-ssb-navy/80'
      )}
    >
      {/* Title row */}
      <div className="flex items-center justify-between gap-2 mb-1">
        <span className="text-[11px] font-bold font-mono text-ssb-white tracking-wider">{incident.id}</span>
        <div className="flex items-center gap-1.5">
          <Badge variant={style.badge} size="sm" className="font-mono">
            {band}
          </Badge>
          <span className={clsx('text-[11px] font-bold font-mono', style.text)}>
            {incident.riskScore}
          </span>
        </div>
      </div>

      {/* Meta */}
      <div className="flex items-center gap-2 text-[10px] text-ssb-text-muted mb-1">
        <span className="font-mono text-ssb-green-bright">{incident.cameraId}</span>
        <span className="text-ssb-border">·</span>
        <span>{incident.title}</span>
      </div>

      {/* Track + correlation */}
      <div className="flex items-center gap-2 text-[10px] text-ssb-text-muted mb-1.5">
        <span className="font-mono">{incident.trackId}</span>
        <span className="text-ssb-border">·</span>
        <span>{incident.correlatedCameras} Camera{incident.correlatedCameras > 1 ? 's' : ''} Correlated</span>
      </div>

      {/* Summary */}
      <p className="text-[10px] text-ssb-text-muted/70 leading-relaxed">{incident.summary}</p>

      {/* Golden Incident timeline */}
      {isGolden && goldenSteps && (
        <div className="mt-2 pt-2 border-t border-ssb-border/30">
          <span className="text-[8px] font-semibold tracking-[0.16em] text-ssb-amber-bright uppercase mb-1.5 block">
            Incident Chain
          </span>
          <div className="space-y-0.5">
            {goldenSteps.map((step, idx) => (
              <div key={idx} className="flex items-start gap-2 text-[10px]">
                <span className="font-mono text-ssb-text-muted/60 w-8 flex-shrink-0">{step.time}</span>
                <span className="font-mono text-ssb-green-bright text-[9px] w-8 flex-shrink-0">{step.cameraId}</span>
                <span className="text-ssb-text-muted leading-tight">{step.text}</span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}