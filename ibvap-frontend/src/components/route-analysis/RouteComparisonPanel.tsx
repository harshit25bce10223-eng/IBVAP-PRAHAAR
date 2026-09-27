// ─────────────────────────────────────────────────────────────────────────────
// RouteComparisonPanel — right-side complete route comparison with risk scores (USP 5).
//
// Shows Route A, Route B (RECOMMENDED), and Route C fully visible simultaneously
// with transparent operational reasoning explaining why Route B is lower-risk.
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'
import { CheckCircle, AlertTriangle, Shield, Radio, Zap, Clock, MapPin } from 'lucide-react'
import type { RouteCandidate, RiskBand, RouteAnalysisData } from '@/types'

interface Props {
  routes: RouteCandidate[]
  selectedRouteId: string | null
  onSelect: (routeId: string | null) => void
  recommendation?: RouteAnalysisData['recommendation']
}

const SEVERITY_STYLE: Record<RiskBand, { bg: string; border: string; text: string; dot: string; label: string }> = {
  LOW: { bg: 'bg-ssb-green/15', border: 'border-ssb-green-bright/50', text: 'text-ssb-green-bright', dot: 'bg-ssb-green-bright', label: 'LOW RISK' },
  MEDIUM: { bg: 'bg-ssb-amber/15', border: 'border-ssb-amber-bright/50', text: 'text-ssb-amber-bright', dot: 'bg-ssb-amber-bright', label: 'MEDIUM RISK' },
  HIGH: { bg: 'bg-ssb-red/15', border: 'border-ssb-red-bright/50', text: 'text-ssb-red-bright', dot: 'bg-ssb-red-bright', label: 'HIGH RISK' },
  CRITICAL: { bg: 'bg-ssb-red/25', border: 'border-ssb-red-bright/70', text: 'text-ssb-red-bright', dot: 'bg-ssb-red-bright', label: 'CRITICAL' },
}

const ROUTE_ACCENTS: Record<string, { indicator: string; text: string; tag: string; note: string }> = {
  'ROUTE-A': {
    indicator: 'bg-ssb-amber-bright',
    text: 'text-ssb-amber-bright',
    tag: 'ALTERNATIVE 1',
    note: 'Restricted buffer zone exposure (+18)',
  },
  'ROUTE-B': {
    indicator: 'bg-ssb-green-bright',
    text: 'text-ssb-green-bright',
    tag: '✓ RECOMMENDED',
    note: 'Lowest comparative risk among feasible routes',
  },
  'ROUTE-C': {
    indicator: 'bg-slate-400',
    text: 'text-slate-300',
    tag: 'ALTERNATIVE 2',
    note: 'Degraded sensor coverage (CAM-07)',
  },
}

