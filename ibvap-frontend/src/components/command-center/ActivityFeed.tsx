// ─────────────────────────────────────────────────────────────────────────────
// ActivityFeed — compact operational stream (spec §22).
//
// Newest-first ordering, consistent with the Golden Incident chain. Each entry
// carries a text + colour tone (never colour alone).
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'
import { ListTree } from 'lucide-react'
import type { ActivityEvent } from '@/types'

interface Props {
  events: ActivityEvent[]
  className?: string
}

const TONE_TEXT: Record<ActivityEvent['tone'], string> = {
  critical: 'text-ssb-red-bright',
  warning:  'text-ssb-amber-bright',
  info:     'text-ssb-text-muted',
  safe:     'text-ssb-green-bright',
}

const TONE_DOT: Record<ActivityEvent['tone'], string> = {
  critical: 'bg-ssb-red-bright',
  warning:  'bg-ssb-amber-bright',
  info:     'bg-ssb-text-muted/60',
  safe:     'bg-ssb-green-bright',
}

export function ActivityFeed({ events, className }: Props) {
  return (
    <div className={clsx('flex flex-col min-h-0 rounded-md border border-ssb-border/70 bg-ssb-navy-deep', className)}>
      <div className="flex items-center gap-2 px-3 py-2 border-b border-ssb-border/40 flex-shrink-0">
        <ListTree size={13} className="text-ssb-green-bright" aria-hidden />
        <span className="text-[10px] font-semibold tracking-[0.16em] text-ssb-text-muted uppercase">
          Recent Activity
        </span>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1">
        {events.map((ev, idx) => (
          <div key={idx} className="flex items-start gap-2">
            <span className={clsx('mt-1 h-1.5 w-1.5 rounded-full flex-shrink-0', TONE_DOT[ev.tone])} aria-hidden />
            <div className="min-w-0 leading-tight">
              <span className="text-[9px] font-mono text-ssb-text-muted/60 mr-1.5">{ev.time}</span>
              <span className={clsx('text-[10px]', TONE_TEXT[ev.tone])}>{ev.text}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}