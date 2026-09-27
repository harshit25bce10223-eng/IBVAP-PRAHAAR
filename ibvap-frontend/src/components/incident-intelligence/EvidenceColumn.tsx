// ─────────────────────────────────────────────────────────────────────────────
// EvidenceColumn — evidence integrity + blockchain process (Incident
// Intelligence, right).
//
// Evidence record, an evidence-integrity pipeline (Incident → … → Transaction
// Verified) and the re-ID / camera-chain context. No fake glowing blockchain
// graphics — a restrained, process-oriented visual (spec §6, §7, §9).
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'
import type { IncidentIntelligenceData } from '@/types'

interface Props {
  data: IncidentIntelligenceData
  className?: string
}

export function EvidenceColumn({ data, className }: Props) {
  const ev = data.evidence
  return (
    <div className={clsx('flex h-full min-h-0 flex-col rounded-md border border-ssb-border/70 bg-ssb-navy/60 p-3', className)}>
      <div className="flex items-start justify-between gap-2 flex-shrink-0">
        <div>
          <h2 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-ssb-white">
            Evidence Trust
          </h2>
          <p className="text-[9.5px] text-ssb-text-muted mt-0.5">
            Integrity process for the incident record
          </p>
        </div>
        <span className="flex-shrink-0 rounded border border-ssb-green-bright/40 bg-ssb-green/15 px-1.5 py-0.5 text-[10px] font-mono font-bold text-ssb-green-bright">
          {ev.evidenceId}
        </span>
      </div>

      {/* Evidence record details */}
      <dl className="mt-3 grid grid-cols-[110px_1fr] gap-x-2 gap-y-1.5 flex-shrink-0">
        <dt className="text-[9.5px] uppercase tracking-wider text-ssb-text-muted/80">Camera</dt>
        <dd className="text-[10.5px] font-mono text-ssb-text">{ev.cameraId}</dd>
        <dt className="text-[9.5px] uppercase tracking-wider text-ssb-text-muted/80">Timestamp</dt>
        <dd className="text-[10.5px] font-mono text-ssb-text">{ev.timestamp}</dd>
        <dt className="text-[9.5px] uppercase tracking-wider text-ssb-text-muted/80">Media</dt>
        <dd className="text-[10.5px] text-ssb-text">{ev.media}</dd>
        <dt className="text-[9.5px] uppercase tracking-wider text-ssb-text-muted/80">SHA-256</dt>
        <dd className="text-[10.5px] font-mono text-ssb-amber-bright">{ev.sha256}</dd>
        <dt className="text-[9.5px] uppercase tracking-wider text-ssb-text-muted/80">Ledger TX</dt>
        <dd className="text-[10.5px] font-mono text-ssb-text">{ev.ledgerTx}</dd>
        <dt className="text-[9.5px] uppercase tracking-wider text-ssb-text-muted/80">Integrity</dt>
        <dd className="text-[10.5px] font-mono font-semibold text-ssb-green-bright">{ev.integrity}</dd>
        <dt className="text-[9.5px] uppercase tracking-wider text-ssb-text-muted/80">Chain of Custody</dt>
        <dd className="text-[10.5px] font-mono font-semibold text-ssb-green-bright">{ev.custody}</dd>
      </dl>

      {/* Re-ID / camera-chain context */}
      <div className="mt-3 flex-shrink-0 rounded border border-ssb-border/60 bg-ssb-navy-deep/50 px-2 py-1.5">
        <div className="flex items-center gap-2">
          <span className="text-[9px] font-semibold uppercase tracking-wider text-ssb-text-muted">Re-ID</span>
          <span className="text-[10px] font-mono text-ssb-text">{data.reId.trackId}</span>
          <span className="text-[10px] text-ssb-text-muted">{data.reId.cameraChain}</span>
          <span className="text-[10px] text-ssb-text">{data.reId.relationLabel}</span>
          <span className="ml-auto text-[10px] font-mono font-semibold text-ssb-white">
            {data.reId.confidencePct}% Candidate Confidence
          </span>
        </div>
        <p className="mt-0.5 text-[8.5px] text-ssb-text-muted/70">
          Not yet "confirmed same person" — production re-ID model pending.
        </p>
      </div>

      {/* Evidence integrity pipeline */}
      <div className="mt-3 flex-1 min-h-0 flex flex-col">
        <span className="text-[9px] font-semibold uppercase tracking-[0.14em] text-ssb-text-muted/80 flex-shrink-0">
          Evidence Integrity Process
        </span>
        <ol className="mt-2 flex-1 min-h-0 flex flex-col justify-between">
          {data.pipeline.map((p, i) => (
            <li key={p.label} className="flex items-center gap-2">
              <span
                className={clsx(
                  'flex h-4 w-4 flex-shrink-0 items-center justify-center rounded-full border text-[8px] font-bold',
                  p.verified
                    ? 'border-ssb-green-bright/60 bg-ssb-green/20 text-ssb-green-bright'
                    : 'border-ssb-border/60 text-ssb-text-muted'
                )}
              >
                {p.verified ? '✓' : String(i + 1)}
              </span>
              <span className="flex-1 min-w-0">
                <span className="block truncate text-[10px] font-medium text-ssb-text">{p.label}</span>
                <span className="block text-[8.5px] text-ssb-text-muted/70">{p.detail}</span>
              </span>
              {i < data.pipeline.length - 1 && (
                <span className="h-px w-2 flex-shrink-0 bg-ssb-border/60" />
              )}
              {i === data.pipeline.length - 1 && (
                <span className="rounded border border-ssb-green-bright/40 bg-ssb-green/15 px-1.5 py-0.5 text-[8px] font-mono font-bold text-ssb-green-bright">
                  VERIFIED
                </span>
              )}
            </li>
          ))}
        </ol>
      </div>

      {/* Security context footer */}
      <div className="mt-2 flex items-center gap-3 border-t border-ssb-border/60 pt-2 flex-shrink-0">
        {data.security.map(s => (
          <span key={s.label} className="flex items-center gap-1 text-[9px] font-mono text-ssb-text-muted">
            <span className="text-ssb-green-bright">{s.ok ? '✓' : '✗'}</span>
            {s.label}
          </span>
        ))}
        <span className="ml-auto text-[8.5px] italic text-ssb-text-muted/60">Integrity sealed on ledger</span>
      </div>
    </div>
  )
}