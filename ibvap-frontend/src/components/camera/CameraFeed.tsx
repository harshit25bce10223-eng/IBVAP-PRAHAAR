import { clsx } from 'clsx'
import type { ReactNode } from 'react'
import type { CameraDetail, TrackVisual } from '@/types'
import { FenceOverlay } from '@/components/fence/FenceOverlay'
import { FEED_VIEWBOX, FEED_ASPECT } from './feedViewport'

import type { FeedState } from '@/types'

interface CameraFeedProps {
  camera: CameraDetail
  tracks: TrackVisual[]
  isNight: boolean
  /** Honest feed freshness. Demo simulation reports BUFFERING, never LIVE. */
  feedState?: FeedState
  lastFrameAgoSec?: number | null
  children?: ReactNode
}

const FEED_STATE_STYLE: Record<FeedState, string> = {
  LIVE: 'text-emerald-400',
  BUFFERING: 'text-amber-400',
  STALE: 'text-amber-400',
  OFFLINE: 'text-red-400',
  DEGRADED: 'text-amber-400',
}

const FEED_STATE_DOT: Record<FeedState, string> = {
  LIVE: 'bg-emerald-400',
  BUFFERING: 'bg-amber-400',
  STALE: 'bg-amber-400',
  OFFLINE: 'bg-red-400',
  DEGRADED: 'bg-amber-400',
}

export { FEED_VIEWBOX, FEED_ASPECT }

/**
 * The camera feed stage. Displays the live feed surface (filled by the video
 * pipeline in production; a simulated scene while Tracking feeds synthetic
 * frames) plus track bounding boxes and the virtual-fence overlay.
 */
export function CameraFeed({ camera, tracks, isNight, feedState = 'BUFFERING', lastFrameAgoSec = null, children }: CameraFeedProps) {
  return (
    <div
      className="relative w-full overflow-hidden rounded-xl border border-[#1e2d40] bg-black"
      style={{ aspectRatio: FEED_ASPECT }}
    >
      {/* Feed surface (video placeholder — honest about simulation) */}
      <div
        className={clsx(
          'absolute inset-0 transition-colors duration-700',
          isNight
            ? 'bg-[radial-gradient(ellipse_at_center,#0b1626_0%,#05080f_70%)]'
            : 'bg-[radial-gradient(ellipse_at_center,#1a2736_0%,#0a1119_70%)]'
        )}
      >
        <FeedScene isNight={isNight} />
        <div className="absolute left-2 top-2 flex items-center gap-2">
          <span className="font-mono text-[10px] text-slate-300 bg-black/60 px-1.5 py-0.5 rounded">{camera.id}</span>
          <span className={clsx('flex items-center gap-1 rounded bg-black/60 px-1.5 py-0.5 font-mono text-[10px]', FEED_STATE_STYLE[feedState])} role="status">
            <span className={clsx('h-1.5 w-1.5 rounded-full', FEED_STATE_DOT[feedState], feedState === 'LIVE' && 'animate-pulse-dot')} aria-hidden />
            {feedState === 'BUFFERING' ? 'DEMO FEED' : feedState}
          </span>
          {feedState === 'STALE' && lastFrameAgoSec !== null && (
            <span className="font-mono text-[10px] text-amber-300 bg-black/60 px-1.5 py-0.5 rounded tabular-nums">
              Last frame: {lastFrameAgoSec} sec ago
            </span>
          )}
        </div>
        <div className="absolute right-2 top-2 font-mono text-[10px] text-slate-500 tabular-nums">
          {camera.resolution.width}×{camera.resolution.height} · {camera.fps} fps
        </div>
      </div>

      {/* Track bounding boxes */}
      <svg
        viewBox={`0 0 ${FEED_VIEWBOX.width} ${FEED_VIEWBOX.height}`}
        className="absolute inset-0 h-full w-full"
        aria-hidden
      >
        {tracks.map(track => (
          <TrackBox key={track.track_id} track={track} />
        ))}
      </svg>

      {/* Virtual fence overlay (zones + editor gestures) */}
      <div className="absolute inset-0">
        <FenceOverlay />
      </div>

      {/* Night indicator */}
      {isNight && (
        <div className="absolute inset-0 pointer-events-none bg-blue-900/10 mix-blend-overlay" />
      )}

      {/* Custom chrome (e.g. editor toolbar) */}
      {children}
    </div>
  )
}

