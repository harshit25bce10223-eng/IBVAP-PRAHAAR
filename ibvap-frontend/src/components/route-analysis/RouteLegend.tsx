// ─────────────────────────────────────────────────────────────────────────────
// RouteLegend — compact map legend (USP 5).
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'
import { MapPin, Circle, Triangle, Square, Minus, Radio, Zap } from 'lucide-react'

interface Props {
  className?: string
}

export function RouteLegend({ className }: Props) {
  const items = [
    { icon: <MapPin size={10} className="text-ssb-green-bright" />, label: 'Start', color: 'text-ssb-green-bright' },
    { icon: <Triangle size={10} className="text-ssb-green-bright" style={{ transform: 'rotate(180deg)' }} />, label: 'Destination', color: 'text-ssb-green-bright' },
    { icon: <div className="w-6 h-0.5 bg-ssb-green-bright rounded" />, label: 'Recommended Route (B)', color: 'text-ssb-green-bright' },
    { icon: <div className="w-6 h-0.5 bg-ssb-amber-bright rounded" />, label: 'Medium Risk Route (A/C)', color: 'text-ssb-amber-bright' },
    { icon: <div className="w-6 h-0.5 border-t border-ssb-red-bright/60" style={{ borderTopStyle: 'dashed' }} />, label: 'High-Risk Segment', color: 'text-ssb-red-bright' },
    { icon: <Radio size={10} className="text-ssb-green-bright" />, label: 'Camera (Online)', color: 'text-ssb-green-bright' },
    { icon: <Radio size={10} className="text-ssb-amber-bright" />, label: 'Camera (Degraded)', color: 'text-ssb-amber-bright' },
    { icon: <Zap size={10} className="text-ssb-red-bright" />, label: 'Active Incident', color: 'text-ssb-red-bright' },
    { icon: <Square size={10} className="text-ssb-amber-bright" style={{ border: '1px solid', borderRadius: 0 }} />, label: 'Restricted Zone', color: 'text-ssb-amber-bright' },
  ]

  return (
    <div className={clsx('rounded-md border border-ssb-border/70 bg-ssb-navy/60 px-3 py-2.5 flex-shrink-0', className)}>
      <div className="flex items-center gap-1.5 mb-1.5">
        <span className="text-[9px] font-semibold uppercase tracking-[0.16em] text-ssb-text-muted/70">
          MAP LEGEND
        </span>
      </div>
      <div className="grid grid-cols-2 gap-1.5">
        {items.map((item, i) => (
          <div key={i} className="flex items-center gap-2">
            <div className="flex-shrink-0 w-8 flex items-center justify-center">{item.icon}</div>
            <span className={clsx('text-[10px] font-medium', item.color)}>{item.label}</span>
          </div>
        ))}
      </div>
    </div>
  )
}