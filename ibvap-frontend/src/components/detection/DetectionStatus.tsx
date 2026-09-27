import { clsx } from 'clsx'
import type { DetectionFeedState, InferenceState } from '@/types/detection'
import { Badge } from '@/components/ui'
import { dotTone, textTone, toneForFeedState } from './detectionTone'
import { formatClock } from './detectionFormat'

const FEED_LABEL: Record<DetectionFeedState, string> = {
  READY: 'DETECTIONS ACTIVE',
  NO_OBJECTS: 'NO OBJECTS DETECTED',
  UNCONFIGURED: 'DETECTION NOT CONFIGURED',
  UNAVAILABLE: 'DETECTION DATA UNAVAILABLE',
  STALE: 'STALE',
  OFFLINE: 'DETECTOR OFFLINE',
}

const INFERENCE_LABEL: Record<InferenceState, string> = {
  READY: 'READY',
  PROCESSING: 'PROCESSING',
  DEGRADED: 'DEGRADED',
  UNAVAILABLE: 'UNAVAILABLE',
  OFFLINE: 'OFFLINE',
  UNKNOWN: 'UNKNOWN',
}

const INFERENCE_TONE: Record<InferenceState, 'info' | 'warning' | 'critical' | 'default' | 'cyan'> = {
  READY: 'cyan',
  PROCESSING: 'cyan',
  DEGRADED: 'warning',
  UNAVAILABLE: 'critical',
  OFFLINE: 'critical',
  UNKNOWN: 'default',
}

interface DetectionStatusProps {
  feedState?: DetectionFeedState | null
  inference?: InferenceState | null
  lastUpdatedAt?: string | null
  className?: string
}

/**
 * Feed-level detection status. Renders the detector's own availability
 * (inference) alongside feed freshness — honest states, never a fabricated
 * "LIVE" heartbeat. STALE carries the last-update time when known.
 */
export function DetectionStatus({ feedState, inference, lastUpdatedAt, className }: DetectionStatusProps) {
  if (!feedState) return null

  const tone = toneForFeedState(feedState)

  return (
    <div className={clsx('flex flex-wrap items-center gap-x-3 gap-y-1.5', className)}>
      <span className="flex items-center gap-1.5">
        <span className={clsx('h-1.5 w-1.5 rounded-full', dotTone(tone))} aria-hidden />
        <span className={clsx('font-mono text-[10px] uppercase tracking-wider', textTone(tone))}>
          {FEED_LABEL[feedState]}
        </span>
      </span>

      {inference && feedState !== 'UNAVAILABLE' && (
        <Badge variant={INFERENCE_TONE[inference]} size="sm">
          inference {INFERENCE_LABEL[inference]}
        </Badge>
      )}

      {lastUpdatedAt && (feedState === 'STALE' || feedState === 'READY') && (
        <span className="font-mono text-[10px] text-slate-500" title="Last feed update">
          last update {formatClock(lastUpdatedAt)}
        </span>
      )}

      {feedState === 'STALE' && (
        <span className="rounded border border-amber-500/30 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider text-amber-400/90">
          edge processing
        </span>
      )}
    </div>
  )
}