// ─────────────────────────────────────────────────────────────────────────────
// GisContextStrip — legend + selected entity / incident context + forest zone.
//
// The bottom strip under the dominant map. Keeps all supporting information to
// one operational band so the map stays the visual centre (spec §3, §9, §12).
// ─────────────────────────────────────────────────────────────────────────────

import { Link } from 'react-router-dom'
import { riskBandFor } from '@/types/commandDashboard'
import { RISK_BAND_STYLE } from '@/types/commandDashboard'
import type { ForestZoneContext, GisSelection } from '@/types'

interface Props {
  selection: GisSelection
  forestZone: ForestZoneContext
  sectorRef: string
  coords: string
}

export function GisContextStrip({ selection, forestZone, sectorRef, coords }: Props) {
  const context = <SelectionPanel selection={selection} />

  return (
    <div className="flex-shrink-0 grid grid-cols-[248px_minmax(0,1fr)_330px] gap-3 rounded-md border border-ssb-border/70 bg-ssb-navy/60 p-2.5">
      {/* Legend */}
      <div className="flex flex-col justify-center gap-2 border-r border-ssb-border/60 pr-3">
        <div>
          <Title>Risk Activity</Title>
          <div className="grid grid-cols-3 gap-2 mt-1.5">
            <LegendDot color="#0B5D3B" label="Low" />
            <LegendDot color="#F4B942" label="Medium" />
            <LegendDot color="#D62828" label="High" />
          </div>
        </div>
        <div>
          <Title>Map Symbols</Title>
          <div className="grid grid-cols-2 gap-x-2 gap-y-1 mt-1.5">
            <LegendLine color="#0B5D3B" label="Camera" />
            <LegendLine color="#F4B942" label="Restricted zone" dashed />
            <LegendLine color="#22D3EE" label="Entity path" dashed />
            <LegendLine color="#5A6578" label="Historical" />
            <LegendLine color="#D62828" label="Incident" />
          </div>
        </div>
      </div>

      {/* Selected entity / incident context */}
      <div className="flex flex-col justify-center min-w-0">{context}</div>

      {/* Forest zone context + reference */}
      <div className="flex flex-col gap-2 border-l border-ssb-border/60 pl-3">
        <div className="flex items-center justify-between">
          <Title>{forestZone.zoneLabel} · {forestZone.cameraId}</Title>
          <span className="text-[9px] font-mono text-ssb-text-muted/60">{sectorRef} · {coords}</span>
        </div>
        <div className="grid grid-cols-2 gap-2">
          <ResultRow label="Animal" confidence={forestZone.animal.confidence} outcome={forestZone.animal.outcome} tone="safe" />
          <ResultRow label="Human" confidence={forestZone.human.confidence} outcome={forestZone.human.outcome} tone="warning" />
        </div>
        <p className="text-[9.5px] text-ssb-text-muted/80 leading-snug">{forestZone.note}</p>
      </div>
    </div>
  )
}

// ─── Legend primitives ───────────────────────────────────────────────────────

function Title({ children }: { children: React.ReactNode }) {
  return (
    <span className="text-[9px] font-semibold uppercase tracking-[0.16em] text-ssb-text-muted/80">{children}</span>
  )
}

function LegendDot({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-1.5">
      <span className="h-2 w-2 rounded-full flex-shrink-0" style={{ backgroundColor: color }} />
      <span className="text-[9px] text-ssb-text-muted uppercase tracking-wider">{label}</span>
    </div>
  )
}

function LegendLine({ color, label, dashed }: { color: string; label: string; dashed?: boolean }) {
  return (
    <div className="flex items-center gap-1.5 min-w-0">
      <span
        className="h-px w-4 flex-shrink-0"
        style={{
          backgroundColor: dashed ? 'transparent' : color,
          ...(dashed ? { backgroundImage: `repeating-linear-gradient(90deg, ${color} 0 3px, transparent 3px 6px)` } : {}),
        }}
      />
      <span className="text-[9px] text-ssb-text-muted uppercase tracking-wider truncate">{label}</span>
    </div>
  )
}

// ─── Selection panel ─────────────────────────────────────────────────────────

