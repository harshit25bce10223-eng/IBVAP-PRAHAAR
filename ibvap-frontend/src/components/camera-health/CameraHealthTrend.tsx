import { useMemo } from 'react'
import { clsx } from 'clsx'
import type { HealthTrend } from '@/types/cameraHealth'
import { TONE, toneForTrend } from './healthTone'

const W = 120
const H = 28

/**
 * Compact sparkline answering "what changed": current direction, signed
 * delta, window and persistence. Points come pre-computed from the record —
 * thin restrained line only, no fill, no glow, no dots.
 */
export function CameraHealthTrend({ trend }: { trend: HealthTrend }) {
  const tone = TONE[toneForTrend(trend.direction)]

  const points = useMemo(() => {
    const s = trend.series
    if (s.length < 2) return null
    const min = Math.min(...s)
    const max = Math.max(...s)
    const span = max - min || 1
    return s
      .map((v, i) => `${((i / (s.length - 1)) * W).toFixed(1)},${(H - 3 - ((v - min) / span) * (H - 6)).toFixed(1)}`)
      .join(' ')
  }, [trend.series])

  return (
    <div className="py-1.5" role="img" aria-label={`${trend.label} trend: ${trend.direction.toLowerCase()}`}>
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-[11px] text-slate-500">{trend.label}</span>
        <span className="flex items-baseline gap-1.5">
          {trend.deltaPercent !== null && (
            <span className="font-mono text-[11px] text-slate-200 tabular-nums">
              {trend.deltaPercent > 0 ? `↑ +${trend.deltaPercent}%` : trend.deltaPercent < 0 ? `↓ ${trend.deltaPercent}%` : '± 0%'}
            </span>
          )}
          <span className={clsx('font-mono text-[10px] uppercase', tone.text)}>{trend.direction}</span>
        </span>
      </div>
      <div className="mt-1 flex items-center gap-2">
        {points ? (
          <svg viewBox={`0 0 ${W} ${H}`} className={clsx('h-7 w-[120px] shrink-0', tone.text)} aria-hidden>
            <polyline points={points} fill="none" stroke="currentColor" strokeWidth={1.5} strokeLinejoin="round" strokeLinecap="round" />
          </svg>
        ) : (
          <span className="font-mono text-[10px] text-slate-600">no series</span>
        )}
        <span className="font-mono text-[10px] text-slate-600">
          {[trend.window, trend.persistence].filter(Boolean).join(' · ') || 'window N/A'}
        </span>
      </div>
    </div>
  )
}
