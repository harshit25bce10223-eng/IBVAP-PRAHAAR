import { Link } from 'react-router-dom'
import type { CameraHealth, CameraHealthStatus } from '@/types/cameraHealth'
import { CameraHealthDot } from './CameraHealthDot'
import { TONE, toneForStatus } from './healthTone'

const COUNT_ORDER: CameraHealthStatus[] = ['ONLINE', 'DEGRADED', 'OFFLINE', 'MAINTENANCE', 'UNKNOWN']

/**
 * Dashboard summary: compact counts + inspectable affected cameras.
 * Each row links to the existing `/camera/:id` route. Calm by design —
 * no giant tiles, no decorative charts.
 */
export function CameraHealthMiniPanel({ records }: { records: CameraHealth[] }) {
  const counts = new Map<CameraHealthStatus, number>()
  for (const r of records) counts.set(r.status, (counts.get(r.status) ?? 0) + 1)

  const attention = records.filter(r => r.status !== 'ONLINE')

  return (
    <section aria-label="Camera health summary" className="rounded-xl border border-[#1e2d40] bg-[#0d1117] p-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-slate-200">Camera Health</h3>
        <span className="rounded border border-cyan-500/30 bg-cyan-500/10 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider text-cyan-400">
          Demo mode
        </span>
      </div>

      <dl className="mt-3 flex flex-wrap gap-x-4 gap-y-1">
        {COUNT_ORDER.map(status => {
          const tone = TONE[toneForStatus(status)]
          return (
            <div key={status} className="flex items-center gap-1.5">
              <CameraHealthDot status={status} label="summary" />
              <dt className="font-mono text-[10px] text-slate-500">{status}</dt>
              <dd className={`font-mono text-xs tabular-nums ${tone.text}`}>{counts.get(status) ?? 0}</dd>
            </div>
          )
        })}
      </dl>

      {attention.length > 0 && (
        <ul className="mt-3 space-y-1 border-t border-white/[0.05] pt-2">
          {attention.map(r => {
            const tone = TONE[toneForStatus(r.status)]
            return (
              <li key={r.cameraId}>
                <Link
                  to={`/camera/${r.cameraId}`}
                  className="flex items-center justify-between gap-2 rounded px-1.5 py-1 text-[11px] transition-colors hover:bg-white/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/60"
                  aria-label={`Inspect camera ${r.cameraId}, ${r.status.toLowerCase()}`}
                >
                  <span className="flex items-center gap-1.5">
                    <CameraHealthDot status={r.status} cameraId={r.cameraId} />
                    <span className="font-mono text-slate-200">{r.cameraId}</span>
                  </span>
                  <span className={`font-mono text-[10px] ${tone.text}`}>{r.status}</span>
                </Link>
              </li>
            )
          })}
        </ul>
      )}
    </section>
  )
}
