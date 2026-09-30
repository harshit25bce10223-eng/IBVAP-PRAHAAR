// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 6 — Track Trajectory Visualization (§56, §106, §193).
//
// Renders track trajectory as a connected path with observation nodes.
// Each recorded detection position is shown as a dot; dots are connected
// by a dashed line in chronological order. Final position is emphasised.
// No positions are interpolated or inferred between observations (§23).
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'
import type { Track } from '@/types/tracking'
import { pointsToContainer } from './geometry'
import { TRACK_CLASS_STROKE } from './trackTone'

interface TrackTrajectoryProps {
  /** Track to render trajectory for (usually the selected one) */
  track: Track | null
  /** Container size for viewport-aware rendering */
  containerSize: { width: number; height: number }
  /** Fit mode: 'contain' (letterbox) or 'cover' (crop) */
  fit: 'contain' | 'cover'
  /** Max points to render */
  maxPoints?: number
  /** @deprecated — kept for prop-compat; has no effect */
  showTimestamps?: boolean
}

export function TrackTrajectory({
  track,
  containerSize,
  fit = 'contain',
  maxPoints = 30,
}: TrackTrajectoryProps) {
  const trajectory = track?.trajectory
  if (!trajectory || trajectory.length < 1) return null

  const trailPoints = trajectory.slice(-maxPoints)
  const containerPoints = pointsToContainer(
    trailPoints.map(p => ({ x: p.x, y: p.y })),
    containerSize,
    fit
  )

  if (containerPoints.length < 1) return null

  const stroke = TRACK_CLASS_STROKE[track.objectClass]
  const markerId = `trail-arrowhead-${track.trackId}`

  // Build SVG path only when we have ≥ 2 points
  const pathData = containerPoints.length >= 2
    ? containerPoints
        .map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
        .join(' ')
    : null

  const last = containerPoints[containerPoints.length - 1]

  return (
    <svg
      viewBox={`0 0 ${containerSize.width} ${containerSize.height}`}
      className={clsx('absolute inset-0 h-full w-full pointer-events-none')}
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        {/* Arrowhead marker for direction */}
        <marker
          id={markerId}
          markerWidth="6"
          markerHeight="6"
          refX="5"
          refY="3"
          orient="auto"
          markerUnits="strokeWidth"
        >
          <path d="M0,0 L0,5 L6,2.5 Z" fill={stroke} />
        </marker>

        {/* Glow filter for current position dot */}
        <filter id={`glow-${track.trackId}`} x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feMerge>
            <feMergeNode in="blur" />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* ── Connected path ── */}
      {pathData && (
        <path
          d={pathData}
          fill="none"
          stroke={stroke}
          strokeWidth={1.5}
          strokeDasharray="5 3"
          opacity={0.55}
          markerEnd={`url(#${markerId})`}
        />
      )}

      {/* ── Observation nodes — every recorded detection position ── */}
      {containerPoints.map((p, idx) => {
        const isLast = idx === containerPoints.length - 1
        const isFirst = idx === 0
        // Fade older points: 0.35 → 0.8 as idx increases
        const opacity = 0.35 + (idx / Math.max(containerPoints.length - 1, 1)) * 0.55

        if (isLast) return null // rendered separately below with glow

        return (
          <g key={idx}>
            {/* Outer ring for first point (origin) */}
            {isFirst && (
              <circle cx={p.x} cy={p.y} r={6} fill="none" stroke={stroke} strokeWidth={1} opacity={0.4} />
            )}
            {/* Detection dot */}
            <circle
              cx={p.x}
              cy={p.y}
              r={isFirst ? 3.5 : 2.5}
              fill={stroke}
              opacity={opacity}
            />
          </g>
        )
      })}

      {/* ── Current / latest position — emphasised with glow ── */}
      <g filter={`url(#glow-${track.trackId})`}>
        <circle
          cx={last.x}
          cy={last.y}
          r={7}
          fill="none"
          stroke="#22d3e4"
          strokeWidth={1}
          opacity={0.35}
        />
        <circle
          cx={last.x}
          cy={last.y}
          r={4.5}
          fill="#22d3e4"
          stroke="#080c12"
          strokeWidth={1.5}
          opacity={1}
        />
      </g>
    </svg>
  )
}