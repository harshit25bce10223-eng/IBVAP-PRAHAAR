import type { EvidenceQuery } from '@/types/evidence'
import { ANCHOR_STATES, EVIDENCE_TYPES, INTEGRITY_STATES } from '@/types/evidence'
import { humanize } from './evidenceFormat'

const SOURCES = ['CAMERA', 'EDGE', 'ANALYTICS', 'INCIDENT', 'SYSTEM', 'UNKNOWN'] as const

/**
 * Ledger filters. Every control maps 1:1 to EvidenceQuery fields so the
 * Phase-2 backend can serve the identical contract server-side.
 */
export function EvidenceFilters({
  query,
  cameras,
  onChange,
  onReset,
}: {
  query: EvidenceQuery
  cameras: string[]
  onChange: (patch: Partial<EvidenceQuery>) => void
  onReset: () => void
}) {
  const hasActive =
    query.search !== '' ||
    query.cameraId !== 'ALL' ||
    query.type !== 'ALL' ||
    query.integrity !== 'ALL' ||
    query.anchor !== 'ALL' ||
    query.source !== 'ALL'

  return (
    <div className="flex flex-wrap items-end gap-2" role="search" aria-label="Evidence filters">
      <label className="flex min-w-[180px] flex-1 flex-col gap-1">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">
          Search ID / hash prefix
        </span>
        <input
          type="search"
          value={query.search}
          onChange={e => onChange({ search: e.target.value })}
          placeholder="EVD-10482 · INC-… · CAM-12 · a3f8…"
          className="rounded-md border border-white/10 bg-[#080c12] px-2.5 py-1.5 font-mono text-xs text-slate-200 placeholder:text-slate-600 focus:border-cyan-400/60 focus:outline-none"
        />
      </label>
      <FilterSelect label="Camera" value={query.cameraId} onChange={v => onChange({ cameraId: v })} options={['ALL', ...cameras]} />
      <FilterSelect label="Type" value={query.type} onChange={v => onChange({ type: v })} options={['ALL', ...EVIDENCE_TYPES]} display={humanize} />
      <FilterSelect label="Integrity" value={query.integrity} onChange={v => onChange({ integrity: v })} options={['ALL', ...INTEGRITY_STATES]} display={humanize} />
      <FilterSelect label="Anchor" value={query.anchor} onChange={v => onChange({ anchor: v })} options={['ALL', ...ANCHOR_STATES]} display={humanize} />
      <FilterSelect label="Source" value={query.source} onChange={v => onChange({ source: v })} options={['ALL', ...SOURCES]} display={humanize} />
      {hasActive && (
        <button
          onClick={onReset}
          className="rounded-md border border-white/10 px-2.5 py-1.5 text-xs text-slate-400 hover:text-slate-200 hover:border-white/20 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/60"
        >
          Clear
        </button>
      )}
    </div>
  )
}

function FilterSelect({
  label,
  value,
  options,
  onChange,
  display,
}: {
  label: string
  value: string
  options: readonly string[]
  onChange: (v: string) => void
  display?: (v: string) => string
}) {
  const render = display ?? ((v: string) => v)
  return (
    <label className="flex flex-col gap-1">
      <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">{label}</span>
      <select
        value={value}
        onChange={e => onChange(e.target.value)}
        className="rounded-md border border-white/10 bg-[#080c12] px-2 py-1.5 text-xs text-slate-200 focus:border-cyan-400/60 focus:outline-none"
      >
        {options.map(o => (
          <option key={o} value={o}>
            {o === 'ALL' ? `All ${label.toLowerCase()}s` : render(o)}
          </option>
        ))}
      </select>
    </label>
  )
}
