// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 6 — Track Timeline (§55, §102).
//
// Chronological list of track observations. Uses backend-supplied observedAt
// timestamps. Does not create timeline entries from frontend clock.
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'
import { ChevronRight } from 'lucide-react'
import type { Track, TrackObservation } from '@/types/tracking'
import { formatClock, formatConfidence, formatSpeed, formatSourceLabel } from './trackFormat'
import { TRACK_CLASS_STROKE, TRACK_CLASS_CHIP } from './trackTone'

interface TrackTimelineProps {
  observations: TrackObservation[]
  /** Track class — observations do not carry a class; the chip shows the
   *  track's class when provided, and is omitted otherwise (never assumed). */
  objectClass?: Track['objectClass'] | null
  /** Optional filter to highlight a specific observation */
  highlightedId?: string | null
  /** Compact mode for inspector embedding */
  compact?: boolean
}

export function TrackTimeline({ observations, objectClass, highlightedId, compact = false }: TrackTimelineProps) {
  if (observations.length === 0) {
    return (
      <div className={clsx('rounded-lg border border-[#1e2d40] bg-[#0d1117] p-4 text-center', !compact && 'min-h-[120px]')}>
        <p className="text-[11px] text-slate-500">No observation history available for this track.</p>
      </div>
    )
  }

  return (
    <div className={clsx('space-y-1.5', !compact && 'max-h-64 overflow-y-auto pr-1')}>
      {observations
        .slice()
        .sort((a, b) => new Date(a.observedAt).getTime() - new Date(b.observedAt).getTime())
        .map((obs) => {
          const highlighted = highlightedId === obs.observationId
          return (
            <div
              key={obs.observationId}
              className={clsx(
                'flex items-center gap-2 rounded-lg border px-2.5 py-2 text-left transition-colors',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/60',
                highlighted
                  ? 'border-cyan-500/40 bg-cyan-500/5'
                  : 'border-white/[0.06] bg-white/[0.02] hover:border-cyan-400/25 hover:bg-white/[0.04]'
              )}
            >
              {objectClass && (
                <span
                  className="rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase shrink-0"
                  style={{
                    backgroundColor: `${TRACK_CLASS_STROKE[objectClass]}1A`,
                    color: TRACK_CLASS_STROKE[objectClass],
                  }}
                >
                  {TRACK_CLASS_CHIP[objectClass]}
                </span>
              )}
              <span className="flex min-w-0 flex-1 flex-col">
                <span className="flex items-center gap-1.5 truncate text-[11px] text-slate-200">
                  {formatClock(obs.observedAt)}
                  <span className="font-mono text-[10px] text-slate-500">{obs.cameraId}</span>
                  <ChevronRight size={10} className="text-slate-600" aria-hidden />
                </span>
                <span className="flex items-center gap-1.5 text-[10px] text-slate-500">
                  <span className="font-mono">{formatConfidence(obs.confidence)}</span>
                  {obs.velocity !== null && obs.velocity !== undefined && (
                    <>
                      <span>·</span>
                      <span className="font-mono">{formatSpeed(obs.velocity)}</span>
                    </>
                  )}
                  <span>·</span>
                  <span className="font-mono">{formatSourceLabel(obs.source)}</span>
                </span>
              </span>
              {obs.sequence !== null && obs.sequence !== undefined && (
                <span className="shrink-0 font-mono text-[10px] text-slate-400">#{obs.sequence}</span>
              )}
            </div>
          )
        })}
    </div>
  )
}