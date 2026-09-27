import { clsx } from 'clsx'
import type { CameraHealth } from '@/types/cameraHealth'
import { TONE, VIEWPOINT_LABEL, toneForViewpoint } from './healthTone'
import { formatAge } from './healthFormat'

/**
 * Viewpoint block. Renders the backend verdict only: stable / shift /
 * severe / unknown. Wording never asserts intent (wind, mount, deliberate
 * movement are indistinguishable here) and never claims auto-correction.
 */
export function ViewpointStability({ viewpoint, nowMs }: {
  viewpoint: CameraHealth['viewpoint']
  nowMs: number
}) {
  const tone = TONE[toneForViewpoint(viewpoint.status)]
  const shifted = viewpoint.status === 'SHIFT_DETECTED' || viewpoint.status === 'SEVERE_SHIFT'

  return (
    <div className="py-1" role={shifted ? 'alert' : undefined}>
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-[11px] text-slate-500">Viewpoint</span>
        <span className={clsx('font-mono text-[11px] uppercase', tone.text)}>
          {VIEWPOINT_LABEL[viewpoint.status]}
        </span>
      </div>
      {viewpoint.shiftScore !== null && (
        <div className="mt-0.5 flex justify-between font-mono text-[10px] text-slate-600 tabular-nums">
          <span>shift score</span>
          <span>{viewpoint.shiftScore.toFixed(2)}</span>
        </div>
      )}
      {viewpoint.detectedAt && (
        <div className="mt-0.5 flex justify-between font-mono text-[10px] text-slate-600 tabular-nums">
          <span>detected</span>
          <span>{formatAge(viewpoint.detectedAt, nowMs)}</span>
        </div>
      )}
      {shifted && viewpoint.fenceConfidenceNote && (
        <p className="mt-1 text-[11px] text-slate-400">
          Potential impact: {viewpoint.fenceConfidenceNote}. The fence was NOT auto-corrected.
        </p>
      )}
    </div>
  )
}
