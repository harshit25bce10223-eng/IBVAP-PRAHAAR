// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 6 — Track Filters (§49, §169–§171). Compact, keyboard
// accessible, clearable. The confidence control is labelled a DISPLAY FILTER
// — it only hides tracks/list rows, it never modifies stored data.
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'
import { DEFAULT_TRACK_QUERY } from '@/types/tracking'
import type { DetectionClass, TrackStatus, TrackSource, TrackQuery } from '@/types/tracking'
import type { CameraDetail } from '@/types/camera'

interface TrackFiltersProps {
  query: TrackQuery
  cameras: CameraDetail[]
  onChange: (patch: Partial<TrackQuery>) => void
  onReset: () => void
}

const CLASSES: { value: DetectionClass | 'ALL'; label: string }[] = [
  { value: 'ALL', label: 'All classes' },
  { value: 'PERSON', label: 'Person' },
  { value: 'VEHICLE', label: 'Vehicle' },
  { value: 'ANIMAL', label: 'Animal' },
  { value: 'OBJECT', label: 'Object' },
  { value: 'UNKNOWN', label: 'Unknown / other' },
]

const STATUSES: { value: TrackStatus | 'ALL'; label: string }[] = [
  { value: 'ALL', label: 'All statuses' },
  { value: 'ACTIVE', label: 'Active' },
  { value: 'TENTATIVE', label: 'Tentative' },
  { value: 'LOST', label: 'Lost' },
  { value: 'REACQUIRED', label: 'Reacquired' },
  { value: 'ENDED', label: 'Ended' },
  { value: 'STALE', label: 'Stale' },
  { value: 'INVALID', label: 'Invalid' },
  { value: 'UNKNOWN', label: 'Unknown' },
]

const SOURCES: { value: TrackSource | 'ALL'; label: string }[] = [
  { value: 'ALL', label: 'All sources' },
  { value: 'LIVE', label: 'Live' },
  { value: 'EDGE', label: 'Edge' },
  { value: 'CENTRAL', label: 'Central' },
  { value: 'DEMO', label: 'Demo' },
  { value: 'UNKNOWN', label: 'Unknown' },
]

const SORTS: { value: TrackQuery['sort']; label: string }[] = [
  { value: 'latest', label: 'Latest' },
  { value: 'oldest', label: 'Oldest' },
  { value: 'longest', label: 'Longest active' },
  { value: 'observations', label: 'Most observations' },
  { value: 'camera', label: 'Camera' },
]

function selectCls(compact?: boolean) {
  return clsx(
    'rounded border border-white/10 bg-bg text-xs text-slate-300 focus:border-cyan-400/60 focus:outline-none',
    compact ? 'px-1.5 py-1' : 'px-2 py-1.5'
  )
}

/**
 * Track filters (Component 6 spec §49, §169–§171). Compact, keyboard
 * accessible, clearable. The confidence control is labelled a DISPLAY FILTER
 * — it only hides tracks/list rows, it never modifies stored data.
 */
export function TrackFilters({ query, cameras, onChange, onReset }: TrackFiltersProps) {
  const isDirty =
    query.search !== DEFAULT_TRACK_QUERY.search ||
    query.cameraId !== DEFAULT_TRACK_QUERY.cameraId ||
    query.class !== DEFAULT_TRACK_QUERY.class ||
    query.status !== DEFAULT_TRACK_QUERY.status ||
    query.source !== DEFAULT_TRACK_QUERY.source ||
    query.timeRange !== DEFAULT_TRACK_QUERY.timeRange ||
    query.sort !== DEFAULT_TRACK_QUERY.sort

  return (
    <div className="space-y-2.5 rounded-xl border border-border bg-surface p-3">
      <div className="flex flex-wrap items-center gap-2">
        <input
          type="search"
          value={query.search}
          onChange={e => onChange({ search: e.target.value })}
          placeholder="Search TRK, CAM, EV, INC, EVD…"
          aria-label="Search tracks"
          className="min-w-[160px] rounded border border-white/10 bg-bg px-2 py-1.5 text-xs text-slate-200 placeholder:text-slate-600 focus:border-cyan-400/60 focus:outline-none"
        />
        <label className="flex items-center gap-1.5 text-[11px] text-slate-400">
          <span className="sr-only">Class</span>
          <select className={selectCls()} value={query.class} onChange={e => onChange({ class: e.target.value as DetectionClass | 'ALL' })}>
            {CLASSES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
          </select>
        </label>
        <label className="flex items-center gap-1.5 text-[11px] text-slate-400">
          <span className="sr-only">Status</span>
          <select className={selectCls()} value={query.status} onChange={e => onChange({ status: e.target.value as TrackStatus | 'ALL' })}>
            {STATUSES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>
        </label>
        <label className="flex items-center gap-1.5 text-[11px] text-slate-400">
          <span className="sr-only">Camera</span>
          <select className={selectCls()} value={query.cameraId} onChange={e => onChange({ cameraId: e.target.value })}>
            <option value="ALL">All cameras</option>
            {cameras.map(c => <option key={c.id} value={c.id}>{c.id}</option>)}
          </select>
        </label>
        <label className="flex items-center gap-1.5 text-[11px] text-slate-400">
          <span className="sr-only">Source</span>
          <select className={selectCls()} value={query.source} onChange={e => onChange({ source: e.target.value as TrackSource | 'ALL' })}>
            {SOURCES.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>
        </label>
        <label className="flex items-center gap-1.5 text-[11px] text-slate-400">
          <span className="sr-only">Time range</span>
          <select className={selectCls()} value={query.timeRange} onChange={e => onChange({ timeRange: e.target.value as TrackQuery['timeRange'] })}>
            <option value="all">All time</option>
            <option value="15m">Last 15 min</option>
            <option value="1h">Last hour</option>
            <option value="today">Today</option>
          </select>
        </label>
        {isDirty && (
          <button
            onClick={onReset}
            className="rounded border border-white/10 px-2 py-1.5 text-[11px] text-slate-400 hover:text-slate-200 hover:border-white/20 transition-colors"
          >
            Clear filters
          </button>
        )}
      </div>
      <div className="flex items-center gap-2">
        <label className="flex items-center gap-1.5 text-[11px] text-slate-400">
          <span className="sr-only">Sort</span>
          <span className="text-slate-500">Sort</span>
          <select className={selectCls(true)} value={query.sort} onChange={e => onChange({ sort: e.target.value as TrackQuery['sort'] })}>
            {SORTS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>
        </label>
        <button
          onClick={() => onChange({ order: query.order === 'asc' ? 'desc' : 'asc' })}
          className="rounded border border-white/10 px-2 py-1 text-[11px] text-slate-400 hover:text-slate-200 hover:border-white/20 transition-colors"
          aria-label={`Order ${query.order === 'asc' ? 'descending' : 'ascending'}`}
        >
          {query.order === 'desc' ? 'Newest first' : 'Oldest first'}
        </button>
      </div>
    </div>
  )
}