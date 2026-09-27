import { Link } from 'react-router-dom'
import { clsx } from 'clsx'
import type { CameraHealth } from '@/types/cameraHealth'
import { CameraHealthDot } from './CameraHealthDot'
import { TONE, toneForStatus } from './healthTone'
import { formatMetricValue } from './healthFormat'

/**
 * COMPACT presentation for the Live Camera Wall (and twin markers):
 * camera id + dot + status word, with a restrained coverage flag only when
 * the backend reports degraded/compromised coverage. Always links to the
 * existing single-camera route — no new routes.
 */
export function CameraHealthTile({ health }: { health: CameraHealth }) {
  const tone = TONE[toneForStatus(health.status)]
  const compromised = health.operationalImpact.coverage === 'COMPROMISED'
  const degradedCoverage = health.operationalImpact.coverage === 'DEGRADED'
  const fps = health.stream.fps !== null && health.stream.expectedFps !== null
    ? `${formatMetricValue(health.stream.fps, 'fps')} / ${health.stream.expectedFps}`
    : health.stream.fps !== null
      ? formatMetricValue(health.stream.fps, 'fps')
      : null

  return (
    <Link
      to={`/camera/${health.cameraId}`}
      aria-label={`Camera ${health.cameraId} status ${health.status.toLowerCase()}${compromised ? ', coverage compromised' : ''}`}
      className={clsx(
        'flex items-center justify-between gap-2 rounded-lg border px-2.5 py-2 transition-colors',
        'border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.04] hover:border-cyan-400/30',
        'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/60'
      )}
    >
      <span className="flex min-w-0 items-center gap-2">
        <CameraHealthDot status={health.status} cameraId={health.cameraId} />
        <span className="font-mono text-[11px] text-slate-200">{health.cameraId}</span>
      </span>
      <span className="flex shrink-0 items-center gap-2">
        {fps && (
          <span className="font-mono text-[10px] text-slate-500 tabular-nums">{fps}</span>
        )}
        {(compromised || degradedCoverage) && (
          <span className={clsx(
            'font-mono text-[9px] uppercase',
            compromised ? 'text-prhaar-failed' : 'text-prhaar-degraded'
          )}>
            {compromised ? 'Coverage compromised' : 'Coverage degraded'}
          </span>
        )}
        <span className={clsx('font-mono text-[10px]', tone.text)}>{health.status}</span>
      </span>
    </Link>
  )
}
