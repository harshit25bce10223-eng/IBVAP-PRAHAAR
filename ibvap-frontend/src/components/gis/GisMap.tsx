// ─────────────────────────────────────────────────────────────────────────────
// GisMap — dominant operational GIS / digital-twin canvas (SVG).
//
// The visual centre of the screen: terrain, border reference, restricted zone +
// virtual fence, risk heatmap, historical activity, entity trajectory and
// camera/incident markers. Interactions follow spec §13:
//   camera / track  → navigate to existing detail routes
//   incident/zone/hotspot → select context in the bottom strip
//
// No external GIS library — lightweight SVG for the prototype; real map
// providers swap in at the service seam.
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'
import { useNavigate } from 'react-router-dom'
import { riskBandFor } from '@/types/commandDashboard'
import type { GisData, GisLayerId, GisSelection, GisTimeWindow } from '@/types'

interface Props {
  data: GisData
  activeLayers: Set<GisLayerId>
  window: GisTimeWindow
  onSelect: (selection: GisSelection) => void
  selectedRef?: string
  className?: string
}

const HEAT_COLOR = { LOW: '#0B5D3B', MEDIUM: '#F4B942', HIGH: '#D62828' } as const
const WINDOW_FILTER: Record<GisTimeWindow, (w: GisTimeWindow) => boolean> = {
  LIVE: () => false,
  '24H': w => w === '24H',
  '7D': () => true,
}

