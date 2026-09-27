// ANPRSummaryCards.tsx — 4 stat cards using existing StatCard primitive
import { Activity, Eye, AlertTriangle, Camera } from 'lucide-react'
import { StatCard, StatCardSkeleton } from '@/components/ui'
import type { ANPRSummary } from '@/types/anpr'

interface ANPRSummaryCardsProps {
  summary: ANPRSummary | null
  loading?: boolean
}

export function ANPRSummaryCards({ summary, loading }: ANPRSummaryCardsProps) {
  if (loading) {
    return (
      <div className="grid grid-cols-2 gap-3">
        {[1, 2, 3, 4].map(i => <StatCardSkeleton key={i} />)}
      </div>
    )
  }

  const val = (n: number | undefined) => (summary ? String(n ?? 0) : '—')

  return (
    <div className="grid grid-cols-2 gap-3">
      <StatCard
        label="Total Plate Reads"
        value={val(summary?.totalReads)}
        icon={<Activity size={16} />}
      />
      <StatCard
        label="Readable Plates"
        value={val(summary?.readablePlates)}
        icon={<Eye size={16} />}
        variant="safe"
      />
      <StatCard
        label="Partial / Unreadable"
        value={summary ? String((summary.partialReads ?? 0) + (summary.unreadablePlates ?? 0)) : '—'}
        icon={<AlertTriangle size={16} />}
        variant={summary && (summary.partialReads + summary.unreadablePlates) > 0 ? 'warning' : 'default'}
      />
      <StatCard
        label="Cameras Reporting"
        value={val(summary?.camerasReporting)}
        icon={<Camera size={16} />}
      />
    </div>
  )
}