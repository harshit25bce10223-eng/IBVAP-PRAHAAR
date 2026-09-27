// ─────────────────────────────────────────────────────────────────────────────
// HumanAnimalCard — compact operational context (spec §19).
//
// Demonstrates why animal differentiation exists: wildlife movement in forest /
// hilly border environments must not raise unnecessary intrusion alerts. Full
// detailed page is not part of the six primary PPT screenshots.
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'
import { PawPrint, User } from 'lucide-react'
import type { HumanAnimalCardData, HumanAnimalClassification } from '@/types'

interface Props {
  data: HumanAnimalCardData
  className?: string
}

export function HumanAnimalCard({ data, className }: Props) {
  return (
    <div className={clsx('flex flex-col min-h-0 rounded-md border border-ssb-border/70 bg-ssb-navy-deep', className)}>
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-ssb-border/40 flex-shrink-0">
        <span className="text-[10px] font-semibold tracking-[0.16em] text-ssb-text-muted uppercase">
          {data.title}
        </span>
        <span className="text-[9px] font-mono text-ssb-green-bright">{data.cameraId}</span>
      </div>

      {/* Classifications */}
      <div className="flex-1 flex flex-col justify-center gap-2.5 px-3 py-2.5">
        {data.results.map(r => (
          <ClassificationRow key={r.kind} result={r} />
        ))}
      </div>

      {/* Purpose footnote */}
      <p className="text-[8px] text-ssb-text-muted/50 px-3 pb-2 leading-relaxed italic">
        {data.purpose}
      </p>
    </div>
  )
}

function ClassificationRow({ result }: { result: HumanAnimalClassification }) {
  const isAnimal = result.kind === 'ANIMAL'
  const Icon = isAnimal ? PawPrint : User
  const outcomeColor = isAnimal ? 'text-ssb-green-bright' : 'text-ssb-amber-bright'

  return (
    <div className="flex items-center gap-2.5">
      <div className={clsx(
        'flex h-7 w-7 items-center justify-center rounded flex-shrink-0',
        isAnimal ? 'bg-ssb-green/20' : 'bg-ssb-amber/20'
      )}>
        <Icon size={14} className={isAnimal ? 'text-ssb-green-bright' : 'text-ssb-amber-bright'} aria-hidden />
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-semibold text-ssb-white">{result.kind}</span>
          <span className="text-[10px] font-mono text-ssb-text-muted">{result.confidence}%</span>
        </div>
        <span className={clsx('text-[9px] font-medium', outcomeColor)}>{result.outcome}</span>
      </div>
    </div>
  )
}