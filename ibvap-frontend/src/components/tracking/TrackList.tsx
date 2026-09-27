// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 6 — Track List (§48, §125).
//
// A table of track records, not observations. Rows render track confidence
// only when the backend supplies it (N/A otherwise). Feed states render
// explicit copy for UNAVAILABLE vs zero-tracks so the operator never mistakes
// a zero-track frame for a broken tracker (§168, §221).
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'
import { ChevronRight } from 'lucide-react'
import type { Track, TrackStatus, TrackingFeedState, TrackContinuityQuality, TrackSource } from '@/types/tracking'
import { Badge } from '@/components/ui'
import { formatClock, formatTrackClassLabel, formatConfidence, formatDuration, formatSpeed } from './trackFormat'
import { badgeTone, toneForStatus, toneForQuality, toneForSource, toneForFeedState } from './trackTone'

interface TrackListProps {
  tracks: Track[]
  selectedId?: string | null
  onSelect?: (track: Track) => void
  /** Feed availability so the list can distinguish zero vs unavailable. */
  feedState?: TrackingFeedState
  state?: 'idle' | 'loading' | 'ready' | 'error'
  error?: string | null
  onRetry?: () => void
  /** Hide the camera column (e.g. single-camera context list). */
  hideCamera?: boolean
  /** Empty copy for filtered-vs-zero cases (§168). */
  filtered?: boolean
  className?: string
}

const QUALITY_LABEL: Record<TrackContinuityQuality, string> = {
  STRONG: 'Strong',
  MODERATE: 'Moderate',
  WEAK: 'Weak',
  UNKNOWN: 'Unknown',
}

const SOURCE_LABEL: Record<TrackSource, string> = {
  LIVE: 'LIVE',
  EDGE: 'EDGE',
  CENTRAL: 'CENTRAL',
  DEMO: 'DEMO',
  UNKNOWN: '—',
}

/**
 * Track list — a table of track records, not observations. Rows render
 * confidence only when the backend supplies it (N/A otherwise). Feed states
 * render explicit copy for UNAVAILABLE vs zero-tracks vs filter-empty so the
 * operator never mistakes a zero-track frame for a broken tracker (§168, §221).
 */
