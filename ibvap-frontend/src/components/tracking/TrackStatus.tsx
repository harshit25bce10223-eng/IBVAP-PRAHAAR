// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 6 — Track Status Display (§83, §84, §120).
//
// Feed-level tracking status. Renders the tracker's own availability
// alongside feed freshness — honest states, never a fabricated
// "LIVE" heartbeat. STALE carries the last-update time when known.
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'
import type { TrackingFeedState, TrackSource } from '@/types/tracking'
import { Badge } from '@/components/ui'
import { toneForFeedState, dotTone, textTone, toneForSource, badgeTone } from './trackTone'
import { formatClock } from './trackFormat'

const FEED_LABEL: Record<TrackingFeedState, string> = {
  READY: 'TRACKS ACTIVE',
  PROCESSING: 'PROCESSING',
  DEGRADED: 'DEGRADED',
  UNAVAILABLE: 'TRACKING DATA UNAVAILABLE',
  STALE: 'STALE',
  OFFLINE: 'TRACKER OFFLINE',
  UNKNOWN: 'UNKNOWN',
}

const INFERENCE_LABEL: Record<TrackingFeedState, string> = {
  READY: 'READY',
  PROCESSING: 'PROCESSING',
  DEGRADED: 'DEGRADED',
  UNAVAILABLE: 'UNAVAILABLE',
  STALE: 'STALE',
  OFFLINE: 'OFFLINE',
  UNKNOWN: 'UNKNOWN',
}

const INFERENCE_TONE: Record<TrackingFeedState, 'info' | 'warning' | 'critical' | 'default' | 'cyan'> = {
  READY: 'cyan',
  PROCESSING: 'cyan',
  DEGRADED: 'warning',
  UNAVAILABLE: 'critical',
  STALE: 'warning',
  OFFLINE: 'critical',
  UNKNOWN: 'default',
}

const SOURCE_LABEL: Record<TrackSource, string> = {
  LIVE: 'LIVE',
  EDGE: 'EDGE',
  CENTRAL: 'CENTRAL',
  DEMO: 'DEMO',
  UNKNOWN: '—',
}

interface TrackStatusProps {
  feedState?: TrackingFeedState | null
  inference?: TrackingFeedState | null
  source?: TrackSource | null
  lastUpdatedAt?: string | null
  className?: string
}

/**
 * Feed-level tracking status. Renders the detector's own availability
 * (inference) alongside feed freshness — honest states, never a fabricated
 * "LIVE" heartbeat. STALE carries the last-update time when known.
 */
export function TrackStatus({ feedState, inference, source, lastUpdatedAt, className }: TrackStatusProps) {
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
          tracker {INFERENCE_LABEL[inference]}
        </Badge>
      )}

      {source && (
        <Badge variant={badgeTone(toneForSource(source))} size="sm" dot>
          {SOURCE_LABEL[source]}
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