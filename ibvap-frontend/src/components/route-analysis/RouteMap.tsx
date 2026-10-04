// ─────────────────────────────────────────────────────────────────────────────
// RouteMap — dominant operational route analysis canvas (SVG).
//
// Tactical Military GIS Visualizer:
//   - High-contrast PRHAAR design tokens (#080B10, #3FCB8C, #F5A623, #F0455B, #2FD5E0)
//   - Glowing neon route trajectories with direction arrows & waypoints
//   - Clear Recommended Route (Route B) highlighting with lowest-risk badge
//   - Radar sensor footprints, pulsing incident hazard warnings, and restricted zones
//   - International border reference & tactical coordinate HUD
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'
import type { RouteAnalysisData, RouteIncident, RouteTimeWindow } from '@/types'

interface Props {
  data: RouteAnalysisData
  timeWindow: RouteTimeWindow
  selectedRouteId: string | null
  onRouteSelect: (routeId: string | null) => void
  className?: string
}

const ROUTE_CONFIG: Record<string, { main: string; glow: string; label: string }> = {
  'ROUTE-A': { main: '#F5A623', glow: 'rgba(245,166,35,0.4)', label: 'Route A (Northern Buffer)' },
  'ROUTE-B': { main: '#3FCB8C', glow: 'rgba(63,203,140,0.5)', label: 'Route B (Recommended Valley)' },
  'ROUTE-C': { main: '#60A5FA', glow: 'rgba(96,165,250,0.35)', label: 'Route C (Ridge Trail)' },
}

const WINDOW_FILTER: Record<RouteTimeWindow, (inc: RouteIncident) => boolean> = {
  LIVE: inc => inc.band === 'HIGH' || inc.band === 'CRITICAL',
  '24H': inc => inc.id === 'INC-024' || inc.id === 'INC-031',
  '7D': () => true,
  '30D': () => true,
}

