// ─────────────────────────────────────────────────────────────────────────────
// Component 7 — Camera-Specific Vehicle Feed (/camera/:cameraId/vehicles)
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

export function CameraVehicles() {
  const { cameraId } = useParams<{ cameraId: string }>()
  const navigate = useNavigate()

  const {
    sightings,
    sightingsState,
    sightingsError,
    selectedSighting,
    selectedSightingId,
    selectSighting,
    fetchSightings,
    setFilter,
  } = useANPRStore()

  useEffect(() => {
    if (cameraId) {
      setFilter({ cameraId })
      fetchSightings()
    }
  }, [cameraId, setFilter, fetchSightings])

  useEffect(() => {
    if (sightings.length > 0 && !selectedSightingId) {
      selectSighting(sightings[0].sightingId)
    }
  }, [sightings, selectedSightingId, selectSighting])

  return (
    <div className="h-full flex flex-col overflow-hidden bg-[#080c12]">
      {/* Header */}
      <header className="border-b border-[#1e2d40] bg-[#0d1117] px-4 py-3 flex-shrink-0">
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
              onClick={fetchSightings}
              className="p-2 rounded-lg border border-[#1e2d40] bg-[#0d1117] text-slate-300 hover:text-white transition-colors"
              title="Refresh"
            >
              <RefreshCw className={`h-4 w-4 ${sightingsState === 'loading' ? 'animate-spin text-cyan-400' : ''}`} />
            </button>
          </div>
        </div>
      </header>

      {/* Main Workspace */}
      <div className="flex-1 min-h-0 flex px-4 py-4 gap-4 overflow-hidden">
        {/* Left Column: Sighting List */}
        <div className="w-96 flex-shrink-0 flex flex-col border border-[#1e2d40] rounded-xl bg-[#0d1117] overflow-hidden">
          <div className="p-3 border-b border-[#1e2d40] flex items-center justify-between flex-shrink-0 bg-[#080c12]/40">
            <span className="text-xs font-mono font-semibold uppercase text-slate-300">
              Sightings ({sightings.length})
            </span>
          </div>

          <div className="flex-1 overflow-y-auto p-2 space-y-2">
            {sightingsState === 'loading' && sightings.length === 0 && (
              <div className="space-y-2 p-2">
                {[1, 2, 3].map((i) => (
                  <Skeleton key={i} className="h-20 w-full rounded-lg" />
                ))}
              </div>
            )}

            {sightingsState === 'error' && (
              <ANPRErrorState
                message={sightingsError ?? 'Failed to load camera vehicle sightings.'}
                onRetry={fetchSightings}
              />
            )}

            {sightingsState === 'ready' && sightings.length === 0 && (
              <ANPREmptyState message={`No vehicle sightings recorded for ${cameraId}.`} />
            )}

            {sightings.map((s) => (
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
        <div className="flex-1 flex flex-col border border-[#1e2d40] rounded-xl bg-[#0d1117] overflow-hidden">
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
