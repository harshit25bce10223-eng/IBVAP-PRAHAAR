// ─────────────────────────────────────────────────────────────────────────────
// KpiSummaryRow — compact operational summary strip (spec §11).
//
// Four KPI cards (Cameras, Incidents, Entities, Health) plus an inline risk
// breakdown. Content-first, no decorative gradients, no glassmorphism.
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'
import { Camera, AlertTriangle, Users, HeartPulse } from 'lucide-react'
import { Badge } from '@/components/ui'
import type { DashboardKpis } from '@/types'
import { RISK_BAND_STYLE } from '@/types'

interface Props {
  kpis: DashboardKpis
  className?: string
}

export function KpiSummaryRow({ kpis, className }: Props) {
  return (
    <div className={clsx('flex gap-3 min-h-0', className)}>
      <KpiCard
        icon={<Camera size={14} className="text-ssb-green-bright" aria-hidden />}
        label="TOTAL CAMERAS"
        value={kpis.totalCameras}
        detail={`${kpis.onlineCameras} Online · ${kpis.offlineCameras} Offline`}
        accent="green"
      />
      <KpiCard
        icon={<AlertTriangle size={14} className="text-ssb-amber-bright" aria-hidden />}
        label="ACTIVE INCIDENTS"
        value={kpis.activeIncidents}
        detail={`${kpis.incidentHigh} High · ${kpis.incidentMedium} Medium`}
        accent="amber"
      />
      <KpiCard
        icon={<Users size={14} className="text-ssb-green-bright" aria-hidden />}
        label="LIVE ENTITIES"
        value={kpis.livePersons + kpis.liveVehicles + kpis.liveAnimals}
        detail={`${kpis.livePersons} Person · ${kpis.liveVehicles} Vehicle · ${kpis.liveAnimals} Animal`}
        accent="green"
      />
      <KpiCard
        icon={<HeartPulse size={14} className="text-ssb-green-bright" aria-hidden />}
        label="SYSTEM HEALTH"
        value={`${kpis.systemHealthPct}%`}
        detail={kpis.healthLabel}
        accent="green"
      />
      <RiskChips summary={kpis.riskSummary} />
    </div>
  )
}

// ─── Single KPI card ────────────────────────────────────────────────────────

function KpiCard({
  icon,
  label,
  value,
  detail,
  accent,
}: {
  icon: React.ReactNode
  label: string
  value: string | number
  detail: string
  accent: 'green' | 'amber' | 'red'
}) {
  const bg = accent === 'amber'
    ? 'bg-ssb-amber/8 border-ssb-amber/20'
    : accent === 'red'
      ? 'bg-ssb-red/8 border-ssb-red/20'
      : 'bg-ssb-green/8 border-ssb-green/20'

  return (
    <div className={clsx('flex-[1] min-w-0 flex flex-col justify-center gap-1.5 rounded-md border px-4 py-3', bg)}>
      <div className="flex items-center gap-2">
        {icon}
        <span className="text-[9px] font-semibold tracking-[0.18em] text-ssb-text-muted uppercase">{label}</span>
      </div>
      <div className="text-[22px] font-bold text-ssb-white font-mono leading-none">{value}</div>
      <span className="text-[10px] text-ssb-text-muted leading-tight truncate">{detail}</span>
    </div>
  )
}

// ─── Risk breakdown chips ───────────────────────────────────────────────────

function RiskChips({ summary }: { summary: { critical: number; high: number; medium: number; low: number } }) {
  const bands = [
    { label: 'CRITICAL', count: summary.critical, key: 'critical' as const },
    { label: 'HIGH',     count: summary.high,     key: 'high'     as const },
    { label: 'MEDIUM',   count: summary.medium,   key: 'medium'   as const },
    { label: 'LOW',      count: summary.low,       key: 'low'      as const },
  ]

  return (
    <div className="flex flex-col justify-center gap-1.5 pl-3 border-l border-ssb-border/50">
      {bands.map(b => {
        const style = RISK_BAND_STYLE[b.key.toUpperCase() as keyof typeof RISK_BAND_STYLE]
        return (
          <div key={b.key} className="flex items-center gap-2">
            <span className={clsx('h-1.5 w-1.5 rounded-full', style.dot)} />
            <span className="text-[10px] font-medium text-ssb-text-muted w-[50px]">{b.label}</span>
            <Badge variant={style.badge} size="sm" className="font-mono">{String(b.count).padStart(2, '0')}</Badge>
          </div>
        )
      })}
    </div>
  )
}