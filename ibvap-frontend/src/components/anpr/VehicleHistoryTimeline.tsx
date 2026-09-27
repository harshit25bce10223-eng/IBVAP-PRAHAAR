// VehicleHistoryTimeline.tsx — Vertical multi-camera sighting timeline
import { Link } from 'react-router-dom'
import { clsx } from 'clsx'
import { VehicleClassBadge } from './VehicleClassBadge'
import type { VehicleHistory } from '@/types/anpr'

interface VehicleHistoryTimelineProps {
  history: VehicleHistory
  className?: string
}

function fmtTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', hour12: false })
  } catch { return iso }
}

export function VehicleHistoryTimeline({ history, className }: VehicleHistoryTimelineProps) {
  const sightings = [...history.sightings].sort((a, b) => a.observedAt < b.observedAt ? -1 : 1)

  return (
    <div className={clsx('relative', className)}>
      {sightings.map((s, i) => (
        <div key={s.sightingId} className="flex gap-3">
          {/* Timeline track */}
          <div className="flex flex-col items-center">
            <div className={clsx(
              'h-3 w-3 rounded-full border-2 mt-0.5 shrink-0',
              s.watchlistStatus === 'WATCHLIST_MATCH'
                ? 'border-red-400 bg-red-900/40'
                : 'border-cyan-400 bg-cyan-900/30'
            )} />
            {i < sightings.length - 1 && (
              <div className="w-px flex-1 bg-[#1e2d40] my-0.5" style={{ minHeight: '24px' }} />
            )}
          </div>

          {/* Content */}
          <div className="pb-4 flex-1">
            <div className="flex items-center gap-2 flex-wrap text-xs font-mono">
              <span className="text-slate-300 font-semibold">{s.cameraId}</span>
              <span className="text-slate-600">·</span>
              <span className="text-slate-400">{fmtTime(s.observedAt)}</span>
              <span className="text-slate-600">·</span>
              {s.plateRead ? (
                <span className="text-ssb-green-bright">{s.plateRead.displayRead}</span>
              ) : (
                <span className="text-slate-600 italic">UNREADABLE</span>
              )}
              {s.confidence !== null && (
                <>
                  <span className="text-slate-600">·</span>
                  <span className={clsx(
                    s.confidence >= 0.8 ? 'text-emerald-400' : s.confidence >= 0.5 ? 'text-amber-400' : 'text-red-400'
                  )}>
                    {Math.round(s.confidence * 100)}%
                  </span>
                </>
              )}
              <VehicleClassBadge vehicleClass={s.vehicleClass} />
              <span className="text-slate-600">→ {s.vehicleDirection}</span>
              {s.vehicleTrackId && (
                <Link
                  to={'/track/' + s.vehicleTrackId}
                  className="text-cyan-400 hover:underline"
                >
                  [{s.vehicleTrackId}]
                </Link>
              )}
            </div>
            {s.locationContext && (
              <div className="text-[10px] text-slate-600 font-mono mt-0.5">{s.locationContext}</div>
            )}
          </div>
        </div>
      ))}
    </div>
  )
}