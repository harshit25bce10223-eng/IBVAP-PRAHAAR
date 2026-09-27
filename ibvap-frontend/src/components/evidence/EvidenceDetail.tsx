import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Check, Copy, ShieldAlert } from 'lucide-react'
import { clsx } from 'clsx'
import { Button } from '@/components/ui'
import { formatClock } from '@/components/camera-health/healthFormat'
import { useEvidenceStore } from '@/store/evidenceState'
import type { EvidenceRecord } from '@/types/evidence'
import {
  INTEGRITY_BLURB,
  TONE,
  toneForAnchor,
  toneForIntegrity,
  toneForRecordStatus,
  toneForSync,
} from './evidenceTone'
import { formatBytes, formatDuration, humanize } from './evidenceFormat'
import { ProvenanceChain } from './ProvenanceChain'

/**
 * Drawer body for one evidence record. Read-only with respect to the
 * original: hashes, capture time and source have no editing controls.
 * Officer notes live in local component state, visually separated under
 * OFFICER NOTE — never merged into the record model.
 */
export function EvidenceDetail({ record }: { record: EvidenceRecord }) {
  const verifyState = useEvidenceStore(s => s.verifyStates[record.evidenceId] ?? 'idle')
  const verifyResult = useEvidenceStore(s => s.verifyResults[record.evidenceId])
  const verifyError = useEvidenceStore(s => s.verifyErrors[record.evidenceId] ?? '')
  const verifyRecord = useEvidenceStore(s => s.verifyRecord)
  const requestExport = useEvidenceStore(s => s.requestExport)
  const [exportMsg, setExportMsg] = useState<string | null>(null)
  const [exportBusy, setExportBusy] = useState(false)
  const [note, setNote] = useState('')
  const [savedNote, setSavedNote] = useState<string | null>(null)

  const integrityTone = TONE[toneForIntegrity(record.integrity)]
  const mismatch = record.integrity === 'MISMATCH'

  return (
    <div className="space-y-4 text-[12px]" key={record.evidenceId}>
      {/* Identity */}
      <div>
        <div className="flex items-center justify-between gap-2">
          <span className="font-mono text-sm text-slate-100">{record.evidenceId}</span>
          <span className={clsx('font-mono text-[11px]', integrityTone.text)}>{record.integrity}</span>
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5 font-mono text-[11px] text-slate-500">
          <span title="Incident reference">{record.incidentId}</span>
          <Link
            to={`/camera/${record.cameraId}`}
            className="text-cyan-400 hover:text-cyan-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/60 rounded"
          >
            {record.cameraId} →
          </Link>
          <span>{humanize(record.type)}</span>
          <span>{formatClock(record.capturedAt)}</span>
        </div>
        <p className="mt-1 text-[11px] text-slate-600">{INTEGRITY_BLURB[record.integrity]}</p>
      </div>

      {/* Role banner for anything that is not the original capture */}
      {record.role !== 'ORIGINAL' && record.role !== 'ORIGINAL_CAPTURE' && (
        <p role="note" className="rounded-md border border-amber-500/30 bg-amber-500/5 px-2.5 py-2 text-[11px] text-amber-200/90">
          <span className="font-mono font-semibold">{humanize(record.role).toUpperCase()}</span>
          {record.roleNote ? ` — ${record.roleNote}` : ' — not the original evidence.'}
        </p>
      )}

      {/* Mismatch callout */}
      {mismatch && (
        <div role="alert" className="rounded-md border border-red-500/40 bg-red-500/5 px-2.5 py-2">
          <p className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-red-400">
            <ShieldAlert size={13} aria-hidden /> Integrity mismatch
          </p>
          <p className="mt-1 text-[11px] text-slate-400">
            Possible causes include corruption, incomplete transfer, an incorrect copy, a storage
            issue, or unauthorized modification. Treat this record as requiring investigation —
            do not delete, overwrite, or re-hash it.
          </p>
        </div>
      )}

      {/* Media */}
      <DetailSection title="Media preview">
        {record.mediaKind === 'none' ? (
          <p className="text-[11px] text-slate-500">
            <span className="font-mono text-slate-300">MEDIA UNAVAILABLE</span>
            {' — hash, metadata, provenance and verification state below remain usable.'}
          </p>
        ) : (
          <dl className="space-y-0.5">
            <KeyRow label="Kind" value={record.mediaKind === 'image' ? 'Still image' : 'Video clip'} />
            {record.mediaDurationSec !== null && <KeyRow label="Duration" value={formatDuration(record.mediaDurationSec)} />}
            {record.codec && <KeyRow label="Container" value={record.codec} />}
            <KeyRow label="File size" value={formatBytes(record.fileSizeBytes)} />
            <p className="pt-1 text-[11px] text-slate-600">
              Preview not embedded in this viewer. Metadata, digest and provenance are authoritative.
            </p>
          </dl>
        )}
      </DetailSection>

      {/* Hash */}
      <DetailSection title="Digest">
        <dl className="space-y-0.5">
          <KeyRow label="Algorithm" value={`${record.hashAlgorithm} (message digest — detects changes; not encryption)`} mono={false} />
        </dl>
        <FullHash hash={record.recordedHash} />
      </DetailSection>

      {/* Ledger / anchor */}
      <DetailSection title="Ledger anchor">
        <dl className="space-y-0.5">
          <KeyRow
            label="Anchor"
            value={record.anchor?.state ?? 'UNKNOWN'}
            valueClass={record.anchor?.state ? TONE[toneForAnchor(record.anchor.state)].text : 'text-slate-500'}
          />
          {record.anchor?.ledgerId && <KeyRow label="Ledger" value={record.anchor.ledgerId} />}
          {record.anchor?.anchoredAt && (
            <KeyRow label="Anchored at" value={formatClock(record.anchor.anchoredAt)} />
          )}
          {record.anchor?.rootValue && (
            <KeyRow label="Root" value={`${record.anchor.rootValue.slice(0, 12)}…${record.anchor.rootValue.slice(-6)}`} />
          )}
          {record.anchor?.recordSequence !== null && record.anchor?.recordSequence !== undefined && (
            <KeyRow label="Sequence" value={String(record.anchor.recordSequence)} />
          )}
          {record.anchor?.treeSize !== null && record.anchor?.treeSize !== undefined && (
            <KeyRow label="Tree size" value={record.anchor.treeSize.toLocaleString('en-IN')} />
          )}
          {!record.anchor?.ledgerId && (
            <p className="pt-0.5 text-[11px] text-slate-600">Anchor status unavailable — no ledger reference supplied.</p>
          )}
        </dl>
      </DetailSection>

      {/* Origin / sync */}
      <DetailSection title="Origin & sync">
        <dl className="space-y-0.5">
          <KeyRow label="Source" value={humanize(record.source)} />
          <KeyRow label="Captured at" value={record.dataSource === 'EDGE' ? 'Edge node' : record.dataSource === 'CENTRAL' ? 'Central ingest' : 'Unknown origin'} />
          <KeyRow
            label="Sync"
            value={humanize(record.syncState)}
            valueClass={TONE[toneForSync(record.syncState)].text}
          />
          {record.syncState === 'SYNC_PENDING' && (
            <p className="pt-0.5 text-[11px] text-amber-200/80">
              Edge capture awaiting central sync — not yet centralized.
            </p>
          )}
          {record.regionProfile && <KeyRow label="Sector profile" value={record.regionProfile} mono={false} />}
          {record.zoneId && <KeyRow label="Zone" value={record.zoneId} />}
        </dl>
      </DetailSection>

      {/* Provenance */}
      <DetailSection title="Provenance">
        <ProvenanceChain chain={record.provenance?.chain ?? []} evidenceId={record.evidenceId} />
      </DetailSection>

      {/* Lifecycle */}
      <DetailSection title="Lifecycle">
        <ol className="divide-y divide-white/[0.04]">
          {record.milestones.map(m => (
            <li key={m.key} className="flex items-baseline justify-between gap-2 py-1">
              <span className="text-[11px] text-slate-400">{m.label}</span>
              <span className="font-mono text-[11px] text-slate-300 tabular-nums">
                {m.at ? formatClock(m.at) : <span className="text-slate-600">NOT AVAILABLE</span>}
              </span>
            </li>
          ))}
        </ol>
      </DetailSection>

      {/* Chain of custody */}
      {record.custody.length > 0 && (
        <DetailSection title="Handling history">
          <ol className="divide-y divide-white/[0.04]">
            {record.custody.map((c, i) => (
              <li key={`${c.stage}-${i}`} className="py-1">
                <div className="flex items-baseline justify-between gap-2">
                  <span className="text-[11px] text-slate-300">{c.stage}</span>
                  <span className="font-mono text-[10px] text-slate-500 tabular-nums">
                    {c.at ? formatClock(c.at) : '—'}
                  </span>
                </div>
                {c.detail && <p className="text-[11px] text-slate-500">{c.detail}</p>}
              </li>
            ))}
          </ol>
        </DetailSection>
      )}

      {/* Verify */}
      <DetailSection title="Integrity verification">
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            isLoading={verifyState === 'verifying'}
            onClick={() => verifyRecord(record.evidenceId)}
          >
            {verifyState === 'verifying' ? 'Verifying…' : 'Verify integrity'}
          </Button>
          {record.lastVerifiedAt && (
            <span className="font-mono text-[10px] text-slate-600 tabular-nums">
              Last run {formatClock(record.lastVerifiedAt)}{record.lastVerifiedBy ? ` · ${record.lastVerifiedBy}` : ''}
            </span>
          )}
        </div>

        {verifyState === 'error' && (
          <p role="alert" className="mt-2 rounded-md border border-amber-500/30 bg-amber-500/5 px-2 py-1.5 text-[11px] text-amber-200/90">
            <span className="font-mono font-semibold">VERIFICATION UNAVAILABLE</span>
            {` — ${verifyError || 'the verifier could not be reached.'} The record is unchanged.`}
          </p>
        )}

        {verifyResult && verifyState === 'done' && (
          <div
            role={verifyResult.outcome === 'MISMATCH' ? 'alert' : 'status'}
            className={clsx(
              'mt-2 rounded-md border px-2.5 py-2',
              verifyResult.outcome === 'MATCH'
                ? 'border-emerald-500/30 bg-emerald-500/5'
                : 'border-red-500/40 bg-red-500/5'
            )}
          >
            <p className={clsx(
              'font-mono text-[11px] font-semibold',
              verifyResult.outcome === 'MATCH' ? 'text-emerald-400' : 'text-red-400'
            )}>
              {verifyResult.outcome === 'MATCH' ? 'INTEGRITY VERIFIED — MATCH' : 'INTEGRITY MISMATCH'}
            </p>
            <dl className="mt-1 space-y-0.5 font-mono text-[11px] break-all">
              <div className="flex gap-2"><dt className="shrink-0 text-slate-500">Recorded:</dt><dd className="text-slate-300">{verifyResult.recordedHash ?? '—'}</dd></div>
              <div className="flex gap-2"><dt className="shrink-0 text-slate-500">Computed:</dt><dd className="text-slate-300">{verifyResult.computedHash ?? '—'}</dd></div>
            </dl>
            <p className="mt-1 text-[11px] text-slate-400">{verifyResult.explanation}</p>
          </div>
        )}

        {record.verificationHistory.length > 0 && (
          <ol className="mt-2 divide-y divide-white/[0.04]">
            {record.verificationHistory.map(h => (
              <li key={h.attemptId} className="flex items-baseline justify-between gap-2 py-1">
                <span className="font-mono text-[10px] text-slate-500 tabular-nums">{formatClock(h.at)}</span>
                <span className={clsx('font-mono text-[10px]', h.result === 'MATCH' ? 'text-emerald-400' : 'text-red-400')}>
                  {h.result}
                </span>
                <span className="truncate text-[11px] text-slate-500">{h.actor}</span>
              </li>
            ))}
          </ol>
        )}
      </DetailSection>

      {/* Export */}
      <DetailSection title="Export">
        <ExportBlock
          record={record}
          busy={exportBusy}
          message={exportMsg}
          onRequest={async () => {
            setExportBusy(true)
            setExportMsg(null)
            try {
              const msg = await requestExport(record.evidenceId)
              setExportMsg(msg)
            } catch (err) {
              setExportMsg(err instanceof Error ? err.message : 'Export request failed.')
            } finally {
              setExportBusy(false)
            }
          }}
        />
      </DetailSection>

      {/* Officer note — local only, never part of the record */}
      <DetailSection title="Officer note">
        <label className="block">
          <span className="sr-only">Add an officer note (kept separate from the original record)</span>
          <textarea
            value={note}
            onChange={e => setNote(e.target.value)}
            rows={2}
            placeholder="Note for the case file — stored separately, never merged into original evidence."
            className="w-full rounded-md border border-white/10 bg-[#080c12] px-2.5 py-1.5 text-xs text-slate-200 placeholder:text-slate-600 focus:border-cyan-400/60 focus:outline-none"
          />
        </label>
        <div className="mt-1.5 flex items-center gap-2">
          <Button size="sm" variant="ghost" disabled={note.trim() === ''} onClick={() => { setSavedNote(note.trim()); setNote('') }}>
            Save note locally
          </Button>
          {savedNote && <span className="text-[11px] text-slate-500">Saved for this session only.</span>}
        </div>
        {savedNote && (
          <p className="mt-1.5 rounded-md border border-white/10 bg-white/[0.02] px-2 py-1.5 text-[11px] text-slate-300">
            <span className="font-mono text-[10px] text-slate-500">OFFICER NOTE — </span>{savedNote}
          </p>
        )}
      </DetailSection>

      {/* Record standing */}
      <p className="font-mono text-[10px] text-slate-600">
        Record standing: <span className={TONE[toneForRecordStatus(record.status)].text}>{record.status.replace('_', ' ')}</span>
        {' · '}Created {formatClock(record.createdAt)}
      </p>
    </div>
  )
}

function DetailSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section aria-label={title} className="border-t border-white/[0.06] pt-3 first:border-0 first:pt-0">
      <h4 className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-slate-400">{title}</h4>
      {children}
    </section>
  )
}

function KeyRow({ label, value, mono = true, valueClass }: { label: string; value: string; mono?: boolean; valueClass?: string }) {
  return (
    <div className="flex items-baseline justify-between gap-2 py-0.5">
      <dt className="shrink-0 text-[11px] text-slate-500">{label}</dt>
      <dd className={clsx('text-right text-[11px] text-slate-200 tabular-nums', mono && 'font-mono', valueClass)}>{value}</dd>
    </div>
  )
}

function FullHash({ hash }: { hash: string }) {
  const [copied, setCopied] = useState(false)
  if (!hash) return <p className="font-mono text-[11px] text-slate-500">HASH NOT AVAILABLE</p>
  return (
    <div className="mt-1 rounded-md border border-white/[0.06] bg-black/30 p-2">
      <p className="font-mono text-[11px] text-slate-300 break-all leading-relaxed">{hash}</p>
      <button
        onClick={() => {
          navigator.clipboard.writeText(hash).then(
            () => {
              setCopied(true)
              setTimeout(() => setCopied(false), 1500)
            },
            () => {}
          )
        }}
        className="mt-1.5 inline-flex items-center gap-1 text-[11px] text-cyan-400 hover:text-cyan-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/60 rounded"
        aria-label="Copy full canonical hash"
      >
        {copied ? <Check size={12} aria-hidden /> : <Copy size={12} aria-hidden />}
        {copied ? 'Copied' : 'Copy full hash'}
      </button>
    </div>
  )
}

