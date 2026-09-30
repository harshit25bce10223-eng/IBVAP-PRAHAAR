// ─────────────────────────────────────────────────────────────────────────────
// Component 7 — ANPR / Vehicle Intelligence Workspace (/anpr)
// Operational layout: Observation Feed | Sighting Detail | Intelligence Context
// ─────────────────────────────────────────────────────────────────────────────
import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Car, RefreshCw, LayoutList, Table as TableIcon, ShieldAlert } from 'lucide-react'
import { useANPRStore } from '@/store/anprState'
import {
  ANPRSummaryCards,
  ANPRFilters,
  ANPRProviderStatus,
  ANPRSearchResults,
  SightingCard,
  SightingDetail,
  SightingTable,
  ANPREmptyState,
  ANPRErrorState,
} from '@/components/anpr'
import { Skeleton } from '@/components/ui'

export function ANPRPage() {
  const [searchParams] = useSearchParams()
  const [viewMode, setViewMode] = useState<'feed' | 'table'>('feed')

  const {
    summary,
    summaryState,
    providerHealth,
    providerHealthState,
    providerHealthError,
    sightings,
    sightingsState,
    sightingsError,
    hasMore,
    moreState,
    moreError,
    selectedSighting,
    selectedSightingId,
    serviceMode,
    searchQuery,
    searchResults,
    searchState,
    selectSighting,
    clearSearch,
    fetchSummary,
    fetchProviderHealth,
    fetchSightings,
    fetchMoreSightings,
    setFilter,
    setServiceMode,
  } = useANPRStore()

  // Sync URL search params to store filter on initial load
  useEffect(() => {
    const cameraParam = searchParams.get('camera') || searchParams.get('cameraId')
    const trackParam = searchParams.get('track_id') || searchParams.get('trackId')
    const vehicleParam = searchParams.get('vehicle') || searchParams.get('vehicle_id')
    const searchParam = searchParams.get('search')

    const patch: Record<string, string> = {}
    if (cameraParam) patch.cameraId = cameraParam
    if (trackParam) patch.trackId = trackParam
    if (vehicleParam) patch.vehicleId = vehicleParam
    if (searchParam) patch.search = searchParam

    if (Object.keys(patch).length > 0) {
      setFilter(patch)
    }
  }, [])

  // §30 — (re)load ANPR data on mount and whenever the provider mode changes.
  // setServiceMode() clears provider-specific state; without this effect the
  // workspace would stay empty after a MOCK/REAL switch until a manual refresh.
  useEffect(() => {
    fetchSummary()
    fetchProviderHealth()
    fetchSightings()
  }, [serviceMode, fetchSummary, fetchProviderHealth, fetchSightings])

  // Auto-select first sighting when list loads and none selected
  useEffect(() => {
    if (sightings.length > 0 && !selectedSightingId) {
      selectSighting(sightings[0].sightingId)
    }
  }, [sightings, selectedSightingId, selectSighting])

  return (
    <div className="h-full flex flex-col overflow-y-auto bg-[#080c12]">
      {/* Top Operational Header */}
      <header className="border-b border-[#1e2d40] bg-[#0d1117]/80 px-4 py-3 flex-shrink-0">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <div className="h-9 w-9 rounded-lg border border-ssb-green/40 bg-ssb-green/10 flex items-center justify-center text-ssb-green-bright">
              <Car className="h-5 w-5" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold tracking-wider text-ssb-text uppercase">प्रहार | PRAHAAR</span>
                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                  COMPONENT 7
                </span>
              </div>
              <h1 className="text-base font-bold font-mono text-slate-100">
                ANPR / Vehicle Intelligence
              </h1>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Mode Toggle (Mock vs Real) */}
            <div className="flex items-center rounded-lg border border-[#1e2d40] bg-[#080c12] p-0.5 text-xs font-mono">
              <button
                onClick={() => setServiceMode('MOCK')}
                className={`px-2.5 py-1 rounded transition-colors ${
                  serviceMode === 'MOCK'
                    ? 'bg-amber-500/20 text-amber-300 font-semibold border border-amber-500/30'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
                title="Use deterministic simulated border ANPR feeds"
              >
                MOCK FEED
              </button>
              <button
                onClick={() => setServiceMode('REAL')}
                className={`px-2.5 py-1 rounded transition-colors ${
                  serviceMode === 'REAL'
                    ? 'bg-emerald-500/20 text-emerald-300 font-semibold border border-emerald-500/30'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
                title="Connect to live backend /api/v1/anpr endpoints"
              >
                LIVE API
              </button>
            </div>

            {/* Refresh */}
            <button
              onClick={() => {
                fetchSummary()
                fetchProviderHealth()
                fetchSightings()
              }}
              className="p-2 rounded-lg border border-[#1e2d40] bg-[#0d1117] text-slate-300 hover:text-white hover:bg-slate-800/60 transition-colors"
              title="Refresh sightings feed"
            >
              <RefreshCw className={`h-4 w-4 ${sightingsState === 'loading' ? 'animate-spin text-cyan-400' : ''}`} />
            </button>
          </div>
        </div>

        {/* Operational Warning / Decision Support Banner */}
        <div className="mt-2.5 flex items-center gap-2 text-[11px] font-mono text-slate-400 bg-[#080c12]/60 px-3 py-1 rounded border border-[#1e2d40]/60">
          <ShieldAlert className="h-3.5 w-3.5 text-amber-400 flex-shrink-0" />
          <span>
            <strong className="text-amber-300">DECISION SUPPORT CONTEXT:</strong> OCR plate reads represent probabilistic recognition candidates, not identity verification. Check camera context, angle, and observation history.
          </span>
        </div>
      </header>

      {/* §28 Provider Status Strip */}
      <div className="px-4 pt-3 flex-shrink-0">
        <ANPRProviderStatus
          health={providerHealth}
          state={providerHealthState}
          error={providerHealthError}
          onRefresh={fetchProviderHealth}
        />
      </div>

      {/* KPI Stat Cards Strip */}
      <div className="px-4 pt-2 flex-shrink-0">
        <ANPRSummaryCards summary={summary} loading={summaryState === 'loading'} />
      </div>

      {/* Filter Toolbar */}
      <div className="px-4 py-2 flex-shrink-0">
        <ANPRFilters />
      </div>

      {/* Main Workspace Layout */}
      <div className="flex-1 min-h-0 flex px-4 pb-4 gap-4 overflow-hidden">
        {/* Left Column: Sighting Feed / Table View / §24 Search Results */}
        <div className="w-96 flex-shrink-0 flex flex-col border border-[#1e2d40] rounded-xl bg-[#0d1117] overflow-hidden">
          {searchQuery ? (
            <ANPRSearchResults
              query={searchQuery}
              results={searchResults}
              state={searchState}
              selectedId={selectedSightingId}
              onSelect={selectSighting}
              onClear={clearSearch}
            />
          ) : (
            <>
              <div className="p-3 border-b border-[#1e2d40] flex items-center justify-between flex-shrink-0 bg-[#080c12]/40">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-mono font-semibold uppercase text-slate-300">Live Observation Feed</span>
                  <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-800 text-slate-400">
                    {sightings.length}
                  </span>
                </div>
                <div className="flex items-center gap-1">
                  <button
                    onClick={() => setViewMode('feed')}
                    className={`p-1 rounded ${viewMode === 'feed' ? 'bg-cyan-500/20 text-cyan-300' : 'text-slate-500 hover:text-slate-300'}`}
                    title="Card Feed"
                  >
                    <LayoutList className="h-3.5 w-3.5" />
                  </button>
                  <button
                    onClick={() => setViewMode('table')}
                    className={`p-1 rounded ${viewMode === 'table' ? 'bg-cyan-500/20 text-cyan-300' : 'text-slate-500 hover:text-slate-300'}`}
                    title="Dense Table"
                  >
                    <TableIcon className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>

              <div className="flex-1 overflow-y-auto p-2 space-y-2">
                {sightingsState === 'loading' && sightings.length === 0 && (
                  <div className="space-y-2 p-2">
                    {[1, 2, 3, 4, 5].map((i) => (
                      <Skeleton key={i} className="h-20 w-full rounded-lg" />
                    ))}
                  </div>
                )}

                {sightingsState === 'error' && (
                  <ANPRErrorState
                    message={sightingsError ?? 'Unable to connect to ANPR service.'}
                    onRetry={fetchSightings}
                  />
                )}

                {sightingsState === 'ready' && sightings.length === 0 && (
                  <ANPREmptyState message="No vehicle observations matched your filters." />
                )}

                {viewMode === 'feed' ? (
                  sightings.map((s) => (
                    <SightingCard
                      key={s.sightingId}
                      sighting={s}
                      selected={s.sightingId === selectedSightingId}
                      onClick={() => selectSighting(s.sightingId)}
                    />
                  ))
                ) : (
                  <SightingTable
                    sightings={sightings}
                    selectedId={selectedSightingId}
                    onSelect={selectSighting}
                  />
                )}

                {/* Cursor pagination — only when the backend reports more rows */}
                {sightings.length > 0 && (hasMore || moreState === 'error') && (
                  <div className="p-1 space-y-1">
                    {moreState === 'error' && (
                      <div className="text-[10px] font-mono text-amber-300 px-1">
                        {moreError ?? 'Could not load more sightings.'}
                      </div>
                    )}
                    <button
                      onClick={fetchMoreSightings}
                      disabled={moreState === 'loading'}
                      className="w-full py-2 rounded-lg border border-[#1e2d40] bg-[#080c12] text-xs font-mono text-slate-300 hover:text-white hover:bg-slate-800/60 transition-colors disabled:opacity-60"
                    >
                      {moreState === 'loading' ? 'Loading more observations…' : 'Load more observations'}
                    </button>
                  </div>
                )}
              </div>
            </>
          )}
        </div>

        {/* Center / Right Column: Selected Sighting Detail & Intelligence Context */}
        <div className="flex-1 flex flex-col border border-[#1e2d40] rounded-xl bg-[#0d1117] overflow-hidden">
          {selectedSighting ? (
            <SightingDetail sighting={selectedSighting} />
          ) : (
            <div className="h-full flex items-center justify-center p-8">
              <ANPREmptyState message="Select a vehicle sighting from the feed to inspect OCR candidates, telemetry, and camera context." />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
