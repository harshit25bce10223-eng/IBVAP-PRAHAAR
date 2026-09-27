import { clsx } from 'clsx'
import type { CSSProperties } from 'react'
import type { DetectionResult } from '@/types/detection'
import { FEED_VIEWBOX } from '@/components/camera/feedViewport'
import { bboxToVB } from './geometry'
import { describeDetection } from './detectionFormat'
import { CLASS_CHIP, CLASS_STROKE } from './detectionTone'

/**
 * Display-only filters applied to the overlay (Component spec §24/§74–§77).
 * These filter RENDERING only — they never alter stored detection data.
 */
export interface DetectionDisplayFilters {
  /** Whitelist of classes; null/empty = show all. */
  classes?: DetectionResult['class'][] | null
  /** Minimum confidence as a 0–1 ratio; null = no threshold. */
  confidenceMin?: number | null
}

interface DetectionOverlayProps {
  detections: DetectionResult[]
  selectedDetectionId?: string | null
  onSelect?: (detection: DetectionResult) => void
  /** Disable pointer/keyboard interaction (e.g. passive tile preview). */
  interactive?: boolean
  displayFilters?: DetectionDisplayFilters
  className?: string
}

function applyFilters(detections: DetectionResult[], filters: DetectionDisplayFilters | undefined): DetectionResult[] {
  if (!filters) return detections
  const classes = filters.classes?.length ? filters.classes : null
  return detections.filter(d => {
    if (classes && !classes.includes(d.class)) return false
    if (filters.confidenceMin !== null && filters.confidenceMin !== undefined && d.confidence !== null) {
      if (d.confidence < filters.confidenceMin) return false
    }
    return true
  })
}

/**
 * Restrained detection overlay (Component spec §10/§23/§98–§104).
 * Neutral class colors, no glow/gradients/neon. The selected box is the only
 * emphatic element, and every box carries a screen-reader-accessible label.
 * Rendering is a single SVG mapped to the feed viewBox, so boxes stay aligned
 * across resize/aspect changes automatically (no percentages to break).
 */
export function DetectionOverlay({
  detections,
  selectedDetectionId,
  onSelect,
  interactive = true,
  displayFilters,
  className,
}: DetectionOverlayProps) {
  const visible = applyFilters(detections, displayFilters)

  const activate = (d: DetectionResult) => {
    if (interactive && onSelect) onSelect(d)
  }

  return (
    <svg
      viewBox={`0 0 ${FEED_VIEWBOX.width} ${FEED_VIEWBOX.height}`}
      className={clsx('absolute inset-0 h-full w-full pointer-events-none', className)}
      xmlns="http://www.w3.org/2000/svg"
    >
      {visible.map(d => {
        const box = bboxToVB(d.bbox)
        if (!box) return null
        const selected = selectedDetectionId === d.detectionId
        const low = d.state === 'LOW_CONFIDENCE' || (d.confidence !== null && d.confidence < 0.5)
        const invalid = d.state === 'INVALID'

        // Accessibility: the box itself is the interactive landmark.
        const common = {
          role: interactive ? ('button' as const) : undefined,
          tabIndex: interactive ? 0 : undefined,
          'aria-label': describeDetection(d.class, d.confidence, d.cameraId, d.timestamp),
          style: { pointerEvents: 'auto' } as CSSProperties,
          onClick: interactive ? () => activate(d) : undefined,
          onKeyDown: interactive
            ? (e: React.KeyboardEvent) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  activate(d)
                }
              }
            : undefined,
        }

        return (
          <g
            key={d.detectionId}
            {...common}
            className={clsx(
              interactive && 'pointer-events-auto cursor-pointer focus:outline-none',
              interactive && 'focus-visible:[&>rect]:stroke-cyan-300'
            )}
          >
            {/* Box */}
            <rect
              x={box.x}
              y={box.y}
              width={box.width}
              height={box.height}
              fill={selected ? 'rgba(34, 213, 224, 0.06)' : 'rgba(10, 15, 25, 0.02)'}
              stroke={selected ? '#22d3e4' : CLASS_STROKE[d.class]}
              strokeWidth={selected ? 2 : 1.5}
              strokeDasharray={d.partial ? '4 3' : undefined}
            />
            {/* Ground-contact tick for boxes that are the primary observation */}
            <line
              x1={box.x + box.width / 2}
              y1={box.y + box.height}
              x2={box.x + box.width / 2}
              y2={Math.min(FEED_VIEWBOX.height, box.y + box.height + (selected ? 8 : 5))}
              stroke={selected ? '#22d3e4' : CLASS_STROKE[d.class]}
              strokeWidth={1.5}
              opacity={0.8}
            />
            {/* Compact label chip: class > confidence; no id on the box (§50) */}
            <g transform={`translate(${Math.min(FEED_VIEWBOX.width - 120, Math.max(0, box.x))}, ${Math.max(2, box.y - 20)})`}>
              <rect
                width={1}
                height={18}
                rx={4}
                fill={invalid ? 'rgba(127, 29, 29, 0.85)' : 'rgba(13, 17, 23, 0.85)'}
                stroke={invalid ? '#b91c1c' : selected ? '#22d3e4' : CLASS_STROKE[d.class]}
                strokeOpacity={0.9}
                strokeWidth={0.75}
              />
              <text
                x={4}
                y={12.5}
                fontSize={10}
                fontFamily="JetBrains Mono, monospace"
                fill={invalid ? '#f87171' : low ? '#fcd34d' : '#cbd5e1'}
              >
                {invalid ? 'INVALID' : `${CLASS_CHIP[d.class]} ${formatConfidenceShort(d.confidence)}`}
              </text>
            </g>
          </g>
        )
      })}
    </svg>
  )
}

function formatConfidenceShort(value: number | null): string {
  if (value === null) return '—'
  const pct = Math.round((value <= 1 ? value * 100 : value))
  return `${pct}%`
}

export { bboxToVB }