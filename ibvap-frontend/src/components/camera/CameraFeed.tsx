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
      className="relative w-full overflow-hidden rounded-xl border border-border bg-black shadow-2xl select-none"
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

      {/* Bottom-right: GPS coords + live clock (was top-center, moved to avoid overlap) */}
      <div className="absolute bottom-2 right-2 z-20 hidden md:flex items-center gap-2 bg-black/75 px-3 py-1 rounded border border-white/10 font-mono text-[10px] text-slate-300">
        <span className="text-[#2FD5E0] font-bold">28°36'14"N 80°32'18"E</span>
        <span className="text-slate-600">|</span>
        <span className="tabular-nums text-slate-200">{currentTimeStr}</span>
      </div>

      {/* Bottom-left: Optics Switcher */}
      <div className="absolute left-2 bottom-2 z-20 flex items-center gap-1.5">
        <div className="flex items-center rounded-lg border border-white/10 bg-black/80 p-0.5 text-[9px] font-mono shadow">
          <button
            type="button"
            onClick={() => setOpticMode('OPTICAL')}
            className={clsx(
              'px-2 py-0.5 rounded transition-all',
              opticMode === 'OPTICAL' ? 'bg-cyan-500/20 text-cyan-300 font-bold border border-cyan-500/40 shadow' : 'text-slate-500 hover:text-slate-200'
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
              opticMode === 'THERMAL' ? 'bg-amber-500/20 text-amber-300 font-bold border border-amber-500/40 shadow' : 'text-slate-500 hover:text-slate-200'
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
              opticMode === 'NVG' ? 'bg-emerald-500/20 text-emerald-300 font-bold border border-emerald-500/40 shadow' : 'text-slate-500 hover:text-slate-200'
            )}
            title="Night-vision phosphor mode"
          >
            NVG IR
          </button>
        </div>
        <div className="hidden lg:flex items-center px-2 py-0.5 rounded bg-black/80 border border-white/10 font-mono text-[10px] text-slate-500 tabular-nums">
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
  const isHuman = track.object_type === 'HUMAN'
  const isVehicle = track.object_type === 'VEHICLE'
  const color = isHuman ? '#22d3ee' : isVehicle ? '#f59e0b' : '#34d399'
  const label = isHuman ? 'PERSON' : isVehicle ? 'VEHICLE' : 'UNKNOWN'
  const x = bbox.x * FEED_VIEWBOX.width
  const y = bbox.y * FEED_VIEWBOX.height
  const w = bbox.width * FEED_VIEWBOX.width
  const h = bbox.height * FEED_VIEWBOX.height
  const cs = 10 // corner size
  const conf = (track.confidence * 100).toFixed(0)

  return (
    <g>
      {/* Corner markers instead of full rect — much cleaner look */}
      {/* Top-left */}
      <path d={`M${x + cs},${y} L${x},${y} L${x},${y + cs}`} fill="none" stroke={color} strokeWidth={2.5} strokeLinecap="round" />
      {/* Top-right */}
      <path d={`M${x + w - cs},${y} L${x + w},${y} L${x + w},${y + cs}`} fill="none" stroke={color} strokeWidth={2.5} strokeLinecap="round" />
      {/* Bottom-left */}
      <path d={`M${x},${y + h - cs} L${x},${y + h} L${x + cs},${y + h}`} fill="none" stroke={color} strokeWidth={2.5} strokeLinecap="round" />
      {/* Bottom-right */}
      <path d={`M${x + w - cs},${y + h} L${x + w},${y + h} L${x + w},${y + h - cs}`} fill="none" stroke={color} strokeWidth={2.5} strokeLinecap="round" />
      {/* Center crosshair dot */}
      <circle cx={x + w / 2} cy={y + h / 2} r={2.5} fill={color} opacity={0.6} />

      {/* Label badge — above box */}
      <g transform={`translate(${x}, ${Math.max(4, y - 22)})`}>
        <rect width={154} height={20} rx={4} fill="#050e18" fillOpacity={0.92} stroke={color} strokeWidth={1} strokeOpacity={0.7} />
        {/* Colored type indicator */}
        <rect width={4} height={20} rx={2} fill={color} opacity={0.8} />
        <text x={12} y={13.5} fontSize={10} fontFamily="JetBrains Mono, ui-monospace, monospace" fill={color} fontWeight="bold">
          {label}
        </text>
        <text x={72} y={13.5} fontSize={10} fontFamily="JetBrains Mono, ui-monospace, monospace" fill="#94a3b8">
          {track.track_id}
        </text>
        <text x={126} y={13.5} fontSize={10} fontFamily="JetBrains Mono, ui-monospace, monospace" fill={Number(conf) >= 80 ? '#34d399' : '#fbbf24'}>
          {conf}%
        </text>
      </g>

      {/* Zone warning below */}
      {track.insideZones.length > 0 && (
        <g transform={`translate(${x + w / 2}, ${y + h + 8})`}>
          <rect x={-62} y={0} width={124} height={16} rx={3} fill="#7c2020" fillOpacity={0.85} stroke="#fb7185" strokeWidth={1} />
          <text textAnchor="middle" y={11} fontSize={9} fontFamily="JetBrains Mono, ui-monospace, monospace" fill="#fb7185" fontWeight="bold">
            ▲ ZONE: {track.insideZones.join(' · ')}
          </text>
        </g>
      )}
    </g>
  )
}

