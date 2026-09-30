// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 6 — Track Lifecycle Timeline (§8, §9, §10)
//
// Renders RECORDED state transitions only (TrackHistory records from the
// backend): TENTATIVE ↓ ACTIVE ↓ LOST ↓ REACQUIRED ↓ ACTIVE ↓ ENDED.
// Each row shows timestamp, revision, old → new state, and the recorded
// reason where the backend supplied one. Nothing is synthesized here.
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'
import { ArrowRight, History } from 'lucide-react'
import type { TrackLifecycleEvent, TrackStatus } from '@/types/tracking'
import { formatClock, formatDate } from './trackFormat'
import { sortNewestFirst } from './trackLifecycle'
import { toneForStatus, type TrackTone } from './trackTone'

const TONE_CHIP: Record<TrackTone, string> = {
  cyan: 'border-cyan-500/40 bg-cyan-500/10 text-cyan-300',
  info: 'border-sky-500/40 bg-sky-500/10 text-sky-300',
  warning: 'border-amber-500/40 bg-amber-500/10 text-amber-300',
  critical: 'border-red-500/40 bg-red-500/10 text-red-300',
  default: 'border-slate-600/40 bg-slate-600/10 text-slate-300',
  emerald: 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300',
  amber: 'border-amber-500/40 bg-amber-500/10 text-amber-300',
}

/** Compact state chip shared with the observation table (§13). */
export function StateChip({ status, muted = false }: { status: TrackStatus | null; muted?: boolean }) {
  if (!status) {
    return <span className="font-mono text-[10px] text-slate-500" title="State not recorded for this instant">—</span>
  }
  return (
    <span
      className={clsx(
        'inline-flex items-center rounded border px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase tracking-wide',
        muted ? 'border-slate-700/60 bg-slate-800/40 text-slate-400' : TONE_CHIP[toneForStatus(status)]
      )}
    >
      {status}
    </span>
  )
}

interface TrackLifecycleTimelineProps {
  history: TrackLifecycleEvent[]
  /** Compact mode for embedding in side panels. */
  compact?: boolean
}

export function TrackLifecycleTimeline({ history, compact = false }: TrackLifecycleTimelineProps) {
  if (history.length === 0) {
    return (
      <div className="rounded-lg border border-[#1e2d40] bg-[#080c12] p-4 text-center">
        <History size={16} className="mx-auto mb-1.5 text-slate-600" aria-hidden />
        <p className="text-[11px] text-slate-400">No lifecycle transitions recorded for this track.</p>
        <p className="mt-0.5 text-[10px] text-slate-500">
          Transition records appear here as the backend records state changes for this track.
        </p>
      </div>
    )
  }

  return (
    <ol className={clsx('space-y-1.5', !compact && 'max-h-72 overflow-y-auto pr-1')} aria-label="Lifecycle transitions, newest first">
      {sortNewestFirst(history).map(event => (
        <li
          key={event.historyId}
          className="rounded-lg border border-white/[0.06] bg-white/[0.02] px-2.5 py-2"
        >
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="font-mono text-[11px] text-slate-200 tabular-nums">
              {formatDate(event.timestamp)} {formatClock(event.timestamp)}
            </span>
            <span className="rounded border border-slate-700/60 bg-slate-800/40 px-1 py-0.5 font-mono text-[9px] text-slate-400" title="Record revision">
              rev {event.revision}
            </span>
            <span className="inline-flex items-center gap-1">
              {event.oldStatus ? <StateChip status={event.oldStatus} muted /> : <span className="font-mono text-[10px] text-slate-500">new track</span>}
              <ArrowRight size={10} className="text-slate-600" aria-hidden />
              <StateChip status={event.newStatus} />
            </span>
          </div>
          {event.reason && <p className="mt-1 text-[10px] text-slate-400">{event.reason}</p>}
          <div className="mt-0.5 flex flex-wrap items-center gap-2 font-mono text-[9px] text-slate-500">
            {event.triggerDetectionId && <span>trigger {event.triggerDetectionId}</span>}
            {event.provider && <span>provider {event.provider}{event.providerVersion ? ` v${event.providerVersion}` : ''}</span>}
          </div>
        </li>
      ))}
    </ol>
  )
}
