import { ArrowRight, Camera, CheckCircle2, Database, FileText, Layers, ShieldCheck, Video } from 'lucide-react'
import { clsx } from 'clsx'

interface ProvenanceChainProps {
  chain: string[]
  evidenceId: string
  className?: string
}

function getIconForStep(step: string) {
  const s = step.toUpperCase()
  if (s.startsWith('CAM') || s.includes('CAMERA')) return Camera
  if (s.includes('FRAME') || s.includes('SNAPSHOT')) return Video
  if (s.includes('EVENT') || s.includes('DETECTION')) return Layers
  if (s.includes('INCIDENT')) return FileText
  if (s.includes('EVIDENCE') || s.includes('PACKAGE')) return Database
  if (s.includes('HASH') || s.includes('LEDGER') || s.includes('ANCHOR')) return ShieldCheck
  return CheckCircle2
}

export function ProvenanceChain({ chain, evidenceId, className }: ProvenanceChainProps) {
  if (!chain || chain.length === 0) {
    return (
      <div className={clsx('rounded-lg border border-white/5 bg-white/[0.02] p-3 text-[11px] text-slate-500', className)}>
        <p className="font-mono text-slate-400">PROVENANCE NOT RECORDED</p>
        <p className="mt-0.5 text-slate-600">
          Source chain was unavailable at ingest time. The system records origin as unknown rather than synthesizing lineage.
        </p>
      </div>
    )
  }

  return (
    <div className={clsx('space-y-2', className)}>
      <div className="flex items-center justify-between text-[10px] uppercase tracking-wider text-slate-500">
        <span>Capture-to-Ledger Custody Chain</span>
        <span className="font-mono text-slate-400">{chain.length} stages</span>
      </div>

      <div className="flex flex-wrap items-center gap-1.5 rounded-lg border border-border bg-bg p-2.5">
        {chain.map((step, idx) => {
          const Icon = getIconForStep(step)
          const isLast = idx === chain.length - 1

          return (
            <div key={`${step}-${idx}`} className="flex items-center gap-1.5">
              <div
                className={clsx(
                  'flex items-center gap-1.5 rounded px-2 py-1 font-mono text-[11px] transition-colors',
                  isLast
                    ? 'border border-cyan-500/40 bg-cyan-500/10 text-cyan-300 font-semibold shadow-sm shadow-cyan-500/20'
                    : 'border border-white/10 bg-white/[0.03] text-slate-300'
                )}
              >
                <Icon className={clsx('h-3 w-3', isLast ? 'text-cyan-400' : 'text-slate-400')} />
                <span>{step}</span>
              </div>
              {!isLast && (
                <ArrowRight className="h-3 w-3 text-slate-600 shrink-0" />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
