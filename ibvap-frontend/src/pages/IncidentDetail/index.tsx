import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import type { ReactNode } from 'react'
import { Badge, ErrorState, PageHeader } from '@/components/ui'
import { useCorrelationDetail } from '@/hooks/useCorrelation'
import {
  CorrelationEventDrawer,
  CorrelationExplanation,
  CorrelationGraph,
  CorrelationHistory,
  CorrelationRisk,
  CorrelationSignals,
  CorrelationStatusBadge,
  CorrelationTimeline,
  CorrelationUncertainty,
  SourceLegend,
  formatCameraList,
  formatConfidence,
  formatModalities,
  formatSignalCount,
  formatWindow,
  GROUP_STATE_LABEL,
  INCIDENT_STATE_LABEL,
  RELIABILITY_LABEL,
  toneForConnectivity,
  toneForGroupState,
  toneForReliability,
  TONE,
} from '@/components/correlation'
import type { CorrelationEventMember } from '@/types/eventCorrelation'

/**
 * Correlation Detail — the §83 acceptance bar. Every value here is a backend
 * field rendered verbatim: correlation, risk, severity, identity and causality
 * are never computed on this page. Absent data is stated as unavailable rather
 * than substituted (§20/§63/§64/§95).
 */
export function IncidentDetail() {
  const { correlationId } = useParams<{ correlationId: string }>()
  const {
    group,
    detailState,
    detailError,
    relationships,
    relationshipState,
    reviewRelationships,
    retry,
  } = useCorrelationDetail(correlationId)
  const [selectedMember, setSelectedMember] = useState<CorrelationEventMember | null>(null)
  const [drawerOpen, setDrawerOpen] = useState(false)

  const memberCameras = useMemo(
    () => (group ? [...new Set(group.memberEvents.map(m => m.cameraId))] : []),
    [group]
  )
  const memberZones = useMemo(
    () => (group ? [...new Set(group.memberEvents.map(m => m.zoneId).filter((z): z is string => z !== null))] : []),
    [group]
  )
  // Plate reads are surfaced exactly as the backend reported them; no OCR or
  // plate logic runs here (§C7 boundary).
  const plateReads = useMemo(() => {
    if (!group) return []
    return group.memberEvents
      .filter(m => m.anprPlate !== null)
      .map(m => ({
        eventId: m.eventId,
        plate: m.anprPlate as string,
        confidence: m.anprPlateConfidence,
        quality: m.anprQuality,
        sightingId: m.anprSightingId,
        cameraId: m.cameraId,
        timestamp: m.timestamp,
      }))
  }, [group])
  const referencedDetections = useMemo(() => {
    if (!group) return []
    return [...new Set(group.memberEvents.map(m => m.detectionId).filter((d): d is string => d !== null))]
  }, [group])
  const referencedTracks = useMemo(() => {
    if (!group) return []
    return [...new Set(group.memberEvents.map(m => m.trackId).filter((t): t is string => t !== null))]
  }, [group])

  const onSelectMember = (member: CorrelationEventMember) => {
    setSelectedMember(member)
    setDrawerOpen(true)
  }
  const onSelectEventId = (eventId: string) => {
    const member = group?.memberEvents.find(m => m.eventId === eventId)
    if (member) onSelectMember(member)
  }

  if (!group) {
    return (
      <div className="h-full overflow-y-auto p-4 md:p-6 space-y-5">
        <PageHeader title="Correlation Detail" subtitle={correlationId} />
        <section className="rounded-xl border border-[#1e2d40] bg-[#0d1117] p-4">
          {detailState === 'loading' || detailState === 'idle' ? (
            <div
              className="mx-auto my-10 h-6 w-6 animate-spin rounded-full border-2 border-cyan-400 border-t-transparent"
              role="status"
              aria-label="Loading correlation detail"
            />
          ) : detailError ? (
            <ErrorState message={detailError} onRetry={retry} />
          ) : (
            <ErrorState message={`No correlation group exists with id ${correlationId ?? '—'}.`} />
          )}
          <div className="mt-2 text-center">
            <Link to="/events" className="text-xs text-cyan-400 underline underline-offset-2 hover:text-cyan-300">
              Back to event log
            </Link>
          </div>
        </section>
      </div>
    )
  }

  const missingMembers =
    group.memberEventsLoaded !== null ? Math.max(0, group.eventCount - group.memberEventsLoaded) : 0
  // A failed refresh over already-loaded data shows that data rather than an
  // empty page (§64) — but it is labelled as stale, never as current.
  const isStale = detailState === 'error'
  // C4 stores no incident state of its own; these ids are the C1 Risk Engine's
  // references surfaced by value-of-reference, never owned or computed here.
  const referencedIncidentIds = group.risk.incidentIds
  const incidentHint = group.incidentId
    ? group.incidentState
      ? INCIDENT_STATE_LABEL[group.incidentState]
      : undefined
    : referencedIncidentIds.length > 0
      ? 'Referenced by the Component 1 Risk Engine'
      : undefined

  return (
    <div className="h-full overflow-y-auto p-4 md:p-6 space-y-5">
      <PageHeader
        title="Correlation Detail"
        subtitle={`${group.correlationId} · ${formatWindow(group.startedAt, group.endedAt)}`}
        actions={
          <div className="flex flex-wrap items-center gap-2">
            <CorrelationStatusBadge status={group.status} />
            <Badge variant={TONE[toneForGroupState(group.state)].badge} size="sm">
              {GROUP_STATE_LABEL[group.state]}
            </Badge>
            <Badge variant={TONE[toneForConnectivity(group.connectivity)].badge} size="sm">
              {group.connectivity}
            </Badge>
          </div>
        }
      />

      {isStale && (
        <div className="rounded-xl border border-amber-500/30 bg-amber-500/5 px-4 py-2.5" role="status">
          <p className="text-xs font-semibold text-amber-300">Showing last available correlation data.</p>
          <p className="mt-0.5 text-[11px] text-amber-200/80">
            The latest refresh did not complete — values may be out of date.
          </p>
        </div>
      )}
      {isStale && detailError && (
        <div className="rounded-xl border border-rose-500/30 bg-rose-500/5 px-4 py-2.5" role="alert">
          <p className="text-xs font-semibold text-rose-300">{detailError}</p>
          <button
            type="button"
            onClick={retry}
            className="mt-2 rounded-md border border-rose-400/40 px-3 py-1 text-[11px] font-semibold text-rose-200 hover:bg-rose-500/10"
          >
            Retry
          </button>
        </div>
      )}

      {/* Situation summary — the §83 questions answered from backend fields only. */}
      <Section title="Situation summary">
        <dl className="grid grid-cols-2 gap-x-6 gap-y-3 text-xs sm:grid-cols-3 lg:grid-cols-4">
          <Summary label="What grouped" value={formatSignalCount(group.eventCount)} />
          <Summary label="Cameras involved" value={formatCameraList(group.cameraChain, memberCameras)} />
          <Summary
            label="Where"
            value={group.sectorId ?? 'Sector not reported'}
            hint={memberZones.length > 0 ? `zones ${memberZones.join(', ')}` : 'no zone reported'}
          />
          <Summary label="When" value={formatWindow(group.startedAt, group.endedAt)} />
          <Summary
            label="Temporal window"
            value={group.temporalWindowSec !== null ? `${group.temporalWindowSec} sec (configured)` : 'Not reported'}
          />
          <Summary label="Modalities" value={formatModalities(group.modalities)} />
          <Summary
            label="Correlation strength"
            value={group.correlationStrength ?? 'Not reported'}
            hint="How strongly the signals relate — not risk."
          />
          <Summary
            label="Confidence"
            value={group.confidence ? formatConfidence(group.confidence.value) : 'Not provided'}
            hint={group.confidence?.note}
          />
          <Summary label="Linked evidence" value={`${group.evidenceCount} record${group.evidenceCount === 1 ? '' : 's'}`} />
          <Summary
            label="Incident"
            value={
              group.incidentId ??
              (referencedIncidentIds.length > 0
                ? referencedIncidentIds.join(', ')
                : 'Not linked to an incident')
            }
            hint={incidentHint}
          />
          <Summary label="Primary event" value={group.primaryEventId ?? 'Not designated'} />
          <Summary label="Last updated" value={new Date(group.updatedAt).toLocaleString()} />
        </dl>
        {group.explanationSummary && (
          <p className="mt-4 border-t border-white/5 pt-3 text-xs leading-relaxed text-slate-300">
            {group.explanationSummary}
          </p>
        )}
        {group.duplicatedOrSuppressed && (
          <p className="mt-3 rounded-md border border-amber-500/30 bg-amber-500/5 px-3 py-2 text-[11px] text-amber-200">
            Backend flags transport duplication or suppression for this group — counts may include repeated or
            withheld signals.
          </p>
        )}
      </Section>

      <div className="grid grid-cols-1 gap-5 xl:grid-cols-3">
        <div className="space-y-5 xl:col-span-2">
          <Section title="Signal timeline" action={<span className="font-mono text-[11px] text-slate-500">{group.correlationId}</span>}>
            <CorrelationTimeline group={group} onSelectMember={onSelectMember} />
          </Section>

          <Section title="Signals in this correlation">
            <CorrelationSignals
              members={group.memberEvents}
              primaryEventId={group.primaryEventId}
              onSelect={onSelectMember}
            />
            {missingMembers > 0 && (
              <p className="mt-3 rounded-md border border-white/10 bg-white/5 px-3 py-2 text-[11px] text-slate-400">
                {missingMembers} of {group.eventCount} member events are not present in this response — the
                backend reports the full count.
              </p>
            )}
          </Section>

          <Section
            title="Relationships"
            action={
              <span className="text-[11px] text-slate-500">
                {relationshipState === 'loading'
                  ? 'loading…'
                  : `${relationships.length} relationship${relationships.length === 1 ? '' : 's'}`}
              </span>
            }
          >
            {relationshipState === 'error' ? (
              <div className="rounded-md border border-rose-500/30 bg-rose-500/5 px-3 py-2" role="alert">
                <p className="text-[11px] text-rose-200">Relationships could not be loaded.</p>
                <button
                  type="button"
                  onClick={reviewRelationships}
                  className="mt-1.5 rounded border border-rose-400/40 px-2 py-0.5 text-[11px] font-semibold text-rose-200 hover:bg-rose-500/10"
                >
                  Retry
                </button>
              </div>
            ) : (
              <>
                <CorrelationGraph group={group} relationships={relationships} onSelect={onSelectEventId} />
                {relationships.length === 0 ? (
                  <p className="mt-3 text-[11px] text-slate-500">
                    No pairwise relationship was reported by the backend for this group.
                  </p>
                ) : (
                  <ul className="mt-3 space-y-2">
                    {relationships.map(r => (
                      <li
                        key={`${r.fromEventId}-${r.toEventId}-${r.type}`}
                        className="rounded-md border border-white/10 bg-[#0d1117]/40 px-3 py-2"
                      >
                        <div className="flex flex-wrap items-center gap-2">
                          <span className="font-mono text-[11px] text-slate-300">{r.fromEventId}</span>
                          <span className="text-[10px] uppercase tracking-wider text-cyan-300">{r.type}</span>
                          <span className="font-mono text-[11px] text-slate-300">{r.toEventId}</span>
                          {r.strength !== null && (
                            <span className="font-mono text-[10px] text-slate-500">
                              strength {formatConfidence(r.strength)}
                            </span>
                          )}
                        </div>
                        <p className="mt-1 text-[11px] text-slate-400">{r.explanation}</p>
                      </li>
                    ))}
                  </ul>
                )}
              </>
            )}
          </Section>

          <Section title="Vehicle / plate reads">
            {plateReads.length === 0 ? (
              <p className="text-[11px] text-slate-500">
                No plate read was reported by the backend for these signals.
              </p>
            ) : (
              <ul className="space-y-2">
                {plateReads.map(p => (
                  <li
                    key={`${p.eventId}-${p.plate}`}
                    className="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-md border border-white/10 bg-[#0d1117]/40 px-3 py-2"
                  >
                    <Link
                      to={`/anpr?search=${encodeURIComponent(p.plate)}`}
                      className="font-mono text-sm font-semibold tracking-wider text-cyan-300 hover:text-cyan-200"
                    >
                      {p.plate}
                    </Link>
                    {p.confidence !== null && (
                      <span className="font-mono text-[11px] text-slate-400">
                        confidence {formatConfidence(p.confidence)}
                      </span>
                    )}
                    {p.quality && <span className="font-mono text-[11px] text-slate-500">quality {p.quality}</span>}
                    <Link
                      to={`/camera/${p.cameraId}`}
                      className="font-mono text-[11px] text-slate-400 hover:text-cyan-300"
                    >
                      {p.cameraId}
                    </Link>
                    <span className="font-mono text-[11px] text-slate-500">
                      {new Date(p.timestamp).toLocaleTimeString([], { hour12: false })}
                    </span>
                    {p.sightingId && (
                      <span className="font-mono text-[10px] text-slate-600">sighting {p.sightingId}</span>
                    )}
                  </li>
                ))}
              </ul>
            )}
            <p className="mt-2 text-[10px] text-slate-500">
              Plate values are reported by the ANPR source and shown verbatim — never an identity claim.
            </p>
          </Section>

          <Section title="Cameras & tracks">
            <ul className="space-y-2">
              {group.memberEvents.map(m => {
                const health = group.healthContext.find(h => h.cameraId === m.cameraId) ?? m.healthContext
                const healthTone = health ? TONE[toneForReliability(health.reliability)] : null
                return (
                  <li
                    key={`${m.eventId}-cam`}
                    className="flex flex-wrap items-center gap-x-4 gap-y-1 rounded-md border border-white/10 bg-[#0d1117]/40 px-3 py-2"
                  >
                    <Link to={`/camera/${m.cameraId}`} className="font-mono text-xs text-cyan-300 hover:text-cyan-200">
                      {m.cameraId}
                    </Link>
                    {m.trackId ? (
                      <Link
                        to={`/track/${m.trackId}`}
                        className="font-mono text-[11px] text-slate-300 hover:text-cyan-300"
                      >
                        track {m.trackId}
                      </Link>
                    ) : (
                      <span className="font-mono text-[11px] text-slate-500">no track</span>
                    )}
                    {m.zoneId && <span className="font-mono text-[11px] text-slate-500">zone {m.zoneId}</span>}
                    {healthTone && health && (
                      <span
                        className={`inline-flex items-center gap-1 font-mono text-[10px] uppercase tracking-wider ${healthTone.text}`}
                      >
                        <span className={`h-1.5 w-1.5 rounded-full ${healthTone.dot}`} aria-hidden />
                        {RELIABILITY_LABEL[health.reliability]}
                      </span>
                    )}
                  </li>
                )
              })}
            </ul>

            {group.trackCandidate && (
              <div className="mt-3 rounded-md border border-white/10 bg-white/5 px-3 py-2">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
                  Possible same-entity candidate
                </p>
                <div className="mt-1 flex flex-wrap items-center gap-3">
                  <Link
                    to={`/track/${group.trackCandidate.trackId}`}
                    className="font-mono text-xs text-cyan-300 hover:text-cyan-200"
                  >
                    {group.trackCandidate.trackId}
                  </Link>
                  {group.trackCandidate.confidence !== null && (
                    <span className="font-mono text-[11px] text-slate-400">
                      confidence {formatConfidence(group.trackCandidate.confidence)}
                    </span>
                  )}
                  <span className="text-[11px] text-slate-400">{group.trackCandidate.label}</span>
                </div>
                <p className="mt-1 text-[10px] text-slate-500">
                  A possibility reported by tracking — not an identity confirmation.
                </p>
              </div>
            )}

            {group.healthContext.length > 0 && (
              <div className="mt-3 space-y-1">
                {group.healthContext.map(h => (
                  <p key={h.cameraId} className="text-[11px] text-slate-400">
                    <span className="font-mono text-slate-300">{h.cameraId}</span> reliability{' '}
                    {RELIABILITY_LABEL[h.reliability]}
                    {h.note ? ` — ${h.note}` : ''}
                  </p>
                ))}
                <p className="text-[10px] text-slate-500">
                  Camera reliability is context only — it does not alter risk.
                </p>
              </div>
            )}
          </Section>
        </div>

        <div className="space-y-5">
          <Section title="Risk & severity" action={<span className="text-[10px] uppercase tracking-wider text-slate-500">Component 1</span>}>
            <CorrelationRisk risk={group.risk} />
          </Section>

          <Section title="Why this grouping">
            <CorrelationExplanation group={group} />
          </Section>

          <Section title="Uncertainty">
            <CorrelationUncertainty group={group} />
          </Section>

          <CorrelationHistory group={group} />

          <Section title="Sources">
            <SourceLegend sources={group.sources} />
          </Section>

          <Section title="Referenced records">
            <p className="text-[11px] text-slate-400">
              This view groups signals owned by other components. Those records remain authoritative.
            </p>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {memberCameras.map(id => (
                <Link
                  key={id}
                  to={`/camera/${id}`}
                  className="rounded border border-white/10 bg-white/5 px-2 py-0.5 font-mono text-[10px] text-slate-300 transition-colors hover:border-cyan-500/40 hover:text-cyan-300"
                >
                  {id}
                </Link>
              ))}
              {referencedTracks.map(id => (
                <Link
                  key={id}
                  to={`/track/${id}`}
                  className="rounded border border-white/10 bg-white/5 px-2 py-0.5 font-mono text-[10px] text-slate-300 transition-colors hover:border-cyan-500/40 hover:text-cyan-300"
                >
                  {id}
                </Link>
              ))}
              {referencedDetections.map(id => (
                <span
                  key={id}
                  className="rounded border border-white/10 bg-white/5 px-2 py-0.5 font-mono text-[10px] text-slate-400"
                >
                  {id}
                </span>
              ))}
            </div>
            <div className="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1">
              {group.evidenceCount > 0 && (
                <Link to="/evidence" className="text-[11px] text-cyan-300 hover:text-cyan-200">
                  View {group.evidenceCount} evidence record{group.evidenceCount === 1 ? '' : 's'} in Component 3 →
                </Link>
              )}
              <Link to="/events" className="text-[11px] text-cyan-300 hover:text-cyan-200">
                Open in event log →
              </Link>
            </div>
            <p className="mt-3 font-mono text-[10px] text-slate-500">
              events {group.memberEvents.map(m => m.eventId).join(', ')}
            </p>
          </Section>
        </div>
      </div>

      <CorrelationEventDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        member={selectedMember}
        group={group}
      />
    </div>
  )
}

function Section({ title, action, children }: { title: string; action?: ReactNode; children: ReactNode }) {
  return (
    <section className="rounded-xl border border-[#1e2d40] bg-[#0d1117] p-4" aria-label={title}>
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-sm font-semibold text-slate-200">{title}</h3>
        {action}
      </div>
      {children}
    </section>
  )
}

function Summary({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div>
      <dt className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">{label}</dt>
      <dd className="mt-0.5 text-xs text-slate-200">{value}</dd>
      {hint && <p className="mt-0.5 text-[10px] text-slate-500">{hint}</p>}
    </div>
  )
}
