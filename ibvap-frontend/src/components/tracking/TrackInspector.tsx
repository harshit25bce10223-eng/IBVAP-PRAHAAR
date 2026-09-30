// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 6 — Track Inspector Drawer (§52, §53–§59, §126).
//
// Sections: Identity, Current Observation, Lifecycle, Class Revisions,
// Detection History, Trajectory, Camera/Health Context, Relationships,
// Downstream Links. Every displayed value is provider-supplied; missing
// values render as N/A or a hidden section, never as a fabricated fact.
// ─────────────────────────────────────────────────────────────────────────────

import { Link } from 'react-router-dom'
import { clsx } from 'clsx'
import { ArrowRight, Camera as CameraIcon, FileSearch, Fingerprint, Network, Route, Shield, AlertTriangle } from 'lucide-react'
import type { Track } from '@/types/tracking'
import { Badge, Drawer } from '@/components/ui'
import {
  formatTrackClassLabel,
  formatContinuityQuality,
  formatClock,
  formatDate,
  formatDuration,
  formatBBox,
  formatSpeed,
  formatVelocity,
  formatObservationCount,
} from './trackFormat'
import { toneForStatus, toneForQuality, toneForSource, badgeTone, dotTone } from './trackTone'

interface TrackInspectorProps {
  open: boolean
  onClose: () => void
  track: Track | null
  /** Any local additional label, e.g. camera label from the camera registry. */
  cameraLabel?: string | null
}

const STATUS_LABEL: Record<Track['status'], string> = {
  ACTIVE: 'ACTIVE',
  TENTATIVE: 'TENTATIVE',
  LOST: 'LOST',
  REACQUIRED: 'REACQUIRED',
  ENDED: 'ENDED',
  STALE: 'STALE',
  INVALID: 'INVALID',
  UNKNOWN: 'UNKNOWN',
}

const SOURCE_LABEL: Record<Track['source'], string> = {
  LIVE: 'LIVE',
  EDGE: 'EDGE',
  CENTRAL: 'CENTRAL',
  DEMO: 'DEMO',
  UNKNOWN: '—',
}

/**
 * Track Inspector (Component 6 spec §52, §53–§59). Sections are hidden when
 * their data is empty. Every displayed value is provider-supplied; missing
 * values render as N/A or a hidden section, never as a fabricated fact.
 * We NEVER display a cross-camera link unless the backend provided one, and
 * related references (event/incident/evidence) are links to existing surfaces only.
 */
