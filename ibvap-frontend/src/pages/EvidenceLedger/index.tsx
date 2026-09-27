import { useMemo, useState } from 'react'
import { clsx } from 'clsx'
import { FileSearch } from 'lucide-react'
import { Drawer, EmptyState, ErrorState, PageHeader, Skeleton } from '@/components/ui'
import { EvidenceDetail, EvidenceFilters, EvidenceTable, AuditLogTab } from '@/components/evidence'
import { TONE, toneForLedger } from '@/components/evidence/evidenceTone'
import { formatCount } from '@/components/evidence/evidenceFormat'
import { formatClock } from '@/components/camera-health/healthFormat'
import { useEvidenceLedger } from '@/hooks/useEvidence'
import { DEFAULT_EVIDENCE_QUERY } from '@/store/evidenceState'
import type { EvidenceQuery, EvidenceRecord } from '@/types/evidence'

/**
 * EVIDENCE & AUDIT LEDGER — tamper-evident evidence records.
 * Header answers: what exists, ledger standing, last verification.
 * Table answers: which incident/camera, verified?, anchored?, anything wrong?
 * Detail drawer answers the rest. Demo data is labelled; the backend stays
 * authoritative for every verdict once Phase 2 lands.
 */
export function EvidenceLedger() {
  const {
    query, page, listState, listError,
    ledger, ledgerState, audit, auditState, auditError,
    setQuery, retryList, retryAudit,
  } = useEvidenceLedger()
  const [tab, setTab] = useState<'evidence' | 'audit'>('evidence')
  const [selected, setSelected] = useState<EvidenceRecord | null>(null)

  const cameras = useMemo(() => {
    const ids = new Set((page?.records ?? []).map(r => r.cameraId))
    return [...ids].sort()
  }, [page])

  const totalPages = page ? Math.max(1, Math.ceil(page.total / query.pageSize)) : 1

  const onSort = (key: EvidenceQuery['sort']) => {
    if (query.sort === key) {
      setQuery({ order: query.order === 'asc' ? 'desc' : 'asc' })
    } else {
      setQuery({ sort: key, order: key === 'integrity' ? 'asc' : 'desc' })
    }
  }

  return (
    <div className="h-full flex flex-col overflow-hidden p-4 gap-4 bg-[#080c12]">
      <PageHeader
        title="Evidence & Audit Ledger"
        subtitle="Tamper-evident evidence records"
        badge={
          <span className="rounded border border-cyan-500/30 bg-cyan-500/10 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider text-cyan-400">
            Demo mode
          </span>
        }
      />

      {/* Summary strip: count · ledger standing · last verification */}
      <dl className="flex flex-wrap gap-x-8 gap-y-2 rounded-xl border border-[#1e2d40] bg-[#0d1117] px-4 py-3">
        <SummaryItem label="Evidence records" value={ledger ? formatCount(ledger.recordCount) : '—'} />
        <div className="flex flex-col gap-0.5">
          <dt className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Ledger</dt>
          <dd className={clsx('font-mono text-sm', ledger ? TONE[toneForLedger(ledger.status)].text : 'text-slate-500')}>
            {ledgerState === 'loading' ? '…' : (ledger?.status ?? 'UNAVAILABLE')}
          </dd>
        </div>
        <SummaryItem
          label="Last verified"
          value={ledger?.lastVerifiedAt ? `${formatClock(ledger.lastVerifiedAt)}${ledger.lastVerifiedBy ? ` · ${ledger.lastVerifiedBy}` : ''}` : '—'}
          mono
        />
      </dl>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-[#1e2d40]" role="tablist" aria-label="Ledger views">
        <TabButton active={tab === 'evidence'} onClick={() => setTab('evidence')} label={`Evidence${page ? ` (${page.total})` : ''}`} id="tab-evidence" />
        <TabButton active={tab === 'audit'} onClick={() => setTab('audit')} label={`Audit log${audit.length > 0 ? ` (${audit.length})` : ''}`} id="tab-audit" />
      </div>

      <main className="flex-1 min-h-0 overflow-y-auto">
        {tab === 'evidence' ? (
          <div className="space-y-3">
            <EvidenceFilters
              query={query}
              cameras={cameras}
              onChange={patch => setQuery(patch)}
              onReset={() => setQuery({ ...DEFAULT_EVIDENCE_QUERY })}
            />

            {listState === 'loading' && !page && <TableSkeleton />}
            {listState === 'error' && (
              <ErrorState message={listError ?? 'Evidence records could not be loaded.'} onRetry={retryList} />
            )}
            {listState !== 'loading' && page && page.records.length === 0 && (
              <EmptyState
                icon={<FileSearch size={28} aria-hidden />}
                title="No evidence records"
                description={
                  query.search !== '' || query.cameraId !== 'ALL'
                    ? 'No evidence records match the selected filters.'
                    : 'No evidence has been created yet.'
                }
              />
            )}
            {page && page.records.length > 0 && (
              <>
                <EvidenceTable
                  records={page.records}
                  sort={query.sort}
                  order={query.order}
                  onSort={onSort}
                  onSelect={setSelected}
                />
                <Pagination
                  page={query.page}
                  totalPages={totalPages}
                  total={page.total}
                  onPage={p => setQuery({ page: p })}
                />
              </>
            )}
          </div>
        ) : (
          <div>
            {auditState === 'loading' && <TableSkeleton rows={5} />}
            {auditState === 'error' && (
              <ErrorState message={auditError ?? 'Audit log could not be loaded.'} onRetry={retryAudit} />
            )}
            {auditState === 'ready' && <AuditLogTab entries={audit} />}
          </div>
        )}
      </main>

      <Drawer
        open={selected !== null}
        onClose={() => setSelected(null)}
        title={selected ? `Evidence ${selected.evidenceId}` : undefined}
        width="w-[520px] max-w-[92vw]"
      >
        {selected && <EvidenceDetail record={selected} />}
      </Drawer>
    </div>
  )
}

function SummaryItem({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex flex-col gap-0.5">
      <dt className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">{label}</dt>
      <dd className={clsx('text-sm text-slate-200 tabular-nums', mono && 'font-mono')}>{value}</dd>
    </div>
  )
}

function TabButton({ active, onClick, label, id }: { active: boolean; onClick: () => void; label: string; id: string }) {
  return (
    <button
      role="tab"
      id={id}
      aria-selected={active}
      onClick={onClick}
      className={clsx(
        'px-3 py-2 text-xs font-medium transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/60 rounded-t',
        active ? 'text-cyan-400 border-b-2 border-cyan-400 -mb-px' : 'text-slate-500 hover:text-slate-300'
      )}
    >
      {label}
    </button>
  )
}

function Pagination({ page, totalPages, total, onPage }: { page: number; totalPages: number; total: number; onPage: (p: number) => void }) {
  return (
    <nav className="flex items-center justify-between" aria-label="Evidence pages">
      <span className="font-mono text-[11px] text-slate-500 tabular-nums">
        Page {page} of {totalPages} · {total} record{total === 1 ? '' : 's'}
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

function TableSkeleton({ rows = 8 }: { rows?: number }) {
  return (
    <div className="rounded-xl border border-[#1e2d40] bg-[#0d1117] p-3 space-y-2" role="status" aria-label="Loading evidence records">
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-8 w-full" />
      ))}
    </div>
  )
}
