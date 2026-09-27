import type { CorrelationSource } from '@/types/eventCorrelation'

const SOURCE_LABEL: Record<CorrelationSource, string> = {
  VIRTUAL_FENCE: 'FENCE',
  DETECTION: 'DETECTION',
  TRACKING: 'TRACKING',
  ANPR: 'ANPR',
  AUDIO: 'AUDIO',
  SURFACE_ANOMALY: 'SURFACE',
  SUSPICIOUS_ACTIVITY: 'ACTIVITY',
  RE_ID: 'RE-ID',
  CAMERA_HEALTH: 'HEALTH',
  SYSTEM: 'SYSTEM',
  UNKNOWN: 'UNKNOWN',
}

/**
 * Compact source legend (§51). Deliberately subtle — neutral labels, no
 * decorative icons. Only sources actually present in the fixtures render.
 */
export function SourceLegend({ sources }: { sources: CorrelationSource[] }) {
  const present = [...new Set(sources)]
  if (present.length === 0) return null
  return (
    <div className="flex flex-wrap items-center gap-x-3 gap-y-1" aria-label="Signal sources">
      {present.map(s => (
        <span key={s} className="inline-flex items-center gap-1.5 font-mono text-[9px] uppercase tracking-widest text-slate-500">
          <span className="h-1 w-1 rounded-full bg-slate-600" aria-hidden />
          {SOURCE_LABEL[s]}
        </span>
      ))}
    </div>
  )
}