import { clsx } from 'clsx'
import type { HealthMetric } from '@/types/cameraHealth'
import { TONE, toneForMetricStatus } from './healthTone'
import { formatMetricValue } from './healthFormat'

/**
 * One dimension row: label → value → backend status word. Missing values
 * render N/A; the backend `reason` (not a frontend threshold) explains
 * non-good states. `title` carries the metric key for tooltips.
 */
export function CameraHealthMetric({ metric }: { metric: HealthMetric }) {
  const tone = TONE[toneForMetricStatus(metric.status)]
  return (
    <div className="flex items-baseline justify-between gap-2 py-1" title={metric.reason ?? metric.label}>
      <dt className="text-[11px] text-slate-500">{metric.label}</dt>
      <dd className="flex items-baseline gap-1.5 text-right">
        <span className="font-mono text-[11px] text-slate-200 tabular-nums">
          {formatMetricValue(metric.value, metric.unit)}
        </span>
        <span className={clsx('font-mono text-[10px] uppercase', tone.text)}>
          {metric.status === 'GOOD' ? '' : metric.status}
        </span>
      </dd>
    </div>
  )
}
