// ─────────────────────────────────────────────────────────────────────────────
// Component 7 — Vehicle Investigation Detail Page (/vehicle/:vehicleId)
// §12 — Vehicle Summary header (top plate candidate, class, camera, track,
// observed time, quality, observation status) + explicit no-physical-presence
// note. §16 — chronological multi-camera observation chronology.
// ─────────────────────────────────────────────────────────────────────────────
import { useEffect } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { ArrowLeft, ShieldAlert, MapPin, ExternalLink } from 'lucide-react'
import { useANPRStore } from '@/store/anprState'
import {
  VehicleHistoryTimeline,
  PlateDisplay,
  VehicleClassBadge,
} from '@/components/anpr'
import { Badge } from '@/components/ui'

function fmtDateTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString('en-IN', {
      dateStyle: 'short', timeStyle: 'medium', hour12: false,
    })
  } catch {
    return iso
  }
}

export function VehicleDetail() {
  const { vehicleId } = useParams<{ vehicleId: string }>()
  const navigate = useNavigate()

  const {
    vehicleHistory,
    vehicleHistoryState,
    vehicleHistoryError,
    fetchVehicleHistory,
  } = useANPRStore()

  useEffect(() => {
    if (vehicleId) {
      fetchVehicleHistory(vehicleId)
    }
  }, [vehicleId, fetchVehicleHistory])

  // Only use history that actually matches the routed vehicle id.
  const history =
    vehicleHistory && vehicleHistory.vehicleId === vehicleId ? vehicleHistory : null

  if (!history && vehicleHistoryState !== 'error') {
    return (
      <div className="h-full flex items-center justify-center bg-bg p-6">
        <div className="flex flex-col items-center gap-3 text-slate-400 font-mono">
          <div className="h-6 w-6 animate-spin rounded-full border-2 border-cyan-400 border-t-transparent" />
          <span className="text-xs">Loading vehicle telemetry &amp; observation history for {vehicleId}…</span>
        </div>
      </div>
    )
  }

  if (!history) {
    return (
      <div className="h-full flex items-center justify-center bg-bg p-6">
        <div className="max-w-md w-full rounded-xl border border-red-500/20 bg-red-500/5 p-6 text-center">
          <ShieldAlert className="h-8 w-8 text-red-400 mx-auto mb-2" />
          <h2 className="text-sm font-semibold text-red-400">Vehicle History Unavailable</h2>
          <p className="mt-1 text-xs text-slate-400 font-mono">
            {vehicleHistoryError ?? `Vehicle record ${vehicleId} could not be retrieved from ANPR telemetry.`}
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
              to="/anpr"
              className="rounded-md border border-cyan-500/30 bg-cyan-500/10 px-3 py-1 text-xs font-mono text-cyan-300 hover:bg-cyan-500/20 transition-colors"
            >
              ANPR Workspace →
            </Link>
          </div>
        </div>
      </div>
    )
  }

  // Newest observation is the reference for the summary header.
  const latestSighting = history.sightings.length > 0
    ? [...history.sightings].sort((a, b) => (a.observedAt < b.observedAt ? 1 : -1))[0]
    : null

  return (
    <div className="h-full flex flex-col overflow-y-auto bg-bg p-4 md:p-6 gap-6">
      {/* Top Header */}
      <header className="border-b border-border pb-4 space-y-3">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate(-1)}
              className="rounded-md border border-slate-700 bg-slate-800/80 p-1.5 text-slate-300 hover:bg-slate-700 transition-colors"
              title="Go back"
            >
              <ArrowLeft className="h-4 w-4" />
            </button>
            <div>
              <div className="flex items-center gap-2.5">
                <span className="text-xs font-mono uppercase tracking-wider text-slate-500">Vehicle Record</span>
                <h1 className="text-xl font-bold font-mono text-cyan-300">{vehicleId}</h1>
                <Badge variant="cyan" size="sm">
                  {history.totalSightings} Observations
                </Badge>
              </div>
              <p className="text-xs text-slate-500 font-mono mt-0.5">
                First observed: {history.firstSeen ? fmtDateTime(history.firstSeen) : 'N/A'} · Last observed: {history.lastSeen ? fmtDateTime(history.lastSeen) : 'N/A'}
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Link
              to={`/gis`}
              className="inline-flex items-center gap-1.5 rounded-md border border-cyan-500/40 bg-cyan-500/10 px-3 py-1.5 text-xs font-mono text-cyan-300 hover:bg-cyan-500/20 transition-colors"
            >
              <MapPin className="h-3.5 w-3.5" />
              <span>View on Digital Twin →</span>
            </Link>
          </div>
        </div>

        {/* §12 — Vehicle Summary header strip (from the newest observation) */}
        {latestSighting && (
          <dl className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-3 rounded-xl border border-border bg-surface p-3 text-xs font-mono">
            <div>
              <dt className="text-[9px] text-slate-600 uppercase">Top Plate Candidate</dt>
              <dd className="text-ssb-green-bright mt-0.5">
                {latestSighting.plateRead?.displayRead ?? 'UNREADABLE'}
              </dd>
            </div>
            <div>
              <dt className="text-[9px] text-slate-600 uppercase">Vehicle Class</dt>
              <dd className="mt-0.5"><VehicleClassBadge vehicleClass={latestSighting.vehicleClass} /></dd>
            </div>
            <div>
              <dt className="text-[9px] text-slate-600 uppercase">Last Camera</dt>
              <dd className="text-cyan-300 mt-0.5">{latestSighting.cameraId}</dd>
            </div>
            <div>
              <dt className="text-[9px] text-slate-600 uppercase">Last Observed</dt>
              <dd className="text-slate-300 mt-0.5">{fmtDateTime(latestSighting.observedAt)}</dd>
            </div>
            <div>
              <dt className="text-[9px] text-slate-600 uppercase">Plate Quality</dt>
              <dd className="text-slate-300 mt-0.5">
                {(latestSighting.plateRead?.quality ?? 'UNKNOWN').replace(/_/g, ' ')}
              </dd>
            </div>
            <div>
              <dt className="text-[9px] text-slate-600 uppercase">Track ID</dt>
              <dd className="mt-0.5">
                {latestSighting.vehicleTrackId ? (
                  <Link
                    to={'/track/' + latestSighting.vehicleTrackId}
                    className="inline-flex items-center gap-1 text-cyan-400 hover:underline"
                  >
                    {latestSighting.vehicleTrackId}
                    <ExternalLink className="h-3 w-3" />
                  </Link>
                ) : (
                  <span className="text-slate-600">—</span>
                )}
              </dd>
            </div>
          </dl>
        )}

        <p className="text-[10px] font-mono text-slate-500">
          Observation record — sightings reflect where and when plates were observed. This is not real-time tracking and
          does not assert the vehicle's current physical presence.
        </p>
      </header>

      {/* Grid: Left Column Summary, Right Column Timeline */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Top Plate Candidate & Telemetry */}
        <div className="space-y-6">
          {latestSighting && (
            <section className="rounded-xl border border-border bg-surface p-4 space-y-3">
              <h3 className="text-[10px] font-mono uppercase tracking-wider text-slate-500 border-b border-slate-800/60 pb-1.5">
                Latest Plate Read
              </h3>
              <PlateDisplay plateRead={latestSighting.plateRead} />
            </section>
          )}

          {latestSighting && (
            <section className="rounded-xl border border-border bg-surface p-4 space-y-3">
              <h3 className="text-[10px] font-mono uppercase tracking-wider text-slate-500 border-b border-slate-800/60 pb-1.5">
                Observed Attributes — Latest Sighting
              </h3>
              <dl className="grid grid-cols-2 gap-3 text-xs font-mono">
                <div>
                  <dt className="text-[10px] text-slate-500 uppercase">Class</dt>
                  <dd className="mt-1">
                    <VehicleClassBadge vehicleClass={latestSighting.vehicleClass} />
                  </dd>
                </div>
                <div>
                  <dt className="text-[10px] text-slate-500 uppercase">Color</dt>
                  <dd className="text-slate-300 mt-1">{latestSighting.vehicleColor}</dd>
                </div>
                <div>
                  <dt className="text-[10px] text-slate-500 uppercase">Direction</dt>
                  <dd className="text-slate-300 mt-1">{latestSighting.vehicleDirection}</dd>
                </div>
                <div>
                  <dt className="text-[10px] text-slate-500 uppercase">Last Camera</dt>
                  <dd className="text-cyan-300 mt-1">{latestSighting.cameraId}</dd>
                </div>
              </dl>
              <p className="text-[9px] text-slate-600 font-mono">
                Provider-reported attributes for the most recent observation, not a live vehicle state.
              </p>
            </section>
          )}
        </div>

        {/* Right 2 Columns: Multi-Camera Timeline */}
        <div className="lg:col-span-2 space-y-6">
          <section className="rounded-xl border border-border bg-surface p-5">
            <div className="flex items-center justify-between mb-4 border-b border-slate-800/60 pb-2">
              <div>
                <h3 className="text-sm font-semibold font-mono text-slate-200">
                  Cross-Camera Sighting Chronology
                </h3>
                <p className="text-xs text-slate-500 font-mono mt-0.5">
                  Chronological observation sequence across border sensors
                </p>
              </div>
              <span className="text-xs font-mono text-slate-400">
                {history.sightings.length} records
              </span>
            </div>

            {history.sightings.length > 0 ? (
              <VehicleHistoryTimeline history={history} />
            ) : (
              <div className="text-xs font-mono text-slate-600 italic">
                No sightings recorded for this vehicle identifier.
              </div>
            )}
          </section>
        </div>
      </div>
    </div>
  )
}
