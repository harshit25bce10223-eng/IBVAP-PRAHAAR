import { clsx } from 'clsx'
import { DEFAULT_CORRELATION_QUERY, CORRELATION_SOURCES, CORRELATION_STATUSES } from '@/types/eventCorrelation'
import type { EventLogQuery, CorrelationSource, CorrelationStatus } from '@/types/eventCorrelation'
import type { Severity } from '@/types/risk'
import type { CameraDetail } from '@/types/camera'

interface EventLogFiltersProps {
  query: EventLogQuery
  cameras: CameraDetail[]
  sectors: string[]
  onChange: (patch: Partial<EventLogQuery>) => void
  onReset: () => void
}

const SEVERITIES: ('ALL' | Severity)[] = ['ALL', 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL']
const TIME_RANGES: { value: EventLogQuery['timeRange']; label: string }[] = [
  { value: '15m', label: 'Last 15 min' },
  { value: '1h', label: 'Last hour' },
  { value: 'today', label: 'Today' },
  { value: 'all', label: 'All time' },
]
const SORTS: { value: EventLogQuery['sort']; label: string }[] = [
  { value: 'time', label: 'Time' },
  { value: 'severity', label: 'Severity' },
  { value: 'signals', label: 'Signal count' },
  { value: 'cameras', label: 'Camera count' },
  { value: 'status', label: 'Correlation' },
]

function selectCls(compact?: boolean) {
  return clsx(
    'rounded border border-white/10 bg-bg text-xs text-slate-300 focus:border-cyan-400/60 focus:outline-none',
    compact ? 'px-1.5 py-1' : 'px-2 py-1.5'
  )
}

/**
 * Event Log filters (§60). Correlation, severity, camera, sector, source and
 * time range — the same filters the Phase-2 backend can reasonably support.
 */
export function EventLogFilters({ query, cameras, sectors, onChange, onReset }: EventLogFiltersProps) {
  const isDirty =
    query.search !== DEFAULT_CORRELATION_QUERY.search ||
    query.correlation !== DEFAULT_CORRELATION_QUERY.correlation ||
    query.severity !== DEFAULT_CORRELATION_QUERY.severity ||
    query.cameraId !== DEFAULT_CORRELATION_QUERY.cameraId ||
    query.sectorId !== DEFAULT_CORRELATION_QUERY.sectorId ||
    query.source !== DEFAULT_CORRELATION_QUERY.source ||
    query.connectivity !== DEFAULT_CORRELATION_QUERY.connectivity ||
    query.timeRange !== DEFAULT_CORRELATION_QUERY.timeRange

  return (
    <div className="space-y-2.5 rounded-xl border border-border bg-surface p-3">
      <div className="flex flex-wrap items-center gap-2">
        <input
          type="search"
          value={query.search}
          onChange={e => onChange({ search: e.target.value })}
          placeholder="Search INC, COR, CAM, EV, TRK…"
          aria-label="Search correlation groups"
          className="min-w-[180px] rounded border border-white/10 bg-bg px-2 py-1.5 text-xs text-slate-200 placeholder:text-slate-600 focus:border-cyan-400/60 focus:outline-none"
        />
        <label className="flex items-center gap-1.5 text-[11px] text-slate-400">
          <span className="sr-only">Correlation</span>
          <select className={selectCls()} value={query.correlation} onChange={e => onChange({ correlation: e.target.value as CorrelationStatus | 'ALL' })}>
            <option value="ALL">All correlation</option>
            {CORRELATION_STATUSES.filter(s => s !== 'UNKNOWN').map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </label>
        <label className="flex items-center gap-1.5 text-[11px] text-slate-400">
          <span className="sr-only">Severity</span>
          <select className={selectCls()} value={query.severity} onChange={e => onChange({ severity: e.target.value as Severity | 'ALL' })}>
            {SEVERITIES.map(s => <option key={s} value={s}>{s === 'ALL' ? 'All severity' : s}</option>)}
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
          <span className="sr-only">Sector</span>
          <select className={selectCls()} value={query.sectorId} onChange={e => onChange({ sectorId: e.target.value })}>
            <option value="ALL">All sectors</option>
            {sectors.map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </label>
        <label className="flex items-center gap-1.5 text-[11px] text-slate-400">
          <span className="sr-only">Source</span>
          <select className={selectCls()} value={query.source} onChange={e => onChange({ source: e.target.value as CorrelationSource | 'ALL' })}>
            <option value="ALL">All sources</option>
            {CORRELATION_SOURCES.filter(s => s !== 'UNKNOWN' && s !== 'SYSTEM' && s !== 'CAMERA_HEALTH').map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </label>
        <label className="flex items-center gap-1.5 text-[11px] text-slate-400">
          <span className="sr-only">Time range</span>
          <select className={selectCls()} value={query.timeRange} onChange={e => onChange({ timeRange: e.target.value as EventLogQuery['timeRange'] })}>
            {TIME_RANGES.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
          </select>
        </label>
        {isDirty && (
          <button
            onClick={onReset}
            className="rounded border border-white/10 px-2 py-1.5 text-[11px] text-slate-400 hover:text-slate-200 hover:border-white/20 transition-colors"
          >
            Reset
          </button>
        )}
      </div>
      <div className="flex items-center gap-2">
        <label className="flex items-center gap-1.5 text-[11px] text-slate-400">
          <span className="sr-only">Sort</span>
          <span className="text-slate-500">Sort</span>
          <select className={selectCls(true)} value={query.sort} onChange={e => onChange({ sort: e.target.value as EventLogQuery['sort'] })}>
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