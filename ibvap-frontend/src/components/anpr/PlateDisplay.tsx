// PlateDisplay.tsx — Top OCR candidate display with quality badge
import { clsx } from 'clsx'
import { Badge } from '@/components/ui'
import type { PlateRead, PlateCandidate, PlateQuality, PlateFormatStatus } from '@/types/anpr'

interface PlateDisplayProps {
  plateRead: PlateRead | null
  candidates: PlateCandidate[]
  className?: string
}

function qualityVariant(q: PlateQuality): 'safe' | 'warning' | 'critical' | 'offline' | 'default' {
  switch (q) {
    case 'GOOD': return 'safe'
    case 'FAIR': return 'warning'
    case 'POOR':
    case 'UNREADABLE':
    case 'OCCLUDED':
    case 'EXTREME_ANGLE': return 'critical'
    case 'PARTIAL':
    case 'GLARE':
    case 'MOTION_BLUR':
    case 'DIRTY':
    case 'LOW_LIGHT': return 'warning'
    case 'UNKNOWN': return 'offline'
    default: return 'default'
  }
}

function qualityLabel(q: PlateQuality): string {
  return q.replace(/_/g, ' ')
}

function formatStatusLabel(f: PlateFormatStatus): string {
  return f.replace(/_/g, ' ')
}

function confidencePct(c: number): string {
  return Math.round(c * 100) + '%'
}

export function PlateDisplay({ plateRead, candidates, className }: PlateDisplayProps) {
  if (!plateRead) {
    return (
      <div className={clsx('rounded-lg border border-[#1e2d40] bg-[#080c12] p-3', className)}>
        <div className="flex items-center justify-between mb-2">
          <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500">Top OCR Candidate</span>
          <Badge variant="critical">UNREADABLE</Badge>
        </div>
        <div className="text-slate-500 font-mono text-sm italic">
          No plate read — image quality insufficient
        </div>
      </div>
    )
  }

  const topCandidate = candidates[0] ?? null
  const conf = topCandidate?.confidence ?? plateRead.confidence

  return (
    <div className={clsx('rounded-lg border border-[#1e2d40] bg-[#080c12] p-3 space-y-2', className)}>
      <div className="flex items-center justify-between">
        <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500">Top OCR Candidate</span>
        <Badge variant={qualityVariant(plateRead.quality)}>{qualityLabel(plateRead.quality)}</Badge>
      </div>

      <div className="flex items-baseline gap-3">
        <span className="font-mono text-xl font-bold text-ssb-green-bright tracking-widest">
          {plateRead.displayRead}
        </span>
        <span className={clsx(
          'text-sm font-mono font-semibold',
          conf >= 0.8 ? 'text-emerald-400' : conf >= 0.5 ? 'text-amber-400' : 'text-red-400'
        )}>
          {confidencePct(conf)}
        </span>
      </div>

      <dl className="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px] font-mono">
        <div>
          <dt className="text-slate-600 uppercase text-[9px]">Raw</dt>
          <dd className="text-slate-400">{plateRead.rawRead}</dd>
        </div>
        <div>
          <dt className="text-slate-600 uppercase text-[9px]">Normalized</dt>
          <dd className="text-slate-300">{plateRead.normalizedRead ?? '—'}</dd>
        </div>
        <div className="col-span-2">
          <dt className="text-slate-600 uppercase text-[9px]">Format</dt>
          <dd className="text-slate-400">{formatStatusLabel(plateRead.formatStatus)}</dd>
        </div>
      </dl>
    </div>
  )
}