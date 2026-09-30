// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 6 — Track Trajectory Visualization (§56, §106, §193).
//
// Renders track trajectory points as a compact path on the camera feed.
// Only the selected track shows full detailed trail; other tracks show
// current position only or very short trail (§193).
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'
import type { Track } from '@/types/tracking'
import { pointsToContainer } from './geometry'
import { TRACK_CLASS_STROKE } from './trackTone'
import { formatClock } from './trackFormat'

interface TrackTrajectoryProps {
  /** Track to render trajectory for (usually the selected one) */
  track: Track | null
  /** Container size for viewport-aware rendering */
  containerSize: { width: number; height: number }
  /** Fit mode: 'contain' (letterbox) or 'cover' (crop) */
  fit: 'contain' | 'cover'
  /** Max points to render */
  maxPoints?: number
  /** Show timestamps on points */
  showTimestamps?: boolean
}

export function TrackTrajectory({
  track,
  containerSize,
  fit = 'contain',
  maxPoints = 30,
  showTimestamps = false,
}: TrackTrajectoryProps) {
  const trajectory = track?.trajectory
  if (!trajectory || trajectory.length < 2) return null

  const trailPoints = trajectory.slice(-maxPoints)
  const containerPoints = pointsToContainer(
    trailPoints.map(p => ({ x: p.x, y: p.y })),
    containerSize,
    fit
  )

  if (containerPoints.length < 2) return null

  const pathData = containerPoints
    .map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`)
    .join(' ')

  return (
    <svg
      viewBox={`0 0 ${containerSize.width} ${containerSize.height}`}
      className={clsx('absolute inset-0 h-full w-full pointer-events-none')}
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        <marker
          id={`trail-arrowhead-${track.trackId}`}
          markerWidth="6"
          markerHeight="6"
          refX="5"
          refY="3"
          orient="auto"
          markerUnits="strokeWidth"
        >
          <path d="M0,0 L0,5 L6,2.5 Z" fill={TRACK_CLASS_STROKE[track.objectClass]} />
        </marker>
      </defs>
      <path
        d={pathData}
        fill="none"
        stroke={TRACK_CLASS_STROKE[track.objectClass]}
        strokeWidth={1.5}
        strokeDasharray="4 4"
        opacity={0.7}
        markerEnd={`url(#trail-arrowhead-${track.trackId})`}
      />
      {showTimestamps && containerPoints.map((p, idx) => (
        <g key={idx} className="pointer-events-none">
          <circle cx={p.x} cy={p.y} r={3} fill={TRACK_CLASS_STROKE[track.objectClass]} opacity={0.8} />
          {trailPoints[idx]?.timestamp && (
            <text
              x={p.x + 5}
              y={p.y - 5}
              fontSize={9}
              fontFamily="JetBrains Mono, monospace"
              fill="#cbd5e1"
            >
              {formatClock(trailPoints[idx].timestamp!)}
            </text>
          )}
        </g>
      ))}
      {/* Current position emphasis */}
      <circle
        cx={containerPoints[containerPoints.length - 1].x}
        cy={containerPoints[containerPoints.length - 1].y}
        r={5}
        fill="#22d3e4"
        stroke="#080c12"
        strokeWidth={2}
        opacity={1}
      />
    </svg>
  )
}