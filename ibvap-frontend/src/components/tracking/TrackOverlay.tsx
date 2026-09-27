// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 6 — Track Overlay
//
// Restrained track visualization on the camera feed. Shows track ID, class,
// state, and optional trajectory. Neutral class colors, no glow/gradients/neon.
// The selected track is the only emphatic element, and every track carries a
// screen-reader-accessible label (§40, §115–§118, §122).
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'
import type { Track, TrackPoint } from '@/types/tracking'
import { FEED_VIEWBOX } from '@/components/camera/feedViewport'
import { bboxToVB, pointsToContainer, pointToVB } from './geometry'
import { describeTrack } from './trackFormat'
import { TRACK_CLASS_STROKE, TRACK_CLASS_CHIP } from './trackTone'

/** Display-only filters applied to the overlay (§49, §169–§171). These filter RENDERING only — they never alter stored track data. */
export interface TrackDisplayFilters {
  /** Whitelist of classes; null/empty = show all. */
  classes?: Track['objectClass'][] | null
  /** Whitelist of statuses; null/empty = show all. */
  statuses?: Track['status'][] | null
}

interface TrackOverlayProps {
  tracks: Track[]
  selectedTrackId?: string | null
  onSelect?: (track: Track) => void
  /** Disable pointer/keyboard interaction (e.g. passive tile preview). */
  interactive?: boolean
  displayFilters?: TrackDisplayFilters
  /** Show trajectory trail for selected track only (§193). */
  showTrajectoryForSelected?: boolean
  /** Max trajectory points to render. */
  maxTrajectoryPoints?: number
  className?: string
}

function applyFilters(tracks: Track[], filters: TrackDisplayFilters | undefined): Track[] {
  if (!filters) return tracks
  const classes = filters.classes?.length ? filters.classes : null
  const statuses = filters.statuses?.length ? filters.statuses : null
  return tracks.filter(t => {
    if (classes && !classes.includes(t.objectClass)) return false
    if (statuses && !statuses.includes(t.status)) return false
    return true
  })
}

function formatTrajectoryLabel(t: Track): string {
  const parts: string[] = []
  if (t.trackId) parts.push(t.trackId)
  if (t.objectClass) parts.push(t.objectClass)
  if (t.status) parts.push(t.status)
  return parts.join(' · ')
}

/**
 * Restrained track overlay (Component 6 spec §40, §106, §113–§116).
 * Rendering is a single SVG mapped to the feed viewBox, so tracks stay aligned
 * across resize/aspect changes automatically (no percentages to break).
 */
