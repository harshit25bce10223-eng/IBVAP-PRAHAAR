// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 6 — TrackDetailPage (/track/:trackId)
//
// Dedicated track investigation route (§175, §238, §240).
// Uses the canonical Track Inspector and Track components.
// Back navigation returns to camera or previous context (§238, §241).
// ─────────────────────────────────────────────────────────────────────────────

import { useEffect, useState } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import {
  ArrowLeft,
  ExternalLink,
  Video,
  Clock,
  Shield,
  Activity,
  FileCheck,
  AlertTriangle,
  RefreshCw,
  Car,
} from 'lucide-react'
import type { Track, TrackObservation } from '@/types/tracking'
import { trackingService } from '@/services/tracking'
import {
  TrackStatus,
  TrackTrajectory,
  TrackTimeline,
  formatTrackClassLabel,
  formatTrackStatus,
  formatClock,
  formatDate,
  formatDuration,
  formatObservationCount,
  formatSpeed,
  formatVelocity,
  formatSourceLabel,
  formatBBox,
} from '@/components/tracking'
import { Badge, PageHeader } from '@/components/ui'
import { badgeTone, toneForQuality, toneForSource, toneForStatus } from '@/components/tracking/trackTone'

export function TrackDetailPage() {
  const { trackId } = useParams<{ trackId: string }>()
  const navigate = useNavigate()

  const [track, setTrack] = useState<Track | null>(null)
  const [observations, setObservations] = useState<TrackObservation[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!trackId) return
    let cancelled = false
    setLoading(true)
    setError(null)

    Promise.all([
      trackingService.getTrack(trackId),
      trackingService.getTrackHistory(trackId).catch(() => [] as TrackObservation[]),
    ])
      .then(([t, obs]) => {
        if (!cancelled) {
          setTrack(t)
          setObservations(obs)
        }
      })
      .catch(err => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Track record could not be loaded.')
        }
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [trackId])

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
      <div className="h-full flex items-center justify-center bg-[#080c12] p-6">
        <div className="max-w-md w-full rounded-xl border border-red-500/20 bg-red-500/5 p-6 text-center">
          <AlertTriangle className="h-8 w-8 text-red-400 mx-auto mb-2" />
          <h2 className="text-sm font-semibold text-red-400">Track Record Unavailable</h2>
          <p className="mt-1 text-xs text-slate-400">
            {error ?? `Track ${trackId} could not be located in active telemetry.`}
          </p>
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

  const age = track.ageMs ? `age ${track.ageMs > 60000 ? `${Math.round(track.ageMs / 60000)}m` : `${Math.round(track.ageMs / 1000)}s`}` :
    track.durationSec ? `${track.durationSec}s` : 'N/A'

  return (
    <div className="h-full flex flex-col overflow-y-auto bg-[#080c12] p-4 md:p-6 gap-6">
      {/* Header */}
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-[#1e2d40] pb-4">
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
            <div className="flex items-center gap-2.5">
              <h1 className="text-xl font-bold font-mono text-cyan-300">{track.trackId}</h1>
              <Badge variant={badgeTone(toneForStatus(track.status))} size="sm" dot>
                {track.status}
              </Badge>
              <span className="text-xs text-slate-400 font-sans">
                {formatTrackClassLabel(track.objectClass)}
              </span>
            </div>
            <p className="text-xs text-slate-500 font-mono mt-0.5">
              Camera: {track.cameraId} {track.regionProfile ? `· ${track.regionProfile}` : ''}
            </p>
          </div>
        </div>

        <Link
          to={`/camera/${track.cameraId}`}
          className="inline-flex items-center gap-1.5 rounded-md border border-cyan-500/40 bg-cyan-500/10 px-3 py-1.5 text-xs font-mono text-cyan-300 hover:bg-cyan-500/20 transition-colors"
        >
          <Video className="h-3.5 w-3.5" />
          <span>View on {track.cameraId} Feed →</span>
        </Link>
      </header>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left 2 Cols: Trajectory & Timeline */}
        <div className="lg:col-span-2 space-y-6">
          {/* Trajectory */}
          <section className="rounded-xl border border-[#1e2d40] bg-[#0d1117] p-4">
            <h3 className="text-sm font-semibold text-slate-200 mb-3">Trajectory Geometry</h3>
            <TrackTrajectory
              track={track}
              containerSize={{ width: 800, height: 450 }}
              fit="contain"
              maxPoints={30}
              showTimestamps={true}
            />
          </section>

          {/* Observation Timeline */}
          <section className="rounded-xl border border-[#1e2d40] bg-[#0d1117] p-4">
            <div className="flex items-center justify-between mb-3 border-b border-slate-800/60 pb-2">
              <h3 className="text-sm font-semibold text-slate-200">Observation Sequence</h3>
              <span className="text-xs font-mono text-slate-500">{observations.length} records</span>
            </div>
            <TrackTimeline observations={observations} />
          </section>
        </div>

        {/* Right Col: Details & Relationships */}
        <div className="space-y-6">
          {/* Primary Telemetry */}
          <section className="rounded-xl border border-[#1e2d40] bg-[#0d1117] p-4">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 mb-3 border-b border-slate-800/60 pb-2">
              Telemetry Summary
            </h3>
            <dl className="grid grid-cols-2 gap-3 text-xs font-mono">
              <div>
                <dt className="text-[10px] text-slate-500 uppercase">First Seen</dt>
                <dd className="text-slate-300">{formatClock(track.firstSeenAt)}</dd>
              </div>
              <div>
                <dt className="text-[10px] text-slate-500 uppercase">Last Seen</dt>
                <dd className="text-slate-300">{formatClock(track.lastSeenAt)}</dd>
              </div>
              <div>
                <dt className="text-[10px] text-slate-500 uppercase">Age / Duration</dt>
                <dd className="text-slate-200">
                  {track.ageMs ? `age ${track.ageMs > 60000 ? `${Math.round(track.ageMs / 60000)}m` : `${Math.round(track.ageMs / 1000)}s`}` :
                    track.durationSec ? `${track.durationSec}s` : 'N/A'}
                </dd>
              </div>
              <div>
                <dt className="text-[10px] text-slate-500 uppercase">Observations</dt>
                <dd className="text-slate-200">{formatObservationCount(track.detectionCount)}</dd>
              </div>
              <div>
                <dt className="text-[10px] text-slate-500 uppercase">Speed</dt>
                <dd className="text-slate-200">{track.speed !== null && track.speed !== undefined ? formatSpeed(track.speed) : 'N/A'}</dd>
              </div>
              <div>
                <dt className="text-[10px] text-slate-500 uppercase">Direction</dt>
                <dd className="text-slate-200">{track.direction ?? 'N/A'}</dd>
              </div>
              <div>
                <dt className="text-[10px] text-slate-500 uppercase">Source</dt>
                <dd className="text-slate-400">{formatSourceLabel(track.source)}</dd>
              </div>
              <div>
                <dt className="text-[10px] text-slate-500 uppercase">Continuity</dt>
                <dd>
                  <Badge variant={badgeTone(toneForQuality(track.continuityQuality ?? 'UNKNOWN'))} size="sm">
                    {track.continuityQuality ?? 'Unknown'}
                  </Badge>
                </dd>
              </div>
            </dl>
          </section>

          {/* Downstream Links */}
          <section className="rounded-xl border border-[#1e2d40] bg-[#0d1117] p-4 text-xs">
            <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-300 mb-3 border-b border-slate-800/60 pb-2">
              Downstream References
            </h3>
            <div className="space-y-2">
              {track.eventId && (
                <div className="flex items-center justify-between p-2 rounded-lg bg-[#080c12] border border-[#1e2d40]">
                  <div className="flex items-center gap-2">
                    <Clock className="h-3.5 w-3.5 text-amber-400" />
                    <span className="font-mono text-slate-200">{track.eventId}</span>
                  </div>
                  <Link
                    to={`/events?track_id=${track.trackId}`}
                    className="text-xs font-mono text-amber-400 hover:underline"
                  >
                    View Event →
                  </Link>
                </div>
              )}
              {track.correlationId && (
                <div className="flex items-center justify-between p-2 rounded-lg bg-[#080c12] border border-[#1e2d40]">
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
              )}
              {track.incidentId && (
                <div className="flex items-center justify-between p-2 rounded-lg bg-[#080c12] border border-[#1e2d40]">
                  <div className="flex items-center gap-2">
                    <Shield className="h-3.5 w-3.5 text-red-400" />
                    <span className="font-mono text-slate-200">{track.incidentId}</span>
                  </div>
                  <Link
                    to={`/incident/${track.incidentId}`}
                    className="text-xs font-mono text-red-400 hover:underline"
                  >
                    View Incident →
                  </Link>
                </div>
              )}
              {track.evidenceId && (
                <div className="flex items-center justify-between p-2 rounded-lg bg-[#080c12] border border-[#1e2d40]">
                  <div className="flex items-center gap-2">
                    <FileCheck className="h-3.5 w-3.5 text-emerald-400" />
                    <span className="font-mono text-slate-200">{track.evidenceId}</span>
                  </div>
                  <Link to="/evidence" className="text-xs font-mono text-emerald-400 hover:underline">
                    View Ledger →
                  </Link>
                </div>
              )}
              {/* Component 7 — ANPR / Vehicle Intelligence */}
              <div className="flex items-center justify-between p-2 rounded-lg bg-[#080c12] border border-[#1e2d40]">
                <div className="flex items-center gap-2">
                  <Car className="h-3.5 w-3.5 text-cyan-400" />
                  <span className="font-mono text-slate-200">Vehicle Intel</span>
                </div>
                <Link
                  to={`/anpr?track_id=${track.trackId}`}
                  className="text-xs font-mono text-cyan-400 hover:underline"
                >
                  View Sightings →
                </Link>
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}