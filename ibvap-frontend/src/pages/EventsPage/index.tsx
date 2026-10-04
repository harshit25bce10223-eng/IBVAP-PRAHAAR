import { useEffect, useMemo, useRef, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { AlertTriangle } from 'lucide-react'
import { EmptyState, ErrorState, PageHeader, Skeleton } from '@/components/ui'
import { useEventLog } from '@/hooks'
import { useCameraStore } from '@/store'
import { useCorrelationStore } from '@/store/correlationState'
import { CorrelationSummary, CorrelationEventDrawer, EventLogFilters } from '@/components/correlation'
import { formatGroupCount } from '@/components/correlation/correlationFormat'
import { correlationService } from '@/services/correlation'
import { queryFromSearchParams, queryToSearchParams } from '@/services/correlation/correlationQueryUrl'
import type { CorrelationEventMember, CorrelationGroup } from '@/types/eventCorrelation'
import { DEFAULT_CORRELATION_QUERY } from '@/types/eventCorrelation'

/**
 * EVENT / INCIDENT LOG — the primary correlation surface (§30/§162).
 *
 * Correlation compresses five raw signals into one summed row instead of five
 * equally-prominent alerts. Each row can be expanded to inspect member
 * signals, or opened in the Incident/Event Detail view. Charts and graphs are
 * secondary; the timeline and list remain primary.
 *
 * Filter/sort/page state is a deep link: it hydrates from the URL once, then
 * writes back so a configured view can be shared or reloaded.
 */
export function EventsPage() {
  const [searchParams, setSearchParams] = useSearchParams()
  const setQueryFromUrl = useCorrelationStore(s => s.setQuery)
  const urlHydrated = useRef(false)

  // Declared before useEventLog so the store is hydrated before its first
  // fetch effect runs — a deep link costs one request, not two. The URL is
  // authoritative for this view: re-applied on back/forward too, and the
  // serialization guard keeps the write-back below from echoing.
  useEffect(() => {
    const fromUrl = { ...DEFAULT_CORRELATION_QUERY, ...queryFromSearchParams(searchParams) }
    const current = useCorrelationStore.getState().query
    if (queryToSearchParams(fromUrl).toString() !== queryToSearchParams(current).toString()) {
      setQueryFromUrl(fromUrl)
    }
    urlHydrated.current = true
  }, [searchParams, setQueryFromUrl])

  const { query, page, listState, listError, expandedIds, setQuery, retry, toggleExpanded, resetList } = useEventLog()
  const cameras = useCameraStore(s => s.cameras)
  const [selectedMember, setSelectedMember] = useState<CorrelationEventMember | null>(null)
  const [selectedGroup, setSelectedGroup] = useState<CorrelationGroup | null>(null)

  // Write the store back to the URL so a configured view is shareable. The
  // render's `query` trails the store until the hydration re-render lands;
  // echoing that stale value would overwrite the deep link with pre-hydration
  // state, so wait for the settled value before writing back.
  useEffect(() => {
    if (!urlHydrated.current) return
    const settled = useCorrelationStore.getState().query
    if (query !== settled) return
    const next = queryToSearchParams(settled).toString()
    if (next !== searchParams.toString()) setSearchParams(next, { replace: true })
  }, [query, searchParams, setSearchParams])

  const totalPages = page ? Math.max(1, Math.ceil(page.total / query.pageSize)) : 1
  // An empty result is only "no activity" when nothing was filtered out; with
  // filters applied it means "nothing matched" — never "all quiet" (§64).
  const isFiltered = useMemo(() => {
    const d = DEFAULT_CORRELATION_QUERY
    return (
      query.search !== d.search ||
      query.correlation !== d.correlation ||
      query.severity !== d.severity ||
      query.cameraId !== d.cameraId ||
      query.sectorId !== d.sectorId ||
      query.source !== d.source ||
      query.connectivity !== d.connectivity ||
      query.timeRange !== d.timeRange
    )
  }, [query])

  const sectors = useMemo(
    () => [...new Set((page?.groups ?? []).map(g => g.sectorId).filter((s): s is string => s !== null))].sort(),
    [page]
  )

  return (
    <div className="h-full flex flex-col overflow-hidden p-4 gap-4 bg-bg">
      <PageHeader
        title="Event / Incident Log"
        subtitle="Correlation engine output — grouped signals, not isolated alerts"
        badge={
          correlationService.source === 'DEMO' ? (
            <span className="rounded border border-cyan-500/30 bg-cyan-500/10 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider text-cyan-400">
              Demo mode
            </span>
          ) : (
            <span className="rounded border border-emerald-500/30 bg-emerald-500/10 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider text-emerald-400">
              Live
            </span>
          )
        }
      />

      <EventLogFilters
        query={query}
        cameras={cameras}
        sectors={sectors}
        onChange={setQuery}
        onReset={resetList}
      />

      <main className="flex-1 min-h-0 overflow-y-auto">
        {listState === 'loading' && !page && <LogSkeleton />}
        {listState === 'error' && (
          <ErrorState message={listError ?? 'Correlation data could not be loaded.'} onRetry={retry} />
        )}
        {listState !== 'loading' && page && page.groups.length === 0 && (
          <EmptyState
            icon={<AlertTriangle size={28} aria-hidden />}
            title="No correlated activity"
            description={
              isFiltered
                ? 'No correlation groups match the selected filters.'
                : 'No event signals have been grouped yet.'
            }
          />
        )}

        {page && page.groups.length > 0 && (
          <div className="space-y-2.5">
            {page.groups.map(group => {
              const expanded = expandedIds.includes(group.correlationId)
              return (
                <CorrelationSummary
                  key={group.correlationId}
                  group={group}
                  to={`/incident/${group.correlationId}`}
                  showExpand
                  expanded={expanded}
                  onExpand={() => toggleExpanded(group.correlationId)}
                  onSelectMember={m => {
                    setSelectedGroup(group)
                    setSelectedMember(m)
                  }}
                />
              )
            })}

            <Pagination
              page={query.page}
              totalPages={totalPages}
              total={page.total}
              onPage={p => setQuery({ page: p })}
            />
          </div>
        )}
      </main>

      <CorrelationEventDrawer
        open={selectedMember !== null}
        onClose={() => {
          setSelectedMember(null)
          setSelectedGroup(null)
        }}
        member={selectedMember}
        group={selectedGroup}
      />
    </div>
  )
}

function Pagination({ page, totalPages, total, onPage }: { page: number; totalPages: number; total: number; onPage: (p: number) => void }) {
  return (
    <nav className="flex items-center justify-between" aria-label="Event log pages">
      <span className="font-mono text-[11px] text-slate-500 tabular-nums">
        Page {page} of {totalPages} · {formatGroupCount(total)}
      </span>
      <span className="flex gap-1">
        <PageBtn label="Previous page" disabled={page <= 1} onClick={() => onPage(page - 1)}>← Prev</PageBtn>
        <PageBtn label="Next page" disabled={page >= totalPages} onClick={() => onPage(page + 1)}>Next →</PageBtn>
      </span>
    </nav>
  )
}

function PageBtn({ label, disabled, onClick, children }: { label: string; disabled: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      aria-label={label}
      disabled={disabled}
      onClick={onClick}
      className="rounded-md border border-white/10 px-2.5 py-1 text-[11px] text-slate-300 hover:border-cyan-500/40 hover:text-cyan-300 disabled:opacity-40 disabled:pointer-events-none focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/60"
    >
      {children}
    </button>
  )
}

function LogSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <div className="space-y-2.5" role="status" aria-label="Loading event log">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-20 w-full rounded-xl" />
      ))}
    </div>
  )
}