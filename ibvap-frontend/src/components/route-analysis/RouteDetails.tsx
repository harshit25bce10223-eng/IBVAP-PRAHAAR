// ─────────────────────────────────────────────────────────────────────────────
// RouteDetails — selected route detail view (USP 5).
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'
import { MapPin, Clock, Shield, Radio, Zap, AlertTriangle, CheckCircle, MinusCircle, HelpCircle } from 'lucide-react'
import { riskBandFor } from '@/types/commandDashboard'
import type { RouteCandidate, RiskBand, RouteIncident, RouteCameraCoverage, RouteRestrictedZone, RouteRiskFactor } from '@/types'

interface Props {
  route: RouteCandidate | null
  incidents: RouteIncident[]
  cameraCoverage: RouteCameraCoverage[]
  restrictedZones: RouteRestrictedZone[]
  riskFactors: RouteRiskFactor[]
}

const SEVERITY_STYLE: Record<RiskBand, { bg: string; border: string; text: string; dot: string }> = {
  LOW: { bg: 'bg-ssb-green/15', border: 'border-ssb-green-bright/40', text: 'text-ssb-green-bright', dot: 'bg-ssb-green-bright' },
  MEDIUM: { bg: 'bg-ssb-amber/15', border: 'border-ssb-amber-bright/40', text: 'text-ssb-amber-bright', dot: 'bg-ssb-amber-bright' },
  HIGH: { bg: 'bg-ssb-red/15', border: 'border-ssb-red-bright/40', text: 'text-ssb-red-bright', dot: 'bg-ssb-red-bright' },
  CRITICAL: { bg: 'bg-ssb-red/20', border: 'border-ssb-red-bright/60', text: 'text-ssb-red-bright', dot: 'bg-ssb-red-bright' },
}

const FACTOR_ICONS: Record<RouteRiskFactor['key'], React.ComponentType<{ className?: string; size?: number }>> = {
  historicalDensity: AlertTriangle,
  currentAlerts: Zap,
  restrictedZoneExposure: Shield,
  cameraCoverage: Radio,
  recentEntityActivity: HelpCircle,
  terrainContext: MapPin,
}

const FACTOR_LEVEL_STYLE: Record<RouteRiskFactor['level'], { text: string; dot: string }> = {
  LOW: { text: 'text-ssb-green-bright', dot: 'bg-ssb-green-bright' },
  MEDIUM: { text: 'text-ssb-amber-bright', dot: 'bg-ssb-amber-bright' },
  HIGH: { text: 'text-ssb-red-bright', dot: 'bg-ssb-red-bright' },
}

function DetailRow({ icon: Icon, label, value, unit, className }: { icon?: React.ComponentType<any>; label: string; value: string | number; unit?: string; className?: string }) {
  return (
    <div className={clsx('flex items-center gap-2', className)}>
      {Icon && <Icon size={13} className="text-ssb-text-muted/60 flex-shrink-0" aria-hidden="true" />}
      <span className="text-[10px] text-ssb-text-muted/80 font-medium min-w-[100px]">{label}</span>
      <span className="text-sm font-mono font-semibold text-ssb-white tabular-nums flex-1 text-right">
        {value}{unit ? <span className="text-[10px] font-normal text-ssb-text-muted/60 ml-0.5">{unit}</span> : null}
      </span>
    </div>
  )
}

function RiskFactorRow({ factor }: { factor: RouteRiskFactor }) {
  const Icon = FACTOR_ICONS[factor.key] ?? HelpCircle
  const style = FACTOR_LEVEL_STYLE[factor.level]

  return (
    <div className="flex items-center gap-2">
      <Icon size={12} className={clsx('flex-shrink-0', style.text)} aria-hidden="true" />
      <span className="text-[10px] font-medium text-ssb-text-muted/90 min-w-[130px]">{factor.label}</span>
      <span className={clsx('flex items-center gap-1.5 px-2 py-0.5 rounded text-[9px] font-semibold tracking-[0.08em] uppercase', `bg-${style.dot.replace('bg-', '')}/15`, `border border-${style.dot.replace('bg-', '')}/40`, style.text)}>
        <span className="w-1.5 h-1.5 rounded-full" style={{ backgroundColor: style.dot.replace('bg-', '') }} aria-hidden="true" />
        {factor.level}
      </span>
    </div>
  )
}