export function TrackList({
  tracks,
  selectedId,
  onSelect,
  feedState,
  state = 'ready',
  error,
  onRetry,
  hideCamera = false,
  filtered = false,
  className,
}: TrackListProps) {
  if (state === 'loading') {
    return (
      <div className={clsx('space-y-2', className)} role="status" aria-label="Loading tracks">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-12 animate-pulse rounded-lg border border-white/5 bg-white/[0.02]" />
        ))}
      </div>
    )
  }

  if (state === 'error') {
    return (
      <div className={clsx('rounded-lg border border-red-500/25 bg-red-500/5 px-3 py-4 text-center', className)} role="alert">
        <p className="text-[11px] font-semibold text-red-400">TRACKING DATA UNAVAILABLE</p>
        <p className="mt-1 text-[10px] text-red-300/80">{error ?? 'Tracking service could not be reached.'}</p>
        {onRetry && (
          <button onClick={onRetry} className="mt-2 text-[11px] text-cyan-400 underline underline-offset-2 hover:text-cyan-300">
            Retry
          </button>
        )}
      </div>
    )
  }

  if (feedState === 'UNAVAILABLE' || feedState === 'OFFLINE' || feedState === 'UNKNOWN') {
    return (
      <div className={clsx('rounded-lg border border-white/10 px-3 py-4 text-center', className)} role="status">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          {feedState === 'UNKNOWN' ? 'Tracking state unknown' : feedState === 'OFFLINE' ? 'Tracker offline' : 'Tracking unavailable'}
        </p>
        <p className="mt-1 text-[10px] text-slate-500">
          {feedState === 'UNKNOWN'
            ? 'Insufficient telemetry to determine tracking state.'
            : 'Inference could not produce output for this camera.'}
        </p>
      </div>
    )
  }

  // Zero tracks is its own state — never shown as an empty list (§168, §221).
  if (tracks.length === 0) {
    return (
      <div className={clsx('rounded-lg border border-white/10 px-3 py-4 text-center', className)} role="status">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          {state === 'idle' ? 'Request pending' : filtered ? 'No tracks match these filters' : 'No active tracks'}
        </p>
        {filtered && <p className="mt-1 text-[10px] text-slate-500">Clear or change the display filters to see results.</p>}
      </div>
    )
  }

  return (
    <ul className={clsx('space-y-1.5', className)} aria-label="Track list">
      {tracks.map(t => {
        const stateTone = toneForStatus(t.status)
        const qualityTone = toneForQuality(t.continuityQuality ?? 'UNKNOWN')
        const sourceTone = toneForSource(t.source)
        const selected = selectedId === t.trackId
        return (
          <li key={t.trackId}>
            <button
              onClick={() => onSelect?.(t)}
              aria-selected={selected}
              aria-label={`${formatTrackClassLabel(t.objectClass)} track, ${formatConfidence(t.confidence)}, ${STATUS_LABEL[t.status].toLowerCase()}`}
              className={clsx(
                'w-full flex items-center gap-2 rounded-lg border px-2.5 py-2 text-left transition-colors',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/60',
                selected
                  ? 'border-cyan-500/40 bg-cyan-500/5'
                  : 'border-white/[0.06] bg-white/[0.02] hover:border-cyan-400/25 hover:bg-white/[0.04]'
              )}
            >
              <span
                className={clsx(
                  'rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase',
                  t.objectClass === 'PERSON' && 'bg-sky-500/10 text-sky-300',
                  t.objectClass === 'VEHICLE' && 'bg-amber-500/10 text-amber-300',
                  t.objectClass === 'ANIMAL' && 'bg-emerald-500/10 text-emerald-300',
                  t.objectClass === 'OBJECT' && 'bg-slate-500/10 text-slate-300',
                  t.objectClass === 'UNKNOWN' && 'bg-purple-500/10 text-purple-300'
                )}
              >
                {t.objectClass}
              </span>
              <span className="flex min-w-0 flex-1 flex-col">
                <span className="flex items-center gap-1.5 truncate text-[11px] text-slate-200">
                  {formatTrackClassLabel(t.objectClass)}
                  {t.trackId && <ChevronRight size={10} className="text-slate-600" aria-hidden />}
                  {!hideCamera && <span className="font-mono text-[10px] text-slate-500">{t.cameraId}</span>}
                  <span className="font-mono text-[10px] text-slate-600">{formatClock(t.lastSeenAt)}</span>
                </span>
                <span className="flex items-center gap-1.5 text-[10px] text-slate-500">
                  <span className="font-mono">{formatConfidence(t.confidence)}</span>
                  <span>·</span>
                  <span>quality {QUALITY_LABEL[t.continuityQuality ?? 'UNKNOWN']}</span>
                  {t.source !== 'UNKNOWN' && (
                    <>
                      <span>·</span>
                      <span className="font-mono">{SOURCE_LABEL[t.source]}</span>
                    </>
                  )}
                </span>
              </span>
              <span className="shrink-0">
                <Badge variant={badgeTone(stateTone)} size="sm" dot>
                  {t.status === 'ACTIVE' ? 'OK' : t.status}
                </Badge>
              </span>
            </button>
          </li>
        )
      })}
    </ul>
  )
}

const STATUS_LABEL: Record<Track['status'], string> = {
  ACTIVE: 'ACTIVE',
  TENTATIVE: 'TENTATIVE',
  LOST: 'LOST',
  REACQUIRED: 'REACQUIRED',
  ENDED: 'ENDED',
  STALE: 'STALE',
  INVALID: 'INVALID',
  UNKNOWN: 'UNKNOWN',
}