function SelectionPanel({ selection }: { selection: GisSelection }) {
  switch (selection.type) {
    case 'incident': {
      const inc = selection.incident
      const band = riskBandFor(inc.riskScore)
      const style = RISK_BAND_STYLE[band]
      return (
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[9px] font-semibold uppercase tracking-[0.16em] text-ssb-text-muted/80">
              Selected Context
            </span>
            <span className={`text-[10px] font-mono font-bold ${style.text}`}>
              {inc.id} · {band} · {inc.riskScore}/100
            </span>
          </div>
          <div className="flex items-center gap-4 mt-1.5 text-[10.5px] text-ssb-text">
            <span><span className="text-ssb-text-muted/70">Camera:</span> <Link className="text-ssb-green-bright hover:underline" to={`/camera/${inc.cameraId}`}>{inc.cameraId}</Link></span>
            <span><span className="text-ssb-text-muted/70">Track:</span> <Link className="text-ssb-green-bright hover:underline" to={`/track/${inc.trackId}`}>{inc.trackId}</Link></span>
            <span><span className="text-ssb-text-muted/70">Reason:</span> {inc.reason}</span>
            <span><span className="text-ssb-text-muted/70">Correlation:</span> <span className="text-ssb-amber-bright">{inc.correlationCount} cameras</span></span>
          </div>
          <p className="text-[9.5px] text-ssb-text-muted/80 mt-1 leading-snug">
            Open camera / track detail for the full record. Selecting map objects updates this context.
          </p>
        </div>
      )
    }
    case 'zone': {
      const zone = selection.zone
      return (
        <div>
          <span className="text-[9px] font-semibold uppercase tracking-[0.16em] text-ssb-text-muted/80">Selected Context · {zone.kind}</span>
          <div className="mt-1.5 flex items-center gap-2">
            <span className="text-[11px] font-mono font-bold text-ssb-amber-bright">{zone.label}</span>
          </div>
          <p className="text-[10.5px] text-ssb-text mt-1">{zone.info}</p>
          <p className="text-[9.5px] text-ssb-text-muted/80 mt-1">Perimeter and zones are layered operational context on the map.</p>
        </div>
      )
    }
    case 'hotspot': {
      const hot = selection.hotspot
      const color = hot.level === 'HIGH' ? '#D62828' : hot.level === 'MEDIUM' ? '#F4B942' : '#0B5D3B'
      return (
        <div>
          <span className="text-[9px] font-semibold uppercase tracking-[0.16em] text-ssb-text-muted/80">Risk Hotspot · {hot.label}</span>
          <div className="mt-1.5 flex items-center gap-2">
            <span className="h-2 w-2 rounded-full" style={{ backgroundColor: color }} />
            <span className="text-[11px] font-mono font-bold text-ssb-white">{hot.level} ACTIVITY</span>
          </div>
          <p className="text-[10.5px] text-ssb-text mt-1">{hot.note}</p>
          <p className="text-[9.5px] text-ssb-text-muted/80 mt-1">Heat reflects current pattern, not a hard risk verdict.</p>
        </div>
      )
    }
    case 'historical': {
      const act = selection.activity
      return (
        <div>
          <span className="text-[9px] font-semibold uppercase tracking-[0.16em] text-ssb-text-muted/80">Historical Pattern</span>
          <div className="mt-1.5 flex items-center gap-2">
            <span className="text-[11px] font-mono font-bold text-ssb-white">{act.label}</span>
            <span className="text-[10px] font-mono text-ssb-text-muted">×{act.count} · {act.window}</span>
          </div>
          <p className="text-[10.5px] text-ssb-text mt-1">
            Repeated {act.kind.toLowerCase()} activity at this location within the selected window.
          </p>
        </div>
      )
    }
    default:
      return <p className="text-[10px] text-ssb-text-muted">Select a map object to inspect context.</p>
  }
}

// ─── Forest zone result row ───────────────────────────────────────────────────

function ResultRow({ label, confidence, outcome, tone }: {
  label: string
  confidence: number
  outcome: string
  tone: 'safe' | 'warning'
}) {
  const color = tone === 'safe' ? 'text-ssb-green-bright' : 'text-ssb-amber-bright'
  return (
    <div className="rounded border border-ssb-border/60 bg-ssb-navy-deep/50 px-2 py-1.5">
      <div className="flex items-center justify-between">
        <span className="text-[9px] font-semibold uppercase tracking-wider text-ssb-text-muted">{label}</span>
        <span className={`text-[12px] font-mono font-bold ${color}`}>{confidence}%</span>
      </div>
      <div className={`text-[10px] font-medium mt-0.5 ${color}`}>{outcome}</div>
    </div>
  )
}