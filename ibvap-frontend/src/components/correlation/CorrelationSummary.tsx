import { clsx } from 'clsx'
import { Link } from 'react-router-dom'
import { ChevronRight } from 'lucide-react'
import { Badge } from '@/components/ui'
import { SeverityBadge } from '@/components/risk/SeverityBadge'
import { CorrelationStatusBadge } from './CorrelationStatusBadge'
import {
  CORRELATION_BLURB,
  CONNECTIVITY_LABEL,
  INCIDENT_STATE_LABEL,
  toneForConnectivity,
  toneForIncidentState,
  TONE,
} from './correlationTone'
import {
  compareByObservedTime,
  formatCameraList,
  formatCameraCount,
  formatClockShort,
  formatSignalCount,
  formatWindow,
} from './correlationFormat'
import type { CorrelationEventMember, CorrelationGroup } from '@/types/eventCorrelation'

type Density = 'compact' | 'normal' | 'detailed'

interface CorrelationSummaryProps {
  group: CorrelationGroup
  density?: Density
  /** Link target for the group; falls back to incident detail navigation. */
  to?: string
  onExpand?: () => void
  /** Opens an event-detail drawer for a member signal (§33/§64). */
  onSelectMember?: (member: CorrelationEventMember) => void
  expanded?: boolean
  showExpand?: boolean
}

/**
 * Reusable correlation summary row (§91). Collapsed shows structured counts,
 * expanded shows member signals. Works in Dashboard feed, Event Log and
 * Single Camera context. Correlation and severity stay visually separate.
 */
export function CorrelationSummary({
  group,
  density = 'normal',
  to,
  onExpand,
  onSelectMember,
  expanded = false,
  showExpand = false,
}: CorrelationSummaryProps) {
  const memberCameras = [...new Set(group.memberEvents.map(m => m.cameraId))]
  const memberSourceLabels = group.sources.map(humanizeSource).join(' · ')
  const connTone = toneForConnectivity(group.connectivity)
  const incTone = group.incidentState ? toneForIncidentState(group.incidentState) : null

  return (
    <div
      className={clsx(
        'rounded-xl border bg-[#0d1117] transition-colors',
        density === 'compact' ? 'border-white/10' : 'border-[#1e2d40]'
      )}
    >
      <div
        className={clsx(
          'flex items-start gap-3',
          density === 'compact' ? 'p-3' : 'p-4'
        )}
      >
        {/* Time */}
        <div className="w-14 shrink-0 font-mono text-[11px] text-slate-400 tabular-nums">
          {density === 'compact' ? formatClockShort(group.startedAt) : formatWindow(group.startedAt, group.endedAt)}
        </div>

        {/* Summary block */}
        <div className="flex-1 min-w-0">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <CorrelationStatusBadge status={group.status} />
            <span className="text-xs font-medium text-slate-200 truncate">{groupTitle(group)}</span>
          </div>
          {density !== 'compact' && (
            <p className="mt-1 text-[11px] text-slate-500">{CORRELATION_BLURB[group.status]}</p>
          )}

          {/* Structured counts — not severity, not risk */}
          <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-slate-400">
            <span className="font-mono tabular-nums">{formatSignalCount(group.eventCount)}</span>
            <span className="font-mono tabular-nums">{formatCameraCount(group.cameraCount)}</span>
            {group.cameraCount > 0 && (
              <span className="font-mono text-slate-500">{formatCameraList(group.cameraChain, memberCameras)}</span>
            )}
            {memberSourceLabels && (
              <span className="hidden md:inline text-slate-500">{memberSourceLabels}</span>
            )}
          </div>

          {group.eventCount > group.memberEvents.length && group.memberEventsLoaded !== null && (
            <p className="mt-1.5 text-[11px] text-amber-400/90">
              {group.eventCount} signals · {group.memberEvents.length} loaded · {group.eventCount - group.memberEvents.length} related signal(s) unavailable.
            </p>
          )}
          {group.duplicatedOrSuppressed && (
            <p className="mt-1.5 text-[11px] text-slate-500">Backend flags transport duplication/suppression.</p>
          )}
        </div>

        {/* Right cluster: severity (separate) + status + nav */}
        <div className="flex shrink-0 items-center gap-2.5">
          {group.risk.severity !== null ? (
            <SeverityBadge severity={group.risk.severity} score={group.risk.score} />
          ) : (
            <span className="font-mono text-[11px] text-slate-500 uppercase tracking-wider">No risk score</span>
          )}
          {group.incidentId && group.incidentState && incTone && (
            <Badge variant={TONE[incTone].badge} size="sm">
              {INCIDENT_STATE_LABEL[group.incidentState]}
            </Badge>
          )}
          <span className={clsx('hidden lg:inline-flex items-center gap-1 font-mono text-[10px] uppercase tracking-wider', TONE[connTone].text)}>
            <span className={clsx('h-1.5 w-1.5 rounded-full', TONE[connTone].dot)} aria-hidden />
            {CONNECTIVITY_LABEL[group.connectivity]}
          </span>
        </div>
      </div>

      {/* Expandable member signals */}
      {showExpand && expanded && (
        <div className="border-t border-[#1e2d40] px-4 py-3">
          <MemberSignals group={group} onSelectMember={onSelectMember} />
        </div>
      )}

      {/* Footer actions */}
      {(to || onExpand) && (
        <div className={clsx('flex items-center justify-between border-t px-4 py-2', density === 'compact' ? 'border-white/10' : 'border-[#1e2d40]')}>
          {showExpand && onExpand ? (
            <button
              onClick={onExpand}
              aria-expanded={expanded}
              className="rounded-md border border-white/10 px-2 py-1 text-[11px] text-slate-300 hover:border-cyan-500/40 hover:text-cyan-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/60 transition-colors"
            >
              {expanded ? 'Collapse signals' : `Show ${formatSignalCount(group.eventCount)}`}
            </button>
          ) : <span />}
          {to && (
            <Link
              to={to}
              className="inline-flex items-center gap-1 rounded-md border border-cyan-500/30 bg-cyan-500/10 px-2.5 py-1 text-[11px] font-medium text-cyan-300 hover:bg-cyan-500/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/60 transition-colors"
            >
              {group.incidentId ? 'View incident' : 'View event'}
              <ChevronRight size={12} aria-hidden />
            </Link>
          )}
        </div>
      )}
    </div>
  )
}

