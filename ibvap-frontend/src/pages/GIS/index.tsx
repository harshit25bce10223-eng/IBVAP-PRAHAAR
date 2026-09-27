// ─────────────────────────────────────────────────────────────────────────────
// GISTwin — GIS / DIGITAL TWIN (SIH screenshot 4)
//
// A dedicated operational GIS view, NOT a dashboard: the map is the dominant
// visual (≈75% of the content band). Terrain, cameras, entity movement,
// restricted zones, incidents, risk hotspots and historical patterns give the
// reviewer spatial context: "प्रहार understands WHERE surveillance
// intelligence is happening."
// ─────────────────────────────────────────────────────────────────────────────

import { useState } from 'react'
import { useGis } from '@/hooks'
import { GisLayerBar, GisMap, GisContextStrip, GisSkeleton } from '@/components/gis'
import type { GisLayerId, GisSelection, GisTimeWindow } from '@/types'

const ALL_LAYERS: GisLayerId[] = ['cameras', 'tracks', 'incidents', 'restrictedZones', 'riskHeat', 'historical']
const DEFAULT_LAYERS = new Set<GisLayerId>(['cameras', 'tracks', 'incidents', 'restrictedZones', 'riskHeat'])

export function GISTwin() {
  const { data, loadState, refetch } = useGis()
  const [layers, setLayers] = useState<Set<GisLayerId>>(DEFAULT_LAYERS)
  const [window, setWindow] = useState<GisTimeWindow>('LIVE')
  const [selection, setSelection] = useState<GisSelection>({ type: 'none' })

  if (loadState === 'error' && !data) {
    return (
      <div className="h-full flex items-center justify-center">
        <button
          onClick={() => refetch().catch(() => {})}
          className="text-xs text-ssb-amber-bright underline underline-offset-2"
        >
          Failed to load GIS context — try again
        </button>
      </div>
    )
  }

  if (!data) {
    return <GisSkeleton />
  }

  const toggleLayer = (layer: GisLayerId) => {
    setLayers(prev => {
      const next = new Set(prev)
      if (next.has(layer)) next.delete(layer)
      else next.add(layer)
      return next
    })
  }

  return (
    <div className="h-full flex flex-col gap-2 overflow-hidden p-4">
      {/* Page identity */}
      <header className="flex items-end justify-between flex-shrink-0">
        <div>
          <h1 className="text-lg font-semibold tracking-[0.12em] text-ssb-white uppercase">
            GIS / Digital Twin
          </h1>
          <p className="text-[11px] text-ssb-text-muted mt-0.5 tracking-wide">
            Geospatial Border Surveillance &amp; Risk Context
          </p>
        </div>
        <span className="text-[9px] font-mono tracking-[0.2em] text-ssb-text-muted/60 uppercase">
          SSB Border Sector · Live Operational Map
        </span>
      </header>

      {/* Filter / layer bar */}
      <GisLayerBar
        layers={ALL_LAYERS}
        activeLayers={layers}
        onToggleLayer={toggleLayer}
        window={window}
        onWindowChange={setWindow}
      />

      {/* Dominant map */}
      <GisMap
        className="flex-1 min-h-0"
        data={data}
        activeLayers={layers}
        window={window}
        onSelect={setSelection}
        selectedRef={selection.type === 'incident' ? selection.incident.id : undefined}
      />

      {/* Legend / selected entity / incident context */}
      <GisContextStrip
        selection={selection}
        forestZone={data.forestZone}
        sectorRef={data.sectorRef}
        coords={data.coords}
      />
    </div>
  )
}