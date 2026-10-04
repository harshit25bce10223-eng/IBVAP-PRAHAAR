// SightingCard.tsx — Compact list card for a single VehicleSighting
import { clsx } from 'clsx'
import { AlertTriangle, FileCheck } from 'lucide-react'
import { Badge } from '@/components/ui'
import { VehicleClassBadge } from './VehicleClassBadge'
import type { VehicleSighting } from '@/types/anpr'

interface SightingCardProps {
  sighting: VehicleSighting
  selected?: boolean
  onClick?: () => void
}

function fmtTime(iso: string): string {
  try {
    return new Date(iso).toLocaleTimeString('en-IN', {
      hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false,
    })
  } catch {
    return iso
  }
}

function confidenceVariant(c: number): 'safe' | 'warning' | 'critical' {
  if (c >= 0.8) return 'safe'
  if (c >= 0.5) return 'warning'
  return 'critical'
}

function qualityVariant(q: string): 'safe' | 'warning' | 'critical' | 'offline' | 'default' {
  switch (q) {
    case 'GOOD': return 'safe'
    case 'FAIR':
    case 'PARTIAL':
    case 'LOW_LIGHT':
    case 'MOTION_BLUR':
    case 'GLARE':
    case 'DIRTY': return 'warning'
    case 'POOR':
    case 'UNREADABLE':
    case 'OCCLUDED':
    case 'EXTREME_ANGLE': return 'critical'
    default: return 'offline'
  }
}

export function SightingCard({ sighting, selected, onClick }: SightingCardProps) {
  const hasPlate = sighting.plateRead !== null
  const conf = sighting.plateRead?.confidence ?? sighting.confidence ?? 0
  const quality = sighting.plateRead?.quality ?? 'UNKNOWN'

  return (
    <button
      type="button"
      onClick={onClick}
      className={clsx(
        'w-full text-left rounded-lg border p-3 transition-colors',
        'hover:border-cyan-500/40 hover:bg-surface',
        selected
          ? 'border-cyan-500/60 bg-surface ring-1 ring-cyan-500/20'
          : 'border-border bg-bg'
      )}
      aria-pressed={selected}
    >
      {/* Row 1: Plate + Quality + Confidence */}
      <div className="flex items-center justify-between gap-2 mb-1.5">
        <div className="flex items-center gap-2">
          {hasPlate ? (
            <span className="font-mono text-sm font-semibold text-ssb-green-bright tracking-wider">
              {sighting.plateRead!.displayRead}
            </span>
          ) : (
            <span className="font-mono text-sm text-slate-600 italic">UNREADABLE</span>
          )}
          {hasPlate && (
            <Badge variant={qualityVariant(quality)} size="sm">
              {quality.replace(/_/g, ' ')}
            </Badge>
          )}
        </div>
        {hasPlate && (
          <Badge variant={confidenceVariant(conf)} size="sm">
            {Math.round(conf * 100)}%
          </Badge>
        )}
      </div>

      {/* Row 2: Class · Camera · Time · Direction */}
      <div className="flex items-center gap-2 text-[11px] font-mono text-slate-400 flex-wrap">
        <VehicleClassBadge vehicleClass={sighting.vehicleClass} />
        <span className="text-slate-600">•</span>
        <span>{sighting.cameraId}</span>
        <span className="text-slate-600">•</span>
        <span>{fmtTime(sighting.observedAt)}</span>
        <span className="text-slate-600">•</span>
        <span>→ {sighting.vehicleDirection}</span>
      </div>

      {/* Row 3: Track ID + health + flags */}
      <div className="flex items-center gap-2 mt-1.5 text-[10px] font-mono">
        {sighting.vehicleTrackId && (
          <span className="text-cyan-600">{sighting.vehicleTrackId}</span>
        )}
        {sighting.cameraHealthState === 'DEGRADED' && (
          <span className="text-amber-400 flex items-center gap-0.5">
            <AlertTriangle className="h-3 w-3" />
            DEGRADED
          </span>
        )}
        {sighting.evidenceRef && (
          <Badge variant="cyan" size="sm">
            <FileCheck className="h-2.5 w-2.5 mr-0.5" />
            {sighting.evidenceRef}
          </Badge>
        )}
        {sighting.incidentRef && (
          <Badge variant="critical" size="sm">
            {sighting.incidentRef}
          </Badge>
        )}
        {sighting.watchlistStatus === 'WATCHLIST_MATCH' && (
          <Badge variant="critical" size="sm" dot>WATCHLIST</Badge>
        )}
      </div>
    </button>
  )
}