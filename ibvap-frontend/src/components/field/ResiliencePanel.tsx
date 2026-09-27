// ─────────────────────────────────────────────────────────────────────────────
// ResiliencePanel — Offline-first resilience (Field Intelligence & Resilience,
// right 35%).
//
// The buffer/sync state machine, degraded-camera health, bandwidth adaptation
// ladder and a remote-BOP station panel. Practical operational status, no
// glowing network diagrams (spec §4–§7).
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'
import type { FieldIntelligenceData, ResilienceStateId } from '@/types'

interface Props {
  data: FieldIntelligenceData
  className?: string
}

const STATE_COLOR: Record<ResilienceStateId, string> = {
  'CONNECTED': '#35B884',
  'NETWORK-LOST': '#F8C35C',
  'BUFFERING': '#F8C35C',
  'SYNCING': '#22D3EE',
  'SYNC-COMPLETE': '#35B884',
}

export function ResiliencePanel({ data, className }: Props) {
  const activeState: ResilienceStateId = 'SYNC-COMPLETE'

  return (
    <div className={clsx('flex h-full min-h-0 flex-col overflow-hidden rounded-md border border-ssb-border/70 bg-ssb-navy/60 p-3', className)}>
      <div className="flex items-start justify-between gap-2 flex-shrink-0">
        <div>
          <h2 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-ssb-white">
            Offline-First Resilience
          </h2>
          <p className="text-[9.5px] text-ssb-text-muted mt-0.5">
            Weak-network &amp; disconnected operations
          </p>
        </div>
      </div>

      {/* Visual states */}
      <div className="mt-2 flex flex-wrap gap-1 flex-shrink-0">
        {data.visualStates.map(state => {
          const active = state.id === activeState
          const color = STATE_COLOR[state.id]
          return (
            <span
              key={state.id}
              className={clsx(
                'flex items-center gap-1 rounded border px-1.5 py-0.5 text-[8px] font-mono font-semibold tracking-wider',
                active ? 'border-ssb-border' : 'border-ssb-border/50'
              )}
              style={active ? { color, backgroundColor: `${color}1f` } : { color: '#9aaebd' }}
            >
              <span className="h-1 w-1 rounded-full" style={{ backgroundColor: color }} />
              {state.label}
            </span>
          )
        })}
      </div>

      {/* State machine flow */}
      <ol className="mt-2 flex-1 min-h-0 flex flex-col justify-between">
        {data.resilienceSteps.map(step => {
          const color = STATE_COLOR[step.stateId]
          const isLast = step.last
          return (
            <li key={step.label} className="flex items-center gap-2">
              <div className="flex w-4 flex-shrink-0 flex-col items-center self-stretch">
                <span className={clsx('w-px flex-1', isLast ? 'bg-transparent' : 'bg-ssb-border/50')} />
                <span className="h-2.5 w-2.5 flex-shrink-0 rounded-full border border-ssb-white/25" style={{ backgroundColor: color }} />
                {!isLast && <span className="w-px flex-1 bg-ssb-border/50" />}
              </div>
              <div className="min-w-0 flex-1">
                <span className="block truncate text-[10px] font-medium text-ssb-text">{step.label}</span>
                <span className="block text-[8.5px] text-ssb-text-muted/70">{step.detail}</span>
              </div>
              {isLast && (
                <span className="flex-shrink-0 rounded border border-ssb-green-bright/40 bg-ssb-green/15 px-1.5 py-0.5 text-[8px] font-mono font-bold text-ssb-green-bright">
                  DONE
                </span>
              )}
            </li>
          )
        })}
      </ol>

      {/* Degraded camera health */}
      <div className="mt-2 flex-shrink-0 rounded border border-ssb-border/60 bg-ssb-navy-deep/50 p-2">
        <div className="flex items-center justify-between">
          <span className="text-[9px] font-semibold uppercase tracking-wider text-ssb-text-muted">Camera Health</span>
          <span className="rounded border border-ssb-amber-bright/40 bg-ssb-amber/15 px-1.5 py-0.5 text-[9px] font-mono font-bold text-ssb-amber-bright">
            {data.degradedCamera.id} · {data.degradedCamera.state}
          </span>
        </div>
        <div className="mt-1.5 grid grid-cols-3 gap-1.5">
          <MiniStat label="Coverage" value={data.degradedCamera.coverage} tone="alert" />
          <MiniStat label="Local Processing" value={data.degradedCamera.localProcessing} tone="ok" />
          <MiniStat label="Buffered Events" value={data.degradedCamera.bufferedEvents} tone="ok" />
        </div>
      </div>

      {/* Bandwidth adaptation */}
      <div className="mt-2 flex-shrink-0 rounded border border-ssb-border/60 bg-ssb-navy-deep/50 p-2">
        <div className="text-[9px] font-semibold uppercase tracking-wider text-ssb-text-muted">Bandwidth Adaptation</div>
        <div className="mt-1 flex items-center gap-1">
          {data.bandwidth.map((step, i) => (
            <span key={step.label} className="flex min-w-0 flex-1 items-center gap-1">
              {i > 0 && <span className="text-[9px] text-ssb-amber-bright flex-shrink-0">↓</span>}
              <span className="min-w-0 rounded border border-ssb-border/50 bg-ssb-navy/60 px-1 py-0.5">
                <span className="block truncate text-[8px] font-mono font-semibold text-ssb-text">{step.label}</span>
                <span className="block truncate text-[7.5px] text-ssb-text-muted/70">{step.detail}</span>
              </span>
            </span>
          ))}
        </div>
      </div>

      {/* Remote BOP station */}
      <div className="mt-2 flex-shrink-0 rounded border border-ssb-border/60 bg-ssb-navy-deep/50 p-2">
        <div className="flex items-center justify-between">
          <span className="text-[9px] font-semibold uppercase tracking-wider text-ssb-text-muted">Operational Value</span>
          <span className="text-[9px] font-mono text-ssb-green-bright">{data.station.name}</span>
        </div>
        <div className="mt-1.5 grid grid-cols-2 gap-x-3 gap-y-1">
          <MiniRow label="Network" value={data.station.network} />
          <MiniRow label="Local Inference" value={data.station.localInference} />
          <MiniRow label="Evidence Buffering" value={data.station.evidenceBuffering} />
          <MiniRow label="Auto Synchronization" value={data.station.autoSync} />
        </div>
      </div>
    </div>
  )
}

function MiniStat({ label, value, tone }: { label: string; value: string; tone: 'ok' | 'alert' }) {
  return (
    <div className="rounded bg-ssb-navy/60 px-1.5 py-1 border border-ssb-border/40">
      <span className="block text-[7.5px] uppercase tracking-wider text-ssb-text-muted/80">{label}</span>
      <span className={clsx('block text-[10px] font-mono font-semibold mt-0.5', tone === 'ok' ? 'text-ssb-green-bright' : 'text-ssb-red-bright')}>
        {value}
      </span>
    </div>
  )
}

function MiniRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-2">
      <span className="text-[8.5px] text-ssb-text-muted">{label}</span>
      <span className="text-[9px] font-mono text-ssb-text">{value}</span>
    </div>
  )
}