// ANPRFilters.tsx — Filter bar with URL sync via useSearchParams
// §24: pressing Enter in the search box runs a typed plate search (five explicit
// match labels rendered by ANPRSearchResults).
// §29: quality filter includes capture-condition states (GLARE, DIRTY, …).
import { useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Search, X } from 'lucide-react'
import { useANPRStore } from '@/store/anprState'
import type { VehicleClass, PlateQuality, VehicleDirection, WatchlistStatus } from '@/types/anpr'

const VEHICLE_CLASSES: VehicleClass[] = [
  'PERSONAL_CAR', 'SUV', 'TRUCK', 'BUS', 'VAN', 'MOTORCYCLE', 'SCOOTER', 'TRACTOR', 'THREE_WHEELER', 'UTILITY', 'OTHER',
]

// §29 — readability + capture-condition states (glare and dirty plate scenarios included).
const QUALITY_OPTIONS: PlateQuality[] = [
  'GOOD', 'FAIR', 'POOR', 'PARTIAL', 'UNREADABLE', 'GLARE', 'DIRTY', 'MOTION_BLUR', 'LOW_LIGHT', 'OCCLUDED', 'EXTREME_ANGLE',
]

const DIRECTIONS: VehicleDirection[] = ['NORTH', 'SOUTH', 'EAST', 'WEST', 'INBOUND', 'OUTBOUND']

const WATCHLIST_OPTIONS: WatchlistStatus[] = ['WATCHLIST_MATCH', 'NO_MATCH', 'NOT_CHECKED', 'UNKNOWN']

const inputCls = 'bg-[#080c12] border border-[#1e2d40] rounded-lg px-3 py-1.5 text-xs font-mono text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500/50 w-full'
const selectCls = inputCls
const dateCls = inputCls + ' [color-scheme:dark]'
const labelCls = 'block text-[9px] font-mono uppercase tracking-wider text-slate-600 mb-0.5'

