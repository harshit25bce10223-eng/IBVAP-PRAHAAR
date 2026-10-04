import { clsx } from 'clsx'
import { compareByObservedTime, formatClock } from './correlationFormat'
import { humanizeEventKind, humanizeSource } from './CorrelationSummary'
import { toneForReliability, RELIABILITY_LABEL, TONE } from './correlationTone'
import type { CorrelationEventMember } from '@/types/eventCorrelation'

interface CorrelationSignalsProps {
  members: CorrelationEventMember[]
  primaryEventId: string | null
  onSelect?: (member: CorrelationEventMember) => void
}

/**
 * Supporting signals list (§37–38). Primary event is visually distinct from
 * supporting signals, which never appear to independently create an incident.
 * Missing members are shown explicitly with the authoritative count (§143).
 */
export function CorrelationSignals({ members, primaryEventId, onSelect }: CorrelationSignalsProps) {
  const sorted = [...members].sort(compareByObservedTime)
  const primary = sorted.find(m => m.eventId === primaryEventId) ?? null
  const supporting = sorted.filter(m => m.eventId !== primaryEventId)

  return (
    <div className="space-y-3">
      {primary && (
        <SignalBlock label="Primary event" member={primary} primary onSelect={onSelect} />
      )}
      {supporting.length > 0 && (
        <div className="space-y-2">
          <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
            Supporting signals
          </label>
          {supporting.map(m => (
            <SignalBlock key={m.eventId} label={null} member={m} primary={false} onSelect={onSelect} />
          ))}
        </div>
      )}
    </div>
  )
}

function SignalBlock({ label, member, primary, onSelect }: {
  label: string | null
  member: CorrelationEventMember
  primary: boolean
  onSelect?: (member: CorrelationEventMember) => void
}) {
  const relTone = toneForReliability(member.reliability ?? 'UNKNOWN')
  const content = (
    <>
      <div className="flex flex-wrap items-center gap-2">
        {label && (
          <span className="text-[10px] font-semibold uppercase tracking-wider text-prhaar-accent">{label}</span>
        )}
        <span className={clsx('text-xs font-semibold', primary ? 'text-prhaar-accent' : 'text-slate-300')}>
          {humanizeEventKind(member.kind)}
        </span>
        <span className="font-mono text-[11px] text-slate-400">{member.cameraId}</span>
        {member.trackId && <span className="font-mono text-[10px] text-slate-500">{member.trackId}</span>}
        <span className="text-[11px] text-slate-500">{humanizeSource(member.source)}</span>
      </div>
      <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-[11px] text-slate-500">
        <span className="font-mono tabular-nums">{formatClock(member.timestamp)}</span>
        {member.confidence !== null && <span className="font-mono">confidence {Math.round(member.confidence * 100)}%</span>}
        <span className={clsx('inline-flex items-center gap-1 font-mono uppercase tracking-wider', TONE[relTone].text)}>
          <span className={clsx('h-1.5 w-1.5 rounded-full', TONE[relTone].dot)} aria-hidden />
          {RELIABILITY_LABEL[member.reliability ?? 'UNKNOWN']}
        </span>
        {member.zoneId && <span className="font-mono">zone {member.zoneId}</span>}
      </div>
      {member.healthContext?.reliability && member.healthContext.reliability !== 'HIGH' && (
        <p className="mt-1 text-[11px] text-prhaar-degraded">
          Camera reliability {RELIABILITY_LABEL[member.healthContext.reliability]} — context only, does not alter risk.
        </p>
      )}
      {member.evidenceIds.length > 0 && (
        <p className="mt-1 font-mono text-[10px] text-slate-500">
          evidence {member.evidenceIds.length} record{member.evidenceIds.length === 1 ? '' : 's'}
        </p>
      )}
    </>
  )
  const base =
    'block w-full rounded-lg border px-3 py-2 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/60 transition-colors'
  const border = primary ? 'border-prhaar-accent/40 bg-prhaar-accent/5' : 'border-white/10 bg-surface/40'
  if (onSelect) {
    return (
      <button type="button" onClick={() => onSelect(member)} className={clsx(base, border, 'hover:border-cyan-500/40')} aria-label={`Inspect signal ${member.eventId}`}>
        {content}
        <span className="mt-0.5 block font-mono text-[10px] text-slate-600">{member.eventId}</span>
      </button>
    )
  }
  return (
    <div className={clsx(base, border)}>
      {content}
      <span className="mt-0.5 block font-mono text-[10px] text-slate-600">{member.eventId}</span>
    </div>
  )
}