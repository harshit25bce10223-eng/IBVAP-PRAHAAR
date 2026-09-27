import { clsx } from 'clsx'
import type { ReactNode } from 'react'
import { TrendingDown, TrendingUp, Minus } from 'lucide-react'

type TrendDir = 'up' | 'down' | 'flat'

interface StatCardProps {
  label: string
  value: string | number
  icon?: ReactNode
  trendValue?: string
  trendDir?: TrendDir
  trendLabel?: string
  variant?: 'default' | 'critical' | 'warning' | 'safe'
  className?: string
}

const trendIcon: Record<TrendDir, ReactNode> = {
  up:   <TrendingUp  size={12} />,
  down: <TrendingDown size={12} />,
  flat: <Minus       size={12} />,
}

const trendColor: Record<TrendDir, string> = {
  up:   'text-emerald-400',
  down: 'text-red-400',
  flat: 'text-slate-500',
}

const variantBorder: Record<string, string> = {
  default:  'border-[#1e2d40]',
  critical: 'border-red-500/30',
  warning:  'border-amber-500/30',
  safe:     'border-emerald-500/30',
}

export function StatCard({
  label, value, icon, trendValue, trendDir = 'flat', trendLabel, variant = 'default', className,
}: StatCardProps) {
  return (
    <div
      className={clsx(
        'rounded-xl border bg-[#0d1117] p-5 flex flex-col gap-3',
        'transition-colors hover:border-[#2a3f58]',
        variantBorder[variant],
        className
      )}
    >
      <div className="flex items-start justify-between">
        <span className="text-xs font-medium text-slate-500 uppercase tracking-widest">{label}</span>
        {icon && (
          <span className="text-slate-600 p-1.5 rounded-lg bg-white/5">{icon}</span>
        )}
      </div>
      <div className="text-3xl font-bold text-slate-100 font-mono">{value}</div>
      {(trendValue || trendLabel) && (
        <div className={clsx('flex items-center gap-1 text-xs', trendColor[trendDir])}>
          {trendDir && trendIcon[trendDir]}
          {trendValue && <span className="font-medium">{trendValue}</span>}
          {trendLabel && <span className="text-slate-500">{trendLabel}</span>}
        </div>
      )}
    </div>
  )
}
