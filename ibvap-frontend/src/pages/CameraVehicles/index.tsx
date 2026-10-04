// ─────────────────────────────────────────────────────────────────────────────
// Component 7 — Camera-Specific Vehicle Feed (/camera/:cameraId/vehicles)
// §42/§43 — consumes GET /anpr/cameras/{id}/vehicles/feed + .../summary.
// §19 — camera feed state and provider health are reported, not recalculated.
// ─────────────────────────────────────────────────────────────────────────────
import { useEffect } from 'react'
import { useParams, Link, useNavigate } from 'react-router-dom'
import { ArrowLeft, Video, RefreshCw } from 'lucide-react'
import { useANPRStore } from '@/store/anprState'
import {
  SightingCard,
  SightingDetail,
  ANPREmptyState,
  ANPRErrorState,
} from '@/components/anpr'
import { Skeleton } from '@/components/ui'
import { clsx } from 'clsx'

function feedStateClass(state: string | null): string {
  switch (state?.toUpperCase()) {
    case 'READY': return 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10'
    case 'DEGRADED': return 'text-amber-400 border-amber-500/30 bg-amber-500/10'
    case 'UNAVAILABLE':
    case 'OFFLINE': return 'text-red-400 border-red-500/30 bg-red-500/10'
    default: return 'text-slate-400 border-slate-600/40 bg-slate-700/20'
  }
}

function fmtTs(iso: string | null): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString('en-IN', { dateStyle: 'short', timeStyle: 'medium', hour12: false })
  } catch { return iso }
}

