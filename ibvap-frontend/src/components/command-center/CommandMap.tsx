// ─────────────────────────────────────────────────────────────────────────────
// CommandMap — SVG digital twin / GIS placeholder (spec §14, §15).
//
// The visual center of the Command Center. Shows terrain, border line,
// restricted zone, camera markers, entity trajectory (the Golden Incident),
// incident marker, risk heat and a compact legend.
//
// No external GIS library — lightweight SVG for the prototype; future map
// providers (Leaflet/Mapbox) swap in at the service seam.
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'
import type { GoldenIncident, DashboardCameraIntel } from '@/types'

interface Props {
  goldenIncident: GoldenIncident
  cameras: DashboardCameraIntel[]
  className?: string
}

/* ── Camera positions (viewBox 1000×600) ─────────────────────────────────── */
const CAM_POSITIONS: Record<string, { x: number; y: number }> = {
  'CAM-01': { x: 160, y: 210 },
  'CAM-02': { x: 400, y: 140 },
  'CAM-03': { x: 610, y: 290 },
  'CAM-07': { x: 820, y: 410 },
}

/* ── Restricted zone boundary ─────────────────────────────────────────────── */
const ZONE_PATH = 'M200,120 L420,90 L460,270 L310,300 Z'

export function CommandMap({ goldenIncident, cameras, className }: Props) {
  // Derive the trajectory from the Golden Incident chain: steps[0] camera is
  // the detection source, steps[3] is the cross-camera candidate.
  const detectCam = goldenIncident.steps[0]?.cameraId
  const matchCam = goldenIncident.steps[3]?.cameraId ?? 'CAM-02'
  const fromPos = detectCam ? CAM_POSITIONS[detectCam] : undefined
  const toPos = CAM_POSITIONS[matchCam]

  let trajectory = ''
  let incidentPos = { x: 300, y: 165 }
  let entityPos = { x: 260, y: 120 }

  if (fromPos && toPos) {
    const midX = Math.round((fromPos.x + toPos.x) / 2)
    const midY = Math.round((fromPos.y + toPos.y) / 2) - 55
    trajectory = `M${fromPos.x},${fromPos.y} Q${midX},${midY} ${toPos.x},${toPos.y}`
    incidentPos = { x: midX, y: midY + 45 }
    entityPos = { x: midX, y: midY - 28 }
  }

  return (
    <div className={clsx('relative rounded-md border border-ssb-border/70 overflow-hidden bg-ssb-navy-deep', className)}>
      {/* SVG terrain map */}
      <svg
        viewBox="0 0 1000 600"
        className="w-full h-full"
        preserveAspectRatio="xMidYMid slice"
        aria-label="Border surveillance GIS — digital twin of operational sector"
      >
        <defs>
          {/* Terrain gradient */}
          <linearGradient id="terrain" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%"   stopColor="#0B1F33" />
            <stop offset="40%"  stopColor="#0B2A2A" />
            <stop offset="100%" stopColor="#0B1F33" />
          </linearGradient>

          {/* Risk heat radial */}
          <radialGradient id="riskHeat" cx="0.32" cy="0.3" r="0.22">
            <stop offset="0%"   stopColor="#D62828" stopOpacity="0.22" />
            <stop offset="60%"  stopColor="#D62828" stopOpacity="0.08" />
            <stop offset="100%" stopColor="#D62828" stopOpacity="0" />
          </radialGradient>

          {/* Zone fill */}
          <linearGradient id="zoneFill" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%"   stopColor="#F4B942" stopOpacity="0.06" />
            <stop offset="100%" stopColor="#F4B942" stopOpacity="0.02" />
          </linearGradient>
        </defs>

        {/* Sky / base terrain */}
        <rect width="1000" height="600" fill="url(#terrain)" />

        {/* Terrain contour lines (subtle hilly/forest context) */}
        {[
          'M0,180 Q100,140 200,150 Q300,160 400,130 Q500,100 600,120 Q700,140 800,110 Q900,80 1000,100',
          'M0,280 Q120,240 250,250 Q380,260 480,230 Q580,200 700,220 Q820,240 1000,210',
          'M0,380 Q150,350 280,360 Q410,370 520,340 Q630,310 760,330 Q880,350 1000,320',
          'M0,480 Q140,460 280,470 Q420,480 560,450 Q700,420 840,440 Q960,460 1000,430',
        ].map((d, i) => (
          <path
            key={i}
            d={d}
            fill="none"
            stroke="#0B5D3B"
            strokeWidth={0.6}
            strokeOpacity={0.25 + i * 0.06}
          />
        ))}

        {/* Forest patches (subtle dark green fills) */}
        <ellipse cx="120" cy="160" rx="90" ry="50" fill="#0B5D3B" fillOpacity="0.08" />
        <ellipse cx="500" cy="200" rx="120" ry="60" fill="#0B5D3B" fillOpacity="0.06" />
        <ellipse cx="800" cy="360" rx="100" ry="55" fill="#0B5D3B" fillOpacity="0.07" />

        {/* Hilly terrain (darker triangular shapes) */}
        <path d="M30,120 L80,60 L130,120 Z" fill="#0B2A1F" fillOpacity="0.4" />
        <path d="M600,80 L660,30 L720,80 Z"   fill="#0B2A1F" fillOpacity="0.35" />
        <path d="M850,260 L910,200 L970,260 Z" fill="#0B2A1F" fillOpacity="0.3" />
        <path d="M180,340 L240,280 L300,340 Z" fill="#0B2A1F" fillOpacity="0.3" />

        {/* Border line (dashed, India–Nepal contextual) */}
        <path
          d="M0,310 Q100,290 200,300 Q300,310 400,280 Q500,250 600,270 Q700,290 800,260 Q900,230 1000,250"
          fill="none"
          stroke="#FFFFFF"
          strokeWidth={1.2}
          strokeDasharray="6 4"
          strokeOpacity="0.35"
        />
        <text x="50" y="302" fill="#FFFFFF" fillOpacity="0.3" fontSize="8" fontFamily="monospace" letterSpacing="1.5">
          INDIA — NEPAL
        </text>

        {/* Risk heat overlay */}
        <rect width="1000" height="600" fill="url(#riskHeat)" />

        {/* Restricted zone */}
        <path d={ZONE_PATH} fill="url(#zoneFill)" stroke="#F4B942" strokeWidth={1.2} strokeDasharray="5 3" strokeOpacity="0.6" />
        <text x="310" y="175" fill="#F4B942" fillOpacity="0.5" fontSize="8" fontFamily="monospace" letterSpacing="1">
          RESTRICTED ZONE
        </text>

        {/* Entity trajectory (Golden Incident path) */}
        <path
          d={trajectory}
          fill="none"
          stroke="#22D3EE"
          strokeWidth={1.6}
          strokeDasharray="4 3"
          strokeOpacity="0.8"
        />
        {/* Trajectory direction arrow */}
        {fromPos && toPos && (
          <polygon
            points={`${toPos.x - 5},${toPos.y - 6} ${toPos.x + 5},${toPos.y} ${toPos.x - 5},${toPos.y + 6}`}
            fill="#22D3EE"
            fillOpacity="0.8"
          />
        )}

        {/* Camera markers */}
        {Object.entries(CAM_POSITIONS).map(([id, pos]) => {
          const cam = cameras.find(c => c.id === id)
          const isOnline = cam?.state === 'ONLINE'
          const isDegraded = cam?.state === 'DEGRADED'
          const color = isDegraded ? '#F4B942' : isOnline ? '#0B5D3B' : '#5A6578'
          const labelColor = isDegraded ? '#F4B942' : '#22D3EE'

          return (
            <g key={id}>
              {/* Camera icon node */}
              <rect
                x={pos.x - 7}
                y={pos.y - 7}
                width={14}
                height={14}
                rx={3}
                fill={color}
                stroke="#FFFFFF"
                strokeWidth={0.8}
                strokeOpacity={0.4}
              />
              {/* Camera crosshair */}
              <line x1={pos.x} y1={pos.y - 3} x2={pos.x} y2={pos.y + 3} stroke="#FFFFFF" strokeWidth={0.6} strokeOpacity={0.6} />
              <line x1={pos.x - 3} y1={pos.y} x2={pos.x + 3} y2={pos.y} stroke="#FFFFFF" strokeWidth={0.6} strokeOpacity={0.6} />

              {/* Label */}
              <text
                x={pos.x}
                y={pos.y - 12}
                textAnchor="middle"
                fill={labelColor}
                fontSize="8"
                fontFamily="monospace"
                fontWeight="600"
                letterSpacing="0.5"
              >
                {id}
              </text>

              {/* Online indicator ring */}
              {isOnline && (
                <circle cx={pos.x} cy={pos.y} r={12} fill="none" stroke={color} strokeWidth={0.6} strokeOpacity={0.3} />
              )}
            </g>
          )
        })}

        {/* Incident marker (Golden Incident) */}
        <g transform={`translate(${incidentPos.x}, ${incidentPos.y})`}>
          <polygon points="0,-14 12,8 -12,8" fill="#D62828" fillOpacity="0.9" stroke="#FFFFFF" strokeWidth={0.8} strokeOpacity={0.5} />
          <text x="0" y="4" textAnchor="middle" fill="#FFFFFF" fontSize="6" fontFamily="monospace" fontWeight="700">
            !
          </text>
          <text x="0" y="-18" textAnchor="middle" fill="#D62828" fontSize="8" fontFamily="monospace" fontWeight="700" letterSpacing="0.5">
            {goldenIncident.incidentId}
          </text>
        </g>

        {/* Entity label (Golden Incident track) */}
        <g transform={`translate(${entityPos.x}, ${entityPos.y})`}>
          <rect x={-22} y={-6} width={44} height={12} rx={2} fill="#0B1F33" stroke="#22D3EE" strokeWidth={0.6} strokeOpacity={0.5} />
          <text x="0" y="3" textAnchor="middle" fill="#22D3EE" fontSize="7" fontFamily="monospace" fontWeight="600" letterSpacing="0.3">
            {goldenIncident.entityId}
          </text>
        </g>

        {/* Sector grid lines (very subtle) */}
        {[200, 400, 600, 800].map(x => (
          <line key={`gv${x}`} x1={x} y1={0} x2={x} y2={600} stroke="#FFFFFF" strokeWidth={0.3} strokeOpacity={0.04} />
        ))}
        {[150, 300, 450].map(y => (
          <line key={`gh${y}`} x1={0} y1={y} x2={1000} y2={y} stroke="#FFFFFF" strokeWidth={0.3} strokeOpacity={0.04} />
        ))}
      </svg>

      {/* Legend (bottom-left overlay) */}
      <div className="absolute bottom-2 left-2 flex flex-col gap-1 rounded bg-ssb-navy/90 border border-ssb-border/50 px-2.5 py-2">
        <LegendItem color="#0B5D3B" label="Camera" />
        <LegendItem color="#22D3EE" label="Entity path" dashed />
        <LegendItem color="#F4B942" label="Restricted zone" dashed />
        <LegendItem color="#D62828" label="Incident" />
      </div>

      {/* Coordinates (top-right overlay) */}
      <div className="absolute top-2 right-2 rounded bg-ssb-navy/90 border border-ssb-border/50 px-2 py-1.5">
        <span className="text-[9px] font-mono text-ssb-text-muted tracking-wider">
          SECTOR-7 · 27.72°N 88.15°E
        </span>
      </div>
    </div>
  )
}

function LegendItem({ color, label, dashed }: { color: string; label: string; dashed?: boolean }) {
  return (
    <div className="flex items-center gap-2">
      <span
        className="h-px w-4 flex-shrink-0"
        style={{
          backgroundColor: color,
          ...(dashed ? { backgroundImage: `repeating-linear-gradient(90deg, ${color} 0 3px, transparent 3px 6px)`, backgroundColor: 'transparent' } : {}),
        }}
      />
      <span className="text-[8px] font-medium text-ssb-text-muted/80 uppercase tracking-wider">{label}</span>
    </div>
  )
}