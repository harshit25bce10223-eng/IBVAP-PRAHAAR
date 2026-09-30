import { clsx } from 'clsx'
import { DEFAULT_DETECTION_QUERY } from '@/types/detection'
import type { DetectionClass, DetectionQuality, DetectionQuery, DetectionSource } from '@/types/detection'
import type { CameraDetail } from '@/types/camera'

interface DetectionFiltersProps {
  query: DetectionQuery
  cameras: CameraDetail[]
  onChange: (patch: Partial<DetectionQuery>) => void
  onReset: () => void
}

const CLASSES: { value: DetectionClass | 'OTHER' | 'ALL'; label: string }[] = [
  { value: 'ALL', label: 'All classes' },
  { value: 'PERSON', label: 'Person' },
  { value: 'VEHICLE', label: 'Vehicle' },
  { value: 'ANIMAL', label: 'Animal' },
  { value: 'OBJECT', label: 'Object' },
  { value: 'OTHER', label: 'Other / unknown' },
]

const QUALITIES: { value: DetectionQuality | 'ALL'; label: string }[] = [
  { value: 'ALL', label: 'All quality' },
  { value: 'GOOD', label: 'Good' },
  { value: 'LIMITED', label: 'Limited' },
  { value: 'POOR', label: 'Poor' },
]

const CONFIDENCE_STEPS: { value: number | null; label: string }[] = [
  { value: null, label: 'Confidence: any' },
  { value: 50, label: 'Show ≥ 50%' },
  { value: 70, label: 'Show ≥ 70%' },
  { value: 85, label: 'Show ≥ 85%' },
]

const SORTS: { value: DetectionQuery['sort']; label: string }[] = [
  { value: 'latest', label: 'Latest' },
  { value: 'oldest', label: 'Oldest' },
  { value: 'confidence', label: 'Confidence' },
  { value: 'class', label: 'Class' },
  { value: 'camera', label: 'Camera' },
]

function selectCls(compact?: boolean) {
  return clsx(
    'rounded border border-white/10 bg-[#080c12] text-xs text-slate-300 focus:border-cyan-400/60 focus:outline-none',
    compact ? 'px-1.5 py-1' : 'px-2 py-1.5'
  )
}

/**
 * Detection filters (Component spec §100/§101/§169–§171). Compact, keyboard
 * accessible, clearable. The confidence control is labelled a DISPLAY FILTER
 * — it only hides boxes/list rows, it never modifies stored data.
 */
