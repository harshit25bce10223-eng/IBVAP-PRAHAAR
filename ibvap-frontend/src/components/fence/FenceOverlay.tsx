import { useCallback, useMemo, useRef } from 'react'
import { clsx } from 'clsx'
import { useFenceStore } from '@/store'
import { FEED_VIEWBOX } from '@/components/camera/feedViewport'
import type { ZonePoint } from '@/types'

import { validateZonePolygon } from './polygonValidation'

const VW = FEED_VIEWBOX.width
const VH = FEED_VIEWBOX.height

const toVb = (p: ZonePoint) => ({ x: p.x * VW, y: p.y * VH })

/**
 * Virtual-fence overlay: renders persisted zones and supports interactive
 * drawing/editing of polygons in normalized [0,1] image space.
 */
export function FenceOverlay() {
  const { zones, mode, draftPoints, addDraftPoint, removeDraftPoint, updateDraftPoint: _updateDraftPoint } =
    useFenceStore()
  const svgRef = useRef<SVGSVGElement>(null)

  const toNormalized = useCallback((e: React.PointerEvent) => {
    const rect = svgRef.current?.getBoundingClientRect()
    if (!rect) return null
    const px = ((e.clientX - rect.left) / rect.width) * VW
    const py = ((e.clientY - rect.top) / rect.height) * VH
    return { x: Math.min(0.995, Math.max(0, px / VW)), y: Math.min(0.995, Math.max(0, py / VH)) }
  }, [])

  const onCanvasClick = useCallback(
    (e: React.PointerEvent) => {
      if (mode !== 'draw') return
      const p = toNormalized(e)
      if (p) addDraftPoint(p)
    },
    [mode, toNormalized, addDraftPoint]
  )

  const rendered = useMemo(() => {
    const zoneEls = zones.map(zone => (
      <ZoneShape key={zone.zone_id} zone={zone} />
    ))
    const draftEls =
      mode === 'draw' || mode === 'edit'
        ? <DraftShape points={draftPoints} mode={mode} onRemove={removeDraftPoint} />
        : null
    return { zoneEls, draftEls }
  }, [zones, mode, draftPoints, removeDraftPoint])

  return (
    <svg
      ref={svgRef}
      viewBox={`0 0 ${VW} ${VH}`}
      className={clsx(
        'absolute inset-0 h-full w-full',
        mode === 'draw' ? 'cursor-crosshair' : 'cursor-default'
      )}
      onPointerDown={mode === 'draw' ? onCanvasClick : undefined}
    >
      {rendered.zoneEls}
      {rendered.draftEls}
    </svg>
  )
}