export function ANPRFilters() {
  const { filter, setFilter, fetchSightings, search, clearSearch } = useANPRStore()
  const [params, setParams] = useSearchParams()

  // Sync search param from URL
  useEffect(() => {
    const urlSearch = params.get('q')
    if (urlSearch && urlSearch !== filter.search) {
      setFilter({ search: urlSearch })
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  function handleSearch(v: string) {
    setFilter({ search: v })
    if (v) setParams(p => { p.set('q', v); return p })
    else setParams(p => { p.delete('q'); return p })
  }

  // §24 — Enter runs a typed plate search; empty input returns to the observation feed.
  function handleSearchKey(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key !== 'Enter') return
    const q = filter.search.trim()
    if (q) void search(q)
    else clearSearch()
  }

  function handleApply() {
    fetchSightings()
  }

  function handleClear() {
    setFilter({
      search: '',
      cameraId: '',
      vehicleId: '',
      trackId: '',
      vehicleClass: '',
      quality: '',
      direction: '',
      watchlistStatus: '',
      confidenceMin: 0,
      confidenceMax: 1,
      from: '',
      to: '',
    })
    clearSearch()
    setParams({})
    setTimeout(() => fetchSightings(), 0)
  }

  const confidencePct = Math.round(filter.confidenceMin * 100)

  return (
    <div className="space-y-2 p-3 rounded-xl border border-[#1e2d40] bg-[#0d1117]">
      <div className="flex items-center justify-between">
        <div className="text-[9px] font-mono uppercase tracking-wider text-slate-500">Filters</div>
        <div className="text-[9px] font-mono text-slate-600">Enter in search runs a plate search</div>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3 w-3 text-slate-600" />
        <input
          type="text"
          placeholder="Search plate, vehicle ID… then Enter"
          value={filter.search}
          onChange={e => handleSearch(e.target.value)}
          onKeyDown={handleSearchKey}
          className={'pl-7 ' + inputCls}
        />
        {filter.search && (
          <button
            onClick={() => handleSearch('')}
            className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-600 hover:text-slate-300"
          >
            <X className="h-3 w-3" />
          </button>
        )}
      </div>

      {/* Field grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-2">
        <input
          type="text"
          placeholder="Camera ID…"
          value={filter.cameraId}
          onChange={e => setFilter({ cameraId: e.target.value })}
          className={inputCls}
        />
        <input
          type="text"
          placeholder="Track ID…"
          value={filter.trackId}
          onChange={e => setFilter({ trackId: e.target.value })}
          className={inputCls}
        />
        <select
          value={filter.vehicleClass}
          onChange={e => setFilter({ vehicleClass: e.target.value as VehicleClass | '' })}
          className={selectCls}
        >
          <option value="">Vehicle class…</option>
          {VEHICLE_CLASSES.map(c => <option key={c} value={c}>{c.replace(/_/g, ' ')}</option>)}
        </select>
        <select
          value={filter.quality}
          onChange={e => setFilter({ quality: e.target.value as PlateQuality | '' })}
          className={selectCls}
        >
          <option value="">Quality…</option>
          {QUALITY_OPTIONS.map(q => <option key={q} value={q}>{q.replace(/_/g, ' ')}</option>)}
        </select>
        <select
          value={filter.direction}
          onChange={e => setFilter({ direction: e.target.value as VehicleDirection | '' })}
          className={selectCls}
        >
          <option value="">Direction…</option>
          {DIRECTIONS.map(d => <option key={d} value={d}>{d}</option>)}
        </select>
        <select
          value={filter.watchlistStatus}
          onChange={e => setFilter({ watchlistStatus: e.target.value as WatchlistStatus | '' })}
          className={selectCls}
        >
          <option value="">Watchlist status…</option>
          {WATCHLIST_OPTIONS.map(w => <option key={w} value={w}>{w.replace(/_/g, ' ')}</option>)}
        </select>
        <label>
          <span className={labelCls}>Observed from</span>
          <input
            type="datetime-local"
            value={filter.from}
            onChange={e => setFilter({ from: e.target.value })}
            className={dateCls}
          />
        </label>
        <label>
          <span className={labelCls}>Observed to</span>
          <input
            type="datetime-local"
            value={filter.to}
            onChange={e => setFilter({ to: e.target.value })}
            className={dateCls}
          />
        </label>
      </div>

      {/* Minimum detection confidence — filters the observation's detection
          confidence (the field persisted on the sighting). Plate read
          confidence is a different value, shown per row. */}
      <div className="flex items-center gap-2">
        <span className="text-[9px] font-mono uppercase tracking-wider text-slate-600 w-28 flex-shrink-0">Min detection conf.</span>
        <input
          type="range"
          min={0}
          max={100}
          step={5}
          value={confidencePct}
          onChange={e => setFilter({ confidenceMin: Number(e.target.value) / 100 })}
          className="flex-1 accent-cyan-500"
          aria-label="Minimum detection confidence threshold"
        />
        <span className="text-[10px] font-mono text-slate-300 w-9 text-right">{confidencePct}%</span>
        {confidencePct > 0 && (
          <button
            onClick={() => setFilter({ confidenceMin: 0 })}
            className="text-slate-600 hover:text-slate-300"
            title="Reset confidence threshold"
          >
            <X className="h-3 w-3" />
          </button>
        )}
      </div>

      {/* Actions */}
      <div className="flex gap-2 pt-1">
        <button
          onClick={handleApply}
          className="flex-1 rounded-lg bg-cyan-500/10 border border-cyan-500/30 px-3 py-1.5 text-xs font-mono text-cyan-300 hover:bg-cyan-500/20 transition-colors"
        >
          Apply
        </button>
        <button
          onClick={handleClear}
          className="flex-1 rounded-lg bg-slate-700/30 border border-slate-700 px-3 py-1.5 text-xs font-mono text-slate-400 hover:bg-slate-700/50 transition-colors"
        >
          Clear
        </button>
      </div>
    </div>
  )
}
