// ─────────────────────────────────────────────────────────────────────────────
// ANPRSearchResults.tsx — §24 typed plate search results
//
// Five explicit match labels mirror the backend classification. Partial text
// matches are never presented as exact; related sightings are never presented
// as the same physical vehicle.
// ─────────────────────────────────────────────────────────────────────────────
import { Search, X } from 'lucide-react'
import { clsx } from 'clsx'
import type { PlateSearchMatchType, VehicleSearchResult } from '@/types/anpr'

interface ANPRSearchResultsProps {
  query: string
  results: VehicleSearchResult[]
  state: 'idle' | 'loading' | 'ready' | 'error'
  selectedId: string | null
  onSelect: (sightingId: string) => void
  onClear: () => void
}

const MATCH_LABEL: Record<PlateSearchMatchType, string> = {
  EXACT_NORMALIZED_MATCH: 'EXACT NORMALIZED',
  RAW_READ_MATCH: 'RAW READ',
  PARTIAL_MATCH: 'PARTIAL',
  CANDIDATE_MATCH: 'CANDIDATE',
  RELATED_SIGHTING: 'RELATED SIGHTING',
}

function matchClass(matchType: PlateSearchMatchType): string {
  switch (matchType) {
    case 'EXACT_NORMALIZED_MATCH':
      return 'text-emerald-300 border-emerald-500/40 bg-emerald-500/10'
    case 'RAW_READ_MATCH':
      return 'text-cyan-300 border-cyan-500/40 bg-cyan-500/10'
    case 'PARTIAL_MATCH':
      return 'text-amber-300 border-amber-500/40 bg-amber-500/10'
    case 'CANDIDATE_MATCH':
      return 'text-sky-300 border-sky-500/40 bg-sky-500/10'
    case 'RELATED_SIGHTING':
      return 'text-slate-300 border-slate-500/40 bg-slate-500/10'
  }
}

function fmtTime(ts: string): string {
  const d = new Date(ts)
  if (Number.isNaN(d.getTime())) return ts
  return d.toLocaleString('en-IN', {
    hour12: false,
    day: '2-digit',
    month: 'short',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  })
}

export function ANPRSearchResults({
  query,
  results,
  state,
  selectedId,
  onSelect,
  onClear,
}: ANPRSearchResultsProps) {
  return (
    <div className="flex flex-col h-full min-h-0">
      <div className="p-3 border-b border-border flex items-center justify-between flex-shrink-0 bg-bg/40">
        <div className="flex items-center gap-2 min-w-0">
          <Search className="h-3.5 w-3.5 text-cyan-400 flex-shrink-0" />
          <span className="text-xs font-mono font-semibold uppercase text-slate-300 truncate">
            Plate Search — <span className="text-cyan-300">{query}</span>
          </span>
          {state === 'ready' && (
            <span className="text-[10px] font-mono px-1.5 py-0.2 rounded bg-slate-800 text-slate-400">
              {results.length}
            </span>
          )}
        </div>
        <button
          onClick={onClear}
          className="p-1 rounded text-slate-500 hover:text-slate-200 hover:bg-slate-800/60 transition-colors"
          title="Clear search results"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-2 space-y-1.5">
        {state === 'loading' && (
          <div className="p-3 text-xs font-mono text-slate-500">Searching plate observations…</div>
        )}

        {state === 'error' && (
          <div className="p-3 text-xs font-mono text-amber-300">
            Plate search failed. Check the backend connection and try again.
          </div>
        )}

        {state === 'ready' && results.length === 0 && (
          <div className="p-3 text-xs font-mono text-slate-500">
            No plate observations matched this query.
          </div>
        )}

        {results.map(({ sighting: s, matchType }) => (
          <button
            key={s.sightingId}
            onClick={() => onSelect(s.sightingId)}
            className={clsx(
              'w-full text-left p-2 rounded-lg border transition-colors',
              s.sightingId === selectedId
                ? 'border-cyan-500/50 bg-cyan-500/10'
                : 'border-border bg-bg/40 hover:bg-slate-800/40'
            )}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="font-mono text-sm text-slate-100 truncate">
                {s.plateRead?.displayRead ?? 'No plate read'}
              </span>
              <span
                className={clsx(
                  'text-[9px] font-mono px-1.5 py-0.5 rounded border whitespace-nowrap',
                  matchClass(matchType)
                )}
              >
                {MATCH_LABEL[matchType]}
              </span>
            </div>
            <div className="mt-1 flex items-center gap-2 text-[10px] font-mono text-slate-400">
              <span>{s.sightingId}</span>
              <span className="text-slate-600">·</span>
              <span>{s.cameraId}</span>
              <span className="text-slate-600">·</span>
              <span>{fmtTime(s.observedAt)}</span>
              <span className="text-slate-600">·</span>
              <span>{s.vehicleClass}</span>
            </div>
          </button>
        ))}
      </div>

      <div className="px-3 py-1.5 border-t border-border text-[10px] font-mono text-slate-500 flex-shrink-0">
        Match labels: exact normalized / raw read / partial / candidate / related sighting.
        Partial and related results are not identity confirmation.
      </div>
    </div>
  )
}
