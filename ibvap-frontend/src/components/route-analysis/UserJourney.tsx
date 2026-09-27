// ─────────────────────────────────────────────────────────────────────────────
// UserJourney — compact visual flow showing the analysis pipeline (USP 5).
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'
import { MapPin, ArrowDown, Shield, Zap, Radio, AlertTriangle, CheckCircle } from 'lucide-react'

interface Props {
  originLabel?: string
  destinationLabel?: string
  recommendedRoute?: string
  recommendedScore?: number
  className?: string
}

const steps = [
  { label: 'YOUR INPUT', icon: MapPin, color: 'text-ssb-text-muted/70', bg: 'bg-ssb-navy/50' },
  { label: 'PRHAAR ANALYZES', icon: Shield, color: 'text-ssb-green-bright', bg: 'bg-ssb-green/10' },
  { label: 'RECOMMENDATION', icon: CheckCircle, color: 'text-ssb-green-bright', bg: 'bg-ssb-green/10' },
]

const analysisItems = [
  { icon: AlertTriangle, label: 'Historical Incidents', color: 'text-ssb-amber-bright', bg: 'bg-ssb-amber/15' },
  { icon: Zap, label: 'Current Intelligence', color: 'text-ssb-red-bright', bg: 'bg-ssb-red/15' },
  { icon: MapPin, label: 'Terrain', color: 'text-ssb-text-muted/70', bg: 'bg-ssb-navy/30' },
  { icon: Shield, label: 'Restricted Zones', color: 'text-ssb-amber-bright', bg: 'bg-ssb-amber/15' },
  { icon: Radio, label: 'Camera Coverage', color: 'text-ssb-green-bright', bg: 'bg-ssb-green/15' },
  { icon: AlertTriangle, label: 'Activity', color: 'text-ssb-text-muted/70', bg: 'bg-ssb-navy/30' },
]

export function UserJourney({ originLabel = 'Border Outpost Alpha', destinationLabel = 'Checkpoint Bravo', recommendedRoute = 'Route B', recommendedScore = 38, className }: Props) {
  return (
    <div className={clsx('rounded-lg border border-ssb-border/60 bg-ssb-navy/50 p-3 flex-shrink-0', className)}>
      <h4 className="text-[9px] font-semibold uppercase tracking-[0.16em] text-ssb-text-muted/70 mb-2">
        ANALYSIS FLOW
      </h4>

      <div className="flex flex-col gap-2">
        {/* Input step */}
        <div className="flex items-start gap-2">
          <div className="flex-shrink-0 w-8 h-8 rounded-full border border-ssb-border/60 bg-ssb-navy/50 flex items-center justify-center">
            <MapPin size={14} className="text-ssb-text-muted/60" aria-hidden="true" />
          </div>
          <div className="flex-1 min-w-0 pt-0.5">
            <div className="text-[9px] font-semibold uppercase tracking-[0.08em] text-ssb-text-muted/70">YOUR INPUT</div>
            <div className="flex items-center gap-1.5 mt-1 text-[10px] font-mono text-ssb-white">
              <span>{originLabel}</span>
              <ArrowDown size={10} className="text-ssb-text-muted/50 mx-1" aria-hidden="true" />
              <span>{destinationLabel}</span>
            </div>
          </div>
        </div>

        <ArrowDown size={16} className="text-ssb-text-muted/40 mx-auto" aria-hidden="true" />

        {/* Analysis step */}
        <div className="flex items-start gap-2">
          <div className="flex-shrink-0 w-8 h-8 rounded-full border border-ssb-green-bright/40 bg-ssb-green/10 flex items-center justify-center">
            <Shield size={14} className="text-ssb-green-bright" aria-hidden="true" />
          </div>
          <div className="flex-1 min-w-0 pt-0.5">
            <div className="text-[9px] font-semibold uppercase tracking-[0.08em] text-ssb-green-bright">PRHAAR ANALYZES</div>
            <div className="flex flex-wrap gap-1 mt-1">
              {analysisItems.map((item, i) => (
                <span key={i} className={clsx('inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[8px] font-medium', item.bg, 'border border-current/30')}>
                  <item.icon size={9} className={item.color} aria-hidden="true" />
                  {item.label}
                </span>
              ))}
            </div>
          </div>
        </div>

        <ArrowDown size={16} className="text-ssb-green-bright/50 mx-auto" aria-hidden="true" />

        {/* Recommendation step */}
        <div className="flex items-start gap-2">
          <div className="flex-shrink-0 w-8 h-8 rounded-full border border-ssb-green-bright/60 bg-ssb-green/15 flex items-center justify-center">
            <CheckCircle size={14} className="text-ssb-green-bright" aria-hidden="true" />
          </div>
          <div className="flex-1 min-w-0 pt-0.5">
            <div className="text-[9px] font-semibold uppercase tracking-[0.08em] text-ssb-green-bright">RECOMMENDATION</div>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-sm font-mono font-semibold text-ssb-green-bright">{recommendedRoute}</span>
              <span className="inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-[9px] font-semibold bg-ssb-green/20 border border-ssb-green-bright/40 text-ssb-green-bright">
                {recommendedScore} / 100 LOW
              </span>
              <span className="text-[9px] font-semibold text-ssb-green-bright uppercase tracking-[0.08em]">✓ LOWER-RISK</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}