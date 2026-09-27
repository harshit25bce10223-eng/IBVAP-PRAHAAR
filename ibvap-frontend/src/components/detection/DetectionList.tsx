import { clsx } from 'clsx'
import { ChevronRight } from 'lucide-react'
import type { DetectionFeedState, DetectionQuality, DetectionResult, DetectionSource } from '@/types/detection'
import { Badge } from '@/components/ui'
import { formatClock, formatClassLabel, formatConfidence } from './detectionFormat'
import { badgeTone, toneForDetectionState } from './detectionTone'

interface DetectionListProps {
  detections: DetectionResult[]
  selectedId?: string | null
  onSelect?: (detection: DetectionResult) => void
  /** Feed availability so the list can distinguish zero vs unavailable. */
  feedState?: DetectionFeedState
  state?: 'idle' | 'loading' | 'ready' | 'error'
  error?: string | null
  onRetry?: () => void
  /** Hide the camera column (e.g. single-camera context list). */
  hideCamera?: boolean
  /** Empty copy for filtered-vs-zero cases (§172). */
  filtered?: boolean
  className?: string
}

const QUALITY_LABEL: Record<DetectionQuality, string> = {
  GOOD: 'Good',
  LIMITED: 'Limited',
  POOR: 'Poor',
  UNKNOWN: 'Unknown',
}

const SOURCE_LABEL: Record<DetectionSource, string> = {
  EDGE: 'EDGE',
  CENTRAL: 'CENTRAL',
  UNKNOWN: '—',
}

/**
 * Detection list — a table of detection records, not tracks. Rows render
 * confidence only when the backend supplies it (N/A otherwise). Feed states
 * render explicit copy for NO_OBJECTS vs UNAVAILABLE vs filter-empty so the
 * operator never mistakes a zero-object frame for a broken detector (§172).
 */
export function DetectionList({
  detections,
  selectedId,
  onSelect,
  feedState,
  state = 'ready',
  error,
  onRetry,
  hideCamera = false,
  filtered = false,
  className,
}: DetectionListProps) {
  if (state === 'loading') {
    return (
      <div className={clsx('space-y-2', className)} role="status" aria-label="Loading detections">
        {Array.from({ length: 4 }).map((_, i) => (
          <div key={i} className="h-12 animate-pulse rounded-lg border border-white/5 bg-white/[0.02]" />
        ))}
      </div>
    )
  }

  if (state === 'error') {
    return (
      <div className={clsx('rounded-lg border border-red-500/25 bg-red-500/5 px-3 py-4 text-center', className)} role="alert">
        <p className="text-[11px] font-semibold text-red-400">DETECTION DATA UNAVAILABLE</p>
        <p className="mt-1 text-[10px] text-red-300/80">{error ?? 'Detection service could not be reached.'}</p>
        {onRetry && (
          <button onClick={onRetry} className="mt-2 text-[11px] text-cyan-400 underline underline-offset-2 hover:text-cyan-300">
            Retry
          </button>
        )}
      </div>
    )
  }

  if (feedState === 'UNAVAILABLE' || feedState === 'OFFLINE' || feedState === 'UNCONFIGURED') {
    return (
      <div className={clsx('rounded-lg border border-white/10 px-3 py-4 text-center', className)} role="status">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          {feedState === 'UNCONFIGURED' ? 'Detection not configured' : feedState === 'OFFLINE' ? 'Detector offline' : 'Detection unavailable'}
        </p>
        <p className="mt-1 text-[10px] text-slate-500">
          {feedState === 'UNCONFIGURED'
            ? 'This camera has no detector configuration.'
            : 'Inference could not produce output for this camera.'}
        </p>
      </div>
    )
  }

  // Zero-object frame is its own state — never shown as an empty list (§58/§59/S4).
  if (feedState === 'NO_OBJECTS' && detections.length === 0) {
    return (
      <div className={clsx('rounded-lg border border-white/10 px-3 py-4 text-center', className)} role="status">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-emerald-400/80">No objects detected</p>
        <p className="mt-1 text-[10px] text-slate-500">Detector is running and found nothing in the frame.</p>
      </div>
    )
  }

  if (detections.length === 0) {
    return (
      <div className={clsx('rounded-lg border border-white/10 px-3 py-4 text-center', className)} role="status">
        <p className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
          {state === 'idle' ? 'Request pending' : filtered ? 'No detections match these filters' : 'No detections'}
        </p>
        {filtered && <p className="mt-1 text-[10px] text-slate-500">Clear or change the display filters to see results.</p>}
      </div>
    )
  }

  return (
    <ul className={clsx('space-y-1.5', className)} aria-label="Detection list">
      {detections.map(d => {
        const tone = toneForDetectionState(d.state)
        const selected = selectedId === d.detectionId
        return (
          <li key={d.detectionId}>
            <button
              onClick={() => onSelect?.(d)}
              aria-selected={selected}
              aria-label={`${formatClassLabel(d.class)} detection, ${formatConfidence(d.confidence)}${d.state !== 'DETECTED' ? `, ${d.state.toLowerCase()}` : ''}`}
              className={clsx(
                'w-full flex items-center gap-2 rounded-lg border px-2.5 py-2 text-left transition-colors',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/60',
                selected
                  ? 'border-cyan-500/40 bg-cyan-500/5'
                  : 'border-white/[0.06] bg-white/[0.02] hover:border-cyan-400/25 hover:bg-white/[0.04]'
              )}
            >
              <span
                className={clsx(
                  'rounded px-1.5 py-0.5 font-mono text-[10px] font-semibold uppercase',
                  d.class === 'PERSON' && 'bg-sky-500/10 text-sky-300',
                  d.class === 'VEHICLE' && 'bg-amber-500/10 text-amber-300',
                  d.class === 'ANIMAL' && 'bg-emerald-500/10 text-emerald-300',
                  d.class === 'OBJECT' && 'bg-slate-500/10 text-slate-300',
                  d.class === 'UNKNOWN' && 'bg-purple-500/10 text-purple-300'
                )}
              >
                {d.class}
              </span>
              <span className="flex min-w-0 flex-1 flex-col">
                <span className="flex items-center gap-1.5 truncate text-[11px] text-slate-200">
                  {formatClassLabel(d.class)}
                  {d.bbox && <ChevronRight size={10} className="text-slate-600" aria-hidden />}
                  {!hideCamera && <span className="font-mono text-[10px] text-slate-500">{d.cameraId}</span>}
                  <span className="font-mono text-[10px] text-slate-600">{formatClock(d.timestamp)}</span>
                </span>
                <span className="flex items-center gap-1.5 text-[10px] text-slate-500">
                  <span className="font-mono">{formatConfidence(d.confidence)}</span>
                  <span>·</span>
                  <span>quality {QUALITY_LABEL[d.quality]}</span>
                  {d.source !== 'UNKNOWN' && (
                    <>
                      <span>·</span>
                      <span className="font-mono">{SOURCE_LABEL[d.source]}</span>
                    </>
                  )}
                </span>
              </span>
              <span className="shrink-0">
                <Badge variant={badgeTone(tone)} size="sm" dot>
                  {d.state === 'DETECTED' ? (
                    <span className="sr-only">Detected</span>
                  ) : null}
                  {d.state === 'DETECTED' ? 'OK' : d.state}
                </Badge>
              </span>
            </button>
          </li>
        )
      })}
    </ul>
  )
}