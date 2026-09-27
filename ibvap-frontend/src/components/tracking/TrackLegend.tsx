// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 6 — Track Legend. Neutral hues: a class is an observation,
// never a severity — PERSON/VEHICLE/ANIMAL never imply threat (§41, §121).
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'
import type { DetectionClass, TrackStatus, TrackContinuityQuality } from '@/types/tracking'
import { TRACK_CLASS_STROKE, TRACK_CLASS_CHIP } from './trackTone'
import { toneForStatus, toneForQuality, dotTone, textTone } from './trackTone'

/**
 * Legend for overlay class colors. Neutral hues: a class is an observation,
 * never a severity — PERSON/VEHICLE/ANIMAL never imply threat (§41, §121).
 */
export function TrackLegend({ className }: { className?: string }) {
  const classItems: { cls: DetectionClass; label: string }[] = [
    { cls: 'PERSON', label: 'Person' },
    { cls: 'VEHICLE', label: 'Vehicle' },
    { cls: 'ANIMAL', label: 'Animal' },
    { cls: 'OBJECT', label: 'Object' },
    { cls: 'UNKNOWN', label: 'Unknown' },
  ]
  const statusItems: { status: TrackStatus; label: string }[] = [
    { status: 'ACTIVE', label: 'Active' },
    { status: 'TENTATIVE', label: 'Tentative' },
    { status: 'LOST', label: 'Lost' },
    { status: 'REACQUIRED', label: 'Reacquired' },
    { status: 'ENDED', label: 'Ended' },
    { status: 'STALE', label: 'Stale' },
    { status: 'INVALID', label: 'Invalid' },
    { status: 'UNKNOWN', label: 'Unknown' },
  ]
  const qualityItems: { quality: TrackContinuityQuality; label: string }[] = [
    { quality: 'STRONG', label: 'Strong' },
    { quality: 'MODERATE', label: 'Moderate' },
    { quality: 'WEAK', label: 'Weak' },
    { quality: 'UNKNOWN', label: 'Unknown' },
  ]

  return (
    <div className={clsx('flex flex-wrap items-center gap-x-4 gap-y-1.5', className)} aria-label="Tracking legend">
      <div className="flex items-center gap-x-4 gap-y-1.5">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Class</span>
        {classItems.map(i => (
          <span key={i.cls} className="flex items-center gap-1.5 text-[10px] text-slate-500">
            <span className="inline-block h-2 w-3.5 rounded-[2px]" style={{ backgroundColor: TRACK_CLASS_STROKE[i.cls] }} aria-hidden />
            {i.label} {TRACK_CLASS_CHIP[i.cls] && <span className="font-mono text-slate-400">({TRACK_CLASS_CHIP[i.cls]})</span>}
          </span>
        ))}
      </div>
      <div className="flex items-center gap-x-4 gap-y-1.5 ml-4">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Status</span>
        {statusItems.map(i => (
          <span key={i.status} className="flex items-center gap-1.5 text-[10px] text-slate-500">
            <span className={clsx('h-1.5 w-1.5 rounded-full', dotTone(toneForStatus(i.status)))} aria-hidden />
            {i.label}
          </span>
        ))}
      </div>
      <div className="flex items-center gap-x-4 gap-y-1.5 ml-4">
        <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-500">Quality</span>
        {qualityItems.map(i => (
          <span key={i.quality} className="flex items-center gap-1.5 text-[10px] text-slate-500">
            <span className={clsx('h-1.5 w-1.5 rounded-full', dotTone(toneForQuality(i.quality)))} aria-hidden />
            {i.label}
          </span>
        ))}
      </div>
      <span className="text-[10px] text-slate-600 ml-4">tracks shown are continuity hypotheses, not identities</span>
    </div>
  )
}