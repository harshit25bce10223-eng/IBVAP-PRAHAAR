// ─────────────────────────────────────────────────────────────────────────────
// RouteMap — dominant operational route analysis canvas (SVG).
//
// The visual centre of the screen: terrain, border reference, restricted zones,
// camera coverage, incidents, and three candidate routes with risk coloring.
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'
import type { RouteAnalysisData, RouteCandidate, RouteIncident, RouteCameraCoverage, RouteRestrictedZone, RouteTimeWindow } from '@/types'

interface Props {
  data: RouteAnalysisData
  timeWindow: RouteTimeWindow
  selectedRouteId: string | null
  onRouteSelect: (routeId: string | null) => void
  className?: string
}

const SEVERITY_COLOR = { LOW: '#0B5D3B', MEDIUM: '#F4B942', HIGH: '#D62828', CRITICAL: '#D62828' } as const
const ROUTE_COLORS = {
  'ROUTE-A': { main: '#F4B942', dash: '#F4B942' },     // Amber
  'ROUTE-B': { main: '#0B5D3B', dash: '#0B5D3B' },     // Green
  'ROUTE-C': { main: '#5A6578', dash: '#5A6578' },     // Neutral gray
} as const

const WINDOW_FILTER: Record<RouteTimeWindow, (inc: RouteIncident) => boolean> = {
  LIVE: inc => inc.band === 'HIGH' || inc.band === 'CRITICAL',
  '24H': inc => inc.id === 'INC-024' || inc.id === 'INC-031',
  '7D': inc => true,
  '30D': inc => true,
}

function interpolatePath(path: string, t: number): { x: number; y: number } {
  // Simple path interpolation for arrow markers
  // Parse path commands
  const coords: { x: number; y: number }[] = []
  const parts = path.replace(/[ML]/g, ' ').trim().split(/\s+/)
  for (let i = 0; i < parts.length; i += 2) {
    coords.push({ x: parseFloat(parts[i]), y: parseFloat(parts[i + 1]) })
  }
  if (coords.length < 2) return coords[0] ?? { x: 0, y: 0 }

  // Calculate total length
  let totalLen = 0
  const segments: { len: number; start: { x: number; y: number }; end: { x: number; y: number } }[] = []
  for (let i = 1; i < coords.length; i++) {
    const dx = coords[i].x - coords[i - 1].x
    const dy = coords[i].y - coords[i - 1].y
    const len = Math.hypot(dx, dy)
    totalLen += len
    segments.push({ len, start: coords[i - 1], end: coords[i] })
  }

  const target = totalLen * t
  let acc = 0
  for (const seg of segments) {
    if (acc + seg.len >= target) {
      const localT = (target - acc) / seg.len
      return {
        x: seg.start.x + (seg.end.x - seg.start.x) * localT,
        y: seg.start.y + (seg.end.y - seg.start.y) * localT,
      }
    }
    acc += seg.len
  }
  return coords[coords.length - 1]
}