export function RouteDetails({ route, incidents, cameraCoverage, restrictedZones, riskFactors }: Props) {
  if (!route) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-ssb-text-muted/60">
        <HelpCircle size={32} className="mb-2 opacity-40" aria-hidden="true" />
        <p className="text-sm">Select a route to view details</p>
        <p className="text-[11px] mt-1">Click on a route card or map line</p>
      </div>
    )
  }

  const style = SEVERITY_STYLE[route.severity]
  const relevantIncidents = incidents.filter(i => i.affectsRoutes.includes(route.id))
  const relevantCameras = cameraCoverage.filter(c => c.coversRoutes.includes(route.id))
  const relevantZones = restrictedZones.filter(z => z.affectsRoutes.includes(route.id))

  return (
    <div className="flex flex-col gap-3 h-full overflow-auto pr-1">
      {/* Header */}
      <div className={clsx('flex items-start justify-between gap-3 rounded-lg border p-3', style.bg, style.border)}>
        <div className="flex items-center gap-2">
          <span className={clsx('text-sm font-semibold tracking-[0.08em] text-ssb-white')}>{route.name}</span>
          <span className={clsx('inline-flex items-center gap-1.5 rounded px-2 py-0.5 text-[10px] font-semibold tracking-[0.08em] uppercase', style.bg, style.border, style.text)}>
            <span className={clsx('w-1.5 h-1.5 rounded-full', style.dot)} aria-hidden="true" />
            {route.severity}
          </span>
        </div>
        {route.recommended && (
          <span className="flex items-center gap-1 rounded-full bg-ssb-green/20 border border-ssb-green-bright/50 px-2 py-0.5 flex-shrink-0">
            <CheckCircle size={10} className="text-ssb-green-bright" aria-hidden="true" />
            <span className="text-[9px] font-semibold text-ssb-green-bright uppercase tracking-[0.08em]">RECOMMENDED</span>
          </span>
        )}
      </div>

      {/* Key metrics */}
      <div className="grid grid-cols-2 gap-2 rounded-lg border border-ssb-border/60 bg-ssb-navy/50 p-3">
        <DetailRow icon={MapPin} label="Distance" value={route.geometry.distanceKm} unit=" km" />
        <DetailRow icon={Clock} label="Est. Time" value={route.geometry.estimatedTimeMin} unit=" min" />
        <DetailRow icon={Shield} label="Hist. Incidents" value={route.historicalIncidents} />
        <DetailRow icon={Zap} label="Current Alerts" value={route.currentAlerts} />
        <DetailRow icon={Radio} label="Coverage" value={route.coverage} unit="%" />
        <DetailRow icon={AlertTriangle} label="RZ Exposure" value={route.restrictedZoneExposure} unit="%" />
        <DetailRow icon={MapPin} label="Terrain" value={route.terrain} />
        <DetailRow icon={CheckCircle} label="Status" value={route.recommended ? 'RECOMMENDED' : 'ALTERNATIVE'} />
      </div>

      {/* Risk Factor Breakdown */}
      <div className="rounded-lg border border-ssb-border/60 bg-ssb-navy/50 p-3">
        <h4 className="text-[10px] font-semibold uppercase tracking-[0.16em] text-ssb-text-muted/70 mb-2">
          ROUTE RISK FACTORS
        </h4>
        <div className="flex flex-col gap-1.5">
          {riskFactors.map(factor => (
            <RiskFactorRow key={factor.key} factor={factor} />
          ))}
        </div>
      </div>

      {/* Affected Incidents */}
      {relevantIncidents.length > 0 && (
        <div className="rounded-lg border border-ssb-border/60 bg-ssb-navy/50 p-3">
          <h4 className="text-[10px] font-semibold uppercase tracking-[0.16em] text-ssb-text-muted/70 mb-2">
            AFFECTING INCIDENTS ({relevantIncidents.length})
          </h4>
          <div className="flex flex-col gap-1.5">
            {relevantIncidents.map(inc => {
              const band = inc.band === 'HIGH' || inc.band === 'CRITICAL' ? '#D62828' : '#F4B942'
              return (
                <div key={inc.id} className="flex items-center justify-between gap-2 rounded border border-ssb-border/50 bg-ssb-navy-deep/50 px-2 py-1.5">
                  <div className="flex items-center gap-2 min-w-0">
                    <div className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: band }} />
                    <div>
                      <div className="text-[10px] font-mono font-semibold text-ssb-white">{inc.id}</div>
                      <div className="text-[9px] text-ssb-text-muted/70 truncate max-w-[180px]">{inc.title}</div>
                    </div>
                  </div>
                  <span className="text-[9px] font-mono text-ssb-text-muted/60">{inc.cameraId}</span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Camera Coverage */}
      {relevantCameras.length > 0 && (
        <div className="rounded-lg border border-ssb-border/60 bg-ssb-navy/50 p-3">
          <h4 className="text-[10px] font-semibold uppercase tracking-[0.16em] text-ssb-text-muted/70 mb-2">
            SURVEILLANCE COVERAGE ({relevantCameras.length})
          </h4>
          <div className="flex flex-col gap-1.5">
            {relevantCameras.map(cam => {
              const color = cam.state === 'DEGRADED' ? '#F4B942' : cam.state === 'OFFLINE' ? '#5A6578' : '#0B5D3B'
              return (
                <div key={cam.id} className="flex items-center justify-between gap-2 rounded border border-ssb-border/50 bg-ssb-navy-deep/50 px-2 py-1.5">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded flex-shrink-0" style={{ backgroundColor: color }} />
                    <div>
                      <div className="text-[10px] font-mono font-semibold text-ssb-white">{cam.id}</div>
                      <div className="text-[9px] text-ssb-text-muted/70 capitalize">{cam.state.toLowerCase()}</div>
                    </div>
                  </div>
                  <span className={clsx('text-[9px] font-semibold px-1.5 py-0.5 rounded', `text-${color.replace('#', '')}`, `bg-${color.replace('#', '')}/15`)}>
                    {cam.coverageQuality}
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* Restricted Zones */}
      {relevantZones.length > 0 && (
        <div className="rounded-lg border border-ssb-border/60 bg-ssb-navy/50 p-3">
          <h4 className="text-[10px] font-semibold uppercase tracking-[0.16em] text-ssb-text-muted/70 mb-2">
            RESTRICTED ZONE EXPOSURE ({relevantZones.length})
          </h4>
          <div className="flex flex-col gap-1.5">
            {relevantZones.map(zone => {
              const exposure = zone.exposureByRoute[route.id] ?? 0
              return (
                <div key={zone.id} className="flex items-center justify-between gap-2 rounded border border-ssb-border/50 bg-ssb-navy-deep/50 px-2 py-1.5">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded flex-shrink-0 bg-ssb-amber-bright" />
                    <div>
                      <div className="text-[10px] font-mono font-semibold text-ssb-white">{zone.label}</div>
                      <div className="text-[9px] text-ssb-text-muted/70 truncate max-w-[180px]">{zone.info}</div>
                    </div>
                  </div>
                  <span className={clsx('text-[9px] font-mono font-semibold px-1.5 py-0.5 rounded',
                    exposure > 50 ? 'text-ssb-red-bright bg-ssb-red/15' :
                    exposure > 20 ? 'text-ssb-amber-bright bg-ssb-amber/15' :
                    'text-ssb-green-bright bg-ssb-green/15'
                  )}>
                    {exposure}%
                  </span>
                </div>
              )
            })}
          </div>
        </div>
      )}
    </div>
  )
}