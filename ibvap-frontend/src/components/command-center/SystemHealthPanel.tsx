// ─────────────────────────────────────────────────────────────────────────────
// SystemHealthPanel — compact health grid (spec §20, §21).
//
// Healthy detection results require healthy coverage. Degraded cameras are
// visibly distinct with explanatory copy; subsystem status shown as text
// (never colour-only). Cameras and subsystems share a 2-column grid so the
// panel stays compact at 1920×1080.
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'
import { Activity } from 'lucide-react'
import { StatusIndicator } from '@/components/ui'
import type { SystemHealthEntry, SystemSubState } from '@/types'

interface Props {
  entries: SystemHealthEntry[]
  className?: string
}

export function SystemHealthPanel({ entries, className }: Props) {
  const cameras = entries.filter(e => e.monospace)
  const subsystems = entries.filter(e => !e.monospace)

  const column = (list: SystemHealthEntry[]) => (
    <div className="flex-1 min-w-0 flex flex-col gap-0.5">
      {list.map(entry => (
        <HealthRow key={entry.name} entry={entry} />
      ))}
    </div>
  )

  return (
    <div className={clsx('flex flex-col min-h-0 rounded-md border border-ssb-border/70 bg-ssb-navy-deep', className)}>
      <div className="flex items-center gap-2 px-3 py-1.5 border-b border-ssb-border/40 flex-shrink-0">
        <Activity size={13} className="text-ssb-green-bright" aria-hidden />
        <span className="text-[10px] font-semibold tracking-[0.16em] text-ssb-text-muted uppercase">
          System Health
        </span>
      </div>

      <div className="flex-1 flex gap-2 min-h-0 p-2">
        {column(cameras)}
        <div className="w-px bg-ssb-border/40 flex-shrink-0" aria-hidden />
        {column(subsystems)}
      </div>
    </div>
  )
}

function HealthRow({ entry }: { entry: SystemHealthEntry }) {
  return (
    <div className="flex items-center justify-between px-1.5 py-1 rounded bg-ssb-navy/50 gap-2">
      <span
        className={clsx(
          'text-[10px] font-medium text-ssb-text-muted tracking-wide truncate',
          entry.monospace && 'font-mono text-ssb-white'
        )}
      >
        {entry.name}
      </span>
      <StatusIndicator status={toStatus(entry.state)} label={entry.state[0] + entry.state.slice(1).toLowerCase()} />
    </div>
  )
}

function toStatus(state: SystemSubState): 'online' | 'degraded' | 'offline' | 'maintenance' | 'idle' {
  switch (state) {
    case 'ONLINE':    return 'online'
    case 'DEGRADED':  return 'degraded'
    case 'OFFLINE':   return 'offline'
    case 'READY':
    case 'VERIFIED':
    case 'STABLE':    return 'online'
    default:          return 'idle'
  }
}