export function GisMap({ data, activeLayers, window, onSelect, selectedRef, className }: Props) {
  const navigate = useNavigate()
  const show = (layer: GisLayerId) => activeLayers.has(layer)

  const historical = window === 'LIVE'
    ? []
    : data.historicalActivity.filter(h => WINDOW_FILTER[window](h.window))

  const camRef = (id: string) => String(id)

  return (
    <div className={clsx('relative rounded-md border border-ssb-border/70 overflow-hidden bg-ssb-navy-deep min-h-0 min-w-0', className)}>
      <svg
        viewBox="0 0 1200 520"
        className="w-full h-full"
        preserveAspectRatio="xMidYMid meet"
        aria-label="Operational GIS map — border sector terrain, cameras, trajectories, risk hotspots"
      >
        <defs>
          <linearGradient id="gisTerrain" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor="#0B1F33" />
            <stop offset="45%"  stopColor="#0C2B2B" />
            <stop offset="100%" stopColor="#0B1F33" />
          </linearGradient>

          {data.riskHeat.map(hot => (
            <radialGradient key={hot.id} id={`heat-${hot.id}`} cx="0.5" cy="0.5" r="0.5">
              <stop offset="0%"   stopColor={HEAT_COLOR[hot.level]} stopOpacity={hot.level === 'HIGH' ? 0.24 : hot.level === 'MEDIUM' ? 0.18 : 0.12} />
              <stop offset="55%"  stopColor={HEAT_COLOR[hot.level]} stopOpacity={hot.level === 'HIGH' ? 0.1 : 0.06} />
              <stop offset="100%" stopColor={HEAT_COLOR[hot.level]} stopOpacity="0" />
            </radialGradient>
          ))}
        </defs>

        {/* Base terrain */}
        <rect width="1200" height="520" fill="url(#gisTerrain)" />

        {/* Reference grid (very subtle) */}
        {[200, 400, 600, 800, 1000].map(x => (
          <line key={`gv${x}`} x1={x} y1={0} x2={x} y2={520} stroke="#FFFFFF" strokeWidth={0.4} strokeOpacity={0.04} />
        ))}
        {[100, 200, 300, 400].map(y => (
          <line key={`gh${y}`} x1={0} y1={y} x2={1200} y2={y} stroke="#FFFFFF" strokeWidth={0.4} strokeOpacity={0.04} />
        ))}

        {/* Hilly terrain (elevation context) */}
        {data.terrain.hillPaths.map((d, i) => (
          <path key={`h${i}`} d={d} fill="#0B2A1F" fillOpacity={0.35 - i * 0.02} />
        ))}

        {/* Forest canopy */}
        {data.terrain.forestPaths.map((d, i) => (
          <path key={`f${i}`} d={d} fill="#0B5D3B" fillOpacity={0.1 + i * 0.015} />
        ))}

        {/* Sector roads / patrol trails */}
        {data.terrain.roadPaths.map((d, i) => (
          <path key={`r${i}`} d={d} fill="none" stroke="#FFFFFF" strokeWidth={0.9} strokeOpacity={0.12} strokeDasharray="3 3" />
        ))}

        {/* Sector boundary (faint operational footprint) */}
        <rect
          x={22} y={64} width={1156} height={432}
          fill="none" stroke="#FFFFFF" strokeOpacity={0.1} strokeWidth={0.8} strokeDasharray="10 6"
        />
        <text x="26" y="78" fill="#FFFFFF" fillOpacity={0.28} fontSize="9" fontFamily="monospace" letterSpacing="1.5">
          {data.sectorRef} · OPERATIONAL BOUNDARY
        </text>

        {/* Border reference — INDIA — NEPAL */}
        <path
          d={data.borderRef.path}
          fill="none"
          stroke="#FFFFFF"
          strokeWidth={1.4}
          strokeDasharray="8 4"
          strokeOpacity={0.45}
        />
        <text x="18" y="200" fill="#FFFFFF" fillOpacity={0.4} fontSize="9" fontFamily="monospace" letterSpacing="2">
          {data.borderRef.label}
        </text>

        {/* Risk heatmap */}
        {show('riskHeat') && data.riskHeat.map(hot => (
          <g key={hot.id} role="button" aria-label={`Risk hotspot ${hot.label}`} className="cursor-pointer"
             onClick={() => onSelect({ type: 'hotspot', hotspot: hot })}>
            <circle cx={hot.x} cy={hot.y} r={hot.radius} fill={`url(#heat-${hot.id})`} />
            <circle
              cx={hot.x} cy={hot.y} r={hot.radius}
              fill="none" stroke={HEAT_COLOR[hot.level]} strokeOpacity={0.35} strokeWidth={0.8} strokeDasharray="4 4"
            />
          </g>
        ))}

        {/* Restricted zones + virtual fence */}
        {show('restrictedZones') && data.zones.map(zone => {
          const restricted = zone.kind === 'RESTRICTED'
          const fence = zone.kind === 'FENCE'
          if (zone.kind === 'FOREST') return null
          return (
            <g key={zone.id} role="button" aria-label={`Zone ${zone.label}`} className="cursor-pointer"
               onClick={() => onSelect({ type: 'zone', zone })}>
              <path
                d={zone.path}
                fill={restricted ? '#F4B942' : 'none'}
                fillOpacity={restricted ? 0.06 : 0}
                stroke={fence ? '#22D3EE' : '#F4B942'}
                strokeWidth={fence ? 1.1 : 1.3}
                strokeDasharray={fence ? '7 4' : '5 4'}
                strokeOpacity={0.6}
              />
              <text
                x={restricted ? 415 : 60}
                y={restricted ? 205 : 213}
                textAnchor="middle"
                fill={fence ? '#22D3EE' : '#F4B942'}
                fillOpacity={0.6}
                fontSize="8"
                fontFamily="monospace"
                letterSpacing="1.2"
              >
                {zone.label}
              </text>
            </g>
          )
        })}

        {/* Historical activity markers (repeated pattern locations) */}
        {show('historical') && historical.map(act => (
          <g key={act.id} role="button" aria-label={`Historical ${act.label}`} className="cursor-pointer"
             onClick={() => onSelect({ type: 'historical', activity: act })}>
            <rect
              x={act.x - 5} y={act.y - 5} width={10} height={10}
              fill="#5A6578" fillOpacity={0.55} stroke="#FFFFFF" strokeOpacity={0.4} strokeWidth={0.6}
              transform={`rotate(45 ${act.x} ${act.y})`}
            />
            <text x={act.x + 9} y={act.y + 3} fill="#FFFFFF" fillOpacity={0.5} fontSize="8" fontFamily="monospace">
              ×{act.count}
            </text>
          </g>
        ))}

        {/* Entity trajectory — TRK-014 (major visual element) */}
        {show('tracks') && data.tracks.map(track => {
          const line = track.points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ')
          const mid = track.points[2] ?? track.points[0]
          return (
            <g key={track.id}>
              <path d={line} fill="none" stroke="#22D3EE" strokeWidth={2} strokeOpacity={0.9} />
              {/* Direction arrows along each leg */}
              {track.points.slice(0, -1).map((p, i) => {
                const nxt = track.points[i + 1]
                const dx = nxt.x - p.x
                const dy = nxt.y - p.y
                const len = Math.hypot(dx, dy)
                if (len === 0) return null
                const ux = dx / len
                const uy = dy / len
                const ax = p.x + dx * 0.55
                const ay = p.y + dy * 0.55
                const px = -uy
                const py = ux
                return (
                  <polygon
                    key={i}
                    points={`${ax - px * 5},${ay - py * 5} ${ax + ux * 9},${ay + uy * 9} ${ax + px * 5},${ay + py * 5}`}
                    fill="#22D3EE"
                    fillOpacity={0.85}
                  />
                )
              })}
              {/* Waypoints with timestamps */}
              {track.points.map((p, i) => (
                <g key={i}>
                  <circle cx={p.x} cy={p.y} r={3} fill="#0B1F33" stroke="#22D3EE" strokeWidth={1} />
                  <text x={p.x + (i % 2 === 0 ? 7 : -7)} y={p.y + (i % 2 === 0 ? -4 : 12)}
                        textAnchor={i % 2 === 0 ? 'start' : 'end'}
                        fill="#22D3EE" fillOpacity={0.85} fontSize="8" fontFamily="monospace">
                    {p.at}
                  </text>
                </g>
              ))}
              {/* Start & direction context */}
              <text x={track.points[0].x} y={track.points[0].y - 12} fill="#22D3EE" fontSize="7" fontFamily="monospace" letterSpacing="0.5" fontWeight="600">
                START CAM-01
              </text>
              <text x={mid.x} y={mid.y - 16} fill="#22D3EE" fillOpacity={0.7} fontSize="7" fontFamily="monospace" letterSpacing="0.5">
                DIRECTION {track.direction}
              </text>
              {/* Camera transition callout */}
              {track.cameraTransitions[1] && (
                <g>
                  <line
                    x1={track.cameraTransitions[1].from === 'CAM-01' ? 430 : 492}
                    y1={track.cameraTransitions[1].from === 'CAM-01' ? 250 : 170}
                    x2={track.cameraTransitions[1].from === 'CAM-01' ? 492 : 560}
                    y2={track.cameraTransitions[1].from === 'CAM-01' ? 168 : 150}
                    stroke="#22D3EE" strokeWidth={0.6} strokeOpacity={0.4} strokeDasharray="3 3"
                  />
                  <text x="405" y="150" fill="#22D3EE" fillOpacity={0.55} fontSize="7.5" fontFamily="monospace">
                    22:46 · CROSS-CAMERA MATCH
                  </text>
                </g>
              )}
            </g>
          )
        })}

        {/* Cameras */}
        {show('cameras') && data.cameras.map(cam => {
          const color = cam.state === 'DEGRADED' ? '#F4B942' : cam.state === 'OFFLINE' ? '#5A6578' : '#0B5D3B'
          return (
            <g key={cam.id} role="button" aria-label={`Camera ${cam.id}`} className="cursor-pointer"
               onClick={() => navigate(`/camera/${cam.id}`)}>
              {cam.state === 'ONLINE' && (
                <circle cx={cam.x} cy={cam.y} r={13} fill="none" stroke={color} strokeOpacity={0.35} strokeWidth={0.7} />
              )}
              <rect x={cam.x - 7} y={cam.y - 7} width={14} height={14} rx={3}
                    fill={color} stroke="#FFFFFF" strokeOpacity={0.45} strokeWidth={0.8} />
              <line x1={cam.x} y1={cam.y - 3} x2={cam.x} y2={cam.y + 3} stroke="#FFFFFF" strokeWidth={0.7} strokeOpacity={0.7} />
              <line x1={cam.x - 3} y1={cam.y} x2={cam.x + 3} y2={cam.y} stroke="#FFFFFF" strokeWidth={0.7} strokeOpacity={0.7} />
              <text x={cam.x} y={cam.y - 13} textAnchor="middle" fill={cam.state === 'DEGRADED' ? '#F4B942' : '#22D3EE'}
                    fontSize="8.5" fontFamily="monospace" fontWeight="600" letterSpacing="0.5">
                {camRef(cam.id)}
              </text>
            </g>
          )
        })}

        {/* Incidents */}
        {show('incidents') && data.incidents.map(inc => {
          const active = selectedRef === inc.id
          const band = riskBandFor(inc.riskScore) === 'HIGH' ? '#D62828' : '#F4B942'
          return (
            <g key={inc.id} role="button" aria-label={`Incident ${inc.id}`} className="cursor-pointer"
               onClick={() => onSelect({ type: 'incident', incident: inc })}>
              <circle cx={inc.x} cy={inc.y} r={active ? 20 : 16} fill="none" stroke={band} strokeOpacity={active ? 0.5 : 0.25} strokeWidth={0.8} />
              <polygon points={`${inc.x},${inc.y - 12} ${inc.x + 10},${inc.y + 6} ${inc.x - 10},${inc.y + 6}`}
                       fill={band} fillOpacity={0.92} stroke="#FFFFFF" strokeOpacity={0.5} strokeWidth={0.8} />
              <text x={inc.x} y={inc.y + 2} textAnchor="middle" fill="#FFFFFF" fontSize="6" fontFamily="monospace" fontWeight="700">
                !
              </text>
              <text x={inc.x} y={inc.y - 18} textAnchor="middle" fill={band} fontSize="8.5" fontFamily="monospace" fontWeight="700" letterSpacing="0.5">
                {inc.id}
              </text>
            </g>
          )
        })}
      </svg>

      {/* Coordinates overlay (top-right, restrained) */}
      <div className="absolute top-2 right-2 rounded bg-ssb-navy/90 border border-ssb-border/50 px-2 py-1">
        <span className="text-[9px] font-mono text-ssb-text-muted tracking-wider">
          {data.sectorRef} · {data.coords}
        </span>
      </div>
    </div>
  )
}