function TrackBox({ track }: { track: TrackVisual }) {
  const bbox = track.bbox
  const color = track.object_type === 'HUMAN' ? '#22d3ee' : track.object_type === 'VEHICLE' ? '#f59e0b' : '#34d399'
  const x = bbox.x * FEED_VIEWBOX.width
  const y = bbox.y * FEED_VIEWBOX.height
  const w = bbox.width * FEED_VIEWBOX.width
  const h = bbox.height * FEED_VIEWBOX.height

  return (
    <g>
      <rect
        x={x}
        y={y}
        width={w}
        height={h}
        fill="none"
        stroke={color}
        strokeWidth={2}
      />
      {/* ground-contact tick at bottom-center (the representative point) */}
      <line
        x1={x + w / 2}
        y1={y + h}
        x2={x + w / 2}
        y2={y + h + 6}
        stroke={color}
        strokeWidth={2}
      />
      <g transform={`translate(${x}, ${Math.max(0, y - 18)})`}>
        <rect width={150} height={18} rx={4} fill="#0d1117" fillOpacity={0.9} stroke={color} strokeOpacity={0.5} />
        <text x={8} y={12.5} fontSize={11} fontFamily="JetBrains Mono, monospace" fill={color}>
          {track.track_id} · {(track.confidence * 100).toFixed(0)}%
        </text>
      </g>
      {track.insideZones.length > 0 && (
        <text
          x={x + w / 2}
          y={y + h + 26}
          textAnchor="middle"
          fontSize={9}
          fontFamily="JetBrains Mono, monospace"
          fill="#f59e0b"
        >
          ▲ {track.insideZones.join(' · ')}
        </text>
      )}
    </g>
  )
}

/** Stylized scene: fence line, ground grid, a couple of structures. */
function FeedScene({ isNight }: { isNight: boolean }) {
  return (
    <svg
      viewBox={`0 0 ${FEED_VIEWBOX.width} ${FEED_VIEWBOX.height}`}
      className="h-full w-full"
      aria-hidden
    >
      <defs>
        <linearGradient id="skyline" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={isNight ? '#111c2c' : '#22344a'} />
          <stop offset="100%" stopColor={isNight ? '#0a1119' : '#151f2c'} />
        </linearGradient>
      </defs>
      <rect width={FEED_VIEWBOX.width} height={FEED_VIEWBOX.height} fill="url(#skyline)" />

      {/* ground plane */}
      <path d="M0 470 L1000 470 L1000 562.5 L0 562.5 Z" fill={isNight ? '#0a0f16' : '#121a24'} />

      {/* perspective grid */}
      {Array.from({ length: 12 }).map((_, i) => (
        <line
          key={`v${i}`}
          x1={250 + i * 60}
          y1={350}
          x2={50 + i * 100}
          y2={562.5}
          stroke={isNight ? '#12202f' : '#1b2a3a'}
          strokeWidth={1}
        />
      ))}
      {Array.from({ length: 6 }).map((_, i) => (
        <line
          key={`h${i}`}
          x1={0}
          y1={470 - i * 22}
          x2={1000}
          y2={470 - i * 22}
          stroke={isNight ? '#12202f' : '#1b2a3a'}
          strokeWidth={1}
        />
      ))}

      {/* physical border fence line */}
      <path
        d="M0 470 L1000 470"
        stroke={isNight ? '#2a3f58' : '#38506b'}
        strokeWidth={2}
        strokeDasharray="10 6"
      />

      {/* watch tower + pole */}
      <g transform="translate(180, 360)" opacity={0.85}>
        <rect x={0} y={0} width={70} height={110} fill={isNight ? '#1b2735' : '#2a3a4e'} />
        <rect x={5} y={5} width={60} height={26} fill="#0a1119" />
        <path d="M35 -30 L0 8 L70 8 Z" fill={isNight ? '#1f2d3d' : '#31445c'} />
        <line x1={35} y1={-30} x2={35} y2={-52} stroke={isNight ? '#3a5168' : '#4a6482'} strokeWidth={3} />
        <circle cx={35} cy={-56} r={4} fill={isNight ? '#f59e0b' : '#e11d48'} />
      </g>

      {/* dirt track */}
      <path d="M420 562.5 Q520 540 660 520 Q780 502 1000 500 L1000 562.5 Z" fill={isNight ? '#141d29' : '#20303f'} />

      {/* vignette */}
      <rect width={FEED_VIEWBOX.width} height={FEED_VIEWBOX.height} fill="url(#skyline)" opacity={0} />
    </svg>
  )
}