export function RouteMap({
  data,
  timeWindow,
  selectedRouteId,
  onRouteSelect,
  className,
}: Props) {
  const { origin, destination, routes, incidents, cameraCoverage, restrictedZones, terrain, borderRef } = data

  const showIncidents = incidents.filter(WINDOW_FILTER[timeWindow])
  const isRouteSelected = (id: string) => selectedRouteId === id

  return (
    <div className={clsx('relative rounded-md border border-ssb-border/70 overflow-hidden bg-ssb-navy-deep min-h-0 min-w-0', className)}>
      <svg
        viewBox="0 0 1200 520"
        className="w-full h-full"
        preserveAspectRatio="xMidYMid meet"
        aria-label="Operational route analysis map — terrain, routes, incidents, cameras, restricted zones"
        role="img"
      >
        <defs>
          <linearGradient id="routeTerrain" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor="#0B1F33" />
            <stop offset="45%"  stopColor="#0C2B2B" />
            <stop offset="100%" stopColor="#0B1F33" />
          </linearGradient>

          {/* Route gradient definitions for selected highlight */}
          {routes.map(route => (
            <linearGradient key={`grad-${route.id}`} id={`route-grad-${route.id}`} gradientUnits="userSpaceOnUse"
              x1={route.geometry.points[0]?.x ?? 0} y1={route.geometry.points[0]?.y ?? 0}
              x2={route.geometry.points[route.geometry.points.length - 1]?.x ?? 0} y2={route.geometry.points[route.geometry.points.length - 1]?.y ?? 0}>
              <stop offset="0%" stopColor={ROUTE_COLORS[route.id as keyof typeof ROUTE_COLORS]?.main ?? '#0B5D3B'} stopOpacity={isRouteSelected(route.id) ? 1 : 0.6} />
              <stop offset="100%" stopColor={ROUTE_COLORS[route.id as keyof typeof ROUTE_COLORS]?.main ?? '#0B5D3B'} stopOpacity={isRouteSelected(route.id) ? 1 : 0.4} />
            </linearGradient>
          ))}

          {/* Camera coverage gradients */}
          {cameraCoverage.map(cam => (
            <radialGradient key={`cov-${cam.id}`} id={`cov-${cam.id}`} cx="0.5" cy="0.5" r="0.5">
              <stop offset="0%" stopColor="#0B5D3B" stopOpacity={cam.coverageQuality === 'HIGH' ? 0.15 : cam.coverageQuality === 'MEDIUM' ? 0.1 : 0.05} />
              <stop offset="70%" stopColor="#0B5D3B" stopOpacity="0" />
            </radialGradient>
          ))}

          {/* Incident pulse for HIGH/CRITICAL */}
          <radialGradient id="incident-pulse" cx="0.5" cy="0.5" r="0.5">
            <stop offset="0%" stopColor="#D62828" stopOpacity="0.3" />
            <stop offset="50%" stopColor="#D62828" stopOpacity="0.1" />
            <stop offset="100%" stopColor="#D62828" stopOpacity="0" />
          </radialGradient>
        </defs>

        {/* Base terrain */}
        <rect width="1200" height="520" fill="url(#routeTerrain)" />

        {/* Reference grid (very subtle) */}
        {[200, 400, 600, 800, 1000].map(x => (
          <line key={`gv${x}`} x1={x} y1={0} x2={x} y2={520} stroke="#FFFFFF" strokeWidth={0.4} strokeOpacity={0.03} />
        ))}
        {[100, 200, 300, 400].map(y => (
          <line key={`gh${y}`} x1={0} y1={y} x2={1200} y2={y} stroke="#FFFFFF" strokeWidth={0.4} strokeOpacity={0.03} />
        ))}

        {/* Water / streams */}
        {terrain.waterPaths.map((d, i) => (
          <path key={`w${i}`} d={d} fill="none" stroke="#1E3A5F" strokeWidth={1.2} strokeOpacity={0.25} strokeDasharray="4 3" />
        ))}

        {/* Hilly terrain (elevation context) */}
        {terrain.hillPaths.map((d, i) => (
          <path key={`h${i}`} d={d} fill="#0B2A1F" fillOpacity={0.3 - i * 0.02} />
        ))}

        {/* Forest canopy */}
        {terrain.forestPaths.map((d, i) => (
          <path key={`f${i}`} d={d} fill="#0B5D3B" fillOpacity={0.08 + i * 0.01} />
        ))}

        {/* Sector roads / patrol trails */}
        {terrain.roadPaths.map((d, i) => (
          <path key={`r${i}`} d={d} fill="none" stroke="#FFFFFF" strokeWidth={0.8} strokeOpacity={0.1} strokeDasharray="3 3" />
        ))}

        {/* Border fence */}
        {terrain.fencePaths.map((d, i) => (
          <path key={`fnc${i}`} d={d} fill="none" stroke="#F4B942" strokeWidth={1.2} strokeOpacity={0.35} strokeDasharray="6 4" />
        ))}

        {/* Sector boundary (faint operational footprint) */}
        <rect
          x={22} y={64} width={1156} height={432}
          fill="none" stroke="#FFFFFF" strokeOpacity={0.08} strokeWidth={0.8} strokeDasharray="10 6"
        />
        <text x="26" y="78" fill="#FFFFFF" fillOpacity={0.25} fontSize="9" fontFamily="monospace" letterSpacing="1.5">
          {data.sectorRef} · OPERATIONAL BOUNDARY
        </text>

        {/* Border reference — INDIA — NEPAL */}
        <path
          d={borderRef.path}
          fill="none"
          stroke="#FFFFFF"
          strokeWidth={1.4}
          strokeDasharray="8 4"
          strokeOpacity={0.4}
        />
        <text x="18" y="200" fill="#FFFFFF" fillOpacity={0.35} fontSize="9" fontFamily="monospace" letterSpacing="2">
          {borderRef.label}
        </text>

        {/* Camera coverage areas (behind routes) */}
        {cameraCoverage.map(cam => {
          if (cam.state === 'OFFLINE') return null
          const color = cam.state === 'DEGRADED' ? '#F4B942' : '#0B5D3B'
          const opacity = cam.coverageQuality === 'HIGH' ? 0.12 : cam.coverageQuality === 'MEDIUM' ? 0.08 : 0.04
          return (
            <circle
              key={cam.id}
              cx={cam.x} cy={cam.y} r={cam.coverageQuality === 'HIGH' ? 95 : cam.coverageQuality === 'MEDIUM' ? 70 : 50}
              fill={`url(#cov-${cam.id})`}
              fillOpacity={opacity}
            />
          )
        })}

        {/* Restricted zones */}
        {restrictedZones.map(zone => (
          <g key={zone.id} role="button" aria-label={`Restricted zone ${zone.label}`} className="cursor-pointer"
             onClick={() => onRouteSelect(null)}>
            <path
              d={zone.path}
              fill="#F4B942"
              fillOpacity={0.07}
              stroke="#F4B942"
              strokeWidth={1.3}
              strokeDasharray="5 4"
              strokeOpacity={0.6}
            />
            <text
              x={415}
              y={205}
              textAnchor="middle"
              fill="#F4B942"
              fillOpacity={0.55}
              fontSize="8"
              fontFamily="monospace"
              letterSpacing="1.2"
            >
              {zone.label}
            </text>
            {/* Restricted zone exposure annotations for each route */}
            {Object.entries(zone.exposureByRoute).map(([routeId, exposure]) => {
              if (exposure > 50) {
                // Find a point on the route that's near this zone
                const route = routes.find(r => r.id === routeId)
                if (route) {
                  const midPt = route.geometry.points[Math.floor(route.geometry.points.length / 2)]
                  return (
                    <text
                      key={routeId}
                      x={midPt.x}
                      y={midPt.y - 25}
                      textAnchor="middle"
                      fill="#F4B942"
                      fillOpacity={0.7}
                      fontSize="7"
                      fontFamily="monospace"
                    >
                      +{exposure}% RZ
                    </text>
                  )
                }
              }
              return null
            })}
          </g>
        ))}

        {/* Routes */}
        {routes.map(route => {
          const color = ROUTE_COLORS[route.id as keyof typeof ROUTE_COLORS]?.main ?? '#0B5D3B'
          const isRec = route.recommended
          const isSel = isRouteSelected(route.id)
          const strokeWidth = isSel ? 4 : isRec ? 3.5 : 2.5

          return (
            <g key={route.id} role="button" aria-label={`${route.name} · Risk ${route.riskScore} · ${route.severity}`} className="cursor-pointer"
               onClick={() => onRouteSelect(isSel ? null : route.id)}>
              {/* Route path with gradient */}
              <path
                d={route.geometry.path}
                fill="none"
                stroke={isSel ? '#FFFFFF' : isRec ? 'url(#route-grad-' + route.id + ')' : color}
                strokeWidth={strokeWidth}
                strokeOpacity={isSel ? 1 : isRec ? 0.95 : 0.7}
                strokeLinecap="round"
                strokeLinejoin="round"
                filter={isSel ? 'drop-shadow(0 0 4px currentColor)' : 'none'}
              />

              {/* Direction arrows along route */}
              {[0.2, 0.4, 0.6, 0.8].map(t => {
                const pt = interpolatePath(route.geometry.path, t)
                // Find direction by looking at nearby points
                const idx = Math.floor(t * (route.geometry.points.length - 1))
                const nextIdx = Math.min(idx + 1, route.geometry.points.length - 1)
                const p1 = route.geometry.points[idx]
                const p2 = route.geometry.points[nextIdx]
                const dx = p2.x - p1.x
                const dy = p2.y - p1.y
                const len = Math.hypot(dx, dy)
                if (len === 0) return null
                const ux = dx / len
                const uy = dy / len
                const px = -uy
                const py = ux
                const ax = pt.x
                const ay = pt.y
                return (
                  <polygon
                    key={t}
                    points={`${ax - px * 4 - ux * 3},${ay - py * 4 - uy * 3} ${ax + ux * 8},${ay + uy * 8} ${ax + px * 4 - ux * 3},${ay + py * 4 - uy * 3}`}
                    fill={isSel ? '#FFFFFF' : color}
                    fillOpacity={isSel ? 1 : 0.85}
                  />
                )
              })}

              {/* Waypoints */}
              {route.geometry.points.map((p, i) => (
                i === 0 || i === route.geometry.points.length - 1 ? (
                  <g key={i}>
                    <circle cx={p.x} cy={p.y} r={isSel ? 7 : 5} fill="#0B1F33" stroke={isSel ? '#FFFFFF' : color} strokeWidth={isSel ? 2 : 1.5} />
                    <text x={p.x + (i === 0 ? 10 : -10)} y={p.y + (i === 0 ? -12 : 18)}
                          textAnchor={i === 0 ? 'start' : 'end'}
                          fill={isSel ? '#FFFFFF' : color} fillOpacity={0.9} fontSize="8" fontFamily="monospace" fontWeight={i === 0 ? 600 : 400}>
                      {i === 0 ? 'START' : 'DEST'}
                    </text>
                  </g>
                ) : null
              ))}

              {/* Recommended badge on route line */}
              {isRec && !isSel && (
                <text
                  x={route.geometry.points[Math.floor(route.geometry.points.length / 2)].x}
                  y={route.geometry.points[Math.floor(route.geometry.points.length / 2)].y - 30}
                  textAnchor="middle"
                  fill="#0B5D3B"
                  fillOpacity={0.9}
                  fontSize="9"
                  fontFamily="monospace"
                  fontWeight="600"
                  letterSpacing="0.5"
                >
                  ✓ RECOMMENDED
                </text>
              )}
            </g>
          )
        })}

        {/* Incidents */}
        {showIncidents.map(inc => {
          const active = selectedRouteId && inc.affectsRoutes.includes(selectedRouteId)
          const band = inc.band === 'HIGH' || inc.band === 'CRITICAL' ? '#D62828' : '#F4B942'
          const pulse = inc.band === 'HIGH' || inc.band === 'CRITICAL'
          return (
            <g key={inc.id} role="button" aria-label={`Incident ${inc.id} · ${inc.title}`} className="cursor-pointer"
               onClick={() => onRouteSelect(null)}>
              {pulse && (
                <animate
                  attributeName="r"
                  values="18;24;18"
                  dur="2s"
                  repeatCount="indefinite"
                />
              )}
              <circle cx={inc.x} cy={inc.y} r={active ? 22 : 18} fill={pulse ? 'url(#incident-pulse)' : 'none'} />
              <circle cx={inc.x} cy={inc.y} r={active ? 20 : 16} fill="none" stroke={band} strokeOpacity={active ? 0.6 : 0.3} strokeWidth={1} />
              <polygon points={`${inc.x},${inc.y - 14} ${inc.x + 12},${inc.y + 7} ${inc.x - 12},${inc.y + 7}`}
                       fill={band} fillOpacity={0.92} stroke="#FFFFFF" strokeOpacity={0.5} strokeWidth={0.8} />
              <text x={inc.x} y={inc.y + 2} textAnchor="middle" fill="#FFFFFF" fontSize="6" fontFamily="monospace" fontWeight="700">
                !
              </text>
              <text x={inc.x} y={inc.y - 22} textAnchor="middle" fill={band} fontSize="8" fontFamily="monospace" fontWeight="700" letterSpacing="0.5">
                {inc.id}
              </text>
            </g>
          )
        })}

        {/* Cameras */}
        {cameraCoverage.map(cam => {
          const color = cam.state === 'DEGRADED' ? '#F4B942' : cam.state === 'OFFLINE' ? '#5A6578' : '#0B5D3B'
          return (
            <g key={cam.id} role="button" aria-label={`Camera ${cam.id} · ${cam.state}`} className="cursor-pointer">
              {cam.state === 'ONLINE' && (
                <circle cx={cam.x} cy={cam.y} r={15} fill="none" stroke={color} strokeOpacity={0.3} strokeWidth={0.7} />
              )}
              <rect x={cam.x - 8} y={cam.y - 8} width={16} height={16} rx={3}
                    fill={color} stroke="#FFFFFF" strokeOpacity={0.4} strokeWidth={0.8} />
              <line x1={cam.x} y1={cam.y - 3} x2={cam.x} y2={cam.y + 3} stroke="#FFFFFF" strokeWidth={0.7} strokeOpacity={0.7} />
              <line x1={cam.x - 3} y1={cam.y} x2={cam.x + 3} y2={cam.y} stroke="#FFFFFF" strokeWidth={0.7} strokeOpacity={0.7} />
              <text x={cam.x} y={cam.y - 15} textAnchor="middle" fill={cam.state === 'DEGRADED' ? '#F4B942' : '#22D3EE'}
                    fontSize="8" fontFamily="monospace" fontWeight="600" letterSpacing="0.5">
                {cam.id}
              </text>
              {cam.state === 'DEGRADED' && (
                <text x={cam.x} y={cam.y + 20} textAnchor="middle" fill="#F4B942" fontSize="7" fontFamily="monospace" fillOpacity={0.8}>
                  DEGRADED
                </text>
              )}
            </g>
          )
        })}

        {/* Origin / Destination markers (prominent) */}
        {origin && (
          <g>
            <circle cx={origin.x} cy={origin.y} r={14} fill="#0B5D3B" stroke="#FFFFFF" strokeWidth={2} strokeOpacity={0.8} />
            <circle cx={origin.x} cy={origin.y} r={8} fill="#0B5D3B" stroke="#0B5D3B" strokeWidth={0} />
            <text x={origin.x} y={origin.y + 3} textAnchor="middle" fill="#FFFFFF" fontSize="9" fontFamily="monospace" fontWeight="700">
              S
            </text>
            <text x={origin.x} y={origin.y - 20} textAnchor="middle" fill="#0B5D3B" fontSize="8.5" fontFamily="monospace" fontWeight="600" letterSpacing="0.5">
              START
            </text>
            <text x={origin.x} y={origin.y - 30} textAnchor="middle" fill="#FFFFFF" fillOpacity={0.7} fontSize="7.5" fontFamily="monospace">
              {origin.label}
            </text>
          </g>
        )}
        {destination && (
          <g>
            <polygon points={`${destination.x},${destination.y - 14} ${destination.x + 12},${destination.y + 9} ${destination.x - 12},${destination.y + 9}`}
                     fill="#0B5D3B" stroke="#FFFFFF" strokeWidth={2} strokeOpacity={0.8} />
            <text x={destination.x} y={destination.y + 3} textAnchor="middle" fill="#FFFFFF" fontSize="9" fontFamily="monospace" fontWeight="700">
              D
            </text>
            <text x={destination.x} y={destination.y - 20} textAnchor="middle" fill="#0B5D3B" fontSize="8.5" fontFamily="monospace" fontWeight="600" letterSpacing="0.5">
              DESTINATION
            </text>
            <text x={destination.x} y={destination.y - 30} textAnchor="middle" fill="#FFFFFF" fillOpacity={0.7} fontSize="7.5" fontFamily="monospace">
              {destination.label}
            </text>
          </g>
        )}

        {/* High-risk segment indicators on routes */}
        {routes.map(route => {
          if (route.restrictedZoneExposure > 50) {
            // Mark high-risk segment
            const midIdx = Math.floor(route.geometry.points.length / 2)
            const pt = route.geometry.points[midIdx]
            return (
              <g key={`hr-${route.id}`}>
                <circle cx={pt.x} cy={pt.y} r={10} fill="none" stroke="#D62828" strokeWidth={1.5} strokeOpacity={0.5} strokeDasharray="3 3" />
                <text x={pt.x} y={pt.y - 16} textAnchor="middle" fill="#D62828" fontSize="7" fontFamily="monospace" fillOpacity={0.8}>
                  HIGH-RISK
                </text>
              </g>
            )
          }
          return null
        })}
      </svg>

      {/* Coordinates overlay */}
      <div className="absolute top-2 right-2 rounded bg-ssb-navy/90 border border-ssb-border/50 px-2 py-1">
        <span className="text-[9px] font-mono text-ssb-text-muted tracking-wider">
          {data.sectorRef} · {data.coords}
        </span>
      </div>
    </div>
  )
}