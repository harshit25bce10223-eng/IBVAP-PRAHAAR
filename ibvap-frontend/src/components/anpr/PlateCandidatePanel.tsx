// PlateCandidatePanel.tsx — Ranked OCR candidate list
import { clsx } from 'clsx'
import type { PlateCandidate } from '@/types/anpr'

interface PlateCandidatePanelProps {
  candidates: PlateCandidate[]
  className?: string
}

function confidenceBar(c: number): string {
  const filled = Math.round(c * 10)
  const empty = 10 - filled
  return '█'.repeat(filled) + '░'.repeat(empty)
}

function confColor(c: number): string {
  if (c >= 0.8) return 'text-emerald-400'
  if (c >= 0.5) return 'text-amber-400'
  return 'text-red-400'
}

export function PlateCandidatePanel({ candidates, className }: PlateCandidatePanelProps) {
  if (!candidates.length) {
    return (
      <div className={clsx('rounded-lg border border-border bg-bg p-3', className)}>
        <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500 mb-2">Candidate Reads</div>
        <div className="text-slate-600 text-xs font-mono italic">No OCR candidates available</div>
      </div>
    )
  }

  return (
    <div className={clsx('rounded-lg border border-border bg-bg p-3', className)}>
      <div className="text-[10px] font-mono uppercase tracking-wider text-slate-500 mb-2">Candidate Reads</div>
      <div className="space-y-1.5">
        {candidates.map(c => (
          <div key={c.rank} className="flex items-center gap-3 font-mono text-xs">
            <span className="text-slate-600 w-3">{c.rank}.</span>
            <span className="text-slate-200 w-28 truncate">{c.normalizedRead ?? c.rawRead}</span>
            <span className={clsx('w-9 text-right', confColor(c.confidence))}>
              {Math.round(c.confidence * 100)}%
            </span>
            <span className={clsx('text-[10px] tracking-tighter', confColor(c.confidence))}>
              {confidenceBar(c.confidence)}
            </span>
          </div>
        ))}
      </div>
      <p className="mt-2 text-[9px] text-slate-600 font-mono uppercase tracking-wider">
        Decision-support only — not an identity confirmation
      </p>
    </div>
  )
}