export function TrackInspector({ open, onClose, track, cameraLabel }: TrackInspectorProps) {
  if (!track) return null

  const stateTone = toneForStatus(track.status)
  const qualityTone = toneForQuality(track.continuityQuality ?? 'UNKNOWN')
  const sourceTone = toneForSource(track.source)
  const relatedCount = [
    track.eventId,
    track.correlationId,
    track.incidentId,
    track.evidenceId,
    track.candidateEntityId,
  ].filter((v): v is string => v !== null).length

  return (
    <Drawer open={open} onClose={onClose} title={`Track Inspector — ${track.trackId}`}>
      {/* Identity strip */}
      <div className="mb-4 flex items-center justify-between border-b border-[#1e2d40] pb-3">
        <div>
          <h2 className="text-sm font-semibold text-slate-200">{track.trackId}</h2>
          <p className="mt-0.5 text-xs text-slate-400">
            {cameraLabel ? `${cameraLabel} · ` : ''}{track.cameraId} · {formatTrackClassLabel(track.objectClass)}
          </p>
        </div>
        <Badge variant={badgeTone(stateTone)} size="sm" dot>
          {STATUS_LABEL[track.status]}
        </Badge>
      </div>

      {/* Camera Health Context (§58, §85) */}
      {track.cameraHealthContext && (
        <section className="mb-4 rounded-lg border border-amber-500/30 bg-amber-500/5 p-3" aria-label="Camera health context">
          <div className="flex items-start gap-2">
            <CameraIcon size={14} className="text-amber-400 mt-0.5 shrink-0" aria-hidden />
            <div>
              <p className="text-[11px] font-semibold text-amber-300">Camera health context</p>
              <p className="mt-1 text-[11px] text-slate-400">
                Camera: <span className="font-mono">{track.cameraHealthContext.status}</span>{' '}
                Reliability: <span className="font-mono">{track.cameraHealthContext.reliability}</span>
              </p>
              {track.cameraHealthContext.viewpointShiftDetected && (
                <p className="mt-1 text-[10px] text-amber-300">
                  ⚠ Viewpoint shift detected — track geometry context may be affected (§86).
                </p>
              )}
              {track.cameraHealthContext.note && (
                <p className="mt-1 text-[10px] text-slate-500">{track.cameraHealthContext.note}</p>
              )}
              <p className="mt-2 text-[10px] text-slate-600">
                Track confidence/quality above is separate from camera/source reliability.
              </p>
            </div>
          </div>
        </section>
      )}

      <div className="space-y-4">
        {/* Section: Current Observation (§54) */}
        <section className="rounded-lg border border-[#1e2d40] bg-[#0d1117] p-3" aria-label="Current observation">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Current Observation</h3>
          <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[11px]">
            <div className="flex items-center justify-between">
              <dt className="text-slate-500">State</dt>
              <dd className="flex items-center gap-1.5 font-mono text-slate-200">
                <span className={clsx('h-1.5 w-1.5 rounded-full', dotTone(stateTone))} aria-hidden />
                {STATUS_LABEL[track.status]}
              </dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-slate-500">Continuity</dt>
              <dd className="flex items-center gap-1.5 font-mono text-slate-200">
                <span className={clsx('h-1.5 w-1.5 rounded-full', dotTone(qualityTone))} aria-hidden />
                {formatContinuityQuality(track.continuityQuality)}
              </dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-slate-500">Track Confidence</dt>
              <dd className="font-mono text-slate-300">{formatConfidence(track.confidence)}</dd>
            </div>
            <div className="flex items-center justify-between col-span-2">
              <dt className="text-slate-500">Current BBox (norm.)</dt>
              <dd className="font-mono text-slate-300">
                {track.currentBoundingBox
                  ? formatBBox(
                      track.currentBoundingBox.x,
                      track.currentBoundingBox.y,
                      track.currentBoundingBox.width,
                      track.currentBoundingBox.height
                    )
                  : 'N/A'}
              </dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-slate-500">Current Detection</dt>
              <dd className="font-mono text-slate-300">{track.currentDetectionId ?? 'N/A'}</dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-slate-500">Last Observed</dt>
              <dd className="font-mono text-slate-300">{formatClock(track.lastSeenAt)}</dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-slate-500">Source</dt>
              <dd className="flex items-center gap-1.5 font-mono text-slate-300">
                <span className={clsx('h-1.5 w-1.5 rounded-full', dotTone(sourceTone))} aria-hidden />
                {SOURCE_LABEL[track.source]}
              </dd>
            </div>
          </dl>
        </section>

        {/* Section: Lifecycle (§53) */}
        <section className="rounded-lg border border-[#1e2d40] bg-[#0d1117] p-3" aria-label="Track lifecycle">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Lifecycle</h3>
          <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[11px]">
            <div className="flex items-center justify-between">
              <dt className="text-slate-500">First Seen</dt>
              <dd className="flex items-center gap-1.5">
                <span className="font-mono text-slate-200">{formatClock(track.firstSeenAt)}</span>
                <span className="text-slate-500">{formatDate(track.firstSeenAt)}</span>
              </dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-slate-500">Last Seen</dt>
              <dd className="flex items-center gap-1.5">
                <span className="font-mono text-slate-200">{formatClock(track.lastSeenAt)}</span>
                <span className="text-slate-500">{formatDate(track.lastSeenAt)}</span>
              </dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-slate-500">Age / Duration</dt>
              <dd className="font-mono text-slate-200">{track.ageMs ? formatDuration(track.ageMs) : track.durationSec ? `${track.durationSec}s` : 'N/A'}</dd>
            </div>
            <div className="flex items-center justify-between">
              <dt className="text-slate-500">Observations</dt>
              <dd className="font-mono text-slate-200">{formatObservationCount(track.detectionCount)}</dd>
            </div>
            {track.speed !== null && track.speed !== undefined && (
              <div className="flex items-center justify-between">
                <dt className="text-slate-500">Speed</dt>
                <dd className="font-mono text-slate-200">{formatSpeed(track.speed)}</dd>
              </div>
            )}
            {track.direction && (
              <div className="flex items-center justify-between">
                <dt className="text-slate-500">Direction</dt>
                <dd className="font-mono text-slate-200">{track.direction}</dd>
              </div>
            )}
            {track.velocity !== null && track.velocity !== undefined && (
              <div className="flex items-center justify-between">
                <dt className="text-slate-500">Velocity</dt>
                <dd className="font-mono text-slate-200">{formatVelocity(track.velocity, track.direction)}</dd>
              </div>
            )}
          </dl>
        </section>

        {/* Section: Class Revisions (§44, §45) */}
        {track.previousClass && (
          <section className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3" aria-label="Class revision history">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-amber-400 mb-2">Class Revision</h3>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[11px]">
              <div className="flex items-center justify-between">
                <dt className="text-slate-500">Previous Class</dt>
                <dd className="font-mono text-slate-300">{formatTrackClassLabel(track.previousClass)}</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-slate-500">Current Class</dt>
                <dd className="font-mono text-slate-300">{formatTrackClassLabel(track.objectClass)}</dd>
              </div>
              {track.classRevisedAt && (
                <div className="flex items-center justify-between col-span-2">
                  <dt className="text-slate-500">Revised At</dt>
                  <dd className="font-mono text-slate-300">{formatClock(track.classRevisedAt)}</dd>
                </div>
              )}
              {track.classRevisionReason && (
                <div className="flex items-center justify-between col-span-2">
                  <dt className="text-slate-500">Reason</dt>
                  <dd className="text-slate-300 col-span-2">{track.classRevisionReason}</dd>
                </div>
              )}
            </dl>
          </section>
        )}

        {/* Section: Detection History (§55) */}
        <section className="rounded-lg border border-[#1e2d40] bg-[#0d1117] p-3" aria-label="Detection history">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">Detection History</h3>
            <span className="font-mono text-[11px] text-slate-500">{track.detectionCount} observations</span>
          </div>
          <p className="text-[10px] text-slate-500 mb-2">
            This drawer summarizes the track record. The full per-observation history is rendered in the Track Detail workspace.
          </p>
          <Link
            to={`/track/${track.trackId}`}
            className="inline-flex items-center gap-1 text-[11px] text-cyan-400 hover:underline underline-offset-2"
          >
            Open track workspace <ArrowRight size={10} aria-hidden />
          </Link>
        </section>

        {/* Section: Trajectory (§56) */}
        {track.trajectory && track.trajectory.length > 0 && (
          <section className="rounded-lg border border-[#1e2d40] bg-[#0d1117] p-3" aria-label="Trajectory">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Trajectory</h3>
            <p className="text-[10px] text-slate-500 mb-2">
              {track.trajectory.length} waypoints · {(track.trajectory.length > 30 ? 'showing last 30' : 'full history')}
            </p>
            <div className="overflow-x-auto">
              <table className="w-full text-[10px]">
                <thead>
                  <tr className="text-left text-slate-500 border-b border-white/10">
                    <th className="pb-1 font-mono">Seq</th>
                    <th className="pb-1 font-mono">Time</th>
                    <th className="pb-1 font-mono">X</th>
                    <th className="pb-1 font-mono">Y</th>
                    <th className="pb-1 font-mono">Speed</th>
                  </tr>
                </thead>
                <tbody>
                  {track.trajectory.slice(-30).map((p, idx) => (
                    <tr key={p.observationId ?? idx} className="border-b border-white/5">
                      <td className="py-1 font-mono text-slate-300">{p.sequence ?? idx + 1}</td>
                      <td className="py-1 font-mono text-slate-300">{p.timestamp ? formatClock(p.timestamp) : '—'}</td>
                      <td className="py-1 font-mono text-slate-300">{p.x.toFixed(3)}</td>
                      <td className="py-1 font-mono text-slate-300">{p.y.toFixed(3)}</td>
                      <td className="py-1 font-mono text-slate-300">{p.speed ? `${p.speed.toFixed(1)} m/s` : '—'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <p className="mt-2 text-[10px] text-slate-600">Trajectory uses provider-supplied normalized coordinates (§30, §106).</p>
          </section>
        )}

        {/* Section: Cross-Camera Candidate (§60–§65) */}
        {track.crossCameraCandidate && (
          <section className="rounded-lg border border-sky-500/30 bg-sky-500/5 p-3" aria-label="Cross-camera candidate">
            <div className="flex items-center gap-2 mb-2">
              <Route size={14} className="text-sky-400" aria-hidden />
              <h3 className="text-xs font-semibold uppercase tracking-wider text-sky-400">Possible Same Entity</h3>
            </div>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[11px]">
              <div className="flex items-center justify-between">
                <dt className="text-slate-500">This Track</dt>
                <dd className="font-mono text-slate-300">{track.trackId}</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-slate-500">Candidate</dt>
                <dd className="font-mono text-slate-300">{track.crossCameraCandidate.candidateTrackId}</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-slate-500">On Camera</dt>
                <dd className="font-mono text-slate-300">{track.crossCameraCandidate.targetCameraId}</dd>
              </div>
              {track.crossCameraCandidate.continuityConfidence !== null && track.crossCameraCandidate.continuityConfidence !== undefined && (
                <div className="flex items-center justify-between">
                  <dt className="text-slate-500">Continuity Confidence</dt>
                  <dd className="font-mono text-slate-300">{formatConfidence(track.crossCameraCandidate.continuityConfidence)}</dd>
                </div>
              )}
              {track.crossCameraCandidate.gapDurationSec !== null && track.crossCameraCandidate.gapDurationSec !== undefined && (
                <div className="flex items-center justify-between">
                  <dt className="text-slate-500">Gap</dt>
                  <dd className="font-mono text-slate-300">{track.crossCameraCandidate.gapDurationSec}s</dd>
                </div>
              )}
              <div className="flex items-center justify-between col-span-2">
                <dt className="text-slate-500">Note</dt>
                <dd className="text-slate-300 col-span-2">{track.crossCameraCandidate.note ?? 'No additional context provided.'}</dd>
              </div>
            </dl>
            <p className="mt-2 text-[10px] text-sky-300/80">
              This is a POSSIBLE CONTINUATION hypothesis from the backend (§61–§65). It does NOT imply confirmed identity (§60, §65).
            </p>
          </section>
        )}

        {/* Section: Relationships (§57) */}
        <section className="rounded-lg border border-[#1e2d40] bg-[#0d1117] p-3" aria-label="Downstream references">
          <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500 mb-2">Downstream Links</h3>
          <dl className="space-y-2 text-[11px]">
            {track.eventId && (
              <div className="flex items-center gap-2">
                <AlertTriangle size={12} className="text-slate-400" aria-hidden />
                <dt className="text-slate-500 shrink-0">Event</dt>
                <dd className="flex-1">
                  {/* 'search' is the URL param the Event Log actually understands (correlationQueryUrl.ts) */}
                  <Link to={`/events?search=${encodeURIComponent(track.eventId)}`} className="font-mono text-cyan-400 hover:underline underline-offset-2">
                    {track.eventId}
                  </Link>
                </dd>
              </div>
            )}
            {track.correlationId && (
              <div className="flex items-center gap-2">
                <Network size={12} className="text-slate-400" aria-hidden />
                <dt className="text-slate-500 shrink-0">Correlation</dt>
                <dd className="flex-1">
                  <Link to={`/incident/${track.correlationId}`} className="font-mono text-cyan-400 hover:underline underline-offset-2">
                    {track.correlationId}
                  </Link>
                </dd>
              </div>
            )}
            {track.incidentId && (
              <div className="flex items-center gap-2">
                <Shield size={12} className="text-slate-400" aria-hidden />
                <dt className="text-slate-500 shrink-0">Incident</dt>
                <dd className="flex-1">
                  {/* No existing surface resolves an INC-* id from a URL — the
                      /incident/:correlationId route accepts correlation ids only.
                      Shown as a reference value, not a false deep link. */}
                  <span className="font-mono text-slate-300">{track.incidentId}</span>
                </dd>
              </div>
            )}
            {track.evidenceId && (
              <div className="flex items-center gap-2">
                <FileSearch size={12} className="text-slate-400" aria-hidden />
                <dt className="text-slate-500 shrink-0">Evidence</dt>
                <dd className="flex-1">
                  {/* Evidence Ledger has no per-record route; it opens unfiltered. */}
                  <Link to="/evidence" className="font-mono text-cyan-400 hover:underline underline-offset-2">
                    {track.evidenceId}
                  </Link>
                </dd>
              </div>
            )}
            {track.candidateEntityId && !track.crossCameraCandidate && (
              <div className="flex items-center gap-2">
                <Fingerprint size={12} className="text-slate-400" aria-hidden />
                <dt className="text-slate-500 shrink-0">Candidate Entity</dt>
                <dd className="font-mono text-slate-300">{track.candidateEntityId}</dd>
              </div>
            )}
            {!track.eventId && !track.correlationId && !track.incidentId && !track.evidenceId && !track.candidateEntityId && (
              <p className="text-slate-500">No downstream event, correlation, incident or evidence linked.</p>
            )}
          </dl>
          <p className="mt-2 text-[10px] text-slate-600">
            {relatedCount} related record{relatedCount === 1 ? '' : 's'} in other domains.
          </p>
        </section>

        {/* Section: Data Quality & Completeness (§142) */}
        {(track.dataCompleteness || track.missingObservationsNote) && (
          <section className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3" aria-label="Data quality">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-amber-400 mb-2">Data Quality</h3>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[11px]">
              {track.dataCompleteness && (
                <div className="flex items-center justify-between">
                  <dt className="text-slate-500">Completeness</dt>
                  <dd className="font-mono text-slate-300">{track.dataCompleteness}</dd>
                </div>
              )}
              {track.missingObservationsNote && (
                <div className="flex items-center justify-between col-span-2">
                  <dt className="text-slate-500">Missing Data Note</dt>
                  <dd className="text-slate-300 col-span-2">{track.missingObservationsNote}</dd>
                </div>
              )}
            </dl>
          </section>
        )}

        {/* Footer */}
        <div className="border-t border-[#1e2d40] pt-3 flex items-center justify-between text-[10px] text-slate-500">
          <span>Provider: {track.provider ?? '—'} · Tracker: {track.trackerName ?? '—'} v{track.trackerVersion ?? '—'}</span>
          <span className="font-mono">rev {track.revision ?? 0}</span>
        </div>
      </div>
    </Drawer>
  )
}

function formatConfidence(value: number | null | undefined | false): string {
  if (value === null || value === undefined || value === false) return 'N/A'
  const pct = value <= 1 ? value * 100 : value
  return `${Math.round(pct)}%`
}