// ─────────────────────────────────────────────────────────────────────────────
// Component 1 — IncidentQuickDrawer
// Rapid command-center side drawer for reviewing flagged incidents without
// navigating away from operational monitoring tables.
// ─────────────────────────────────────────────────────────────────────────────

import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { X, ExternalLink, ShieldAlert, Clock, Camera, Layers } from 'lucide-react'
import { Button } from '@/components/ui'
import { RiskFactorsPanel } from './RiskFactorsPanel'
import type { IncidentRecord } from '@/types'

export interface IncidentQuickDrawerProps {
  open: boolean
  onClose: () => void
  incident: IncidentRecord | null
}

export function IncidentQuickDrawer({ open, onClose, incident }: IncidentQuickDrawerProps) {
  // Close drawer on Escape key
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && open) onClose()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [open, onClose])

  if (!open || !incident) return null

  return (
    <div
      className="fixed inset-0 z-50 flex justify-end bg-black/60 backdrop-blur-xs transition-opacity"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-labelledby="incident-drawer-title"
    >
      <div
        className="w-full max-w-md bg-[#0d1117] border-l border-[#1e2d40] h-full shadow-2xl flex flex-col overflow-hidden"
        onClick={e => e.stopPropagation()}
      >
        {/* Drawer Header */}
        <div className="flex items-center justify-between border-b border-[#1e2d40] p-4 bg-[#080c12]">
          <div className="flex items-center gap-2">
            <ShieldAlert className="h-4 w-4 text-cyan-400" />
            <div>
              <span className="text-[10px] font-mono uppercase text-slate-500 tracking-wider">
                Quick Situation Review
              </span>
              <h2 id="incident-drawer-title" className="text-sm font-bold font-mono text-slate-100">
                {incident.incident_id}
              </h2>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <Link
              to={`/incident/${incident.incident_id}`}
              className="text-xs font-mono text-cyan-400 hover:text-cyan-300 flex items-center gap-1 p-1 hover:bg-white/5 rounded"
              title="Open dedicated Incident / Situation View"
            >
              <span>Full View</span>
              <ExternalLink className="h-3.5 w-3.5" />
            </Link>

            <button
              onClick={onClose}
              className="p-1 rounded text-slate-400 hover:text-white hover:bg-white/5"
              aria-label="Close drawer"
            >
              <X className="h-5 w-5" />
            </button>
          </div>
        </div>

        {/* Drawer Body */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {/* Metadata quick strip */}
          <div className="grid grid-cols-2 gap-2 text-xs font-mono bg-white/[0.02] border border-white/5 p-2.5 rounded-lg">
            <div>
              <span className="text-slate-500 text-[10px] flex items-center gap-1">
                <Camera className="h-3 w-3" /> Camera
              </span>
              <p className="text-slate-200 mt-0.5">{incident.camera_id}</p>
            </div>
            <div>
              <span className="text-slate-500 text-[10px] flex items-center gap-1">
                <Layers className="h-3 w-3" /> Track ID
              </span>
              <p className="text-slate-200 mt-0.5">{incident.track_id}</p>
            </div>
            <div>
              <span className="text-slate-500 text-[10px]">Zone</span>
              <p className="text-slate-200 mt-0.5">{incident.zone_id}</p>
            </div>
            <div>
              <span className="text-slate-500 text-[10px] flex items-center gap-1">
                <Clock className="h-3 w-3" /> Timestamp
              </span>
              <p className="text-slate-300 mt-0.5 tabular-nums">
                {new Date(incident.created_at).toLocaleTimeString([], {
                  hour: '2-digit',
                  minute: '2-digit',
                  second: '2-digit',
                })}
              </p>
            </div>
          </div>

          {/* Full explainable factor panel */}
          <RiskFactorsPanel
            score={incident.risk_score}
            severity={incident.severity}
            factors={incident.factors}
            cameraId={incident.camera_id}
            trackId={incident.track_id}
            eventId={incident.event_id}
            zoneName={incident.zone_id}
          />
        </div>

        {/* Drawer Footer Actions */}
        <div className="p-4 border-t border-[#1e2d40] bg-[#080c12] flex items-center justify-between gap-3">
          <Button variant="ghost" size="sm" onClick={onClose} className="font-mono text-xs">
            Close
          </Button>

          <Link to={`/incident/${incident.incident_id}`} className="flex-1">
            <Button variant="primary" size="sm" className="w-full font-mono text-xs">
              Inspect Full Situation →
            </Button>
          </Link>
        </div>
      </div>
    </div>
  )
}