export function TrackOverlay({
  tracks,
  selectedTrackId,
  onSelect,
  interactive = true,
  displayFilters,
  showTrajectoryForSelected = true,
  maxTrajectoryPoints = 30,
  className,
}: TrackOverlayProps) {
  const visible = applyFilters(tracks, displayFilters)

  const activate = (t: Track) => {
    if (interactive && onSelect) onSelect(t)
  }

  return (
    <svg
      viewBox={`0 0 ${FEED_VIEWBOX.width} ${FEED_VIEWBOX.height}`}
      className={clsx('absolute inset-0 h-full w-full pointer-events-none', className)}
      xmlns="http://www.w3.org/2000/svg"
    >
      {/* Trajectories (selected track gets full trail, others get current pos only §193) */}
      {visible.map(t => {
        if (!t.trajectory || t.trajectory.length === 0) return null
        const selected = selectedTrackId === t.trackId
        const showTrail = selected || !showTrajectoryForSelected

        if (!showTrail) return null

        const trailPoints = t.trajectory
          .slice(-maxTrajectoryPoints)
          .map(p => pointToVB(p.x, p.y))

        if (trailPoints.length < 2) return null

        const pathData = trailPoints
          .map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
          .join(' ')

        return (
          <path
            key={`trail-${t.trackId}`}
            d={pathData}
            fill="none"
            stroke={TRACK_CLASS_STROKE[t.objectClass]}
            strokeWidth={selected ? 2 : 1}
            strokeDasharray={selected ? undefined : '4 4'}
            opacity={selected ? 0.9 : 0.5}
            className={clsx(
              'transition-opacity duration-200',
              interactive && 'pointer-events-none'
            )}
          />
        )
      })}

      {/* Track boxes & labels */}
      {visible.map(t => {
        const box = bboxToVB(t.currentBoundingBox)
        if (!box) return null
        const selected = selectedTrackId === t.trackId
        const lowContinuity = t.continuityQuality === 'WEAK' || t.continuityQuality === 'UNKNOWN'
        const invalid = t.status === 'INVALID'

        // Accessibility: the box itself is the interactive landmark.
        const common = {
          role: interactive ? ('button' as const) : undefined,
          tabIndex: interactive ? 0 : undefined,
          'aria-label': describeTrack(t.trackId, t.objectClass, t.status, t.confidence ?? null, t.cameraId, t.lastSeenAt),
          focusable: interactive ? ('true' as const) : undefined,
          onClick: interactive ? () => activate(t) : undefined,
          onKeyDown: interactive
            ? (e: React.KeyboardEvent) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault()
                  activate(t)
                }
              }
            : undefined,
        }

        return (
          <g
            key={t.trackId}
            {...common}
            className={clsx(
              interactive && 'pointer-events-auto cursor-pointer focus:outline-none',
              interactive && 'focus-visible:[&>rect]:stroke-cyan-300'
            )}
          >
            {/* Track box */}
            <rect
              x={box.x}
              y={box.y}
              width={box.width}
              height={box.height}
              fill={selected ? 'rgba(34, 213, 224, 0.06)' : 'rgba(10, 15, 25, 0.02)'}
              stroke={selected ? '#22d3e4' : TRACK_CLASS_STROKE[t.objectClass]}
              strokeWidth={selected ? 2 : 1.5}
            />
            {/* Ground-contact tick */}
            <line
              x1={box.x + box.width / 2}
              y1={box.y + box.height}
              x2={box.x + box.width / 2}
              y2={Math.min(FEED_VIEWBOX.height, box.y + box.height + (selected ? 8 : 5))}
              stroke={selected ? '#22d3e4' : TRACK_CLASS_STROKE[t.objectClass]}
              strokeWidth={1.5}
              opacity={0.8}
            />
            {/* Direction arrow (if velocity available) */}
            {t.velocity && t.direction && (
              <>
                <line
                  x1={box.x + box.width / 2}
                  y1={box.y + box.height / 2}
                  x2={box.x + box.width / 2 + Math.cos(dirToRad(t.direction!)) * 20}
                  y2={box.y + box.height / 2 + Math.sin(dirToRad(t.direction!)) * 20}
                  stroke={TRACK_CLASS_STROKE[t.objectClass]}
                  strokeWidth={2}
                  markerEnd="url(#arrowhead)"
                />
                <defs>
                  <marker
                    id="arrowhead"
                    markerWidth="8"
                    markerHeight="8"
                    refX="6"
                    refY="3"
                    orient="auto"
                    markerUnits="strokeWidth"
                  >
                    <path d="M0,0 L0,6 L8,3 Z" fill={TRACK_CLASS_STROKE[t.objectClass]} />
                  </marker>
                </defs>
              </>
            )}
            {/* Compact label chip: class > state > confidence; no id on the box (§50) */}
            <g transform={`translate(${Math.min(FEED_VIEWBOX.width - 140, Math.max(0, box.x))}, ${Math.max(2, box.y - 20)})`}>
              <rect
                width={1}
                height={18}
                rx={4}
                fill={invalid ? 'rgba(127, 29, 29, 0.85)' : lowContinuity ? 'rgba(252, 211, 77, 0.2)' : 'rgba(13, 17, 23, 0.85)'}
                stroke={invalid ? '#b91c1c' : selected ? '#22d3e4' : TRACK_CLASS_STROKE[t.objectClass]}
                strokeOpacity={0.9}
                strokeWidth={0.75}
              />
              <text
                x={4}
                y={12.5}
                fontSize={10}
                fontFamily="JetBrains Mono, monospace"
                fill={invalid ? '#f87171' : lowContinuity ? '#fcd34d' : '#cbd5e1'}
              >
                {TRACK_CLASS_CHIP[t.objectClass]} {formatConfidenceShort(t.confidence ?? null)}
                {t.status !== 'ACTIVE' && ` · ${t.status}`}
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
  const pct = value <= 1 ? value * 100 : value
  return `${Math.round(pct)}%`
}

function dirToRad(dir: string): number {
  const map: Record<string, number> = {
    N: -Math.PI / 2,
    NE: -Math.PI / 4,
    E: 0,
    SE: Math.PI / 4,
    S: Math.PI / 2,
    SW: (3 * Math.PI) / 4,
    W: Math.PI,
    NW: (-3 * Math.PI) / 4,
  }
  if (dir.startsWith('MOVING ')) {
    const d = dir.replace('MOVING ', '')
    return map[d] ?? 0
  }
  return map[dir] ?? 0
}