function ExportBlock({
  record,
  busy,
  message,
  onRequest,
}: {
  record: EvidenceRecord
  busy: boolean
  message: string | null
  onRequest: () => void
}) {
  return (
    <div>
      <div className="flex items-center gap-2">
        <span className="font-mono text-[11px] text-slate-300">{record.exportState}</span>
        {(record.exportState === 'NONE' || record.exportState === 'FAILED') && (
          <Button size="sm" variant="ghost" isLoading={busy} onClick={onRequest}>
            {record.exportState === 'FAILED' ? 'Retry export request' : 'Request export'}
          </Button>
        )}
      </div>
      {record.exportState === 'READY' && record.exportHash && (
        <dl className="mt-1 space-y-0.5">
          <KeyRow label="Export digest" value={`${record.exportHash.slice(0, 12)}…${record.exportHash.slice(-6)}`} />
          <KeyRow label="Requested" value={record.exportRequestedAt ? formatClock(record.exportRequestedAt) : '—'} />
          <p className="pt-0.5 text-[11px] text-slate-600">
            The export matches the original only if its digest matches the recorded digest above.
          </p>
        </dl>
      )}
      {record.exportState === 'REQUESTED' && (
        <p className="mt-1 text-[11px] text-slate-500">Export requested — the backend prepares the file. This view generates no files.</p>
      )}
      {message && <p role="status" className="mt-1 text-[11px] text-slate-400">{message}</p>}
    </div>
  )
}
