// ─────────────────────────────────────────────────────────────────────────────
// CameraIntelRow — compact row of 3 representative cameras (spec §18).
//
// Each card shows camera state, detection classification, confidence and
// optional track association. Degraded cameras are visibly distinct to
// communicate "healthy detection requires healthy coverage."
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'
import { Video } from 'lucide-react'
import { StatusIndicator } from '@/components/ui'
import type { DashboardCameraIntel, CameraIntelState } from '@/types'

interface Props {
  cameras: DashboardCameraIntel[]
  className?: string
}

const STATE_TO_STATUS: Record<CameraIntelState, 'online' | 'degraded' | 'offline'> = {
  ONLINE:   'online',
  DEGRADED: 'degraded',
  OFFLINE:  'offline',
}

export function CameraIntelRow({ cameras, className }: Props) {
  return (
    <div className={clsx('flex flex-col min-h-0 rounded-md border border-ssb-border/70 bg-ssb-navy-deep', className)}>
      <div className="flex items-center gap-2 px-3 py-2 border-b border-ssb-border/40 flex-shrink-0">
        <Video size={13} className="text-ssb-green-bright" aria-hidden />
        <span className="text-[10px] font-semibold tracking-[0.16em] text-ssb-text-muted uppercase">
          Live Camera Intelligence
        </span>
      </div>

      <div className="flex-1 flex gap-2 p-2 overflow-x-auto">
        {cameras.map(cam => (
          <CameraCard key={cam.id} camera={cam} />
        ))}
      </div>
    </div>
  )
}

// ─── Single camera card ─────────────────────────────────────────────────────

function CameraCard({ camera }: { camera: DashboardCameraIntel }) {
  const isOnline = camera.state === 'ONLINE'
  const isDegraded = camera.state === 'DEGRADED'

  return (
    <div
      className={clsx(
        'flex-1 min-w-[140px] flex flex-col gap-1.5 rounded border px-2.5 py-2',
        isDegraded
          ? 'border-ssb-amber/30 bg-ssb-amber/5'
          : isOnline
            ? 'border-ssb-border/40 bg-ssb-navy/60'
            : 'border-ssb-border/30 bg-ssb-navy-deep/40 opacity-60'
      )}
    >
      {/* Header row */}
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-bold font-mono text-ssb-white tracking-wider">{camera.id}</span>
        <StatusIndicator
          status={STATE_TO_STATUS[camera.state]}
          label={camera.stateLabel}
        />
      </div>

      {/* Classification */}
      <div className="flex items-center gap-2">
        <span className="text-[11px] font-medium text-ssb-text">{camera.classification}</span>
        {camera.trackId && (
          <span className="text-[9px] font-mono text-ssb-green-bright">{camera.trackId}</span>
        )}
      </div>

      {/* Confidence bar */}
      <div className="flex items-center gap-2">
        <div className="flex-1 h-1 rounded bg-ssb-navy-deep/80 overflow-hidden">
          <div
            className={clsx('h-full rounded', isDegraded ? 'bg-ssb-amber-bright' : 'bg-ssb-green-bright')}
            style={{ width: `${camera.classConfidence}%` }}
          />
        </div>
        <span className="text-[10px] font-mono text-ssb-text-muted">{camera.classConfidence}%</span>
      </div>

      {/* Note */}
      <span className="text-[9px] text-ssb-text-muted/60 leading-tight">{camera.note}</span>
    </div>
  )
}