/** Fills the polygon and draws full vertices, each drag-movable when editing. */
function DraftShape({
  points,
  mode,
  onRemove,
}: {
  points: ZonePoint[]
  mode: 'draw' | 'edit'
  onRemove: (index: number) => void
}) {
  const { updateDraftPoint } = useFenceStore()
  const vb = points.map(toVb)
  if (vb.length === 0) return null

  const validation = validateZonePolygon(points)
  const isInvalid = points.length >= 3 && !validation.valid

  const strokeColor = isInvalid ? '#ef4444' : mode === 'edit' ? '#22d3ee' : '#f59e0b'
  const fillColor = isInvalid ? '#ef4444' : mode === 'edit' ? '#22d3ee' : '#f59e0b'

  return (
    <g>
      <polygon
        points={vb.map(p => `${p.x},${p.y}`).join(' ')}
        fill={fillColor}
        fillOpacity={isInvalid ? 0.2 : 0.15}
        stroke={strokeColor}
        strokeWidth={1.5}
        strokeDasharray="6 4"
      />
      {/* "close" preview edge between last and first point */}
      {mode === 'draw' && vb.length >= 2 && (
        <line
          x1={vb[vb.length - 1].x}
          y1={vb[vb.length - 1].y}
          x2={vb[0].x}
          y2={vb[0].y}
          stroke={strokeColor}
          strokeWidth={1}
          strokeDasharray="4 4"
          opacity={0.7}
        />
      )}
      {vb.map((p, i) => (
        <g
          key={i}
          transform={`translate(${p.x}, ${p.y})`}
          // right-click removes a vertex; drag moves it when editing
          onContextMenu={e => {
            e.preventDefault()
            onRemove(i)
          }}
          pointerEvents="visiblePainted"
        >
          {(mode === 'edit') && (
            <circle
              r={12}
              fill="transparent"
              onPointerDown={e => {
                e.stopPropagation()
                const wrapper = e.currentTarget.ownerSVGElement
                const move = (me: Event) => {
                  const ev = me as PointerEvent
                  const rect = wrapper?.getBoundingClientRect()
                  if (!rect) return
                  const nx = Math.min(0.995, Math.max(0, ((ev.clientX - rect.left) / rect.width)))
                  const ny = Math.min(0.995, Math.max(0, ((ev.clientY - rect.top) / rect.height)))
                  updateDraftPoint(i, { x: nx, y: ny })
                }
                const up = () => {
                  window.removeEventListener('pointermove', move)
                  window.removeEventListener('pointerup', up)
                }
                window.addEventListener('pointermove', move)
                window.addEventListener('pointerup', up)
              }}
            />
          )}
          <circle r={5} fill={mode === 'draw' ? '#f59e0b' : '#22d3ee'} stroke="#0d1117" strokeWidth={1.5} />
          <title>{mode === 'draw' ? 'Add point' : 'Drag to move · right-click to delete'}</title>
        </g>
      ))}

      {points.length >= 3 && (
        <text
          x={vb[0].x}
          y={vb[0].y - 14}
          fontSize={10}
          fontFamily="JetBrains Mono, monospace"
          fill="#f59e0b"
        >
          {mode === 'draw' ? 'click to add · right-click last point to undo' : 'drag vertices to reshape · right-click to remove'}
        </text>
      )}
    </g>
  )
}

function ZoneShape({ zone }: { zone: { zone_id: string; name: string; polygon: ZonePoint[]; active: boolean } }) {
  const { beginEdit } = useFenceStore()
  // Guard: skip any point with NaN or non-finite coordinates to prevent SVG errors
  const safePolygon = zone.polygon.filter(p => isFinite(p.x) && isFinite(p.y))
  const vb = safePolygon.map(toVb)
  if (vb.length < 3) return null   // can't draw a meaningful polygon
  const pts = vb.map(p => `${p.x.toFixed(2)},${p.y.toFixed(2)}`).join(' ')
  const labelX = vb.reduce((s, p) => s + p.x, 0) / vb.length
  const labelY = vb.reduce((s, p) => s + p.y, 0) / vb.length

  return (
    <g
      role="button"
      aria-label={`Edit zone ${zone.name}`}
      className="cursor-pointer"
      onClick={e => {
        e.stopPropagation()
        beginEdit(zone.zone_id, zone.polygon)
      }}
    >
      <polygon
        points={pts}
        fill={zone.active ? '#22d3ee' : '#475569'}
        fillOpacity={0.1}
        stroke={zone.active ? '#22d3ee' : '#64748b'}
        strokeWidth={1.5}
        strokeDasharray={zone.active ? undefined : '5 4'}
      />
      {/* vertex dots */}
      {vb.map((p, i) => (
        <circle key={i} cx={p.x} cy={p.y} r={3} fill={zone.active ? '#22d3ee' : '#64748b'} />
      ))}
      <g transform={`translate(${labelX}, ${labelY})`}>
        <rect x={-60} y={-11} width={120} height={20} rx={4} fill="#0d1117" fillOpacity={0.85} stroke="#22d3ee" strokeOpacity={0.5} />
        <text x={0} y={3} textAnchor="middle" fontSize={10} fontFamily="JetBrains Mono, monospace" fill={zone.active ? '#22d3ee' : '#94a3b8'}>
          {zone.name}
        </text>
      </g>
    </g>
  )
}