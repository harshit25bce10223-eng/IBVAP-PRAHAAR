import { clsx } from 'clsx'
import type { DetectionClass } from '@/types/detection'
import { CLASS_STROKE } from './detectionTone'

/**
 * Legend for overlay class colors. Neutral hues: a class is an observation,
 * never a severity — PERSON/VEHICLE/ANIMAL never imply threat (§20/§179).
 */
export function DetectionLegend({ className }: { className?: string }) {
  const items: { cls: DetectionClass; label: string }[] = [
    { cls: 'PERSON', label: 'Person' },
    { cls: 'VEHICLE', label: 'Vehicle' },
    { cls: 'ANIMAL', label: 'Animal' },
    { cls: 'OBJECT', label: 'Object' },
    { cls: 'UNKNOWN', label: 'Unknown' },
  ]
  return (
    <div className={clsx('flex flex-wrap items-center gap-x-4 gap-y-1.5', className)} aria-label="Detection legend">
      {items.map(i => (
        <span key={i.cls} className="flex items-center gap-1.5 text-[10px] text-slate-500">
          <span className="inline-block h-2 w-3.5 rounded-[2px]" style={{ backgroundColor: CLASS_STROKE[i.cls] }} aria-hidden />
          {i.label}
        </span>
      ))}
      <span className="text-[10px] text-slate-600">classes shown are observations, not risks</span>
    </div>
  )
}