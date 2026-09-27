// ─────────────────────────────────────────────────────────────────────────────
// GisLayerBar — restrained operational controls for the GIS / Digital Twin map.
//
// Layer toggles + time window are deliberately small and non-dominant (spec §8):
// the map stays the visual centre of the screen.
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'
import type { GisLayerId, GisTimeWindow } from '@/types'

interface Props {
  layers: GisLayerId[]
  activeLayers: Set<GisLayerId>
  onToggleLayer: (layer: GisLayerId) => void
  window: GisTimeWindow
  onWindowChange: (window: GisTimeWindow) => void
}

const LAYER_LABELS: Record<GisLayerId, string> = {
  cameras: 'Cameras',
  tracks: 'Tracks',
  incidents: 'Incidents',
  restrictedZones: 'Restricted Zones',
  riskHeat: 'Risk Heat',
  historical: 'Historical Activity',
}

const WINDOWS: GisTimeWindow[] = ['LIVE', '24H', '7D']

export function GisLayerBar({ layers, activeLayers, onToggleLayer, window, onWindowChange }: Props) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-md border border-ssb-border/70 bg-ssb-navy/60 px-3 py-1.5 flex-shrink-0">
      <div className="flex items-center gap-1.5 flex-wrap">
        <span className="text-[9px] font-semibold uppercase tracking-[0.16em] text-ssb-text-muted/70 mr-1">
          Layers
        </span>
        {layers.map(layer => {
          const active = activeLayers.has(layer)
          return (
            <button
              key={layer}
              type="button"
              onClick={() => onToggleLayer(layer)}
              aria-pressed={active}
              className={clsx(
                'rounded px-2 py-0.5 text-[10px] font-medium transition-colors border cursor-pointer',
                active
                  ? 'bg-ssb-green/20 border-ssb-green-bright/50 text-ssb-green-bright'
                  : 'border-ssb-border/60 text-ssb-text-muted hover:text-ssb-white hover:border-ssb-text-muted/50'
              )}
            >
              {LAYER_LABELS[layer]}
            </button>
          )
        })}
      </div>

      <div className="flex items-center gap-1">
        <span className="text-[9px] font-semibold uppercase tracking-[0.16em] text-ssb-text-muted/70 mr-1">
          Window
        </span>
        {WINDOWS.map(w => (
          <button
            key={w}
            type="button"
            onClick={() => onWindowChange(w)}
            aria-pressed={window === w}
            className={clsx(
              'rounded px-2 py-0.5 text-[10px] font-mono font-semibold transition-colors border cursor-pointer',
              window === w
                ? 'bg-ssb-amber/20 border-ssb-amber-bright/60 text-ssb-amber-bright'
                : 'border-ssb-border/60 text-ssb-text-muted hover:text-ssb-white'
            )}
          >
            {w}
          </button>
        ))}
      </div>
    </div>
  )
}