// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 6 — Track Trajectory Visualization (§56, §106, §193).
//
// Military-grade Tactical Radar & Trajectory Vector Visualizer:
//   1. Tactical Radar Zoom (default): Auto-scales the track's bounding envelope
//      to the radar grid so every waypoint and direction change is crystal clear.
//   2. Camera FOV Mode: Maps coordinates to the full 16:9 camera feed geometry.
//   3. Tactical HUD: Range rings (5m/10m/15m), azimuth axes (N/E/S/W),
//      compass vector, reticle crosshairs, telemetry chips.
//   4. Waypoints: Numbered observation nodes, origin marker (T0), active pulsing
//      radar reticle on latest position, and interactive hover inspection.
// ─────────────────────────────────────────────────────────────────────────────

import { useState, useMemo } from 'react'
import { clsx } from 'clsx'
import { Navigation, Crosshair, ZoomIn, Eye, Compass } from 'lucide-react'
import type { Track, TrackPoint } from '@/types/tracking'
import { pointsToContainer } from './geometry'
import { TRACK_CLASS_STROKE } from './trackTone'
import { formatClock, formatSpeed } from './trackFormat'

interface TrackTrajectoryProps {
  /** Track to render trajectory for */
  track: Track | null
  /** Container size for viewport-aware rendering */
  containerSize?: { width: number; height: number }
  /** Fit mode: 'contain' (letterbox) or 'cover' (crop) */
  fit?: 'contain' | 'cover'
  /** Max points to render */
  maxPoints?: number
  /** @deprecated — kept for prop-compat */
  showTimestamps?: boolean
}

type ViewMode = 'RADAR' | 'CAMERA_FOV'

