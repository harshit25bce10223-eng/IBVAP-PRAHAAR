// ANPRFilters.tsx — Filter bar with URL sync via useSearchParams
import { useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Search, X } from 'lucide-react'
import { useANPRStore } from '@/store/anprState'
import type { VehicleClass, PlateQuality, VehicleDirection, WatchlistStatus } from '@/types/anpr'

const VEHICLE_CLASSES: VehicleClass[] = [
  'PERSONAL_CAR', 'SUV', 'TRUCK', 'BUS', 'VAN', 'MOTORCYCLE', 'SCOOTER', 'TRACTOR', 'THREE_WHEELER', 'UTILITY', 'OTHER',
]

const QUALITY_OPTIONS: PlateQuality[] = [
  'GOOD', 'FAIR', 'POOR', 'UNREADABLE', 'PARTIAL', 'GLARE', 'MOTION_BLUR', 'LOW_LIGHT', 'OCCLUDED',
]

const DIRECTIONS: VehicleDirection[] = ['NORTH', 'SOUTH', 'EAST', 'WEST', 'INBOUND', 'OUTBOUND']

const WATCHLIST_OPTIONS: WatchlistStatus[] = ['WATCHLIST_MATCH', 'NO_MATCH', 'NOT_CHECKED', 'UNKNOWN']

const inputCls = 'bg-[#080c12] border border-[#1e2d40] rounded-lg px-3 py-1.5 text-xs font-mono text-slate-200 placeholder-slate-600 focus:outline-none focus:border-cyan-500/50 w-full'
const selectCls = inputCls

export function ANPRFilters() {
  const { filter, setFilter, fetchSightings } = useANPRStore()
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

  function handleApply() {
    fetchSightings()
  }

  function handleClear() {
    setFilter({ search: '', cameraId: '', vehicleClass: '', quality: '', direction: '', watchlistStatus: '' })
    setParams({})
    setTimeout(() => fetchSightings(), 0)
  }

  return (
    <div className="space-y-2 p-3 rounded-xl border border-[#1e2d40] bg-[#0d1117]">
      <div className="text-[9px] font-mono uppercase tracking-wider text-slate-500 mb-1">Filters</div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3 w-3 text-slate-600" />
        <input
          type="text"
          placeholder="Search plate, vehicle ID…"
          value={filter.search}
          onChange={e => handleSearch(e.target.value)}
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

      {/* Camera + Direction row */}
      <div className="grid grid-cols-2 gap-2">
        <input
          type="text"
          placeholder="Camera ID…"
          value={filter.cameraId}
          onChange={e => setFilter({ cameraId: e.target.value })}
          className={inputCls}
        />
        <select
          value={filter.direction}
          onChange={e => setFilter({ direction: e.target.value as VehicleDirection | '' })}
          className={selectCls}
        >
          <option value="">Direction…</option>
          {DIRECTIONS.map(d => <option key={d} value={d}>{d}</option>)}
        </select>
      </div>

      {/* Class + Quality row */}
      <div className="grid grid-cols-2 gap-2">
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
      </div>

      {/* Watchlist */}
      <select
        value={filter.watchlistStatus}
        onChange={e => setFilter({ watchlistStatus: e.target.value as WatchlistStatus | '' })}
        className={selectCls}
      >
        <option value="">Watchlist status…</option>
        {WATCHLIST_OPTIONS.map(w => <option key={w} value={w}>{w.replace(/_/g, ' ')}</option>)}
      </select>

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