/** Clear surveillance-style fallback scene — border terrain, fence, watchtower, road */
function FeedScene({ isNight }: { isNight: boolean }) {
  const sky    = isNight ? '#08111c' : '#111f2e'
  const ground = isNight ? '#0c1520' : '#14202e'
  const fence  = isNight ? '#2a4060' : '#3a5478'
  const road   = isNight ? '#121c28' : '#1c2c3c'
  const label  = isNight ? '#3a6080' : '#4a7898'
  const grid   = isNight ? '#0f1e2c' : '#182840'
  const glow   = isNight ? '#1a3a5a' : '#223040'

  return (
    <svg
      viewBox={`0 0 ${FEED_VIEWBOX.width} ${FEED_VIEWBOX.height}`}
      className="h-full w-full"
      aria-hidden
    >
      <defs>
        <linearGradient id="ff-sky" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={sky} />
          <stop offset="100%" stopColor={isNight ? '#060c14' : '#0e1a26'} />
        </linearGradient>
        <linearGradient id="ff-ground" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={ground} />
          <stop offset="100%" stopColor={isNight ? '#070e18' : '#101c28'} />
        </linearGradient>
        {/* Night starfield scatter */}
        {isNight && (
          <radialGradient id="ff-glow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor="#1a4060" stopOpacity="0.3" />
            <stop offset="100%" stopColor="#1a4060" stopOpacity="0" />
          </radialGradient>
        )}
      </defs>

      {/* Sky */}
      <rect width={FEED_VIEWBOX.width} height={FEED_VIEWBOX.height * 0.55} fill="url(#ff-sky)" />

      {/* Stars (night only) */}
      {isNight && [
        [120,40],[280,20],[410,55],[560,30],[700,18],[820,42],[940,28],
        [60,80],[350,75],[620,65],[850,70],[180,95],[480,88],[730,82],
      ].map(([sx,sy],i) => (
        <circle key={i} cx={sx} cy={sy} r={0.8} fill="#a0c8e0" opacity={0.5 + (i % 3) * 0.15} />
      ))}

      {/* Tree/hill silhouette */}
      <path
        d={`M0 ${FEED_VIEWBOX.height * 0.38} Q80 ${FEED_VIEWBOX.height * 0.32} 160 ${FEED_VIEWBOX.height * 0.36} T320 ${FEED_VIEWBOX.height * 0.34} T480 ${FEED_VIEWBOX.height * 0.37} T640 ${FEED_VIEWBOX.height * 0.33} T800 ${FEED_VIEWBOX.height * 0.36} T${FEED_VIEWBOX.width} ${FEED_VIEWBOX.height * 0.35} L${FEED_VIEWBOX.width} 0 L0 0Z`}
        fill={isNight ? '#0a1820' : '#121e2c'}
        opacity={0.7}
      />

      {/* Ground */}
      <rect y={FEED_VIEWBOX.height * 0.55} width={FEED_VIEWBOX.width} height={FEED_VIEWBOX.height * 0.45} fill="url(#ff-ground)" />

      {/* Perspective grid lines on ground */}
      {Array.from({ length: 10 }, (_, i) => (
        <line
          key={`v${i}`}
          x1={100 + i * 90} y1={FEED_VIEWBOX.height * 0.55}
          x2={-200 + i * 175} y2={FEED_VIEWBOX.height}
          stroke={grid} strokeWidth={1} opacity={0.8}
        />
      ))}
      {Array.from({ length: 5 }, (_, i) => (
        <line
          key={`h${i}`}
          x1={0} y1={FEED_VIEWBOX.height * 0.55 + i * (FEED_VIEWBOX.height * 0.45 / 5)}
          x2={FEED_VIEWBOX.width} y2={FEED_VIEWBOX.height * 0.55 + i * (FEED_VIEWBOX.height * 0.45 / 5)}
          stroke={grid} strokeWidth={1} opacity={0.6}
        />
      ))}

      {/* Patrol road */}
      <path
        d={`M${FEED_VIEWBOX.width * 0.25} ${FEED_VIEWBOX.height} L${FEED_VIEWBOX.width * 0.38} ${FEED_VIEWBOX.height * 0.58} L${FEED_VIEWBOX.width * 0.72} ${FEED_VIEWBOX.height * 0.58} L${FEED_VIEWBOX.width * 0.85} ${FEED_VIEWBOX.height}`}
        fill={road} opacity={0.9}
      />
      {/* Road center line */}
      <path
        d={`M${FEED_VIEWBOX.width * 0.315} ${FEED_VIEWBOX.height * 0.85} L${FEED_VIEWBOX.width * 0.385} ${FEED_VIEWBOX.height * 0.6}`}
        stroke={isNight ? '#1a3040' : '#253848'} strokeWidth={2} strokeDasharray="8 6" opacity={0.6}
      />

      {/* Border fence line */}
      <line
        x1={0} y1={FEED_VIEWBOX.height * 0.58}
        x2={FEED_VIEWBOX.width} y2={FEED_VIEWBOX.height * 0.58}
        stroke={fence} strokeWidth={2.5}
      />
      {/* Fence posts */}
      {Array.from({ length: 16 }, (_, i) => (
        <g key={i}>
          <line
            x1={60 + i * 62} y1={FEED_VIEWBOX.height * 0.52}
            x2={60 + i * 62} y2={FEED_VIEWBOX.height * 0.6}
            stroke={fence} strokeWidth={2}
          />
          <line
            x1={60 + i * 62 - 8} y1={FEED_VIEWBOX.height * 0.52}
            x2={60 + i * 62 + 8} y2={FEED_VIEWBOX.height * 0.52}
            stroke={fence} strokeWidth={1.5} opacity={0.6}
          />
        </g>
      ))}
      {/* Fence label */}
      <rect x={8} y={FEED_VIEWBOX.height * 0.505} width={140} height={16} rx={3} fill="#050e18" fillOpacity={0.85} />
      <text x={14} y={FEED_VIEWBOX.height * 0.521} fontSize={10} fontFamily="ui-monospace, monospace" fill={fence} fontWeight="600" dominantBaseline="middle">
        PARAKH VIRTUAL FENCE
      </text>

      {/* Watchtower — left */}
      <g transform={`translate(148, ${FEED_VIEWBOX.height * 0.35})`}>
        {/* Tower body */}
        <rect x={0} y={0} width={52} height={90} fill={isNight ? '#142030' : '#1e3040'} />
        {/* Windows */}
        <rect x={6} y={8} width={18} height={14} fill="#08131e" stroke={glow} strokeWidth={0.5} />
        <rect x={28} y={8} width={18} height={14} fill="#08131e" stroke={glow} strokeWidth={0.5} />
        {/* Roof */}
        <path d="M-6 0 L26 -20 L58 0Z" fill={isNight ? '#1a2e3e' : '#263a4e'} />
        {/* Antenna */}
        <line x1={26} y1={-20} x2={26} y2={-38} stroke={isNight ? '#3a6080' : '#4a7090'} strokeWidth={2} />
        {/* Light */}
        <circle cx={26} cy={-40} r={4} fill={isNight ? '#f59e0b' : '#e11d48'} opacity={0.9} />
        {isNight && <circle cx={26} cy={-40} r={10} fill="#f59e0b" opacity={0.15} />}
        {/* CCTV arm */}
        <line x1={52} y1={15} x2={68} y2={10} stroke={fence} strokeWidth={2} />
        <rect x={68} y={6} width={12} height={8} rx={2} fill={isNight ? '#22d3ee' : '#2a90b0'} opacity={0.8} />
      </g>

      {/* Label: ENTRY POST */}
      <rect x={140} y={FEED_VIEWBOX.height * 0.35 + 92} width={70} height={14} rx={3} fill="#050e18" fillOpacity={0.8} />
      <text x={175} y={FEED_VIEWBOX.height * 0.35 + 102} textAnchor="middle" fontSize={9} fontFamily="ui-monospace, monospace" fill={label}>
        ENTRY POST
      </text>

      {/* Perimeter light cone (night) */}
      {isNight && (
        <path
          d={`M174 ${FEED_VIEWBOX.height * 0.38} L60 ${FEED_VIEWBOX.height * 0.65} L290 ${FEED_VIEWBOX.height * 0.65}Z`}
          fill="#f59e0b" opacity={0.04}
        />
      )}

      {/* HUD corner reticle */}
      <g opacity={0.3}>
        <path d="M16 16 L16 28 M16 16 L28 16" stroke={isNight ? '#22d3ee' : '#3a7090'} strokeWidth={1.5} strokeLinecap="round" />
        <path d={`M${FEED_VIEWBOX.width - 16} 16 L${FEED_VIEWBOX.width - 28} 16 M${FEED_VIEWBOX.width - 16} 16 L${FEED_VIEWBOX.width - 16} 28`} stroke={isNight ? '#22d3ee' : '#3a7090'} strokeWidth={1.5} strokeLinecap="round" />
        <path d={`M16 ${FEED_VIEWBOX.height - 16} L28 ${FEED_VIEWBOX.height - 16} M16 ${FEED_VIEWBOX.height - 16} L16 ${FEED_VIEWBOX.height - 28}`} stroke={isNight ? '#22d3ee' : '#3a7090'} strokeWidth={1.5} strokeLinecap="round" />
        <path d={`M${FEED_VIEWBOX.width - 16} ${FEED_VIEWBOX.height - 16} L${FEED_VIEWBOX.width - 28} ${FEED_VIEWBOX.height - 16} M${FEED_VIEWBOX.width - 16} ${FEED_VIEWBOX.height - 16} L${FEED_VIEWBOX.width - 16} ${FEED_VIEWBOX.height - 28}`} stroke={isNight ? '#22d3ee' : '#3a7090'} strokeWidth={1.5} strokeLinecap="round" />
      </g>

      {/* Mode label bottom-right */}
      <rect x={FEED_VIEWBOX.width - 130} y={FEED_VIEWBOX.height - 26} width={122} height={18} rx={4} fill="#050e18" fillOpacity={0.85} />
      <text
        x={FEED_VIEWBOX.width - 69}
        y={FEED_VIEWBOX.height - 14}
        textAnchor="middle"
        fontSize={10}
        fontFamily="ui-monospace, monospace"
        fill={isNight ? '#34d399' : '#60a8c8'}
        fontWeight="600"
      >
        {isNight ? 'NVG IR · STANDBY' : 'OPTICAL · STANDBY'}
      </text>
    </svg>
  )
}