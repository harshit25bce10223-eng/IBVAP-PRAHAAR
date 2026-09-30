import { useEffect, useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'
import { Radar } from 'lucide-react'
import { EmptyState, ErrorState, PageHeader, Skeleton } from '@/components/ui'
import { useDetectionList } from '@/hooks'
import { useCameraStore, useDetectionStore } from '@/store'
import {
  DetectionFilters,
  DetectionInspector,
  DetectionList,
  DetectionSummary,
  formatDetectionCount,
} from '@/components/detection'
import { detectionService } from '@/services/detection'
import { buildSummary } from '@/services/detection/detectionSummary'
import { DEFAULT_DETECTION_QUERY } from '@/types/detection'

/**
 * DETECTION INTELLIGENCE — the fleet-wide detector output workspace (§23/§25).
 *
 * Every row is a raw observation from the detection service; nothing here
 * interprets a detection as a threat, identity or correlation (§116). The
 * summary card composes the CURRENT PAGE and states that scope explicitly —
 * the list API returns a page + matching total only, so a whole-result-set
 * per-class breakdown cannot be shown and is not implied (§24).
 *
 * Loading, error and zero-result states stay distinct (§28): a failed request
 * surfaces as DETECTION DATA UNAVAILABLE, a filtered empty set as 'no
 * matches', and an unfiltered empty set as 'no observations recorded'.
 */
export function DetectionIntelligence() {
  const [searchParams] = useSearchParams()
  const { query, page, listState, listError, setQuery, retry, resetList } = useDetectionList()
  const cameras = useCameraStore(s => s.cameras)
  const selected = useDetectionStore(s => s.selected)
  const selectDetection = useDetectionStore(s => s.selectDetection)

  // §14 deep-link: Track Intelligence's observation table links here as
  // /detections?search=DET-xxx. Apply the param once on mount, mirroring the
  // ANPR workspace's URL-param handling. The search field covers detection ids
  // (backend Detection.detection_id.ilike), so the row resolves end-to-end.
  useEffect(() => {
    const searchParam = searchParams.get('search')
    if (searchParam && searchParam !== query.search) {
      setQuery({ search: searchParam })
    }
  }, []) // mount-time URL read only — afterwards the filter UI owns the query

  const totalPages = page ? Math.max(1, Math.ceil(page.total / query.pageSize)) : 1

  // Filter changes empty the result set for a different reason than a quiet
  // repository — the empty copy must not confuse the two (§64/§172).
  const isFiltered = useMemo(() => {
    const d = DEFAULT_DETECTION_QUERY
    return (
      query.search !== d.search ||
      query.cameraId !== d.cameraId ||
      query.class !== d.class ||
      query.confidenceMin !== d.confidenceMin ||
      query.quality !== d.quality ||
      query.source !== d.source ||
      query.timeRange !== d.timeRange
    )
  }, [query])

  // Page-scoped structural summary (counts only). The scope line below the
  // heading is what makes it honest: it names the page and the matching
  // total the counts were drawn from.
  const summary = useMemo(() => (page ? buildSummary('ALL', page.detections) : null), [page])

  const selectedCameraLabel = useMemo(
    () => (selected ? cameras.find(c => c.id === selected.cameraId)?.label ?? null : null),
    [selected, cameras]
  )

  const isDemo = detectionService.source === 'DEMO'
  // While a new query loads, the previous page stays visible; its counts no
  // longer describe the current filters, so the footer says 'Updating…'
  // instead of presenting stale page numbers as current.
  const isRefreshing = listState === 'loading' && page !== null

  return (
    <div className="h-full flex flex-col overflow-hidden p-4 gap-4 bg-[#080c12]">
      <PageHeader
        title="Detection Intelligence"
        subtitle="Fleet-wide detector output — observations, not alerts"
        badge={
          isDemo ? (
            <span className="rounded border border-cyan-500/30 bg-cyan-500/10 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider text-cyan-400">
              Demo mode
            </span>
          ) : (
            <span className="rounded border border-emerald-500/30 bg-emerald-500/10 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider text-emerald-400">
              Live backend
            </span>
          )
        }
      />

      <DetectionFilters
        query={query}
        cameras={cameras}
        onChange={setQuery}
        onReset={resetList}
      />

      <main className="flex-1 min-h-0 overflow-y-auto">
        {(listState === 'idle' || listState === 'loading') && !page && <ListSkeleton />}
        {listState === 'error' && (
          <ErrorState message={listError ?? 'Detection data could not be loaded.'} onRetry={retry} />
        )}

        {listState !== 'error' && page && (
          <div className="flex flex-col gap-3 xl:flex-row xl:items-start">
            <div className="min-w-0 flex-1 space-y-2.5">
              {page.detections.length === 0 ? (
                <EmptyState
                  icon={<Radar size={28} aria-hidden />}
                  title={isFiltered ? 'No detections match these filters' : 'No detections recorded'}
                  description={
                    isFiltered
                      ? 'Clear or change the filters to see results — this is not a detector outage.'
                      : 'The detection repository returned no observations for the current query.'
                  }
                />
              ) : (
                <>
                  <DetectionList
                    detections={page.detections}
                    selectedId={selected?.detectionId ?? null}
                    onSelect={d => selectDetection(d, d.cameraId)}
                    filtered={isFiltered}
                  />
                  <Pagination
                    page={query.page}
                    totalPages={totalPages}
                    total={page.total}
                    filtered={isFiltered}
                    refreshing={isRefreshing}
                    onPage={p => setQuery({ page: p })}
                  />
                </>
              )}
            </div>

            {page.detections.length > 0 && summary && (
              <DetectionSummary
                summary={summary}
                demo={isDemo}
                title="Page composition"
                scopeNote={`Page ${query.page} of ${totalPages} · ${page.total} matching`}
                className="order-first w-full shrink-0 xl:order-none xl:sticky xl:top-0 xl:w-[300px]"
              />
            )}
          </div>
        )}
      </main>

      <DetectionInspector
        open={selected !== null}
        onClose={() => selectDetection(null, null)}
        detection={selected}
        cameraLabel={selectedCameraLabel}
      />
    </div>
  )
}

function Pagination({
  page,
  totalPages,
  total,
  filtered,
  refreshing,
  onPage,
}: {
  page: number
  totalPages: number
  total: number
  filtered: boolean
  refreshing: boolean
  onPage: (p: number) => void
}) {
  return (
    <nav className="flex items-center justify-between" aria-label="Detection pages">
      <span className="font-mono text-[11px] text-slate-500 tabular-nums" role="status">
        {refreshing
          ? 'Updating results…'
          : `Page ${page} of ${totalPages} · ${formatDetectionCount(total)}${filtered ? ' matching' : ''}`}
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

function ListSkeleton({ rows = 6 }: { rows?: number }) {
  return (
    <div className="space-y-2" role="status" aria-label="Loading detections">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-12 w-full rounded-lg" />
      ))}
    </div>
  )
}
