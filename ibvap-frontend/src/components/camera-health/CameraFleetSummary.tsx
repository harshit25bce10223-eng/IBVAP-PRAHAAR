// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 2 — Camera Fleet Operational Summary Cards
// ─────────────────────────────────────────────────────────────────────────────

import { useMemo } from 'react'
import { ShieldCheck, AlertTriangle, AlertOctagon, PauseCircle, Clock, Wrench, EyeOff } from 'lucide-react'
import type { CameraHealth } from '@/types/cameraHealth'

export interface CameraFleetSummaryProps {
  healthRecords: CameraHealth[]
  selectedFilter: string | null
  onSelectFilter: (filter: string | null) => void
}

export function CameraFleetSummary({
  healthRecords,
  selectedFilter,
  onSelectFilter,
}: CameraFleetSummaryProps) {
  const counts = useMemo(() => {
    let healthy = 0
    let degraded = 0
    let offline = 0
    let frozen = 0
    let stale = 0
    let maintenance = 0
    let coverageCompromised = 0

    for (const h of healthRecords) {
      if (h.status === 'ONLINE') healthy++
      else if (h.status === 'DEGRADED') degraded++
      else if (h.status === 'OFFLINE') offline++
      else if (h.status === 'FROZEN') frozen++
      else if (h.status === 'STALE') stale++
      else if (h.status === 'MAINTENANCE') maintenance++

      if (h.operationalImpact?.coverage === 'COMPROMISED') {
        coverageCompromised++
      }
    }

    return {
      healthy,
      degraded,
      offline,
      frozen,
      stale,
      maintenance,
      coverageCompromised,
      total: healthRecords.length,
    }
  }, [healthRecords])

  const items = [
    {
      id: 'ONLINE',
      label: 'Healthy',
      count: counts.healthy,
      icon: ShieldCheck,
      color: 'text-prhaar-good',
      border: 'border-prhaar-good/30',
      bg: 'hover:bg-prhaar-good/10',
      activeBg: 'bg-prhaar-good/15 border-prhaar-good',
    },
    {
      id: 'DEGRADED',
      label: 'Degraded',
      count: counts.degraded,
      icon: AlertTriangle,
      color: 'text-prhaar-degraded',
      border: 'border-prhaar-degraded/30',
      bg: 'hover:bg-prhaar-degraded/10',
      activeBg: 'bg-prhaar-degraded/15 border-prhaar-degraded',
    },
    {
      id: 'OFFLINE',
      label: 'Offline',
      count: counts.offline,
      icon: AlertOctagon,
      color: 'text-prhaar-failed',
      border: 'border-prhaar-failed/30',
      bg: 'hover:bg-prhaar-failed/10',
      activeBg: 'bg-prhaar-failed/15 border-prhaar-failed',
    },
    {
      id: 'FROZEN',
      label: 'Frozen',
      count: counts.frozen,
      icon: PauseCircle,
      color: 'text-cyan-400',
      border: 'border-cyan-500/30',
      bg: 'hover:bg-cyan-500/10',
      activeBg: 'bg-cyan-500/15 border-cyan-400',
    },
    {
      id: 'STALE',
      label: 'Stale',
      count: counts.stale,
      icon: Clock,
      color: 'text-amber-400',
      border: 'border-amber-500/30',
      bg: 'hover:bg-amber-500/10',
      activeBg: 'bg-amber-500/15 border-amber-400',
    },
    {
      id: 'MAINTENANCE',
      label: 'Maintenance',
      count: counts.maintenance,
      icon: Wrench,
      color: 'text-purple-400',
      border: 'border-purple-500/30',
      bg: 'hover:bg-purple-500/10',
      activeBg: 'bg-purple-500/15 border-purple-400',
    },
    {
      id: 'COVERAGE_COMPROMISED',
      label: 'Coverage Compromised',
      count: counts.coverageCompromised,
      icon: EyeOff,
      color: 'text-rose-400',
      border: 'border-rose-500/40',
      bg: 'hover:bg-rose-500/10',
      activeBg: 'bg-rose-500/20 border-rose-400',
    },
  ]

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-7 gap-2.5">
      {items.map(item => {
        const Icon = item.icon
        const isActive = selectedFilter === item.id
        return (
          <button
            key={item.id}
            type="button"
            onClick={() => onSelectFilter(isActive ? null : item.id)}
            className={`flex flex-col justify-between p-3 rounded-lg border text-left transition-all cursor-pointer ${
              isActive ? item.activeBg : `border-white/[0.08] bg-[#0F141C] ${item.bg}`
            }`}
          >
            <div className="flex items-center justify-between gap-1 w-full text-slate-400 mb-2">
              <span className="text-[11px] font-medium tracking-wide uppercase">{item.label}</span>
              <Icon size={14} className={item.color} />
            </div>
            <div className="flex items-baseline justify-between w-full">
              <span className={`text-xl font-bold font-mono ${item.color}`}>{item.count}</span>
              <span className="text-[10px] font-mono text-slate-500">
                {counts.total > 0 ? `${Math.round((item.count / counts.total) * 100)}%` : '0%'}
              </span>
            </div>
          </button>
        )
      })}
    </div>
  )
}
