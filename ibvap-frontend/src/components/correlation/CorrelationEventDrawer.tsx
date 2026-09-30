import { Link } from 'react-router-dom'
import { Drawer, Badge } from '@/components/ui'
import { SeverityBadge } from '@/components/risk/SeverityBadge'
import { formatClock, formatDate } from './correlationFormat'
import { humanizeEventKind, humanizeSource } from './CorrelationSummary'
import { RELIABILITY_LABEL, toneForReliability, TONE } from './correlationTone'
import type { CorrelationEventMember, CorrelationGroup } from '@/types/eventCorrelation'

interface CorrelationEventDrawerProps {
  open: boolean
  onClose: () => void
  member: CorrelationEventMember | null
  group: CorrelationGroup | null
}

/**
 * Event Detail drawer (§64). Shows the raw member signal, its relationship to
 * the group and links to evidence/camera. Never duplicates the Incident
 * Detail page; it is a focused inspection surface.
 */
export function CorrelationEventDrawer({ open, onClose, member, group }: CorrelationEventDrawerProps) {
  const relTone = member ? toneForReliability(member.reliability ?? 'UNKNOWN') : null
  const isPrimary = group?.primaryEventId === member?.eventId

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title={member ? `Event ${member.eventId}` : undefined}
      width="w-[480px] max-w-[92vw]"
    >
      {!member ? (
        <p className="text-xs text-slate-500">Select a signal to inspect it.</p>
      ) : (
        <div className="space-y-5">
          <dl className="grid grid-cols-2 gap-x-4 gap-y-3 text-xs">
            <Detail label="Type"><span className="font-medium text-slate-200">{humanizeEventKind(member.kind)}</span></Detail>
            <Detail label="Source"><span className="font-mono text-slate-300">{humanizeSource(member.source)}</span></Detail>
            <Detail label="Camera">
              <Link to={`/camera/${member.cameraId}`} className="font-mono text-cyan-400 hover:text-cyan-300 underline underline-offset-2">
                {member.cameraId}
              </Link>
            </Detail>
            <Detail label="Track">
              {member.trackId ? (
                <Link to={`/track/${member.trackId}`} className="font-mono text-cyan-400 hover:text-cyan-300 underline underline-offset-2">
                  {member.trackId}
                </Link>
              ) : (
                <span className="text-slate-500">none</span>
              )}
            </Detail>
            <Detail label="Date"><span className="font-mono text-slate-300">{formatDate(member.timestamp)}</span></Detail>
            <Detail label="Time"><span className="font-mono text-slate-300">{formatClock(member.timestamp)}</span></Detail>
            <Detail label="Zone">{member.zoneId ? <span className="font-mono text-slate-300">{member.zoneId}</span> : <span className="text-slate-500">none</span>}</Detail>
            <Detail label="Sector">{member.sectorId ?? '—'}</Detail>
            <Detail label="Modality"><span className="font-mono text-slate-300">{member.modality}</span></Detail>
            <Detail label="Reliability">
              {relTone ? (
                <span className={`inline-flex items-center gap-1 font-mono uppercase tracking-wider ${TONE[relTone].text}`}>
                  <span className={`h-1.5 w-1.5 rounded-full ${TONE[relTone].dot}`} aria-hidden />
                  {RELIABILITY_LABEL[member.reliability ?? 'UNKNOWN']}
                </span>
              ) : (
                <span className="text-slate-500">N/A</span>
              )}
            </Detail>
            <Detail label="Severity">
              {member.severity ? (
                <SeverityBadge severity={member.severity} />
              ) : (
                <span className="text-slate-500">NOT SCORED</span>
              )}
            </Detail>
            <Detail label="Detection ref (C5)">
              {member.detectionId ? (
                <span className="font-mono text-slate-300">{member.detectionId}</span>
              ) : (
                <span className="text-slate-500">not referenced</span>
              )}
            </Detail>
          </dl>

          {member.confidence !== null && (
            <div>
              <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Confidence</label>
              <p className="mt-1 font-mono text-sm text-slate-200">{Math.round(member.confidence * 100)}%</p>
            </div>
          )}

          {group && (
            <div>
              <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Relationship to group</label>
              <div className="mt-1.5 flex flex-wrap items-center gap-2">
                <Badge variant={isPrimary ? 'cyan' : 'default'} size="sm">
                  {isPrimary ? 'Primary event' : 'Supporting signal'}
                </Badge>
                <span className="font-mono text-[11px] text-slate-400">{group.correlationId}</span>
                {group.incidentId && (
                  <Link to={`/incident/${group.correlationId}`} className="font-mono text-[11px] text-cyan-400 hover:text-cyan-300 underline underline-offset-2">
                    {group.incidentId}
                  </Link>
                )}
              </div>
            </div>
          )}

          {member.healthContext?.reliability && member.healthContext.reliability !== 'HIGH' && (
            <div className="rounded-md border border-amber-500/30 bg-amber-500/5 px-3 py-2">
              <p className="text-[11px] font-semibold uppercase tracking-wider text-amber-300">
                Camera reliability {RELIABILITY_LABEL[member.healthContext.reliability]}
              </p>
              {member.healthContext.note && (
                <p className="mt-1 text-[11px] text-amber-200/80">{member.healthContext.note}</p>
              )}
              <p className="mt-1 text-[10px] text-amber-300/70">Context only — does not alter risk.</p>
            </div>
          )}

          {(member.anprPlate || member.anprSightingId) && (
            <div>
              <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                ANPR read (C7)
              </label>
              <div className="mt-1.5 space-y-1 rounded-md border border-white/10 bg-white/5 px-3 py-2">
                {member.anprPlate && (
                  <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                    <Link
                      to={`/anpr?search=${encodeURIComponent(member.anprPlate)}`}
                      className="font-mono text-sm font-semibold tracking-wider text-cyan-300 hover:text-cyan-200"
                    >
                      {member.anprPlate}
                    </Link>
                    {member.anprPlateConfidence !== null && (
                      <span className="font-mono text-[11px] text-slate-400">
                        confidence {Math.round(
                          member.anprPlateConfidence <= 1
                            ? member.anprPlateConfidence * 100
                            : member.anprPlateConfidence
                        )}
                        %
                      </span>
                    )}
                    {member.anprQuality && (
                      <span className="font-mono text-[11px] text-slate-500">quality {member.anprQuality}</span>
                    )}
                  </div>
                )}
                {member.anprSightingId && (
                  <p className="font-mono text-[10px] text-slate-500">sighting {member.anprSightingId}</p>
                )}
                <p className="text-[10px] text-slate-500">
                  Reported by the ANPR source — shown verbatim, never an identity claim.
                </p>
              </div>
            </div>
          )}

          <div>
            <label className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Evidence</label>
            {member.evidenceIds.length > 0 ? (
              <div className="mt-1.5 flex flex-wrap gap-1.5">
                {member.evidenceIds.map(id => (
                  <Link key={id} to="/evidence" className="rounded border border-white/10 bg-white/5 px-2 py-0.5 font-mono text-[10px] text-slate-300 hover:border-cyan-500/40 hover:text-cyan-300 transition-colors">
                    {id}
                  </Link>
                ))}
              </div>
            ) : (
              <p className="mt-1 text-[11px] text-slate-500">Evidence unavailable.</p>
            )}
          </div>
        </div>
      )}
    </Drawer>
  )
}

function Detail({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <dt className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">{label}</dt>
      <dd className="mt-0.5">{children}</dd>
    </div>
  )
}