/** Compact member-signal list for the expanded log row (§33/§134). */
export function MemberSignals({ group, onSelectMember }: { group: CorrelationGroup; onSelectMember?: (m: CorrelationEventMember) => void }) {
  const signals = [...group.memberEvents].sort(compareByObservedTime)
  const base = 'grid grid-cols-[5.5rem_7rem_1fr] items-baseline gap-2 text-[11px] rounded px-1 py-0.5'
  return (
    <ol className="space-y-1">
      {signals.map(m => (
        <li key={m.eventId}>
          {onSelectMember ? (
            <button
              type="button"
              onClick={() => onSelectMember(m)}
              className={`${base} w-full text-left hover:bg-cyan-500/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/60 transition-colors`}
              aria-label={`Inspect signal ${m.eventId}`}
            >
              <RowContent member={m} />
            </button>
          ) : (
            <div className={base}>
              <RowContent member={m} />
            </div>
          )}
        </li>
      ))}
    </ol>
  )
}

function RowContent({ member }: { member: CorrelationEventMember }) {
  return (
    <>
      <span className="font-mono text-slate-400 tabular-nums">{formatClockShort(member.timestamp)}</span>
      <span className="font-mono text-slate-500">{member.cameraId}</span>
      <span className="flex items-center gap-2 min-w-0">
        <span className="text-slate-200 truncate">{humanizeEventKind(member.kind)}</span>
        <span className="text-slate-500 hidden sm:inline">{humanizeSource(member.source)}</span>
        <span className="font-mono text-[9px] text-slate-600">{member.eventId}</span>
      </span>
    </>
  )
}

function groupTitle(group: CorrelationGroup): string {
  if (group.incidentId) return group.incidentId
  if (group.status === 'STANDALONE' && group.memberEvents[0]) {
    return humanizeEventKind(group.memberEvents[0].kind)
  }
  return group.correlationId
}

export function humanizeEventKind(kind: string): string {
  return kind
    .toLowerCase()
    .split('_')
    .map(w => (w ? w[0].toUpperCase() + w.slice(1) : w))
    .join(' ')
}

export function humanizeSource(source: string): string {
  if (source === 'VIRTUAL_FENCE') return 'FENCE'
  if (source === 'SURFACE_ANOMALY') return 'SURFACE'
  if (source === 'SUSPICIOUS_ACTIVITY') return 'SUSPICIOUS ACTIVITY'
  if (source === 'CAMERA_HEALTH') return 'CAMERA HEALTH'
  if (source === 'RE_ID') return 'RE-ID'
  return source.replace(/_/g, ' ')
}