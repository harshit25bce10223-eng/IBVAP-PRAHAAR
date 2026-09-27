// ─────────────────────────────────────────────────────────────────────────────
// TimelineColumn — correlated event timeline (Incident Intelligence, left).
//
// Vertical investigation-style chain: time rail + phase nodes. The visual
// transition highlights where separate ALERTS become a CORRELATED INCIDENT
// (spec §3).
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'
import type { GoldenIncidentStep } from '@/types'

interface Props {
  timeline: GoldenIncidentStep[]
  correlationIndex: number
  className?: string
}

const PHASE_LEGEND = [
  { color: '#F4B942', label: 'ALERT' },
  { color: '#22D3EE', label: 'CORRELATE' },
  { color: '#D62828', label: 'INCIDENT' },
]

export function TimelineColumn({ timeline, correlationIndex, className }: Props) {
  return (
    <div className={clsx('flex h-full min-h-0 flex-col rounded-md border border-ssb-border/70 bg-ssb-navy/60 p-3', className)}>
      <div className="flex items-start justify-between gap-2 flex-shrink-0">
        <div>
          <h2 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-ssb-white">
            Correlated Event Timeline
          </h2>
          <p className="text-[9.5px] text-ssb-text-muted mt-0.5">
            Multiple signals → correlated incident
          </p>
        </div>
        <div className="flex gap-2">
          {PHASE_LEGEND.map(p => (
            <span key={p.label} className="flex items-center gap-1">
              <span className="h-1.5 w-1.5 rounded-full" style={{ backgroundColor: p.color }} />
              <span className="text-[8px] font-mono text-ssb-text-muted tracking-wider">{p.label}</span>
            </span>
          ))}
        </div>
      </div>

      <ol className="mt-3 flex-1 min-h-0 overflow-hidden">
        {timeline.map((step, i) => {
          const isCorrelate = i >= correlationIndex
          const isIncident = step.step === timeline[timeline.length - 1]?.step
          const color = isIncident ? '#D62828' : isCorrelate ? '#22D3EE' : '#F4B942'
          const isTransition = i === correlationIndex

          return (
            <li key={step.step} className="relative">
              {/* Transition highlight: alerts → correlated incident */}
              {isTransition && (
                <div className="absolute -top-[7px] left-[46px] right-0 flex items-center gap-2">
                  <span className="h-px flex-1 bg-ssb-amber-bright/40" />
                  <span className="text-[8px] font-mono font-semibold tracking-[0.14em] text-ssb-amber-bright">
                    CORRELATION CHAIN INITIATED
                  </span>
                  <span className="h-px flex-1 bg-ssb-amber-bright/40" />
                </div>
              )}

              <div className="flex items-center gap-3 py-[5px]">
                {/* Time */}
                <span className="w-10 flex-shrink-0 text-right text-[10px] font-mono text-ssb-text-muted">
                  {step.time}
                </span>

                {/* Rail + node */}
                <div className="flex w-4 flex-shrink-0 flex-col items-center self-stretch">
                  <span
                    className={clsx('w-px flex-1', i === 0 ? 'bg-transparent' : 'bg-ssb-border/60')}
                  />
                  <span
                    className="h-2.5 w-2.5 flex-shrink-0 rounded-full border border-ssb-white/30"
                    style={{ backgroundColor: color }}
                  />
                  <span
                    className={clsx('w-px flex-1', i === timeline.length - 1 ? 'bg-transparent' : 'bg-ssb-border/60')}
                  />
                </div>

                {/* Event */}
                <div className="min-w-0 flex-1">
                  <span className={clsx(
                    'block truncate text-[10.5px] font-medium',
                    isIncident ? 'text-ssb-red-bright' : 'text-ssb-text'
                  )}>
                    {step.text}
                  </span>
                  <span className="block text-[9px] text-ssb-text-muted/80">
                    {isIncident ? 'Incident raised from correlated signals' : 'Signal from sector sensing'}
                  </span>
                </div>

                {/* Camera chip */}
                <span className="flex-shrink-0 rounded border border-ssb-border/70 bg-ssb-navy-deep/60 px-1.5 py-0.5 text-[9px] font-mono text-ssb-green-bright">
                  {step.cameraId}
                </span>
              </div>
            </li>
          )
        })}
      </ol>
    </div>
  )
}