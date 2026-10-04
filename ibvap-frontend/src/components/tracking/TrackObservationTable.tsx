// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 6 — Track Observation Table (§13, §14, §23)
//
// Exact column contract: Time · Detection ID · Camera · BBox · Confidence ·
// Quality · Track State · Provider. Monospace for IDs and timestamps.
//
// Track State is DERIVED from recorded lifecycle transitions (state at the
// observation's timestamp); when no transition record covers that instant the
// cell shows '—' — state is never assumed. Detection IDs deep-link into the
// Detection Intelligence workspace (Component 5 remains the detection source;
// no detection data is duplicated into the tracking domain).
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'
import { Link } from 'react-router-dom'
import type { TrackLifecycleEvent, TrackObservation } from '@/types/tracking'
import { formatBBox, formatClock, formatConfidence, formatSourceLabel } from './trackFormat'
import { lifecycleStateAt } from './trackLifecycle'
import { toneForQuality, badgeTone } from './trackTone'
import { StateChip } from './TrackLifecycleTimeline'
import { Badge } from '@/components/ui'

interface TrackObservationTableProps {
  observations: TrackObservation[]
  /** Recorded lifecycle transitions — used only to derive Track State per row. */
  history: TrackLifecycleEvent[]
  /** Compact mode for constrained panels. */
  compact?: boolean
}

const HEAD_CELL =
  'px-2 py-1.5 text-left text-[10px] font-semibold uppercase tracking-wider text-slate-500 whitespace-nowrap'
const BODY_CELL = 'px-2 py-1.5 text-[11px] text-slate-300 whitespace-nowrap'

export function TrackObservationTable({ observations, history, compact = false }: TrackObservationTableProps) {
  if (observations.length === 0) {
    return (
      <div className="rounded-lg border border-border bg-bg p-4 text-center">
        <p className="text-[11px] text-slate-500">No observations recorded for this track.</p>
      </div>
    )
  }

  const ordered = observations
    .slice()
    .sort((a, b) => new Date(a.observedAt).getTime() - new Date(b.observedAt).getTime())

  return (
    <div className={clsx('overflow-x-auto rounded-lg border border-border', !compact && 'max-h-96 overflow-y-auto')}>
      <table className="w-full border-collapse">
        <caption className="sr-only">
          Track observations in chronological order. Track State is derived from recorded lifecycle transitions;
          the Provider column reflects the source recorded on each observation.
        </caption>
        <thead className="sticky top-0 z-10 bg-surface">
          <tr className="border-b border-border">
            <th scope="col" className={HEAD_CELL}>Time</th>
            <th scope="col" className={HEAD_CELL}>Detection ID</th>
            <th scope="col" className={HEAD_CELL}>Camera</th>
            <th scope="col" className={HEAD_CELL}>BBox</th>
            <th scope="col" className={HEAD_CELL}>Confidence</th>
            <th scope="col" className={HEAD_CELL}>Quality</th>
            <th scope="col" className={HEAD_CELL}>Track State</th>
            <th scope="col" className={HEAD_CELL}>Provider</th>
          </tr>
        </thead>
        <tbody>
          {ordered.map(obs => {
            const state = lifecycleStateAt(history, obs.observedAt)
            return (
              <tr key={obs.observationId} className="border-b border-white/[0.04] last:border-0 hover:bg-white/[0.02]">
                <td className={clsx(BODY_CELL, 'font-mono tabular-nums text-slate-200')}>
                  {formatClock(obs.observedAt)}
                </td>
                <td className={BODY_CELL}>
                  {obs.detectionId ? (
                    <Link
                      to={`/detections?search=${encodeURIComponent(obs.detectionId)}`}
                      className="font-mono text-cyan-300 hover:underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/60 rounded"
                      title="Open this detection in Detection Intelligence (Component 5)"
                    >
                      {obs.detectionId}
                    </Link>
                  ) : (
                    <span className="font-mono text-slate-500" title="No detection reference recorded for this observation">—</span>
                  )}
                </td>
                <td className={clsx(BODY_CELL, 'font-mono')}>{obs.cameraId}</td>
                <td className={clsx(BODY_CELL, 'font-mono text-[10px] text-slate-400')}>
                  {obs.bbox ? formatBBox(obs.bbox.x, obs.bbox.y, obs.bbox.width, obs.bbox.height) : 'N/A'}
                </td>
                <td className={clsx(BODY_CELL, 'font-mono')}>{formatConfidence(obs.confidence)}</td>
                <td className={BODY_CELL}>
                  {obs.quality ? (
                    <Badge variant={badgeTone(toneForQuality(obs.quality))} size="sm">
                      {obs.quality}
                    </Badge>
                  ) : (
                    <span className="font-mono text-[10px] text-slate-500">—</span>
                  )}
                </td>
                <td className={BODY_CELL}>
                  <StateChip status={state} />
                </td>
                <td className={clsx(BODY_CELL, 'font-mono text-slate-400')}>{formatSourceLabel(obs.source)}</td>
              </tr>
            )
          })}
        </tbody>
      </table>
      <p className="border-t border-border bg-surface px-2 py-1.5 text-[9px] leading-relaxed text-slate-500">
        Track State is derived from recorded lifecycle transitions and shows '—' where no record covers that instant.
        The Provider column reflects the source recorded per observation (LIVE / EDGE / CENTRAL / DEMO).
      </p>
    </div>
  )
}