export function RouteComparisonPanel({ routes, selectedRouteId, onSelect, recommendation }: Props) {
  const isSelected = (id: string) => selectedRouteId === id
  const recommendedRoute = routes.find(r => r.recommended) ?? routes[1] ?? routes[0]

  return (
    <div className="flex flex-col gap-2.5 h-full min-w-0 justify-between">
      {/* Header */}
      <div className="flex items-center justify-between flex-shrink-0 px-0.5">
        <div className="flex items-center gap-2">
          <h2 className="text-xs font-semibold tracking-[0.14em] text-ssb-white uppercase">
            Route Comparison
          </h2>
          <span className="text-[10px] font-mono font-medium text-ssb-green-bright bg-ssb-green/15 border border-ssb-green-bright/30 rounded px-1.5 py-0.2">
            3 FEASIBLE ROUTES
          </span>
        </div>
        <span className="text-[9px] font-mono text-ssb-text-muted/60 uppercase tracking-wider">
          COMPARATIVE RISK EVAL
        </span>
      </div>

      {/* 3 Route Cards — Compact, clear, fully visible together */}
      <div className="flex flex-col gap-2 flex-shrink-0">
        {routes.map(route => {
          const style = SEVERITY_STYLE[route.severity]
          const accent = ROUTE_ACCENTS[route.id] ?? {
            indicator: 'bg-ssb-text-muted',
            text: 'text-ssb-white',
            tag: 'ROUTE',
            note: '',
          }
          const selected = isSelected(route.id)
          const isRec = route.recommended

          return (
            <div
              key={route.id}
              onClick={() => onSelect(selected ? null : route.id)}
              className={clsx(
                'relative rounded-md border p-2 transition-all text-left cursor-pointer select-none',
                isRec
                  ? 'border-ssb-green-bright/60 bg-ssb-green/10 shadow-sm shadow-ssb-green/20'
                  : 'border-ssb-border/70 bg-ssb-navy/60 hover:border-ssb-border hover:bg-ssb-navy/80',
                selected && 'ring-2 ring-ssb-green-bright/70 border-ssb-green-bright'
              )}
              role="button"
              tabIndex={0}
              onKeyDown={e => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  onSelect(selected ? null : route.id)
                }
              }}
              aria-pressed={selected}
            >
              {/* Header row: Name, Badge, Recommended Tag */}
              <div className="flex items-center justify-between gap-2 mb-1">
                <div className="flex items-center gap-2">
                  <span className={clsx('w-2 h-2 rounded-full flex-shrink-0', accent.indicator)} aria-hidden="true" />
                  <span className={clsx('text-xs font-semibold tracking-[0.08em]', isRec ? 'text-ssb-white' : 'text-ssb-text-muted/90')}>
                    {route.name}
                  </span>
                  <span className={clsx('inline-flex items-center gap-1 rounded px-1.5 py-0.2 text-[8px] font-mono font-semibold uppercase', style.bg, style.border, style.text)}>
                    <span className={clsx('w-1 h-1 rounded-full', style.dot)} aria-hidden="true" />
                    {route.severity}
                  </span>
                </div>

                {isRec ? (
                  <span className="inline-flex items-center gap-1 rounded bg-ssb-green/25 border border-ssb-green-bright/60 px-2 py-0.5 text-[8.5px] font-semibold text-ssb-green-bright uppercase tracking-[0.06em]">
                    <CheckCircle size={10} className="text-ssb-green-bright flex-shrink-0" aria-hidden="true" />
                    RECOMMENDED
                  </span>
                ) : (
                  <span className="text-[8.5px] font-mono text-ssb-text-muted/50 uppercase tracking-wider">
                    {accent.tag}
                  </span>
                )}
              </div>

              {/* Score & Tagline Row */}
              <div className="flex items-baseline justify-between gap-2 mb-1.5 pb-1 border-b border-ssb-border/40">
                <div className="flex items-baseline gap-1.5">
                  <span className="text-[9px] font-mono text-ssb-text-muted/70 uppercase">RISK:</span>
                  <span className={clsx('text-base font-mono font-bold tabular-nums leading-none', style.text)}>
                    {route.riskScore}
                  </span>
                  <span className="text-[9px] font-mono text-ssb-text-muted/50">/ 100</span>
                  <span className={clsx('text-[9px] font-semibold ml-1', style.text)}>
                    {style.label}
                  </span>
                </div>
                <span className="text-[8.5px] text-ssb-text-muted/70 truncate text-right font-medium">
                  {accent.note}
                </span>
              </div>

              {/* Metrics Grid: Compact 3 columns x 2 rows */}
              <div className="grid grid-cols-3 gap-x-1.5 gap-y-0.5 text-[9px] font-mono">
                <div className="flex items-center justify-between gap-1 bg-ssb-navy-deep/40 rounded px-1.5 py-0.5 border border-ssb-border/30">
                  <span className="text-ssb-text-muted/70 text-[8.5px]">Dist:</span>
                  <span className="text-ssb-white font-semibold">{route.geometry.distanceKm} km</span>
                </div>
                <div className="flex items-center justify-between gap-1 bg-ssb-navy-deep/40 rounded px-1.5 py-0.5 border border-ssb-border/30">
                  <span className="text-ssb-text-muted/70 text-[8.5px]">Time:</span>
                  <span className="text-ssb-white font-semibold">{route.geometry.estimatedTimeMin}m</span>
                </div>
                <div className="flex items-center justify-between gap-1 bg-ssb-navy-deep/40 rounded px-1.5 py-0.5 border border-ssb-border/30">
                  <span className="text-ssb-text-muted/70 text-[8.5px]">Coverage:</span>
                  <span className={clsx('font-semibold', route.coverage >= 90 ? 'text-ssb-green-bright' : route.coverage >= 80 ? 'text-ssb-amber-bright' : 'text-slate-400')}>
                    {route.coverage}%
                  </span>
                </div>
                <div className="flex items-center justify-between gap-1 bg-ssb-navy-deep/40 rounded px-1.5 py-0.5 border border-ssb-border/30">
                  <span className="text-ssb-text-muted/70 text-[8.5px]">Events:</span>
                  <span className="text-ssb-white font-semibold">{route.historicalIncidents}</span>
                </div>
                <div className="flex items-center justify-between gap-1 bg-ssb-navy-deep/40 rounded px-1.5 py-0.5 border border-ssb-border/30">
                  <span className="text-ssb-text-muted/70 text-[8.5px]">Alerts:</span>
                  <span className={clsx('font-semibold', route.currentAlerts > 0 ? 'text-ssb-red-bright' : 'text-ssb-green-bright')}>
                    {route.currentAlerts}
                  </span>
                </div>
                <div className="flex items-center justify-between gap-1 bg-ssb-navy-deep/40 rounded px-1.5 py-0.5 border border-ssb-border/30">
                  <span className="text-ssb-text-muted/70 text-[8.5px]">RZ Expos:</span>
                  <span className={clsx('font-semibold', route.restrictedZoneExposure > 50 ? 'text-ssb-red-bright' : route.restrictedZoneExposure > 20 ? 'text-ssb-amber-bright' : 'text-ssb-green-bright')}>
                    {route.restrictedZoneExposure}%
                  </span>
                </div>
              </div>
            </div>
          )
        })}
      </div>

      {/* Transparent Reasoning Panel: WHY ROUTE B (RECOMMENDED)? */}
      <div className="rounded-md border border-ssb-green-bright/50 bg-ssb-green/10 p-2 flex flex-col gap-1 flex-shrink-0">
        <div className="flex items-center justify-between gap-2 border-b border-ssb-green-bright/25 pb-0.5">
          <div className="flex items-center gap-1.5">
            <CheckCircle size={12} className="text-ssb-green-bright flex-shrink-0" aria-hidden="true" />
            <span className="text-[9.5px] font-semibold text-ssb-green-bright uppercase tracking-[0.08em]">
              WHY {recommendedRoute.name.toUpperCase()}? (LOWER-RISK RECOMMENDATION)
            </span>
          </div>
          <span className="text-[9px] font-mono font-bold text-ssb-green-bright">
            {recommendedRoute.riskScore} / 100
          </span>
        </div>

        {/* 4 Reasoning Points */}
        <div className="grid grid-cols-1 gap-0.5 text-[8.5px] text-ssb-text-muted/90 leading-tight">
          <div className="flex items-start gap-1">
            <span className="text-ssb-green-bright font-bold mt-[-1px]">•</span>
            <span>
              <strong className="text-ssb-white font-medium">Lower Alert Density:</strong> 0 active alerts along route vs 1 active breach alert on Route A.
            </span>
          </div>
          <div className="flex items-start gap-1">
            <span className="text-ssb-green-bright font-bold mt-[-1px]">•</span>
            <span>
              <strong className="text-ssb-white font-medium">Higher Surveillance Coverage:</strong> 94% continuous coverage by CAM-01, CAM-02, CAM-12 (vs 82% & 71%).
            </span>
          </div>
          <div className="flex items-start gap-1">
            <span className="text-ssb-green-bright font-bold mt-[-1px]">•</span>
            <span>
              <strong className="text-ssb-white font-medium">Lower Historical Concentration:</strong> Only 1 past incident in 7-day window (vs 4 on A & 3 on C).
            </span>
          </div>
          <div className="flex items-start gap-1">
            <span className="text-ssb-green-bright font-bold mt-[-1px]">•</span>
            <span>
              <strong className="text-ssb-white font-medium">Favourable Terrain & Buffer:</strong> Avoids primary restricted buffer breach (12% perimeter vs 68% on A).
            </span>
          </div>
        </div>

        {/* Operational conclusion */}
        <div className="flex items-center justify-between pt-0.5 border-t border-ssb-green-bright/20 text-[8px] font-mono text-ssb-green-bright/90 uppercase tracking-wider">
          <span>COMPARATIVELY LOWER OPERATIONAL RISK</span>
          <span className="text-ssb-text-muted/70">DECISION SUPPORT ONLY</span>
        </div>
      </div>
    </div>
  )
}