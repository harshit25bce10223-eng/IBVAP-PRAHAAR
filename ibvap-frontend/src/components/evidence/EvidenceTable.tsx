import { clsx } from 'clsx'
import { ArrowDown, ArrowUp, Copy, Check } from 'lucide-react'
import { useState } from 'react'
import type { EvidenceQuery, EvidenceRecord } from '@/types/evidence'
import { formatClock } from '@/components/camera-health/healthFormat'
import { TONE, toneForAnchor, toneForIntegrity, toneForRecordStatus } from './evidenceTone'
import { humanize, truncateHash } from './evidenceFormat'

type SortKey = EvidenceQuery['sort']

/**
 * Dense operational table. One row per record (never cards); a 2px semantic
 * marker carries integrity state while text always accompanies color.
 * Hashes render truncated — full digest + copy live in the detail drawer.
 */
export function EvidenceTable({
  records,
  sort,
  order,
  onSort,
  onSelect,
}: {
  records: EvidenceRecord[]
  sort: SortKey
  order: 'asc' | 'desc'
  onSort: (key: SortKey) => void
  onSelect: (record: EvidenceRecord) => void
}) {
  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-surface">
      <table className="w-full min-w-[960px] border-collapse text-left">
        <caption className="sr-only">Tamper-evident evidence records</caption>
        <thead>
          <tr className="border-b border-border text-[10px] uppercase tracking-wider text-slate-500">
            <Th label="Evidence ID" />
            <Th label="Incident ID" />
            <SortTh label="Captured at" active={sort === 'captured_at'} order={order} onClick={() => onSort('captured_at')} />
            <SortTh label="Camera" active={sort === 'camera'} order={order} onClick={() => onSort('camera')} />
            <Th label="Track" />
            <Th label="Type" />
            <Th label="Hash" />
            <SortTh label="Integrity" active={sort === 'integrity'} order={order} onClick={() => onSort('integrity')} />
            <Th label="Anchor" />
            <Th label="Last Verified" />
            <Th label="Status" />
          </tr>
        </thead>
        <tbody>
          {records.map(r => {
            const integrity = TONE[toneForIntegrity(r.integrity)]
            return (
              <tr
                key={r.evidenceId}
                onClick={() => onSelect(r)}
                onKeyDown={e => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault()
                    onSelect(r)
                  }
                }}
                tabIndex={0}
                className="cursor-pointer border-b border-white/[0.04] transition-colors last:border-0 hover:bg-white/[0.03] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-cyan-500/60"
                aria-label={`Evidence ${r.evidenceId}, integrity ${r.integrity.toLowerCase()}`}
              >
                <td className="py-2 pl-3 pr-2">
                  <span className="flex items-center gap-2">
                    <span className={clsx('h-6 w-0.5 rounded-full', integrity.dot)} aria-hidden />
                    <span className="font-mono text-[11px] text-slate-200">{r.evidenceId}</span>
                  </span>
                </td>
                <td className="px-2 py-2 font-mono text-[11px] text-slate-400">{r.incidentId}</td>
                <td className="px-2 py-2 font-mono text-[11px] text-slate-400 tabular-nums">{formatClock(r.capturedAt)}</td>
                <td className="px-2 py-2 font-mono text-[11px] text-slate-200">{r.cameraId}</td>
                <td className="px-2 py-2 font-mono text-[11px] text-slate-400">{r.trackId ?? '—'}</td>
                <td className="px-2 py-2 text-[11px] text-slate-400">{humanize(r.type)}</td>
                <td className="px-2 py-2">
                  <HashCell hash={r.recordedHash} />
                </td>
                <td className={clsx('px-2 py-2 font-mono text-[11px]', integrity.text)}>{r.integrity}</td>
                <td className={clsx('px-2 py-2 font-mono text-[11px]', r.anchor?.state ? TONE[toneForAnchor(r.anchor.state)].text : 'text-slate-500')}>
                  {r.anchor?.state ?? '—'}
                </td>
                <td className="px-2 py-2 font-mono text-[10px] text-slate-500 tabular-nums">
                  {r.lastVerifiedAt ? formatClock(r.lastVerifiedAt) : '—'}
                </td>
                <td className={clsx('px-2 py-2 pr-3 font-mono text-[11px]', TONE[toneForRecordStatus(r.status)].text)}>
                  {r.status.replace('_', ' ')}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

function Th({ label }: { label: string }) {
  return <th scope="col" className="px-2 py-2 font-medium first:pl-3 last:pr-3">{label}</th>
}

function SortTh({
  label,
  active,
  order,
  onClick,
}: {
  label: string
  active: boolean
  order: 'asc' | 'desc'
  onClick: () => void
}) {
  return (
    <th scope="col" aria-sort={active ? (order === 'asc' ? 'ascending' : 'descending') : 'none'} className="px-2 py-2">
      <button
        onClick={e => {
          e.stopPropagation()
          onClick()
        }}
        className="inline-flex items-center gap-1 font-medium uppercase hover:text-slate-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/60 rounded"
        aria-label={`Sort by ${label.toLowerCase()}`}
      >
        {label}
        {active &&
          (order === 'asc' ? <ArrowUp size={11} aria-hidden /> : <ArrowDown size={11} aria-hidden />)}
      </button>
    </th>
  )
}

function HashCell({ hash }: { hash: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <span className="inline-flex items-center gap-1 font-mono text-[11px] text-slate-400" title={hash}>
      {truncateHash(hash)}
      <button
        onClick={e => {
          e.stopPropagation()
          copyText(hash).then(ok => {
            if (!ok) return
            setCopied(true)
            setTimeout(() => setCopied(false), 1500)
          })
        }}
        className="rounded p-0.5 text-slate-600 hover:text-cyan-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/60"
        aria-label="Copy full hash"
        title="Copy full hash"
      >
        {copied ? <Check size={11} aria-hidden /> : <Copy size={11} aria-hidden />}
      </button>
      {copied && <span className="text-[10px] text-slate-500">Copied</span>}
    </span>
  )
}

async function copyText(text: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(text)
    return true
  } catch {
    return false
  }
}
