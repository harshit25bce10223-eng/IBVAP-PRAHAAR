import { clsx } from 'clsx'
import { formatClock } from './correlationFormat'
import { humanizeEventKind, humanizeSource } from './CorrelationSummary'
import { CONNECTIVITY_LABEL, toneForConnectivity, TONE } from './correlationTone'
import type { CorrelationGroup, CorrelationEventMember } from '@/types/eventCorrelation'

interface CorrelationTimelineProps {
  group: CorrelationGroup
  onSelectMember?: (member: CorrelationEventMember) => void
}

/**
 * Primary chronological timeline (§28/§78). A single subtle connector rail ties
 * the signals together; no animated lines, no glowing particles. The final
 * entry marks when the correlation group was created — cause → evidence →
 * grouping, never causality (§81).
 */
export function CorrelationTimeline({ group, onSelectMember }: CorrelationTimelineProps) {
  const signals = [...group.memberEvents].sort(
    (a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
  )
  const hasIncident = group.incidentId !== null
  const connTone = toneForConnectivity(group.connectivity)
  const primaryId = group.primaryEventId ?? signals[0]?.eventId ?? null

  return (
    <ol className="relative" aria-label="Correlation timeline">
      {signals.map(m => (
        <TimelineEntry
          key={m.eventId}
          member={m}
          isPrimary={m.eventId === primaryId}
          onSelectMember={onSelectMember}
        />
      ))}

      {/* Group creation marker */}
      <li className="relative pl-9 pb-0 pt-3">
        <RailDot className="bg-prhaar-accent border-prhaar-accent" aria-hidden />
        <div>
          <p className="text-[10px] font-mono uppercase tracking-wider text-prhaar-accent">
            {hasIncident ? 'Correlated event created' : 'Group created'}
          </p>
          <p className="mt-0.5 flex items-center gap-2 text-[11px] text-slate-500">
            <span className="font-mono tabular-nums">{formatClock(group.history.createdAt)}</span>
            <span className={clsx('inline-flex items-center gap-1 uppercase tracking-wider', TONE[connTone].text)}>
              <span className={clsx('h-1.5 w-1.5 rounded-full', TONE[connTone].dot)} aria-hidden />
              {CONNECTIVITY_LABEL[group.connectivity]}
            </span>
          </p>
        </div>
      </li>
    </ol>
  )
}

function TimelineEntry({ member, isPrimary, onSelectMember }: {
  member: CorrelationEventMember
  isPrimary: boolean
  onSelectMember?: (member: CorrelationEventMember) => void
}) {
  const buttonStyle =
    'w-full rounded-lg border border-transparent px-1.5 py-1 text-left hover:border-cyan-500/30 hover:bg-cyan-500/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/60 transition-colors'
  const content = (
    <div className="flex flex-wrap items-baseline gap-x-3 gap-y-0.5">
      <span className="font-mono text-[11px] text-slate-200 tabular-nums">{formatClock(member.timestamp)}</span>
      <span className={clsx('text-xs font-semibold uppercase tracking-wider', isPrimary ? 'text-prhaar-accent' : 'text-slate-300')}>
        {humanizeEventKind(member.kind)}
      </span>
      <span className="font-mono text-[11px] text-slate-400">{member.cameraId}</span>
      {member.trackId && <span className="font-mono text-[10px] text-slate-500">{member.trackId}</span>}
      <span className="text-[11px] text-slate-500">{humanizeSource(member.source)}</span>
      <span className={clsx('text-[10px] font-mono uppercase tracking-wider', reliabilityTone(member.reliability))}>
        {member.reliability ?? 'reliability N/A'}
      </span>
    </div>
  )
  return (
    <li className="relative pl-9 pb-3">
      <RailDot aria-hidden />
      {onSelectMember ? (
        <button type="button" onClick={() => onSelectMember(member)} className={buttonStyle} aria-label={`Inspect signal ${member.eventId}`}>
          {content}
          <span className="font-mono text-[10px] text-slate-500">{member.eventId}</span>
        </button>
      ) : (
        <div className={buttonStyle}>
          {content}
          <span className="font-mono text-[10px] text-slate-500">{member.eventId}</span>
        </div>
      )}
    </li>
  )
}

/** Shared subtle correlation rail. Never animated; respects reduced motion. */
function RailDot({ className, 'aria-hidden': ariaHidden }: { className?: string; 'aria-hidden'?: boolean }) {
  return (
    <>
      <span
        className={clsx('absolute left-[3px] top-1.5 h-2 w-2 rounded-full border bg-[#0d1117]', className ?? 'border-slate-600')}
        aria-hidden={ariaHidden}
      />
      <span className="absolute left-[7px] top-3 bottom-0 w-px bg-[#1e2d40]" aria-hidden />
    </>
  )
}

function reliabilityTone(reliability: CorrelationEventMember['reliability']): string {
  switch (reliability) {
    case 'HIGH': return 'text-prhaar-good'
    case 'MEDIUM': return 'text-prhaar-degraded'
    case 'LOW': return 'text-prhaar-failed'
    default: return 'text-slate-500'
  }
}