function interpolatePath(path: string, t: number): { x: number; y: number } {
  const coords: { x: number; y: number }[] = []
  const parts = path.replace(/[ML]/g, ' ').trim().split(/\s+/)
  for (let i = 0; i < parts.length; i += 2) {
    coords.push({ x: parseFloat(parts[i]), y: parseFloat(parts[i + 1]) })
  }
  if (coords.length < 2) return coords[0] ?? { x: 0, y: 0 }

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
    <div className={clsx('relative rounded-xl border border-border overflow-hidden bg-[#070D15] shadow-2xl flex flex-col', className)}>
      {/* ── Tactical Header HUD ── */}
      <div className="absolute top-2.5 left-3 right-3 z-10 flex items-center justify-between text-[10px] font-mono pointer-events-none">
        <div className="flex items-center gap-2 bg-[#0C121D]/90 border border-border px-3 py-1 rounded backdrop-blur shadow-lg">
          <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse shadow-[0_0_8px_rgba(63,203,140,0.8)]" />
          <span className="text-emerald-300 font-semibold tracking-wider">TACTICAL ROUTE MAP</span>
          <span className="text-slate-600">|</span>
          <span className="text-slate-300">SECTOR: {data.sectorRef}</span>
          <span className="text-slate-600">|</span>
          <span className="text-cyan-400">3 FEASIBLE PATHS</span>
        </div>

        <div className="flex items-center gap-2 bg-[#0C121D]/90 border border-border px-3 py-1 rounded backdrop-blur shadow-lg">
          <span className="text-slate-400">WINDOW: <strong className="text-cyan-300">{timeWindow}</strong></span>
          <span className="text-slate-600">|</span>
          <span className="text-slate-400">WGS-84: <strong className="text-slate-200">{data.coords}</strong></span>
        </div>
      </div>

      {/* ── SVG Tactical Map Canvas ── */}
      <svg
        viewBox="0 0 1200 520"
        className="w-full h-full flex-1 min-h-0"
        preserveAspectRatio="xMidYMid meet"
        aria-label="Operational route analysis map"
        role="img"
      >
        <defs>
          {/* Rich Tactical Terrain Gradient */}
          <linearGradient id="routeTerrain" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor="#08101A" />
            <stop offset="50%"  stopColor="#0D1A24" />
            <stop offset="100%" stopColor="#08101A" />
          </linearGradient>

          {/* Grid pattern */}
          <pattern id="tacGrid" width="60" height="60" patternUnits="userSpaceOnUse">
            <path d="M 60 0 L 0 0 0 60" fill="none" stroke="#1E2D40" strokeWidth="0.6" strokeOpacity="0.5" />
          </pattern>

          {/* Neon Route Glow Filters */}
          <filter id="glow-rec" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
          <filter id="glow-warn" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>

          {/* Camera Coverage Sensor Beam Radial */}
          {cameraCoverage.map(cam => (
            <radialGradient key={`cov-${cam.id}`} id={`cov-${cam.id}`} cx="0.5" cy="0.5" r="0.5">
              <stop offset="0%" stopColor="#2FD5E0" stopOpacity={cam.coverageQuality === 'HIGH' ? 0.22 : 0.12} />
              <stop offset="60%" stopColor="#2FD5E0" stopOpacity="0.06" />
              <stop offset="100%" stopColor="#2FD5E0" stopOpacity="0" />
            </radialGradient>
          ))}

          {/* Hazard Incident Pulse */}
          <radialGradient id="hazardPulse" cx="0.5" cy="0.5" r="0.5">
            <stop offset="0%" stopColor="#F0455B" stopOpacity="0.5" />
            <stop offset="50%" stopColor="#F0455B" stopOpacity="0.15" />
            <stop offset="100%" stopColor="#F0455B" stopOpacity="0" />
          </radialGradient>

          {/* Diagonal hatch for restricted zones */}
          <pattern id="restrictedHatch" width="10" height="10" patternTransform="rotate(45 0 0)" patternUnits="userSpaceOnUse">
            <line x1="0" y1="0" x2="0" y2="10" stroke="#F5A623" strokeWidth="1.2" strokeOpacity="0.25" />
          </pattern>
        </defs>

        {/* 1. Base Terrain Fill */}
        <rect width="1200" height="520" fill="url(#routeTerrain)" />

        {/* 2. Tactical Coordinate Grid */}
        <rect width="1200" height="520" fill="url(#tacGrid)" />

        {/* 3. Water Streams (Cyan-tinted) */}
        {terrain.waterPaths.map((d, i) => (
          <g key={`w${i}`}>
            <path d={d} fill="none" stroke="#2FD5E0" strokeWidth={3} strokeOpacity={0.12} />
            <path d={d} fill="none" stroke="#2FD5E0" strokeWidth={1.2} strokeOpacity={0.4} strokeDasharray="6 3" />
          </g>
        ))}

        {/* 4. Topographic Hill Contours */}
        {terrain.hillPaths.map((d, i) => (
          <path key={`h${i}`} d={d} fill="#102522" fillOpacity={0.4 - i * 0.03} stroke="#1A3E36" strokeWidth={0.7} strokeOpacity={0.4} />
        ))}

        {/* 5. Forest Canopy */}
        {terrain.forestPaths.map((d, i) => (
          <path key={`f${i}`} d={d} fill="#0E2F23" fillOpacity={0.3} stroke="#1D4B39" strokeWidth={0.8} strokeOpacity={0.5} />
        ))}

        {/* 6. Sector Boundary Box & Roads */}
        {terrain.roadPaths.map((d, i) => (
          <path key={`r${i}`} d={d} fill="none" stroke="#64748B" strokeWidth={1} strokeOpacity={0.25} strokeDasharray="4 3" />
        ))}

        <rect
          x={22} y={54} width={1156} height={442}
          fill="none" stroke="#334155" strokeOpacity={0.3} strokeWidth={1} strokeDasharray="12 6"
        />

        {/* 7. Border Fence Path */}
        {terrain.fencePaths.map((d, i) => (
          <g key={`fnc${i}`}>
            <path d={d} fill="none" stroke="#F5A623" strokeWidth={2.5} strokeOpacity={0.15} />
            <path d={d} fill="none" stroke="#F5A623" strokeWidth={1.2} strokeOpacity={0.65} strokeDasharray="6 4" />
          </g>
        ))}

        {/* 8. International Border Reference (INDIA ─── NEPAL) */}
        <g opacity="0.85">
          <path
            d={borderRef.path}
            fill="none"
            stroke="#CBD5E1"
            strokeWidth={1.8}
            strokeDasharray="10 5"
            strokeOpacity={0.7}
          />
          <rect x="22" y="196" width="310" height="20" rx="3" fill="#0C121D" fillOpacity="0.8" stroke="#334155" strokeWidth="0.8" />
          <text x="32" y="210" fill="#E2E8F0" fontSize="9.5" fontFamily="monospace" fontWeight="bold" letterSpacing="1.8">
            🇮🇳 INDIA ─── NEPAL 🇳🇵 BORDER
          </text>
        </g>

        {/* 9. Camera Sensor Footprints (Cones of Coverage) */}
        {cameraCoverage.map(cam => {
          if (cam.state === 'OFFLINE') return null
          const isDeg = cam.state === 'DEGRADED'
          const radius = cam.coverageQuality === 'HIGH' ? 100 : cam.coverageQuality === 'MEDIUM' ? 75 : 55

          return (
            <g key={cam.id} className="cursor-pointer">
              <circle
                cx={cam.x} cy={cam.y} r={radius}
                fill={`url(#cov-${cam.id})`}
              />
              <circle
                cx={cam.x} cy={cam.y} r={radius}
                fill="none"
                stroke={isDeg ? '#F5A623' : '#2FD5E0'}
                strokeWidth={0.8}
                strokeDasharray="4 3"
                strokeOpacity={0.35}
              />
            </g>
          )
        })}

        {/* 10. Restricted Zones (Zero-Tolerance Buffer) */}
        {restrictedZones.map(zone => (
          <g key={zone.id} role="button" aria-label={`Restricted zone ${zone.label}`} className="cursor-pointer"
             onClick={() => onRouteSelect(null)}>
            {/* Zone Fill with Hatch Pattern */}
            <path d={zone.path} fill="url(#restrictedHatch)" />
            <path
              d={zone.path}
              fill="#F5A623"
              fillOpacity={0.08}
              stroke="#F5A623"
              strokeWidth={1.6}
              strokeDasharray="6 4"
              strokeOpacity={0.7}
            />
            {/* Zone Label Badge */}
            <rect x="360" y="194" width="135" height="18" rx="3" fill="#0C121D" fillOpacity="0.9" stroke="#F5A623" strokeWidth="0.8" />
            <text
              x="427"
              y="206"
              textAnchor="middle"
              fill="#F5A623"
              fontSize="8.5"
              fontWeight="bold"
              fontFamily="monospace"
              letterSpacing="1"
            >
              ⚠ {zone.label}
            </text>
          </g>
        ))}

        {/* 11. Candidate Routes (The Visual Core) */}
        {routes.map(route => {
          const cfg = ROUTE_CONFIG[route.id] || { main: '#60A5FA', glow: 'rgba(96,165,250,0.3)', label: route.name }
          const isRec = route.recommended
          const isSel = isRouteSelected(route.id)
          const strokeWidth = isSel ? 4.5 : isRec ? 3.8 : 2.6

          return (
            <g
              key={route.id}
              role="button"
              aria-label={`${route.name} · Risk ${route.riskScore}`}
              className="cursor-pointer transition-all duration-150"
              onClick={() => onRouteSelect(isSel ? null : route.id)}
            >
              {/* Soft Ambient Glow under-stroke */}
              <path
                d={route.geometry.path}
                fill="none"
                stroke={cfg.main}
                strokeWidth={isRec ? 9 : 6}
                opacity={isSel ? 0.45 : isRec ? 0.35 : 0.15}
                filter={isRec ? 'url(#glow-rec)' : 'url(#glow-warn)'}
              />

              {/* Main Vector Path */}
              <path
                d={route.geometry.path}
                fill="none"
                stroke={isSel ? '#FFFFFF' : cfg.main}
                strokeWidth={strokeWidth}
                strokeOpacity={isSel ? 1 : isRec ? 0.95 : 0.75}
                strokeLinecap="round"
                strokeLinejoin="round"
              />

              {/* Direction Arrows along the route */}
              {[0.2, 0.4, 0.6, 0.8].map(t => {
                const pt = interpolatePath(route.geometry.path, t)
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
                    points={`${ax - px * 4 - ux * 3},${ay - py * 4 - uy * 3} ${ax + ux * 9},${ay + uy * 9} ${ax + px * 4 - ux * 3},${ay + py * 4 - uy * 3}`}
                    fill={isSel ? '#FFFFFF' : cfg.main}
                    fillOpacity={isSel ? 1 : 0.9}
                  />
                )
              })}

              {/* Waypoints along route */}
              {route.geometry.points.map((p, i) => (
                <circle
                  key={i}
                  cx={p.x}
                  cy={p.y}
                  r={i === 0 || i === route.geometry.points.length - 1 ? 4 : 2.5}
                  fill="#080C12"
                  stroke={isSel ? '#FFFFFF' : cfg.main}
                  strokeWidth={1.5}
                />
              ))}

              {/* Recommended Badge on Route B */}
              {isRec && (
                <g transform={`translate(${route.geometry.points[Math.floor(route.geometry.points.length / 2)].x}, ${route.geometry.points[Math.floor(route.geometry.points.length / 2)].y - 28})`}>
                  <rect x="-85" y="-12" width="170" height="22" rx="4" fill="#0C1A14" stroke="#3FCB8C" strokeWidth="1.2" filter="url(#glow-rec)" />
                  <text
                    x="0"
                    y="2"
                    textAnchor="middle"
                    fill="#3FCB8C"
                    fontSize="9"
                    fontFamily="monospace"
                    fontWeight="bold"
                    letterSpacing="0.8"
                  >
                    ✓ RECOMMENDED (RISK: 38)
                  </text>
                </g>
              )}
            </g>
          )
        })}

        {/* 12. Incidents & Threat Clusters */}
        {showIncidents.map(inc => {
          const active = selectedRouteId && inc.affectsRoutes.includes(selectedRouteId)
          const isCrit = inc.band === 'HIGH' || inc.band === 'CRITICAL'
          const col = isCrit ? '#F0455B' : '#F5A623'

          return (
            <g key={inc.id} role="button" aria-label={`Incident ${inc.id}`} className="cursor-pointer"
               onClick={() => onRouteSelect(null)}>
              {/* Pulsing Sonar Ping */}
              {isCrit && (
                <circle cx={inc.x} cy={inc.y} r="24" fill="url(#hazardPulse)" className="animate-ping" opacity="0.75" />
              )}
              <circle cx={inc.x} cy={inc.y} r={active ? 20 : 16} fill="none" stroke={col} strokeWidth="1.2" strokeDasharray="3 3" opacity="0.6" />
              {/* Hazard Polygon */}
              <polygon
                points={`${inc.x},${inc.y - 13} ${inc.x + 11},${inc.y + 7} ${inc.x - 11},${inc.y + 7}`}
                fill={col}
                stroke="#FFFFFF"
                strokeWidth="1"
              />
              <text x={inc.x} y={inc.y + 3} textAnchor="middle" fill="#FFFFFF" fontSize="7" fontFamily="monospace" fontWeight="bold">
                !
              </text>
              <text x={inc.x} y={inc.y - 18} textAnchor="middle" fill={col} fontSize="8.5" fontFamily="monospace" fontWeight="bold">
                {inc.id}
              </text>
            </g>
          )
        })}

        {/* 13. Camera Sensors */}
        {cameraCoverage.map(cam => {
          const isDeg = cam.state === 'DEGRADED'
          const isOff = cam.state === 'OFFLINE'
          const camCol = isDeg ? '#F5A623' : isOff ? '#64748B' : '#2FD5E0'

          return (
            <g key={cam.id} className="cursor-pointer">
              <rect x={cam.x - 9} y={cam.y - 9} width="18" height="18" rx="4"
                    fill="#080C12" stroke={camCol} strokeWidth="1.4" />
              <circle cx={cam.x} cy={cam.y} r="3" fill={camCol} />
              <text x={cam.x} y={cam.y - 14} textAnchor="middle" fill={camCol}
                    fontSize="8.5" fontFamily="monospace" fontWeight="bold">
                {cam.id}
              </text>
              {isDeg && (
                <text x={cam.x} y={cam.y + 20} textAnchor="middle" fill="#F5A623" fontSize="7.5" fontFamily="monospace">
                  DEGRADED
                </text>
              )}
            </g>
          )
        })}

        {/* 14. Origin (S) & Destination (D) Reticles */}
        {origin && (
          <g>
            <circle cx={origin.x} cy={origin.y} r="16" fill="none" stroke="#3FCB8C" strokeWidth="1.8" strokeDasharray="3 2" className="animate-spin" style={{ animationDuration: '8s' }} />
            <circle cx={origin.x} cy={origin.y} r="10" fill="#3FCB8C" stroke="#080C12" strokeWidth="2" />
            <text x={origin.x} y={origin.y + 3.5} textAnchor="middle" fill="#080C12" fontSize="9" fontFamily="monospace" fontWeight="900">
              S
            </text>
            <rect x={origin.x - 45} y={origin.y - 32} width="90" height="16" rx="3" fill="#0C121D" stroke="#3FCB8C" strokeWidth="0.8" />
            <text x={origin.x} y={origin.y - 21} textAnchor="middle" fill="#3FCB8C" fontSize="8" fontFamily="monospace" fontWeight="bold">
              START: {origin.id}
            </text>
          </g>
        )}

        {destination && (
          <g>
            <polygon
              points={`${destination.x},${destination.y - 15} ${destination.x + 13},${destination.y + 9} ${destination.x - 13},${destination.y + 9}`}
              fill="#2FD5E0"
              stroke="#080C12"
              strokeWidth="2"
            />
            <text x={destination.x} y={destination.y + 4} textAnchor="middle" fill="#080C12" fontSize="9" fontFamily="monospace" fontWeight="900">
              D
            </text>
            <rect x={destination.x - 45} y={destination.y - 32} width="90" height="16" rx="3" fill="#0C121D" stroke="#2FD5E0" strokeWidth="0.8" />
            <text x={destination.x} y={destination.y - 21} textAnchor="middle" fill="#2FD5E0" fontSize="8" fontFamily="monospace" fontWeight="bold">
              DEST: {destination.id}
            </text>
          </g>
        )}
      </svg>

      {/* ── Tactical Footer HUD ── */}
      <div className="absolute bottom-2 left-3 right-3 z-10 flex items-center justify-between text-[10px] font-mono pointer-events-none text-slate-400">
        <div className="flex items-center gap-3 bg-[#0C121D]/90 border border-border px-3 py-1 rounded backdrop-blur">
          <span>RECOMMENDED: <strong className="text-emerald-400">ROUTE B (SCORE 38)</strong></span>
          <span className="text-slate-600">|</span>
          <span>LOWEST BUFFER EXPOSURE</span>
          <span className="text-slate-600">|</span>
          <span>FULL SENSOR LINE-OF-SIGHT</span>
        </div>

        <div className="flex items-center gap-2 bg-[#0C121D]/90 border border-border px-3 py-1 rounded backdrop-blur">
          <span className="h-1.5 w-1.5 rounded-full bg-cyan-400" />
          <span className="text-slate-300">SCALE: 1:25,000</span>
          <span className="text-slate-600">|</span>
          <span className="text-slate-400">CONTOUR: 10m INTERVAL</span>
        </div>
      </div>
    </div>
  )
}