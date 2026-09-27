// SightingDetail.tsx — Full detail panel for selected sighting
import { Link } from 'react-router-dom'
import { ExternalLink, FileCheck, AlertTriangle, Shield, Activity, Clock } from 'lucide-react'
import { Badge } from '@/components/ui'
import { PlateDisplay } from './PlateDisplay'
import { PlateCandidatePanel } from './PlateCandidatePanel'
import { VehicleClassBadge } from './VehicleClassBadge'
import { CameraHealthContext } from './CameraHealthContext'
import type { VehicleSighting } from '@/types/anpr'

interface SightingDetailProps {
  sighting: VehicleSighting
}

function fmtDateTime(iso: string): string {
  try {
    return new Date(iso).toLocaleString('en-IN', {
      dateStyle: 'short', timeStyle: 'medium', hour12: false,
    })
  } catch {
    return iso
  }
}

function watchlistBadge(status: VehicleSighting['watchlistStatus']) {
  switch (status) {
    case 'WATCHLIST_MATCH':
      return <Badge variant="critical" dot>WATCHLIST MATCH</Badge>
    case 'NO_MATCH':
      return <Badge variant="safe">NO MATCH</Badge>
    case 'NOT_CHECKED':
      return <Badge variant="offline">NOT CHECKED</Badge>
    case 'UNKNOWN':
    default:
      return <Badge variant="default">UNKNOWN</Badge>
  }
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-[#1e2d40] bg-[#0d1117] p-4">
      <h3 className="text-[10px] font-mono uppercase tracking-wider text-slate-500 mb-3 border-b border-slate-800/60 pb-1.5">
        {title}
      </h3>
      {children}
    </section>
  )
}

