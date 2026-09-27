import { clsx } from 'clsx'
import type { OperationalImpact } from '@/types/cameraHealth'

const LEVEL_TONE = {
  NONE: 'text-slate-500',
  MINOR: 'text-slate-300',
  DEGRADED: 'text-prhaar-degraded',
  COMPROMISED: 'text-prhaar-failed',
  UNKNOWN: 'text-slate-400',
} as const

/**
 * "So what?" block. Coverage state comes from the backend — the frontend
 * never decides when degradation becomes COMPROMISED.
 */
export function CoverageImpact({ impact }: { impact: OperationalImpact }) {
  return (
    <div className="py-1" role={impact.level === 'COMPROMISED' ? 'alert' : undefined}>
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-[11px] text-slate-500">Operational impact</span>
        <span className={clsx('font-mono text-[11px] uppercase', LEVEL_TONE[impact.level])}>
          {impact.level === 'NONE' ? 'No impact' : impact.level}
        </span>
      </div>
      {impact.coverage !== 'NORMAL' && (
        <p className={clsx(
          'mt-0.5 font-mono text-[10px] uppercase',
          impact.coverage === 'COMPROMISED' ? 'text-prhaar-failed'
          : impact.coverage === 'DEGRADED' ? 'text-prhaar-degraded'
          : 'text-slate-500'
        )}>
          Coverage: {impact.coverage}
        </p>
      )}
      {impact.message && (
        <p className="mt-0.5 text-[11px] text-slate-400">{impact.message}</p>
      )}
      {impact.affectedModules.length > 0 && (
        <p className="mt-0.5 font-mono text-[10px] text-slate-600">
          affects {impact.affectedModules.join(', ')}
        </p>
      )}
    </div>
  )
}
