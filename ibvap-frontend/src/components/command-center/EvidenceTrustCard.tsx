// ─────────────────────────────────────────────────────────────────────────────
// EvidenceTrustCard — compact trust + security indicator (spec §23, §24).
//
// Reminds the reviewer the platform does not only detect — it also protects
// evidence. Compact, not a full Evidence Vault (that is Component 3).
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'
import { FileCheck2, ShieldCheck } from 'lucide-react'
import type { EvidenceTrustInfo } from '@/types'

interface Props {
  data: EvidenceTrustInfo
  className?: string
}

export function EvidenceTrustCard({ data, className }: Props) {
  return (
    <div className={clsx('flex gap-2 min-h-0 rounded-md border border-ssb-border/70 bg-ssb-navy-deep', className)}>
      {/* Evidence block */}
      <div className="flex-1 flex items-center gap-2 px-3 py-2 min-w-0">
        <FileCheck2 size={14} className="text-ssb-green-bright flex-shrink-0" aria-hidden />
        <div className="min-w-0 leading-tight">
          <span className="block text-[9px] font-semibold tracking-[0.16em] text-ssb-text-muted uppercase">
            Evidence
          </span>
          <span className="block text-[10px] text-ssb-green-bright font-medium">{data.state}</span>
          <span className="block text-[9px] font-mono text-ssb-text-muted/70">
            {data.algorithm} · {data.ledger}
          </span>
        </div>
      </div>

      {/* Security chips */}
      <div className="flex items-center gap-1.5 px-3 py-2 border-l border-ssb-border/40">
        <ShieldCheck size={14} className="text-ssb-green-bright flex-shrink-0" aria-hidden />
        <div className="flex flex-col gap-0.5">
          {data.security.map(s => (
            <span key={s.label} className="flex items-center gap-1.5 text-[9px]">
              <span className={s.ok ? 'text-ssb-green-bright' : 'text-ssb-red-bright'}>
                {s.ok ? '✓' : '✗'}
              </span>
              <span className="text-ssb-text-muted font-mono tracking-wider">{s.label}</span>
            </span>
          ))}
        </div>
      </div>
    </div>
  )
}