export function SightingDetail({ sighting }: SightingDetailProps) {
  return (
    <div className="space-y-4 p-4 overflow-y-auto h-full">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div>
          <div className="font-mono text-xs text-slate-500 uppercase tracking-wider">Sighting Record</div>
          <div className="font-mono text-lg font-bold text-cyan-300 mt-0.5">{sighting.sightingId}</div>
        </div>
        <div className="flex flex-col items-end gap-1">
          {watchlistBadge(sighting.watchlistStatus)}
          {sighting.confidence !== null && (
            <span className="text-[11px] font-mono text-slate-400">
              Match Confidence: {Math.round(sighting.confidence * 100)}%
            </span>
          )}
        </div>
      </div>

      {/* 1. Plate Information */}
      <Section title="Plate Information">
        <PlateDisplay plateRead={sighting.plateRead} candidates={sighting.plateCandidates} className="mb-3" />
        {sighting.plateCandidates.length > 0 && (
          <PlateCandidatePanel candidates={sighting.plateCandidates} />
        )}
      </Section>

      {/* 2. Vehicle Context */}
      <Section title="Vehicle Context">
        <dl className="grid grid-cols-2 gap-3 text-xs font-mono">
          <div>
            <dt className="text-[9px] text-slate-600 uppercase">Class</dt>
            <dd><VehicleClassBadge vehicleClass={sighting.vehicleClass} /></dd>
          </div>
          <div>
            <dt className="text-[9px] text-slate-600 uppercase">Color</dt>
            <dd className="text-slate-300">{sighting.vehicleColor}</dd>
          </div>
          <div>
            <dt className="text-[9px] text-slate-600 uppercase">Direction</dt>
            <dd className="text-slate-300">{sighting.vehicleDirection}</dd>
          </div>
          <div>
            <dt className="text-[9px] text-slate-600 uppercase">Detection Quality</dt>
            <dd className="text-slate-400">{sighting.detectionQuality ?? '—'}</dd>
          </div>
        </dl>
      </Section>

      {/* 3. Camera & Timing */}
      <Section title="Camera & Timing">
        <div className="space-y-2 text-xs font-mono">
          <CameraHealthContext cameraId={sighting.cameraId} healthState={sighting.cameraHealthState} />
          <div className="flex items-center gap-2 text-slate-400">
            <Clock className="h-3.5 w-3.5" />
            <span>{fmtDateTime(sighting.observedAt)}</span>
          </div>
          {sighting.locationContext && (
            <div className="text-slate-500">{sighting.locationContext}</div>
          )}
        </div>
      </Section>

      {/* 4. Track Link */}
      {sighting.vehicleTrackId && (
        <Section title="Track Link">
          <div className="flex items-center justify-between">
            <span className="font-mono text-sm text-cyan-300">{sighting.vehicleTrackId}</span>
            <Link
              to={'/track/' + sighting.vehicleTrackId}
              className="inline-flex items-center gap-1 text-xs font-mono text-cyan-400 hover:underline"
            >
              <ExternalLink className="h-3 w-3" />
              View Track
            </Link>
          </div>
        </Section>
      )}

      {/* 5. Related Intelligence */}
      {(sighting.evidenceRef || sighting.eventRef || sighting.incidentRef || sighting.correlationRef) && (
        <Section title="Related Intelligence">
          <div className="space-y-2">
            {sighting.incidentRef && (
              <div className="flex items-center justify-between p-2 rounded-lg bg-[#080c12] border border-[#1e2d40]">
                <div className="flex items-center gap-2">
                  <Shield className="h-3.5 w-3.5 text-red-400" />
                  <span className="font-mono text-slate-200 text-xs">{sighting.incidentRef}</span>
                </div>
                <Link to={'/incident/' + sighting.incidentRef} className="text-xs font-mono text-red-400 hover:underline">
                  View Incident →
                </Link>
              </div>
            )}
            {sighting.correlationRef && (
              <div className="flex items-center justify-between p-2 rounded-lg bg-[#080c12] border border-[#1e2d40]">
                <div className="flex items-center gap-2">
                  <Activity className="h-3.5 w-3.5 text-purple-400" />
                  <span className="font-mono text-slate-200 text-xs">{sighting.correlationRef}</span>
                </div>
                <Link to={'/incident/' + sighting.correlationRef} className="text-xs font-mono text-purple-400 hover:underline">
                  View Activity →
                </Link>
              </div>
            )}
            {sighting.eventRef && (
              <div className="flex items-center justify-between p-2 rounded-lg bg-[#080c12] border border-[#1e2d40]">
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
                  <span className="font-mono text-slate-200 text-xs">{sighting.eventRef}</span>
                </div>
                <Link to={'/events?ref=' + sighting.eventRef} className="text-xs font-mono text-amber-400 hover:underline">
                  View Event →
                </Link>
              </div>
            )}
            {sighting.evidenceRef && (
              <div className="flex items-center justify-between p-2 rounded-lg bg-[#080c12] border border-[#1e2d40]">
                <div className="flex items-center gap-2">
                  <FileCheck className="h-3.5 w-3.5 text-emerald-400" />
                  <span className="font-mono text-slate-200 text-xs">{sighting.evidenceRef}</span>
                </div>
                <Link to="/evidence" className="text-xs font-mono text-emerald-400 hover:underline">
                  View Evidence →
                </Link>
              </div>
            )}
          </div>
        </Section>
      )}

      {/* 6. Watchlist Status */}
      <Section title="Watchlist Status">
        <div className="flex items-center gap-3">
          {watchlistBadge(sighting.watchlistStatus)}
          {(sighting.watchlistStatus === 'NOT_CHECKED' || sighting.watchlistStatus === 'UNKNOWN') && (
            <span className="text-xs text-slate-500 font-mono">
              Plate has not been cross-referenced with operational watchlists.
            </span>
          )}
        </div>
      </Section>

      {/* 7. Relation Graph (simple chain) */}
      <Section title="Intelligence Chain">
        <div className="flex items-center gap-2 text-[11px] font-mono text-slate-500 flex-wrap">
          <span className="text-cyan-400">{sighting.sightingId}</span>
          <span>→</span>
          {sighting.vehicleTrackId ? (
            <Link to={'/track/' + sighting.vehicleTrackId} className="text-cyan-300 hover:underline">
              {sighting.vehicleTrackId}
            </Link>
          ) : (
            <span className="text-slate-700">No Track</span>
          )}
          <span>→</span>
          {sighting.eventRef ? (
            <span className="text-amber-400">{sighting.eventRef}</span>
          ) : (
            <span className="text-slate-700">No Event</span>
          )}
          <span>→</span>
          {sighting.incidentRef ? (
            <Link to={'/incident/' + sighting.incidentRef} className="text-red-400 hover:underline">
              {sighting.incidentRef}
            </Link>
          ) : (
            <span className="text-slate-700">No Incident</span>
          )}
          <span>→</span>
          {sighting.evidenceRef ? (
            <Link to="/evidence" className="text-emerald-400 hover:underline">
              {sighting.evidenceRef}
            </Link>
          ) : (
            <span className="text-slate-700">No Evidence</span>
          )}
        </div>
      </Section>
    </div>
  )
}