import { clsx } from 'clsx'
import { useState, useEffect, useRef, type ReactNode } from 'react'
import type { CameraDetail, TrackVisual } from '@/types'
import { FenceOverlay } from '@/components/fence/FenceOverlay'
import { FEED_VIEWBOX, FEED_ASPECT } from './feedViewport'
import type { FeedState } from '@/types'

// Real surveillance video streams / clips for cameras
const SURVEILLANCE_VIDEOS: Record<string, string> = {
  'CAM-01': 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4',
  'CAM-02': 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerEscapes.mp4',
  'CAM-07': 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/WeAreGoingOnBullrun.mp4',
  'CAM-12': 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4',
}

interface CameraFeedProps {
  camera: CameraDetail
  tracks: TrackVisual[]
  isNight: boolean
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

export type OpticMode = 'OPTICAL' | 'THERMAL' | 'NVG'

export function CameraFeed({ camera, tracks, isNight, feedState = 'BUFFERING', lastFrameAgoSec = null, children }: CameraFeedProps) {
  const [opticMode, setOpticMode] = useState<OpticMode>(isNight ? 'NVG' : 'OPTICAL')
  const [videoLoaded, setVideoLoaded] = useState(false)
  const [videoFailed, setVideoFailed] = useState(false)
  const [currentTimeStr, setCurrentTimeStr] = useState('')
  const videoRef = useRef<HTMLVideoElement>(null)

  // Sync isNight prop
  useEffect(() => {
    if (isNight && opticMode === 'OPTICAL') {
      setOpticMode('NVG')
    } else if (!isNight && opticMode === 'NVG') {
      setOpticMode('OPTICAL')
    }
  }, [isNight])

  // Live military OSD clock with milliseconds
  useEffect(() => {
    const timer = setInterval(() => {
      const now = new Date()
      const pad = (n: number, d = 2) => String(n).padStart(d, '0')
      const ms = String(now.getMilliseconds()).padStart(3, '0').slice(0, 2)
      setCurrentTimeStr(
        `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())} ${pad(now.getHours())}:${pad(now.getMinutes())}:${pad(now.getSeconds())}.${ms} IST`
      )
    }, 60)
    return () => clearInterval(timer)
  }, [])

  const videoUrl = SURVEILLANCE_VIDEOS[camera.id] ?? SURVEILLANCE_VIDEOS['CAM-07']

  // Visual filter for thermal and night vision
  const getOpticFilterClass = () => {
    switch (opticMode) {
      case 'THERMAL':
        return 'contrast-[220%] invert hue-rotate-[185deg] saturate-[250%] brightness-[110%]'
      case 'NVG':
        return 'contrast-[160%] brightness-[120%] sepia hue-rotate-[85deg] saturate-[300%]'
      default:
        return 'contrast-[105%] saturate-[110%]'
    }
  }

  return (
    <div
      className="relative w-full overflow-hidden rounded-xl border border-[#1e2d40] bg-black shadow-2xl select-none"
      style={{ aspectRatio: FEED_ASPECT }}
    >
      {/* Background Video Layer */}
      {!videoFailed && (
        <video
          ref={videoRef}
          src={videoUrl}
          autoPlay
          loop
          muted
          playsInline
          onLoadedData={() => setVideoLoaded(true)}
          onError={() => setVideoFailed(true)}
          className={clsx(
            'absolute inset-0 h-full w-full object-cover transition-all duration-500',
            getOpticFilterClass(),
            videoLoaded ? 'opacity-90' : 'opacity-0'
          )}
        />
      )}

      {/* Fallback Tactical Scene (if video loading or failed) */}
      {(!videoLoaded || videoFailed) && (
        <div
          className={clsx(
            'absolute inset-0 transition-colors duration-700',
            opticMode !== 'OPTICAL'
              ? 'bg-[radial-gradient(ellipse_at_center,#0b1626_0%,#05080f_70%)]'
              : 'bg-[radial-gradient(ellipse_at_center,#1a2736_0%,#0a1119_70%)]'
          )}
        >
          <FeedScene isNight={opticMode !== 'OPTICAL'} />
        </div>
      )}

      {/* Surveillance Scanline / CRT Vignette Texture */}
      <div
        className="absolute inset-0 pointer-events-none opacity-20 bg-[repeating-linear-gradient(0deg,transparent,transparent_2px,rgba(0,0,0,0.4)_2px,rgba(0,0,0,0.4)_4px)]"
        aria-hidden
      />

      {/* Top HUD Info Bar */}
      <div className="absolute left-2 top-2 z-20 flex items-center gap-2">
        <span className="font-mono text-[10px] font-bold text-slate-200 bg-black/80 px-2 py-0.5 rounded border border-white/10 shadow">
          {camera.id}
        </span>
        <span className={clsx('flex items-center gap-1.5 rounded bg-black/80 px-2 py-0.5 font-mono text-[10px] border border-white/10', FEED_STATE_STYLE[feedState])} role="status">
          <span className="h-1.5 w-1.5 rounded-full bg-red-500 animate-pulse" aria-hidden />
          <span className="font-bold">REC ● LIVE SENSOR</span>
        </span>
        {videoLoaded && (
          <span className="hidden sm:inline font-mono text-[9px] text-[#2FD5E0] bg-[#2FD5E0]/10 px-1.5 py-0.5 rounded border border-[#2FD5E0]/30 tracking-wider">
            AI STREAM
          </span>
        )}
      </div>

      {/* Top Center: Military Grid Coordinates & Live Clock */}
      <div className="absolute top-2 left-1/2 -translate-x-1/2 z-20 hidden md:flex items-center gap-2 bg-black/75 px-3 py-0.5 rounded border border-white/10 font-mono text-[10px] text-slate-300">
        <span className="text-[#2FD5E0] font-bold">28°36'14"N 80°32'18"E</span>
        <span className="text-slate-600">|</span>
        <span className="tabular-nums text-slate-200">{currentTimeStr}</span>
      </div>

      {/* Top Right: Optics Switcher & Telemetry */}
      <div className="absolute right-2 top-2 z-20 flex items-center gap-1.5">
        <div className="flex items-center rounded-lg border border-white/10 bg-black/80 p-0.5 text-[9px] font-mono shadow">
          <button
            type="button"
            onClick={() => setOpticMode('OPTICAL')}
            className={clsx(
              'px-2 py-0.5 rounded transition-all',
              opticMode === 'OPTICAL' ? 'bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/40 shadow' : 'text-slate-400 hover:text-slate-200'
            )}
            title="Standard daytime optical feed"
          >
            OPTICAL
          </button>
          <button
            type="button"
            onClick={() => setOpticMode('THERMAL')}
            className={clsx(
              'px-2 py-0.5 rounded transition-all',
              opticMode === 'THERMAL' ? 'bg-amber-500/20 text-amber-300 font-bold border border-amber-500/40 shadow' : 'text-slate-400 hover:text-slate-200'
            )}
            title="FLIR Thermal heat signature mode"
          >
            THERMAL
          </button>
          <button
            type="button"
            onClick={() => setOpticMode('NVG')}
            className={clsx(
              'px-2 py-0.5 rounded transition-all',
              opticMode === 'NVG' ? 'bg-emerald-500/20 text-emerald-300 font-bold border border-emerald-500/40 shadow' : 'text-slate-400 hover:text-slate-200'
            )}
            title="Night-vision phosphor mode"
          >
            NVG IR
          </button>
        </div>

        <div className="hidden lg:flex items-center px-2 py-0.5 rounded bg-black/80 border border-white/10 font-mono text-[10px] text-slate-400 tabular-nums">
          {camera.resolution.width}×{camera.resolution.height} · {camera.fps} FPS
        </div>
      </div>

      {/* Track bounding boxes */}
      <svg
        viewBox={`0 0 ${FEED_VIEWBOX.width} ${FEED_VIEWBOX.height}`}
        className="absolute inset-0 h-full w-full pointer-events-none z-10"
        aria-hidden
      >
        {tracks.map(track => (
          <TrackBox key={track.track_id} track={track} />
        ))}
      </svg>

      {/* Virtual fence overlay (zones + editor gestures) */}
      <div className="absolute inset-0 z-10">
        <FenceOverlay />
      </div>

      {/* Thermal / NVG Color Tint Layer */}
      {opticMode === 'THERMAL' && (
        <div className="absolute inset-0 pointer-events-none bg-amber-500/10 mix-blend-color-dodge z-10" />
      )}
      {opticMode === 'NVG' && (
        <div className="absolute inset-0 pointer-events-none bg-emerald-500/15 mix-blend-overlay z-10" />
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