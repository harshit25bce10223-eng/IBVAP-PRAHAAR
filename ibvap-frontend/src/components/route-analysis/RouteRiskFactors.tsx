// ─────────────────────────────────────────────────────────────────────────────
// RouteRiskFactors — compact risk factor breakdown for recommended route (USP 5).
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'
import { Shield, Zap, Radio, MapPin, AlertTriangle, Activity } from 'lucide-react'
import type { RouteRiskFactor } from '@/types'

interface Props {
  factors: RouteRiskFactor[]
  routeName?: string
  className?: string
}

const FACTOR_ICONS: Record<string, React.ComponentType<{ className?: string; size?: number }>> = {
  historicalDensity: AlertTriangle,
  currentAlerts: Zap,
  restrictedZoneExposure: Shield,
  cameraCoverage: Radio,
  recentEntityActivity: Activity,
  terrainContext: MapPin,
}

const LEVEL_STYLE: Record<'LOW' | 'MEDIUM' | 'HIGH', { text: string; bg: string; border: string; dot: string }> = {
  LOW: { text: 'text-ssb-green-bright', bg: 'bg-ssb-green/15', border: 'border-ssb-green-bright/40', dot: 'bg-ssb-green-bright' },
  MEDIUM: { text: 'text-ssb-amber-bright', bg: 'bg-ssb-amber/15', border: 'border-ssb-amber-bright/40', dot: 'bg-ssb-amber-bright' },
  HIGH: { text: 'text-ssb-red-bright', bg: 'bg-ssb-red/15', border: 'border-ssb-red-bright/40', dot: 'bg-ssb-red-bright' },
}

export function RouteRiskFactors({ factors, routeName = 'Route B', className }: Props) {
  return (
    <div className={clsx('rounded-md border border-ssb-border/70 bg-ssb-navy/60 px-3 py-2.5 flex-shrink-0 flex flex-col justify-between', className)}>
      <div className="flex items-center justify-between gap-1.5 mb-1.5">
        <div className="flex items-center gap-1.5">
          <span className="text-[9px] font-semibold uppercase tracking-[0.16em] text-ssb-text-muted/70">
            ROUTE RISK FACTORS
          </span>
          <span className="text-[9px] font-mono text-ssb-green-bright font-medium">({routeName})</span>
        </div>
        <span className="text-[8px] font-mono text-ssb-text-muted/50 uppercase">COMPARATIVE EVAL</span>
      </div>

      <div className="grid grid-cols-2 gap-x-3 gap-y-1.5">
        {factors.map(factor => {
          const Icon = FACTOR_ICONS[factor.key] ?? Shield
          const style = LEVEL_STYLE[factor.level] ?? LEVEL_STYLE.LOW

          return (
            <div key={factor.key} className="flex items-center justify-between gap-1.5 min-w-0">
              <div className="flex items-center gap-1.5 min-w-0">
                <Icon size={11} className="text-ssb-text-muted/60 flex-shrink-0" aria-hidden="true" />
                <span className="text-[10px] text-ssb-text-muted/80 font-medium truncate" title={factor.label}>
                  {factor.label}
                </span>
              </div>
              <span className={clsx('inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[8px] font-mono font-semibold uppercase flex-shrink-0', style.bg, style.border, style.text)}>
                <span className={clsx('w-1 h-1 rounded-full', style.dot)} aria-hidden="true" />
                {factor.level === 'LOW' && factor.key === 'currentAlerts' ? 'NONE' : factor.level}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}