export function DetectionFilters({ query, cameras, onChange, onReset }: DetectionFiltersProps) {
  // Time sorts label their direction explicitly; the toggle switches between
  // newest-first ('latest' + desc) and oldest-first ('oldest' + asc) so the
  // label can never disagree with the rows below it. Other sorts toggle the
  // order on their own field.
  const isTimeSort = query.sort === 'latest' || query.sort === 'oldest'
  const orderLabel = isTimeSort
    ? query.order === 'desc' ? 'Newest first' : 'Oldest first'
    : query.order === 'desc' ? 'Descending' : 'Ascending'

  const toggleOrder = () => {
    if (isTimeSort) {
      onChange(
        query.order === 'desc'
          ? { sort: 'oldest', order: 'asc' }
          : { sort: 'latest', order: 'desc' }
      )
    } else {
      onChange({ order: query.order === 'asc' ? 'desc' : 'asc' })
    }
  }

  const isDirty =
    query.search !== DEFAULT_DETECTION_QUERY.search ||
    query.cameraId !== DEFAULT_DETECTION_QUERY.cameraId ||
    query.class !== DEFAULT_DETECTION_QUERY.class ||
    query.confidenceMin !== DEFAULT_DETECTION_QUERY.confidenceMin ||
    query.quality !== DEFAULT_DETECTION_QUERY.quality ||
    query.source !== DEFAULT_DETECTION_QUERY.source ||
    query.timeRange !== DEFAULT_DETECTION_QUERY.timeRange ||
    query.sort !== DEFAULT_DETECTION_QUERY.sort ||
    query.order !== DEFAULT_DETECTION_QUERY.order

  return (
    <div className="space-y-2.5 rounded-xl border border-[#1e2d40] bg-[#0d1117] p-3">
      <div className="flex flex-wrap items-center gap-2">
        <input
          type="search"
          value={query.search}
          onChange={e => onChange({ search: e.target.value })}
          placeholder="Search DET, CAM, EV, TRK, INC…"
          aria-label="Search detections"
          className="min-w-[160px] rounded border border-white/10 bg-[#080c12] px-2 py-1.5 text-xs text-slate-200 placeholder:text-slate-600 focus:border-cyan-400/60 focus:outline-none"
        />
        <label className="flex items-center gap-1.5 text-[11px] text-slate-400">
          <span className="sr-only">Class</span>
          <select className={selectCls()} value={query.class} onChange={e => onChange({ class: e.target.value as DetectionClass | 'OTHER' | 'ALL' })}>
            {CLASSES.map(c => <option key={c.value} value={c.value}>{c.label}</option>)}
          </select>
        </label>
        <label className="flex items-center gap-1.5 text-[11px] text-slate-400">
          <span className="sr-only">Camera</span>
          <select className={selectCls()} value={query.cameraId} onChange={e => onChange({ cameraId: e.target.value })}>
            <option value="ALL">All cameras</option>
            {cameras.map(c => <option key={c.id} value={c.id}>{c.id}</option>)}
          </select>
        </label>
        <label className="flex items-center gap-1.5 text-[11px] text-slate-400" title="Display filter — boxes/list rows are only hidden, never altered">
          <span className="sr-only">Confidence display filter</span>
          <span className="text-slate-500">Display filter</span>
          <select className={selectCls()} value={query.confidenceMin ?? ''} onChange={e => onChange({ confidenceMin: e.target.value === '' ? null : Number(e.target.value) })}>
            {CONFIDENCE_STEPS.map(s => <option key={s.label} value={s.value ?? ''}>{s.label}</option>)}
          </select>
        </label>
        <label className="flex items-center gap-1.5 text-[11px] text-slate-400">
          <span className="sr-only">Quality</span>
          <select className={selectCls()} value={query.quality} onChange={e => onChange({ quality: e.target.value as DetectionQuality | 'ALL' })}>
            {QUALITIES.map(q => <option key={q.value} value={q.value}>{q.label}</option>)}
          </select>
        </label>
        <label className="flex items-center gap-1.5 text-[11px] text-slate-400">
          <span className="sr-only">Source</span>
          <select className={selectCls()} value={query.source} onChange={e => onChange({ source: e.target.value as DetectionSource | 'ALL' })}>
            <option value="ALL">All sources</option>
            <option value="EDGE">Edge</option>
            <option value="CENTRAL">Central</option>
            <option value="REMOTE">Remote</option>
            <option value="DEMO">Demo</option>
          </select>
        </label>
        <label className="flex items-center gap-1.5 text-[11px] text-slate-400">
          <span className="sr-only">Time range</span>
          <select className={selectCls()} value={query.timeRange} onChange={e => onChange({ timeRange: e.target.value as DetectionQuery['timeRange'] })}>
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
          <select className={selectCls(true)} value={query.sort} onChange={e => onChange({ sort: e.target.value as DetectionQuery['sort'] })}>
            {SORTS.map(s => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>
        </label>
        <button
          onClick={toggleOrder}
          className="rounded border border-white/10 px-2 py-1 text-[11px] text-slate-400 hover:text-slate-200 hover:border-white/20 transition-colors"
          aria-label={`Sort order: ${orderLabel}. Activate to reverse.`}
        >
          {orderLabel}
        </button>
      </div>
    </div>
  )
}