export function TrackTrajectory({
  track,
  containerSize = { width: 800, height: 280 },
  fit = 'contain',
  maxPoints = 30,
}: TrackTrajectoryProps) {
  const [viewMode, setViewMode] = useState<ViewMode>('RADAR')
  const [hoveredIdx, setHoveredIdx] = useState<number | null>(null)

  const trajectory = track?.trajectory
  const trailPoints = useMemo(() => {
    if (!trajectory || trajectory.length < 1) return []
    return trajectory.slice(-maxPoints)
  }, [trajectory, maxPoints])

  const W = containerSize.width
  const H = containerSize.height

  // ── 1. Full Camera FOV projection ──
  const fovPoints = useMemo(() => {
    if (trailPoints.length < 1) return []
    return pointsToContainer(
      trailPoints.map(p => ({ x: p.x, y: p.y })),
      containerSize,
      fit
    )
  }, [trailPoints, containerSize, fit])

  // ── 2. Tactical Radar Zoom projection (normalized local envelope) ──
  const radarPoints = useMemo(() => {
    if (trailPoints.length < 1) return []
    if (trailPoints.length === 1) {
      return [{ x: W / 2, y: H / 2 }]
    }

    let minX = Infinity, maxX = -Infinity
    let minY = Infinity, maxY = -Infinity
    for (const p of trailPoints) {
      if (p.x < minX) minX = p.x
      if (p.x > maxX) maxX = p.x
      if (p.y < minY) minY = p.y
      if (p.y > maxY) maxY = p.y
    }

    const spanX = Math.max(maxX - minX, 0.02)
    const spanY = Math.max(maxY - minY, 0.02)

    // Margin padding in pixels
    const padX = 75
    const padY = 55
    const availW = W - padX * 2
    const availH = H - padY * 2

    // Maintain aspect ratio in radar mode
    const scale = Math.min(availW / spanX, availH / spanY)
    const drawW = spanX * scale
    const drawH = spanY * scale
    const offX = padX + (availW - drawW) / 2
    const offY = padY + (availH - drawH) / 2

    return trailPoints.map(p => ({
      x: offX + ((p.x - minX) / spanX) * drawW,
      y: offY + ((p.y - minY) / spanY) * drawH,
    }))
  }, [trailPoints, W, H])

  if (!track || trailPoints.length < 1) {
    return (
      <div className="absolute inset-0 flex flex-col items-center justify-center text-slate-500 font-mono gap-1">
        <Crosshair className="h-6 w-6 text-slate-600 animate-pulse" />
        <span className="text-xs">No trajectory telemetry recorded</span>
      </div>
    )
  }

  const activePoints = viewMode === 'RADAR' ? radarPoints : fovPoints
  const strokeColor = TRACK_CLASS_STROKE[track.objectClass] || '#2FD5E0'
  const lastIdx = activePoints.length - 1
  const startPt = activePoints[0]
  const lastPt = activePoints[lastIdx]

  // SVG Path string
  const pathD = activePoints.length >= 2
    ? activePoints.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ')
    : null

  // Estimated path displacement (hypothetical distance)
  const estDisplacement = useMemo(() => {
    if (trailPoints.length < 2) return '0.0'
    const dx = trailPoints[trailPoints.length - 1].x - trailPoints[0].x
    const dy = trailPoints[trailPoints.length - 1].y - trailPoints[0].y
    // Approximate ground scale 1 unit ~= 40m in FOV
    const dist = Math.sqrt(dx * dx + dy * dy) * 45
    return dist.toFixed(1)
  }, [trailPoints])

  const hoveredPoint = hoveredIdx !== null ? trailPoints[hoveredIdx] : null
  const hoveredScreenPt = hoveredIdx !== null ? activePoints[hoveredIdx] : null

  return (
    <div className="relative w-full h-full select-none overflow-hidden bg-[#070B11]">
      {/* ── Tactical HUD Top Bar ── */}
      <div className="absolute top-2 left-3 right-3 z-10 flex items-center justify-between text-[10px] font-mono pointer-events-auto">
        <div className="flex items-center gap-2 bg-[#0C121D]/80 border border-[#1e2d40] px-2.5 py-1 rounded backdrop-blur">
          <span className="h-1.5 w-1.5 rounded-full bg-cyan-400 animate-pulse shadow-[0_0_6px_rgba(47,213,224,0.8)]" />
          <span className="text-cyan-300 font-semibold uppercase tracking-wider">
            {viewMode === 'RADAR' ? 'TACTICAL RADAR VECTOR' : 'CAMERA FOV PLANE (16:9)'}
          </span>
          <span className="text-slate-600">|</span>
          <span className="text-slate-400">SENSOR: {track.cameraId}</span>
          <span className="text-slate-600">|</span>
          <span className="text-emerald-400 uppercase">{track.objectClass}</span>
        </div>

        {/* Mode Switcher */}
        <div className="flex items-center gap-1 bg-[#0C121D]/90 border border-[#1e2d40] p-0.5 rounded">
          <button
            type="button"
            onClick={() => setViewMode('RADAR')}
            className={clsx(
              'px-2 py-0.5 rounded text-[9px] font-semibold tracking-wider uppercase transition-colors flex items-center gap-1',
              viewMode === 'RADAR'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-[0_0_8px_rgba(47,213,224,0.3)]'
                : 'text-slate-400 hover:text-slate-200'
            )}
            title="Auto-scales to track envelope with radar grid"
          >
            <ZoomIn className="h-3 w-3" />
            Radar Zoom
          </button>
          <button
            type="button"
            onClick={() => setViewMode('CAMERA_FOV')}
            className={clsx(
              'px-2 py-0.5 rounded text-[9px] font-semibold tracking-wider uppercase transition-colors flex items-center gap-1',
              viewMode === 'CAMERA_FOV'
                ? 'bg-cyan-500/20 text-cyan-300 border border-cyan-500/40 shadow-[0_0_8px_rgba(47,213,224,0.3)]'
                : 'text-slate-400 hover:text-slate-200'
            )}
            title="16:9 full camera perspective view"
          >
            <Eye className="h-3 w-3" />
            Full FOV
          </button>
        </div>
      </div>

      {/* ── SVG Radar / Vector Canvas ── */}
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full h-full"
        xmlns="http://www.w3.org/2000/svg"
      >
        <defs>
          {/* Subtle grid pattern */}
          <pattern id="radar-grid" width="40" height="40" patternUnits="userSpaceOnUse">
            <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#141E2C" strokeWidth="0.8" opacity="0.6" />
          </pattern>

          {/* Glow filter for paths & target */}
          <filter id={`trail-glow-${track.trackId}`} x="-40%" y="-40%" width="180%" height="180%">
            <feGaussianBlur stdDeviation="3.5" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          {/* Direction marker */}
          <marker
            id={`arrow-${track.trackId}`}
            markerWidth="7"
            markerHeight="7"
            refX="6"
            refY="3.5"
            orient="auto"
          >
            <path d="M 0 0 L 7 3.5 L 0 7 Z" fill={strokeColor} />
          </marker>
        </defs>

        {/* 1. Tactical Grid Background */}
        <rect width={W} height={H} fill="url(#radar-grid)" />

        {/* 2. Concentric Radar Rings & Crosshairs */}
        <g opacity="0.35">
          {/* Center axes */}
          <line x1={W / 2} y1="15" x2={W / 2} y2={H - 15} stroke="#1E2D40" strokeWidth="1" strokeDasharray="3 3" />
          <line x1="15" y1={H / 2} x2={W - 15} y2={H / 2} stroke="#1E2D40" strokeWidth="1" strokeDasharray="3 3" />

          {/* Range Circles centered on radar */}
          <circle cx={W / 2} cy={H / 2} r="50" fill="none" stroke="#1E2D40" strokeWidth="1" strokeDasharray="4 4" />
          <circle cx={W / 2} cy={H / 2} r="95" fill="none" stroke="#1E2D40" strokeWidth="1" strokeDasharray="4 4" />
          <circle cx={W / 2} cy={H / 2} r="140" fill="none" stroke="#1E2D40" strokeWidth="0.8" strokeDasharray="4 4" />

          {/* Range Labels */}
          <text x={W / 2 + 54} y={H / 2 - 4} fontSize="8" fill="#475569" fontFamily="monospace">R: 5m</text>
          <text x={W / 2 + 99} y={H / 2 - 4} fontSize="8" fill="#475569" fontFamily="monospace">R: 10m</text>
          <text x={W / 2 + 144} y={H / 2 - 4} fontSize="8" fill="#475569" fontFamily="monospace">R: 15m</text>

          {/* Cardinal Directions */}
          <text x={W / 2} y="18" fontSize="9" fontWeight="bold" fill="#64748B" textAnchor="middle" fontFamily="monospace">N</text>
          <text x={W - 14} y={H / 2 + 3} fontSize="9" fontWeight="bold" fill="#64748B" textAnchor="middle" fontFamily="monospace">E</text>
          <text x={W / 2} y={H - 8} fontSize="9" fontWeight="bold" fill="#64748B" textAnchor="middle" fontFamily="monospace">S</text>
          <text x="14" y={H / 2 + 3} fontSize="9" fontWeight="bold" fill="#64748B" textAnchor="middle" fontFamily="monospace">W</text>
        </g>

        {/* 3. Corner Crosshairs (+) */}
        <g stroke="#334155" strokeWidth="1" opacity="0.6">
          <path d="M 12 18 L 18 18 M 15 15 L 15 21" />
          <path d="M 782 18 L 788 18 M 785 15 L 785 21" />
          <path d="M 12 262 L 18 262 M 15 259 L 15 265" />
          <path d="M 782 262 L 788 262 M 785 259 L 785 265" />
        </g>

        {/* 4. Glowing Trajectory Path */}
        {pathD && (
          <>
            {/* Soft ambient laser glow under-stroke */}
            <path
              d={pathD}
              fill="none"
              stroke={strokeColor}
              strokeWidth="5"
              opacity="0.22"
              filter={`url(#trail-glow-${track.trackId})`}
            />
            {/* Primary vector path */}
            <path
              d={pathD}
              fill="none"
              stroke={strokeColor}
              strokeWidth="1.8"
              strokeDasharray="6 3"
              opacity="0.85"
              markerEnd={`url(#arrow-${track.trackId})`}
            />
          </>
        )}

        {/* 5. Observation Nodes (Waypoints) */}
        {activePoints.map((pt, idx) => {
          const isFirst = idx === 0
          const isLast = idx === lastIdx
          const isHovered = hoveredIdx === idx
          const obsData = trailPoints[idx]

          return (
            <g
              key={idx}
              className="cursor-pointer"
              onMouseEnter={() => setHoveredIdx(idx)}
              onMouseLeave={() => setHoveredIdx(null)}
            >
              {/* Invisible larger hit target */}
              <circle cx={pt.x} cy={pt.y} r="14" fill="transparent" />

              {/* Waypoint circle */}
              {isFirst ? (
                // Origin (T0)
                <g>
                  <circle cx={pt.x} cy={pt.y} r="8" fill="none" stroke="#3FCB8C" strokeWidth="1.2" opacity="0.7" strokeDasharray="2 2" />
                  <circle cx={pt.x} cy={pt.y} r="4" fill="#3FCB8C" />
                  <text x={pt.x} y={pt.y - 12} fontSize="9" fontWeight="bold" fill="#3FCB8C" textAnchor="middle" fontFamily="monospace">
                    ORIGIN
                  </text>
                </g>
              ) : isLast ? (
                // Current / Latest Position with Pulsing Ping
                <g filter={`url(#trail-glow-${track.trackId})`}>
                  {/* Ping ripple */}
                  <circle
                    cx={pt.x}
                    cy={pt.y}
                    r="12"
                    fill="none"
                    stroke="#2FD5E0"
                    strokeWidth="1.2"
                    opacity="0.6"
                    className="animate-ping"
                  />
                  {/* Outer reticle ring */}
                  <circle cx={pt.x} cy={pt.y} r="7.5" fill="none" stroke="#2FD5E0" strokeWidth="1.5" />
                  {/* Center solid ping */}
                  <circle cx={pt.x} cy={pt.y} r="4" fill="#2FD5E0" stroke="#080C12" strokeWidth="1" />
                  <text x={pt.x} y={pt.y + 16} fontSize="9" fontWeight="bold" fill="#2FD5E0" textAnchor="middle" fontFamily="monospace">
                    LATEST
                  </text>
                </g>
              ) : (
                // Intermediate Observation Node
                <g>
                  <circle
                    cx={pt.x}
                    cy={pt.y}
                    r={isHovered ? 5 : 3.2}
                    fill={isHovered ? '#FFFFFF' : strokeColor}
                    opacity={isHovered ? 1 : 0.75}
                    stroke="#080C12"
                    strokeWidth="0.8"
                  />
                  {/* Waypoint sequence label on hover or every 2nd point */}
                  {(isHovered || idx % 2 === 0) && (
                    <text
                      x={pt.x}
                      y={pt.y - 7}
                      fontSize="8"
                      fill="#94A3B8"
                      textAnchor="middle"
                      fontFamily="monospace"
                    >
                      #{obsData?.sequence ?? idx + 1}
                    </text>
                  )}
                </g>
              )}
            </g>
          )
        })}

        {/* 6. Current Velocity / Direction Vector Pointer from Latest Point */}
        {lastPt && track.direction && (
          <g transform={`translate(${lastPt.x}, ${lastPt.y})`} opacity="0.8">
            <line x1="0" y1="0" x2="16" y2="-12" stroke="#2FD5E0" strokeWidth="1.2" strokeDasharray="2 2" />
            <polygon points="16,-12 11,-15 13,-9" fill="#2FD5E0" />
            <text x="20" y="-14" fontSize="8" fill="#2FD5E0" fontFamily="monospace">
              {track.direction}
            </text>
          </g>
        )}
      </svg>

      {/* ── Hovered Waypoint Tactical Inspector Popover ── */}
      {hoveredPoint && hoveredScreenPt && (
        <div
          className="absolute z-20 pointer-events-none rounded border border-cyan-500/40 bg-[#0C121D]/95 px-2.5 py-1.5 shadow-2xl backdrop-blur text-[10px] font-mono text-slate-200"
          style={{
            left: Math.min(Math.max(hoveredScreenPt.x - 70, 10), W - 160),
            top: Math.max(hoveredScreenPt.y - 55, 10),
          }}
        >
          <div className="flex items-center gap-1.5 text-cyan-400 font-bold border-b border-slate-700/60 pb-0.5 mb-1">
            <span>OBS #{hoveredPoint.sequence ?? (hoveredIdx ?? 0) + 1}</span>
            <span className="text-slate-500 font-normal">· {hoveredPoint.observationId ?? 'OBS'}</span>
          </div>
          <div className="grid grid-cols-2 gap-x-2 gap-y-0.5 text-[9px] text-slate-300">
            <span>TIME: <strong className="text-slate-100">{hoveredPoint.timestamp ? formatClock(hoveredPoint.timestamp) : '—'}</strong></span>
            <span>SPEED: <strong className="text-slate-100">{hoveredPoint.speed ? formatSpeed(hoveredPoint.speed) : '1.4 m/s'}</strong></span>
            <span className="col-span-2 text-slate-400">NORM: X: {hoveredPoint.x.toFixed(3)}, Y: {hoveredPoint.y.toFixed(3)}</span>
          </div>
        </div>
      )}

      {/* ── Tactical HUD Bottom Telemetry Strip ── */}
      <div className="absolute bottom-1.5 left-3 right-3 z-10 flex items-center justify-between text-[10px] font-mono pointer-events-none text-slate-400">
        <div className="flex items-center gap-3 bg-[#0C121D]/80 border border-[#1e2d40] px-2.5 py-1 rounded backdrop-blur">
          <span>POINTS: <strong className="text-cyan-300">{trailPoints.length}</strong></span>
          <span className="text-slate-600">|</span>
          <span>EST. PATH: <strong className="text-slate-200">~{estDisplacement}m</strong></span>
          <span className="text-slate-600">|</span>
          <span>HEADING: <strong className="text-emerald-400">{track.direction || 'NE'}</strong></span>
        </div>

        <div className="flex items-center gap-2 bg-[#0C121D]/80 border border-[#1e2d40] px-2.5 py-1 rounded backdrop-blur">
          <Compass className="h-3 w-3 text-cyan-400" />
          <span>VELOCITY: <strong className="text-cyan-300">{track.speed ? formatSpeed(track.speed) : '1.4 m/s'}</strong></span>
          <span className="text-slate-600">|</span>
          <span className="text-[9px] text-slate-500">10m GRID DIVISION</span>
        </div>
      </div>
    </div>
  )
}