export function CameraVehicles() {
  const { cameraId } = useParams<{ cameraId: string }>()
  const navigate = useNavigate()

  const {
    cameraFeed,
    cameraFeedState,
    cameraFeedError,
    cameraSummary,
    selectedSighting,
    selectedSightingId,
    selectSighting,
    fetchCameraFeed,
    fetchCameraSummary,
  } = useANPRStore()

  useEffect(() => {
    if (cameraId) {
      fetchCameraFeed(cameraId)
      fetchCameraSummary(cameraId)
    }
  }, [cameraId, fetchCameraFeed, fetchCameraSummary])

  const feedSightings = cameraFeed?.sightings ?? []
  const feedState = cameraFeed?.state ?? null
  const isUnavailable = feedState?.toUpperCase() === 'UNAVAILABLE'

  // Auto-select the newest sighting once the feed is available.
  useEffect(() => {
    if (feedSightings.length > 0 && !selectedSightingId) {
      selectSighting(feedSightings[0].sightingId)
    }
  }, [feedSightings, selectedSightingId, selectSighting])

  const summaryForCamera =
    cameraSummary && cameraSummary.cameraId === cameraId ? cameraSummary : null

  const qualityCounts = summaryForCamera
    ? Object.entries(summaryForCamera.byQuality)
        .filter(([, n]) => n > 0)
        .map(([k, n]) => `${k.replace(/_/g, ' ')} ${n}`)
        .join(' · ')
    : ''

  return (
    <div className="h-full flex flex-col overflow-hidden bg-bg">
      {/* Header */}
      <header className="border-b border-border bg-surface px-4 py-3 flex-shrink-0 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => navigate(-1)}
              className="rounded-md border border-slate-700 bg-slate-800/80 p-1.5 text-slate-300 hover:bg-slate-700 transition-colors"
              title="Back"
            >
              <ArrowLeft className="h-4 w-4" />
            </button>
            <div>
              <div className="flex items-center gap-2 font-mono">
                <span className="text-xs text-slate-400">CAMERA VEHICLE OBSERVATIONS</span>
                <span className="text-xs font-bold text-cyan-400">{cameraId}</span>
                <span className={clsx('text-[10px] px-1.5 py-0.5 rounded border font-mono', feedStateClass(feedState))}>
                  FEED: {feedState ?? 'UNKNOWN'}
                </span>
                {cameraFeed?.providerHealth && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded border border-border bg-bg text-slate-400 font-mono">
                    PROVIDER: {cameraFeed.providerHealth}
                  </span>
                )}
              </div>
              <h1 className="text-lg font-bold font-mono text-slate-100 mt-0.5">
                Observed Plates &amp; Vehicles
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-3">
            {cameraId && (
              <Link
                to={`/camera/${cameraId}`}
                className="inline-flex items-center gap-1.5 rounded-md border border-cyan-500/40 bg-cyan-500/10 px-3 py-1.5 text-xs font-mono text-cyan-300 hover:bg-cyan-500/20 transition-colors"
              >
                <Video className="h-3.5 w-3.5" />
                <span>Camera Stream →</span>
              </Link>
            )}
            <button
              onClick={() => {
                if (cameraId) {
                  fetchCameraFeed(cameraId)
                  fetchCameraSummary(cameraId)
                }
              }}
              className="p-2 rounded-lg border border-border bg-surface text-slate-300 hover:text-white transition-colors"
              title="Refresh camera feed"
            >
              <RefreshCw className={`h-4 w-4 ${cameraFeedState === 'loading' ? 'animate-spin text-cyan-400' : ''}`} />
            </button>
          </div>
        </div>

        {/* Camera observation counts (provider-reported; counts only, no accuracy claims) */}
        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-[11px] font-mono text-slate-400 bg-bg/60 px-3 py-1 rounded border border-border/60">
          {summaryForCamera ? (
            <>
              <span>Observations: <span className="text-slate-200">{summaryForCamera.totalSightings}</span></span>
              <span>Watchlist matches: <span className="text-slate-200">{summaryForCamera.byStatus['WATCHLIST_MATCH'] ?? 0}</span></span>
              <span>Quality: <span className="text-slate-200">{qualityCounts || '—'}</span></span>
              <span>Last updated: <span className="text-slate-200">{fmtTs(summaryForCamera.lastUpdatedAt)}</span></span>
            </>
          ) : (
            <span>Feed last updated: <span className="text-slate-200">{fmtTs(cameraFeed?.lastUpdatedAt ?? null)}</span></span>
          )}
          <span className="text-slate-600">Camera state is reported by the ANPR service, not recalculated here.</span>
        </div>
      </header>

      {/* Main Workspace */}
      <div className="flex-1 min-h-0 flex px-4 py-4 gap-4 overflow-hidden">
        {/* Left Column: Sighting List */}
        <div className="w-96 flex-shrink-0 flex flex-col border border-border rounded-xl bg-surface overflow-hidden">
          <div className="p-3 border-b border-border flex items-center justify-between flex-shrink-0 bg-bg/40">
            <span className="text-xs font-mono font-semibold uppercase text-slate-300">
              Sightings ({feedSightings.length})
            </span>
          </div>

          <div className="flex-1 overflow-y-auto p-2 space-y-2">
            {cameraFeedState === 'loading' && feedSightings.length === 0 && (
              <div className="space-y-2 p-2">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-20 w-full rounded-lg" />
                ))}
              </div>
            )}

            {isUnavailable && (
              <div className="m-1 p-3 rounded-lg border border-red-500/30 bg-red-500/10 text-xs font-mono text-red-300">
                ANPR DATA UNAVAILABLE — the ANPR service reports no available provider for {cameraId}.
                No observation data is shown.
              </div>
            )}

            {cameraFeedState === 'error' && (
              <ANPRErrorState
                message={cameraFeedError ?? 'ANPR DATA UNAVAILABLE: camera feed could not be retrieved.'}
                onRetry={() => { if (cameraId) fetchCameraFeed(cameraId) }}
              />
            )}

            {cameraFeedState === 'ready' && !isUnavailable && feedSightings.length === 0 && (
              <ANPREmptyState message={`No vehicle sightings recorded for ${cameraId}.`} />
            )}

            {feedSightings.map((s) => (
              <SightingCard
                key={s.sightingId}
                sighting={s}
                selected={s.sightingId === selectedSightingId}
                onClick={() => selectSighting(s.sightingId)}
              />
            ))}
          </div>
        </div>

        {/* Right Column: Sighting Details */}
        <div className="flex-1 flex flex-col border border-border rounded-xl bg-surface overflow-hidden">
          {selectedSighting ? (
            <SightingDetail sighting={selectedSighting} />
          ) : (
            <div className="h-full flex items-center justify-center p-8">
              <ANPREmptyState message="Select a vehicle sighting to inspect plate reads and evidence." />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
