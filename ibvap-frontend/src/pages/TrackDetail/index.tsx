// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 6 — TRACK INTELLIGENCE (/track/:trackId) — §2, §6–§24
//
// The single-track investigation workspace. Fourteen sections per §6:
//   1. Track summary (header, §7)          8. Observation timeline (§13)
//   2. Current state (§8)                  9. Trajectory (§11–§12)
//   3. Camera (§7/§15)                     10. Detection chain (§14 links)
//   4. Object class (§6/§44)               11. Vehicle/ANPR context (§16)
//   5. First/last observed (§7)            12. Event/correlation (§17)
//   6. Continuity quality (§7/§21)         13. Incident (§18)
//   7. Lifecycle timeline (§8–§10)         14. Evidence + camera health (§19/§15)
//
// Everything rendered here is recorded data or explicitly labelled derivation.
// LOST is not ENDED (§9); REACQUIRED never asserts identity across a gap (§10);
// classes are observations, never severity (§41, §121). Section-level failures
// degrade to labelled notes — a failed section is never shown as 'empty'.
//
// The route component keys the view by trackId so a new track mounts fresh
// state (no reset effects, no cascading renders).
// ─────────────────────────────────────────────────────────────────────────────

import { useEffect, useMemo, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import {
  ArrowLeft,
  Video,
  Clock,
  Shield,
  Activity,
  FileCheck,
  AlertTriangle,
  Car,
  History,
  MapPin,
  Camera,
  Route,
} from 'lucide-react'
import type { CorrelationGroup } from '@/types/eventCorrelation'
import type { VehicleSighting } from '@/types/anpr'
import { DEFAULT_ANPR_FILTER } from '@/types/anpr'
import type { Track, TrackCandidate, TrackLifecycleEvent, TrackObservation } from '@/types/tracking'
import { trackingService } from '@/services/tracking'
import { correlationService } from '@/services/correlation'
import { getANPRService } from '@/services/anpr'
import { useANPRStore } from '@/store/anprState'
import {
  TrackTrajectory,
  TrackLifecycleTimeline,
  TrackObservationTable,
  StateChip,
  correlationStatusText,
  findLatestReacquisition,
  findLatestTransition,
  formatTrackClassLabel,
  formatClock,
  formatConfidence,
  formatDate,
  formatDuration,
  formatObservationCount,
  formatSpeed,
  formatSourceLabel,
  formatVelocity,
  relationLabel,
  trajectoryQualityNotes,
} from '@/components/tracking'
import { Badge } from '@/components/ui'
import {
  badgeTone,
  toneForCameraHealth,
  toneForQuality,
  toneForSource,
  toneForStatus,
} from '@/components/tracking/trackTone'

type Load = 'idle' | 'loading' | 'ready' | 'error'

const SECTION =
  'rounded-xl border border-[#1e2d40] bg-[#0d1117] p-4'
const SECTION_HEAD =
  'mb-3 border-b border-slate-800/60 pb-2 text-xs font-semibold uppercase tracking-wider text-slate-300'

function errText(err: unknown, fallback: string): string {
  return err instanceof Error ? err.message : fallback
}

/** '07 Sep 02:14:11' — honest composite for panel lines. */
function ts(iso: string | null | undefined): string {
  if (!iso) return '—'
  return `${formatDate(iso)} ${formatClock(iso)}`
}

export function TrackDetailPage() {
  const { trackId } = useParams<{ trackId: string }>()

  if (!trackId) {
    return <TrackUnavailablePanel message="No track id was provided in the route." />
  }
  // Fresh mount per track id — section load states start in their true value.
  return <TrackDetailView key={trackId} trackId={trackId} />
}

function TrackDetailView({ trackId }: { trackId: string }) {
  const navigate = useNavigate()
  const anprMode = useANPRStore(s => s.serviceMode)

  const [track, setTrack] = useState<Track | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // §8–§10 recorded lifecycle transitions (GET /tracks/{id}/history).
  const [lifecycle, setLifecycle] = useState<TrackLifecycleEvent[]>([])
  const [lifecycleLoad, setLifecycleLoad] = useState<Load>('loading')
  const [lifecycleError, setLifecycleError] = useState<string | null>(null)

  // §13 observation chain (GET /tracks/{id}/observations).
  const [observations, setObservations] = useState<TrackObservation[]>([])
  const [observationsLoad, setObservationsLoad] = useState<Load>('loading')
  const [observationsError, setObservationsError] = useState<string | null>(null)

  // §20 cross-camera candidates (GET /tracks/{id}/candidates).
  const [candidates, setCandidates] = useState<TrackCandidate[]>([])
  const [candidatesLoad, setCandidatesLoad] = useState<Load>('loading')
  const [candidatesError, setCandidatesError] = useState<string | null>(null)

  // §17 relation status — best-effort, display only. No correlation logic here.
  const [correlation, setCorrelation] = useState<CorrelationGroup | null>(null)
  const [correlationLoad, setCorrelationLoad] = useState<Load>('idle')

  // §16 vehicle/plate observations — VEHICLE tracks only, read-only sighting search.
  const [sightings, setSightings] = useState<VehicleSighting[]>([])
  const [sightingsLoad, setSightingsLoad] = useState<Load>('idle')
  const [sightingsError, setSightingsError] = useState<string | null>(null)

  // Core record + section records. A section failure is isolated: the page
  // still renders the record with an explicit unavailable note (§28).
  useEffect(() => {
    let cancelled = false

    trackingService
      .getTrack(trackId)
      .then(t => {
        if (!cancelled) setTrack(t)
      })
      .catch(err => {
        if (!cancelled) setError(errText(err, 'Track record could not be loaded.'))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    trackingService
      .getTrackHistory(trackId)
      .then(obs => {
        if (cancelled) return
        setObservations(obs)
        setObservationsLoad('ready')
      })
      .catch(err => {
        if (cancelled) return
        setObservationsError(errText(err, 'Observation history unavailable.'))
        setObservationsLoad('error')
      })

    trackingService
      .getTrackLifecycleHistory(trackId)
      .then(hist => {
        if (cancelled) return
        setLifecycle(hist)
        setLifecycleLoad('ready')
      })
      .catch(err => {
        if (cancelled) return
        setLifecycleError(errText(err, 'Lifecycle transitions unavailable.'))
        setLifecycleLoad('error')
      })

    trackingService
      .getTrackCandidates(trackId)
      .then(list => {
        if (cancelled) return
        setCandidates(list)
        setCandidatesLoad('ready')
      })
      .catch(err => {
        if (cancelled) return
        setCandidatesError(errText(err, 'Candidate records unavailable.'))
        setCandidatesLoad('error')
      })

    return () => {
      cancelled = true
    }
  }, [trackId])

  // §17 — when the record references a correlation group, surface its recorded
  // relation status. Display only; correlation authority stays in Component 4.
  useEffect(() => {
    const correlationId = track?.correlationId
    if (!correlationId) return
    let cancelled = false
    correlationService
      .getGroup(correlationId)
      .then(group => {
        if (cancelled) return
        setCorrelation(group)
        setCorrelationLoad('ready')
      })
      .catch(() => {
        if (cancelled) return
        setCorrelation(null)
        setCorrelationLoad('error')
      })
    return () => {
      cancelled = true
    }
  }, [track])

  // §16 — VEHICLE tracks only: search this track's sighting linkage (read-only;
  // never mutates the ANPR workspace store). Demo search covers vehicleTrackId.
  useEffect(() => {
    if (!track || track.objectClass !== 'VEHICLE') return
    let cancelled = false
    getANPRService(anprMode)
      .listSightings({ ...DEFAULT_ANPR_FILTER, search: track.trackId })
      .then(page => {
        if (cancelled) return
        setSightings(page.sightings)
        setSightingsLoad('ready')
      })
      .catch(err => {
        if (cancelled) return
        setSightingsError(errText(err, 'Vehicle sightings could not be loaded.'))
        setSightingsLoad('error')
      })
    return () => {
      cancelled = true
    }
  }, [track, anprMode])

  const latestLost = useMemo(() => findLatestTransition(lifecycle, 'LOST'), [lifecycle])
  const reacquisition = useMemo(() => findLatestReacquisition(lifecycle), [lifecycle])

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-[#080c12] p-6">
        <div className="flex flex-col items-center gap-3 text-slate-400 font-mono">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-cyan-400 border-t-transparent" />
          <span className="text-xs">Loading track telemetry for {trackId}…</span>
        </div>
      </div>
    )
  }

  if (error || !track) {
    return (
      <TrackUnavailablePanel
        message={error ?? `Track ${trackId} could not be located in active telemetry.`}
      />
    )
  }

  const health = track.cameraHealthContext ?? null
  const isVehicle = track.objectClass === 'VEHICLE'

  return (
    <div className="h-full flex flex-col overflow-y-auto bg-[#080c12] p-4 md:p-6 gap-5">
      {/* ── §7 Track summary header ─────────────────────────────────────────── */}
      <header className="border-b border-[#1e2d40] pb-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate(-1)}
              className="rounded-md border border-slate-700 bg-slate-800/80 p-1.5 text-slate-300 hover:bg-slate-700 transition-colors"
              title="Go back"
              aria-label="Go back"
            >
              <ArrowLeft className="h-4 w-4" />
            </button>
            <div>
              <p className="text-[10px] font-semibold uppercase tracking-[0.18em] text-slate-500">
                Track Intelligence
                <span className="ml-2 rounded border border-white/10 px-1.5 py-0.5 font-mono text-[9px] tracking-normal text-slate-400">
                  {trackingService.source === 'DEMO' ? 'Demo data' : 'Live backend'}
                </span>
              </p>
              <div className="mt-0.5 flex flex-wrap items-center gap-2.5">
                <h1 className="text-xl font-bold font-mono text-cyan-300">{track.trackId}</h1>
                <Badge variant={badgeTone(toneForStatus(track.status))} size="sm" dot>
                  {track.status}
                </Badge>
                <span className="text-xs text-slate-400 font-sans">
                  {formatTrackClassLabel(track.objectClass)}
                </span>
              </div>
            </div>
          </div>

          <Link
            to={`/camera/${track.cameraId}`}
            className="inline-flex items-center gap-1.5 rounded-md border border-cyan-500/40 bg-cyan-500/10 px-3 py-1.5 text-xs font-mono text-cyan-300 hover:bg-cyan-500/20 transition-colors"
          >
            <Video className="h-3.5 w-3.5" />
            <span>View on {track.cameraId} Feed →</span>
          </Link>
        </div>

        {/* §7 summary fields — recorded values only, no invented metrics. */}
        <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px]">
          <HeaderStat label="Camera">
            <Link to={`/camera/${track.cameraId}`} className="font-mono text-cyan-300 hover:underline">
              {track.cameraId}
            </Link>
          </HeaderStat>
          <HeaderStat label="First observed">
            <span className="font-mono text-slate-200 tabular-nums">{ts(track.firstSeenAt)}</span>
          </HeaderStat>
          <HeaderStat label="Last observed">
            <span className="font-mono text-slate-200 tabular-nums">{ts(track.lastSeenAt)}</span>
          </HeaderStat>
          <HeaderStat label="Observations">
            <span className="font-mono text-slate-200">{formatObservationCount(track.detectionCount)}</span>
          </HeaderStat>
          <HeaderStat label="Continuity">
            <Badge variant={badgeTone(toneForQuality(track.continuityQuality ?? 'UNKNOWN'))} size="sm">
              {track.continuityQuality ?? 'Unknown'}
            </Badge>
          </HeaderStat>
          {track.regionProfile && (
            <HeaderStat label="Region">
              <span className="font-mono text-slate-300">{track.regionProfile}</span>
            </HeaderStat>
          )}
        </div>
      </header>

      {/* ── §9 LOST — temporary, never permanent disappearance ─────────────── */}
      {track.status === 'LOST' && (
        <section className="rounded-xl border border-amber-500/30 bg-amber-500/5 p-4" aria-label="Track lost">
          <div className="flex items-start gap-3">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" aria-hidden />
            <div className="min-w-0">
              <h2 className="text-xs font-bold uppercase tracking-wider text-amber-300">
                Track lost — temporarily unobserved
              </h2>
              <p className="mt-1 text-[11px] text-slate-300">
                Last observed <span className="font-mono text-slate-200">{ts(track.lastSeenAt)}</span> on{' '}
                <span className="font-mono text-cyan-300">{track.cameraId}</span>.
              </p>
              <p className="mt-1 text-[11px] text-slate-400">
                Reason:{' '}
                {lifecycleLoad === 'loading' ? (
                  <span className="text-slate-500">loading recorded transitions…</span>
                ) : lifecycleLoad === 'error' ? (
                  <span className="text-amber-300/90">
                    not available — lifecycle transitions could not be loaded.
                  </span>
                ) : latestLost?.reason ? (
                  <span className="text-slate-300">{latestLost.reason}</span>
                ) : (
                  <span className="text-slate-500">Reason not recorded.</span>
                )}
              </p>
              <p className="mt-1.5 text-[10px] text-amber-300/90">
                A LOST track may still be reacquired — this is not an end-of-track (§9).
              </p>
            </div>
          </div>
        </section>
      )}

      {/* ── §10 REACQUIRED — continuity hypothesis across a recorded gap ────── */}
      {track.status === 'REACQUIRED' && reacquisition && (
        <section className="rounded-xl border border-sky-500/30 bg-sky-500/5 p-4" aria-label="Track reacquired">
          <div className="flex items-start gap-3">
            <History className="mt-0.5 h-4 w-4 shrink-0 text-sky-400" aria-hidden />
            <div className="min-w-0">
              <h2 className="text-xs font-bold uppercase tracking-wider text-sky-300">
                Track reacquired — continuity resumed across a gap
              </h2>
              <dl className="mt-1.5 grid gap-x-6 gap-y-1 text-[11px] sm:grid-cols-3">
                <div>
                  <dt className="text-[10px] uppercase text-slate-500">Last observation before loss</dt>
                  <dd className="font-mono text-slate-200 tabular-nums">{ts(reacquisition.lost.timestamp)}</dd>
                </div>
                <div>
                  <dt className="text-[10px] uppercase text-slate-500">First observation after reacquisition</dt>
                  <dd className="font-mono text-slate-200 tabular-nums">{ts(reacquisition.reacquired.timestamp)}</dd>
                </div>
                <div>
                  <dt className="text-[10px] uppercase text-slate-500">Gap</dt>
                  <dd className="font-mono text-slate-200">{formatDuration(reacquisition.gapSec * 1000)}</dd>
                </div>
              </dl>
              <p className="mt-1.5 text-[10px] text-sky-300/90">
                The link across this gap is a tracking-provider continuity hypothesis recorded at
                reacquisition — identity across the gap is not asserted (§10).
              </p>
            </div>
          </div>
        </section>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* ══ Left 2 columns — lifecycle, trajectory, observations ═══════════ */}
        <div className="lg:col-span-2 space-y-5">
          {/* §8/§2 Current state + lifecycle timeline */}
          <section className={SECTION} aria-label="Lifecycle transitions">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-3 border-b border-slate-800/60 pb-2">
              <h2 className={SECTION_HEAD + ' mb-0 border-0 pb-0'}>
                <span className="inline-flex items-center gap-1.5">
                  <Activity className="h-3.5 w-3.5 text-cyan-400" aria-hidden />
                  Lifecycle transitions (recorded)
                </span>
              </h2>
              <span className="flex items-center gap-2 text-[10px] text-slate-500">
                Current state
                <StateChip status={track.status} />
                <span className="tabular-nums">as recorded at {ts(track.updatedAt ?? track.observedAt)}</span>
              </span>
            </div>
            {lifecycleLoad === 'error' ? (
              <SectionError
                title="Lifecycle transitions unavailable"
                message={lifecycleError ?? 'The transition record store could not be reached.'}
                note="Track state below is still the value recorded on the track record itself."
              />
            ) : lifecycleLoad === 'loading' ? (
              <SectionLoading label="Loading recorded transitions…" />
            ) : (
              <TrackLifecycleTimeline history={lifecycle} />
            )}
          </section>

          {/* §11/§12 Trajectory + quality context (§23 observed vs inferred) */}
          <section className={SECTION} aria-label="Trajectory">
            <h2 className={SECTION_HEAD}>
              <span className="inline-flex items-center gap-1.5">
                <Route className="h-3.5 w-3.5 text-cyan-400" aria-hidden />
                Trajectory
              </span>
            </h2>
            <TrackTrajectory
              track={track}
              containerSize={{ width: 800, height: 450 }}
              fit="contain"
              maxPoints={30}
              showTimestamps={true}
            />
            <TrajectoryQualityNotes track={track} />
            <p className="mt-2 text-[10px] leading-relaxed text-slate-500">
              OBSERVED: the points above are recorded detection positions for this track. No positions
              are interpolated or inferred between observations (§23).
            </p>
          </section>

          {/* §13/§14 Observation table — detection chain back into Component 5 */}
          <section className={SECTION} aria-label="Observations">
            <div className="flex flex-wrap items-center justify-between gap-2 mb-3 border-b border-slate-800/60 pb-2">
              <h2 className={SECTION_HEAD + ' mb-0 border-0 pb-0'}>Observations</h2>
              <span className="text-[10px] font-mono text-slate-500">
                {observationsLoad === 'ready' ? `${observations.length} records loaded` : ''}
              </span>
            </div>
            {observationsLoad === 'error' ? (
              <SectionError
                title="Observation history unavailable"
                message={observationsError ?? 'The observation store could not be reached.'}
                note="The track record itself loaded — no observations are shown or invented."
              />
            ) : observationsLoad === 'loading' ? (
              <SectionLoading label="Loading observation chain…" />
            ) : (
              <>
                {lifecycleLoad === 'error' && (
                  <div className="mb-2 rounded-md border border-amber-500/25 bg-amber-500/5 px-2.5 py-1.5 text-[10px] text-amber-300/90">
                    Lifecycle transitions could not be loaded — the Track State column shows '—' where
                    state cannot be derived from records.
                  </div>
                )}
                <TrackObservationTable observations={observations} history={lifecycle} />
              </>
            )}
          </section>
        </div>

        {/* ══ Right column — telemetry, health, vehicle, links, metadata ═════ */}
        <div className="space-y-5">
          {/* §6/§7/§21/§22 Telemetry summary */}
          <section className={SECTION} aria-label="Telemetry summary">
            <h2 className={SECTION_HEAD}>Telemetry Summary</h2>
            <dl className="grid grid-cols-2 gap-3 text-xs font-mono">
              <div>
                <dt className="text-[10px] text-slate-500 uppercase">First observed</dt>
                <dd className="text-slate-300 tabular-nums">{ts(track.firstSeenAt)}</dd>
              </div>
              <div>
                <dt className="text-[10px] text-slate-500 uppercase">Last observed</dt>
                <dd className="text-slate-300 tabular-nums">{ts(track.lastSeenAt)}</dd>
              </div>
              <div>
                <dt className="text-[10px] text-slate-500 uppercase">Duration</dt>
                <dd className="text-slate-200">
                  {track.durationSec !== null && track.durationSec !== undefined
                    ? formatDuration(track.durationSec * 1000)
                    : formatDuration(track.ageMs)}
                </dd>
              </div>
              <div>
                <dt className="text-[10px] text-slate-500 uppercase">Observations</dt>
                <dd className="text-slate-200">{formatObservationCount(track.detectionCount)}</dd>
              </div>
              <div>
                <dt className="text-[10px] text-slate-500 uppercase">Speed</dt>
                <dd className="text-slate-200">
                  {track.speed !== null && track.speed !== undefined ? formatSpeed(track.speed) : 'N/A'}
                </dd>
              </div>
              <div>
                <dt className="text-[10px] text-slate-500 uppercase">Velocity · direction</dt>
                <dd className="text-slate-200">
                  {formatVelocity(track.velocity ?? track.speed ?? null, track.direction)}
                </dd>
              </div>
              <div>
                <dt className="text-[10px] text-slate-500 uppercase">Track source</dt>
                <dd>
                  <Badge variant={badgeTone(toneForSource(track.source))} size="sm">
                    {formatSourceLabel(track.source)}
                  </Badge>
                </dd>
              </div>
              <div>
                <dt className="text-[10px] text-slate-500 uppercase">Continuity</dt>
                <dd>
                  <Badge variant={badgeTone(toneForQuality(track.continuityQuality ?? 'UNKNOWN'))} size="sm">
                    {track.continuityQuality ?? 'Unknown'}
                  </Badge>
                </dd>
              </div>
              {track.previousClass && (
                <div className="col-span-2">
                  <dt className="text-[10px] text-slate-500 uppercase">Reclassification</dt>
                  <dd className="text-[11px] text-slate-300">
                    Class revised from {formatTrackClassLabel(track.previousClass)} to{' '}
                    {formatTrackClassLabel(track.objectClass)}
                    {track.classRevisionReason ? ` — ${track.classRevisionReason}` : ''}
                    {track.classRevisedAt ? ` (${ts(track.classRevisedAt)})` : ''}.
                  </dd>
                </div>
              )}
            </dl>
            <p className="mt-3 border-t border-slate-800/60 pt-2 text-[10px] leading-relaxed text-slate-500">
              Detection confidence (Component 5) · track continuity · camera health · correlation
              strength are recorded separately and are not combined into a single score here (§21).
            </p>
          </section>

          {/* §15 Camera health context (consume C2; never terminates the track) */}
          <section className={SECTION} aria-label="Camera health context">
            <h2 className={SECTION_HEAD}>
              <span className="inline-flex items-center gap-1.5">
                <Camera className="h-3.5 w-3.5 text-cyan-400" aria-hidden />
                Camera Health Context
              </span>
            </h2>
            {health ? (
              <dl className="space-y-2 text-xs">
                <div className="flex items-center justify-between">
                  <dt className="text-[10px] uppercase text-slate-500">Status</dt>
                  <dd>
                    <Badge variant={badgeTone(toneForCameraHealth(health.status))} size="sm" dot>
                      {health.status}
                    </Badge>
                  </dd>
                </div>
                <div className="flex items-center justify-between">
                  <dt className="text-[10px] uppercase text-slate-500">Reliability</dt>
                  <dd className="font-mono text-slate-300">{health.reliability}</dd>
                </div>
                <div className="flex items-center justify-between">
                  <dt className="text-[10px] uppercase text-slate-500">Viewpoint shift</dt>
                  <dd className="font-mono text-slate-300">
                    {health.viewpointShiftDetected === true
                      ? 'Detected'
                      : health.viewpointShiftDetected === false
                        ? 'Not detected'
                        : 'Not reported'}
                  </dd>
                </div>
                {health.note && <dd className="text-[10px] text-slate-400">{health.note}</dd>}
              </dl>
            ) : (
              <p className="text-[11px] text-slate-500">
                No camera health context was recorded with this track.
              </p>
            )}
            <p className="mt-3 border-t border-slate-800/60 pt-2 text-[10px] leading-relaxed text-slate-500">
              Track state is independent of camera health — a degraded or offline camera does not
              terminate the track (§15).
            </p>
            <Link to="/camera-health" className="mt-1.5 inline-block text-[10px] font-mono text-cyan-400 hover:underline">
              Open Camera Health →
            </Link>
          </section>

          {/* §16 Vehicle / ANPR context — VEHICLE tracks only */}
          {isVehicle && (
            <section className={SECTION} aria-label="Vehicle plate observations">
              <h2 className={SECTION_HEAD}>
                <span className="inline-flex items-center gap-1.5">
                  <Car className="h-3.5 w-3.5 text-cyan-400" aria-hidden />
                  Vehicle &amp; Plate Observations
                </span>
              </h2>
              {sightingsLoad === 'error' ? (
                <SectionError
                  title="Vehicle sightings unavailable"
                  message={sightingsError ?? 'The ANPR service could not be reached.'}
                  note="Plate observations are never inferred from the track alone."
                />
              ) : sightingsLoad !== 'ready' ? (
                <SectionLoading label="Searching linked vehicle sightings…" />
              ) : sightings.length === 0 ? (
                <p className="text-[11px] text-slate-500">
                  No vehicle sightings recorded against this track.
                </p>
              ) : (
                <ul className="space-y-2">
                  {sightings.slice(0, 3).map(s => (
                    <li key={s.sightingId} className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-2.5">
                      <div className="flex flex-wrap items-center gap-2 text-[10px] font-mono text-slate-400">
                        <span className="text-slate-300">{s.sightingId}</span>
                        <span>{s.cameraId}</span>
                        <span className="tabular-nums">{formatClock(s.observedAt)}</span>
                      </div>
                      {s.plateRead && (
                        <p className="mt-1 text-[11px]">
                          <span className="text-[9px] font-semibold uppercase tracking-wider text-cyan-400/90">
                            Plate observation
                          </span>{' '}
                          <span className="font-mono text-slate-200">{s.plateRead.displayRead}</span>{' '}
                          <span className="text-[10px] text-slate-500">
                            {formatConfidence(s.plateRead.confidence)} read · quality {s.plateRead.quality}
                          </span>
                        </p>
                      )}
                      {s.plateCandidates.length > 0 && (
                        <p className="mt-0.5 text-[10px] text-slate-500">
                          <span className="text-[9px] font-semibold uppercase tracking-wider text-slate-400">
                            Top plate candidate
                          </span>{' '}
                          <span className="font-mono text-slate-300">{s.plateCandidates[0].rawRead}</span>{' '}
                          <span className="font-mono">{formatConfidence(s.plateCandidates[0].confidence)}</span>
                        </p>
                      )}
                      {!s.plateRead && s.plateCandidates.length === 0 && (
                        <p className="mt-1 text-[10px] text-slate-500">No plate observation on this sighting.</p>
                      )}
                    </li>
                  ))}
                </ul>
              )}
              <p className="mt-3 border-t border-slate-800/60 pt-2 text-[10px] leading-relaxed text-slate-500">
                Plate reads are decision-support observations, not vehicle identity confirmation (§16).
              </p>
              <Link
                to={`/anpr?track_id=${encodeURIComponent(track.trackId)}`}
                className="mt-1.5 inline-block text-[10px] font-mono text-cyan-400 hover:underline"
              >
                Open in ANPR workspace →
              </Link>
            </section>
          )}

          {/* §20 Cross-camera candidates — hypotheses only */}
          <section className={SECTION} aria-label="Cross-camera candidates">
            <h2 className={SECTION_HEAD}>
              <span className="inline-flex items-center gap-1.5">
                <MapPin className="h-3.5 w-3.5 text-cyan-400" aria-hidden />
                Cross-Camera Candidates
              </span>
            </h2>
            {candidatesLoad === 'error' ? (
              <SectionError
                title="Candidate records unavailable"
                message={candidatesError ?? 'The candidate store could not be reached.'}
                note="No candidate links are shown or invented."
              />
            ) : candidatesLoad === 'loading' ? (
              <SectionLoading label="Loading candidate records…" />
            ) : candidates.length === 0 && !track.crossCameraCandidate ? (
              <p className="text-[11px] text-slate-500">
                No cross-camera candidates recorded for this track.
              </p>
            ) : (
              <ul className="space-y-2">
                {candidates.map(c => (
                  <li key={c.candidateId} className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-2.5">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded border border-cyan-500/30 bg-cyan-500/10 px-1.5 py-0.5 font-mono text-[9px] font-semibold uppercase tracking-wide text-cyan-300">
                        {relationLabel(c.relationType)}
                      </span>
                      <span className="font-mono text-[11px] text-slate-300">
                        → {c.targetCameraId}
                        {c.candidateTrackId ? ` · ${c.candidateTrackId}` : ''}
                      </span>
                    </div>
                    <div className="mt-1 flex flex-wrap gap-x-3 gap-y-0.5 font-mono text-[10px] text-slate-500">
                      {c.strength !== null && c.strength !== undefined && (
                        <span>hypothesis strength {formatConfidence(c.strength)}</span>
                      )}
                      {c.gapDurationSec !== null && c.gapDurationSec !== undefined && (
                        <span>gap {formatDuration(c.gapDurationSec * 1000)}</span>
                      )}
                      <span>status {c.status}</span>
                      {c.expiresAt && <span>expires {ts(c.expiresAt)}</span>}
                    </div>
                    {c.reason && <p className="mt-1 text-[10px] text-slate-400">{c.reason}</p>}
                  </li>
                ))}
                {candidates.length === 0 && track.crossCameraCandidate && (
                  <li className="rounded-lg border border-white/[0.06] bg-white/[0.02] p-2.5">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded border border-cyan-500/30 bg-cyan-500/10 px-1.5 py-0.5 font-mono text-[9px] font-semibold uppercase tracking-wide text-cyan-300">
                        Possible continuation
                      </span>
                      <span className="font-mono text-[11px] text-slate-300">
                        → {track.crossCameraCandidate.targetCameraId} ·{' '}
                        {track.crossCameraCandidate.candidateTrackId}
                      </span>
                    </div>
                    <div className="mt-1 flex flex-wrap gap-x-3 font-mono text-[10px] text-slate-500">
                      {track.crossCameraCandidate.continuityConfidence != null && (
                        <span>
                          hypothesis strength{' '}
                          {formatConfidence(track.crossCameraCandidate.continuityConfidence)}
                        </span>
                      )}
                      {track.crossCameraCandidate.gapDurationSec != null && (
                        <span>
                          gap {formatDuration(track.crossCameraCandidate.gapDurationSec * 1000)}
                        </span>
                      )}
                      <span>recorded on the track record</span>
                    </div>
                    {track.crossCameraCandidate.note && (
                      <p className="mt-1 text-[10px] text-slate-400">{track.crossCameraCandidate.note}</p>
                    )}
                  </li>
                )}
              </ul>
            )}
            <p className="mt-3 border-t border-slate-800/60 pt-2 text-[10px] leading-relaxed text-slate-500">
              Candidate linkage is a tracking-provider hypothesis only — it does not confirm identity
              across cameras (§20). No correlation logic runs in this component (§17).
            </p>
          </section>

          {/* §17–§19 Event / correlation / incident / evidence references */}
          <section className={SECTION + ' text-xs'} aria-label="Downstream references">
            <h2 className={SECTION_HEAD}>Event · Correlation · Incident · Evidence</h2>
            <div className="space-y-2">
              {track.eventId && (
                <div className="flex items-center justify-between p-2 rounded-lg bg-[#080c12] border border-[#1e2d40]">
                  <div className="flex items-center gap-2">
                    <Clock className="h-3.5 w-3.5 text-amber-400" />
                    <span className="font-mono text-slate-200">{track.eventId}</span>
                  </div>
                  {/* 'search' is the URL param the Event Log understands */}
                  <Link
                    to={`/events?search=${encodeURIComponent(track.eventId)}`}
                    className="text-xs font-mono text-amber-400 hover:underline"
                  >
                    View Event →
                  </Link>
                </div>
              )}
              {track.correlationId && (
                <div className="p-2 rounded-lg bg-[#080c12] border border-[#1e2d40]">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <Activity className="h-3.5 w-3.5 text-purple-400" />
                      <span className="font-mono text-slate-200">{track.correlationId}</span>
                    </div>
                    <Link
                      to={`/incident/${track.correlationId}`}
                      className="text-xs font-mono text-purple-400 hover:underline"
                    >
                      View Activity →
                    </Link>
                  </div>
                  {/* §17 relation status — display only; correlation stays in C4 */}
                  <p className="mt-1 text-[10px] text-slate-500">
                    {correlationStatusText(correlationLoad, correlation)}
                  </p>
                </div>
              )}
              {track.incidentId && (
                <div className="flex items-center justify-between p-2 rounded-lg bg-[#080c12] border border-[#1e2d40]">
                  <div className="flex items-center gap-2">
                    <Shield className="h-3.5 w-3.5 text-red-400" />
                    <span className="font-mono text-slate-200">{track.incidentId}</span>
                  </div>
                  {/* No existing surface resolves an INC-* id from a URL —
                      /incident/:correlationId accepts correlation ids only. */}
                  <span className="text-[10px] text-slate-500">No deep link</span>
                </div>
              )}
              {track.evidenceId && (
                <div className="flex items-center justify-between p-2 rounded-lg bg-[#080c12] border border-[#1e2d40]">
                  <div className="flex items-center gap-2">
                    <FileCheck className="h-3.5 w-3.5 text-emerald-400" />
                    <span className="font-mono text-slate-200">{track.evidenceId}</span>
                  </div>
                  {/* Evidence Ledger has no per-record route; it opens unfiltered. */}
                  <Link to="/evidence" className="text-xs font-mono text-emerald-400 hover:underline">
                    View Ledger →
                  </Link>
                </div>
              )}
              {!track.eventId && !track.correlationId && !track.incidentId && !track.evidenceId && (
                <p className="text-[11px] text-slate-500">
                  No downstream references recorded for this track yet.
                </p>
              )}
            </div>
          </section>

          {/* §24 Provider & record metadata */}
          <section className={SECTION} aria-label="Provider and record metadata">
            <h2 className={SECTION_HEAD}>Provider &amp; Record Metadata</h2>
            <dl className="grid grid-cols-2 gap-x-3 gap-y-2 text-[11px] font-mono">
              <MetaItem label="Provider" value={track.provider ?? 'Not recorded'} />
              <MetaItem
                label="Tracker"
                value={
                  track.trackerName
                    ? `${track.trackerName}${track.trackerVersion ? ` v${track.trackerVersion}` : ''}`
                    : 'Not recorded'
                }
              />
              <MetaItem label="Source" value={formatSourceLabel(track.source)} />
              <MetaItem label="Data source" value={formatSourceLabel(track.dataSource)} />
              <MetaItem label="Schema" value={track.schemaVersion ?? 'N/A'} />
              <MetaItem label="Record revision" value={track.revision != null ? String(track.revision) : 'N/A'} />
              <MetaItem label="Observed at" value={ts(track.observedAt)} />
              <MetaItem label="Updated at" value={track.updatedAt ? ts(track.updatedAt) : 'N/A'} />
            </dl>
            <p className="mt-3 border-t border-slate-800/60 pt-2 text-[10px] leading-relaxed text-slate-500">
              Recorded tracking-provider metadata only — no model, storage path or credential details
              are exposed here (§24).
            </p>
          </section>
        </div>
      </div>
    </div>
  )
}

// ── Small local building blocks ──────────────────────────────────────────────

function TrackUnavailablePanel({ message }: { message: string }) {
  const navigate = useNavigate()
  return (
    <div className="h-full flex items-center justify-center bg-[#080c12] p-6">
      <div className="max-w-md w-full rounded-xl border border-red-500/20 bg-red-500/5 p-6 text-center">
        <AlertTriangle className="h-8 w-8 text-red-400 mx-auto mb-2" />
        <h2 className="text-sm font-semibold text-red-400">Track Record Unavailable</h2>
        <p className="mt-1 text-xs text-slate-400">{message}</p>
        <div className="mt-4 flex items-center justify-center gap-3">
          <button
            onClick={() => navigate(-1)}
            className="inline-flex items-center gap-1 text-xs text-slate-300 hover:text-white"
          >
            <ArrowLeft className="h-3.5 w-3.5" />
            <span>Go back</span>
          </button>
          <Link
            to="/wall"
            className="rounded-md border border-cyan-500/30 bg-cyan-500/10 px-3 py-1 text-xs text-cyan-300 hover:bg-cyan-500/20 transition-colors"
          >
            Camera Wall
          </Link>
        </div>
      </div>
    </div>
  )
}

function HeaderStat({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <span className="inline-flex items-baseline gap-1.5 rounded-md border border-[#1e2d40] bg-[#0d1117] px-2 py-1">
      <span className="text-[9px] uppercase tracking-wider text-slate-500">{label}</span>
      {children}
    </span>
  )
}

function MetaItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-[9px] uppercase tracking-wider text-slate-500">{label}</dt>
      <dd className="mt-0.5 text-slate-300 break-all">{value}</dd>
    </div>
  )
}

