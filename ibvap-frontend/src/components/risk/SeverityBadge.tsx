// ─────────────────────────────────────────────────────────────────────────────
// Component 1 — SeverityBadge & RiskScoreGauge
// Canonical representation of risk severity bands and observation reliability.
// Strict adherence to PRHAAR design tokens and semantic separation: Risk ≠ Confidence.
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'
import { Badge } from '@/components/ui'
import type { Severity } from '@/types'

const VARIANT: Record<Severity, 'critical' | 'warning' | 'info' | 'safe'> = {
  LOW:      'safe',
  MEDIUM:   'warning',
  HIGH:     'critical',
  CRITICAL: 'critical',
}

export function SeverityBadge({
  severity,
  score,
  size = 'md',
}: {
  severity: Severity
  score?: number | null
  size?: 'sm' | 'md'
}) {
  return (
    <span className="inline-flex items-center gap-1.5 font-mono">
      <Badge variant={VARIANT[severity]} dot size={size}>
        {severity}
      </Badge>
      {typeof score === 'number' && (
        <span className={clsx(
          'font-mono tabular-nums font-semibold',
          size === 'md' ? 'text-sm text-slate-100' : 'text-xs text-slate-300'
        )}>
          {score}
        </span>
      )}
    </span>
  )
}

/**
 * Reliability badge displaying sensor/observation reliability (HIGH / MEDIUM / LOW).
 * Intentionally separated from threat severity so operators never confuse data quality with threat level.
 */
export function ReliabilityBadge({
  reliability,
  size = 'md',
}: {
  reliability?: string | null
  size?: 'sm' | 'md'
}) {
  const rel = (reliability || 'UNKNOWN').toUpperCase()
  let variant: 'safe' | 'warning' | 'critical' | 'offline' = 'offline'
  let label = rel

  if (rel === 'HIGH') {
    variant = 'safe'
  } else if (rel === 'MEDIUM') {
    variant = 'warning'
  } else if (rel === 'LOW') {
    variant = 'critical'
  }

  return (
    <span className="inline-flex items-center gap-1 font-mono" title="Observation reliability measures sensor data quality, not threat level">
      <span className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">Reliability:</span>
      <Badge variant={variant} size={size}>
        {label}
      </Badge>
    </span>
  )
}

/**
 * Transparent gauge showing exact score within [0, 100] and the 4 canonical severity bands:
 * LOW [0–39], MEDIUM [40–64], HIGH [65–84], CRITICAL [85–100].
 */
export function RiskScoreGauge({
  score,
  severity,
  className,
}: {
  score: number
  severity: Severity
  className?: string
}) {
  const bandColor: Record<Severity, string> = {
    LOW:      'bg-emerald-400',
    MEDIUM:   'bg-amber-400',
    HIGH:     'bg-red-400',
    CRITICAL: 'bg-red-500',
  }

  const clampedScore = Math.max(0, Math.min(100, score))

  return (
    <div className={clsx('space-y-1.5', className)}>
      <div className="relative h-2.5 w-full rounded-full bg-[#16202c] overflow-hidden border border-white/5">
        {/* Band thresholds background */}
        <div className="absolute inset-y-0 left-0 bg-emerald-500/10 border-r border-white/10" style={{ width: '40%' }} title="LOW (0–39)" />
        <div className="absolute inset-y-0 left-[40%] bg-amber-500/10 border-r border-white/10" style={{ width: '25%' }} title="MEDIUM (40–64)" />
        <div className="absolute inset-y-0 left-[65%] bg-red-500/10 border-r border-white/10" style={{ width: '20%' }} title="HIGH (65–84)" />
        <div className="absolute inset-y-0 left-[85%] bg-red-600/20" style={{ width: '15%' }} title="CRITICAL (85–100)" />

        {/* Dynamic active score fill */}
        <div
          className={clsx('absolute inset-y-0 transition-all duration-500 rounded-full', bandColor[severity])}
          style={{ width: `${Math.max(2, clampedScore)}%` }}
        />
      </div>

      <div className="flex justify-between text-[10px] text-slate-500 font-mono select-none px-0.5">
        <span>0</span>
        <span className="text-slate-400">39 / 40</span>
        <span className="text-slate-400">64 / 65</span>
        <span className="text-slate-400">84 / 85</span>
        <span>100</span>
      </div>
    </div>
  )
}