function SectionLoading({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 rounded-lg border border-[#1e2d40] bg-[#080c12] p-3 text-[11px] text-slate-400" role="status">
      <div className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-cyan-400 border-t-transparent" />
      <span>{label}</span>
    </div>
  )
}

function SectionError({ title, message, note }: { title: string; message: string; note: string }) {
  return (
    <div className="rounded-lg border border-amber-500/30 bg-amber-500/5 p-3.5 text-center">
      <AlertTriangle className="h-5 w-5 text-amber-400 mx-auto mb-1.5" aria-hidden />
      <p className="text-[11px] font-semibold text-amber-300">{title}</p>
      <p className="mt-1 text-[10px] text-slate-400">{message}</p>
      <p className="mt-1 text-[10px] text-slate-500">{note}</p>
    </div>
  )
}

/** §12 trajectory quality context — notes come from the record only. */
function TrajectoryQualityNotes({ track }: { track: Track }) {
  const notes = trajectoryQualityNotes(track)

  if (notes.length === 0) {
    return (
      <p className="mt-2 text-[10px] text-slate-500">
        No trajectory quality flags recorded for this track.
      </p>
    )
  }
  return (
    <ul className="mt-2 space-y-1" aria-label="Trajectory quality notes">
      {notes.map((n, i) => (
        <li key={i} className="flex items-start gap-1.5 text-[10px] text-slate-400">
          <span className="mt-1 h-1 w-1 shrink-0 rounded-full bg-amber-400/70" aria-hidden />
          <span>{n}</span>
        </li>
      ))}
    </ul>
  )
}

