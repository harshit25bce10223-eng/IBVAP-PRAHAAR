// SightingDetail.tsx — Full detail panel for selected sighting
// §11 — 12-section decision-support structure:
//  01 Observation Summary · 02 Vehicle Context · 03 Plate Read · 04 Alternative Candidates
//  05 Plate Quality · 06 Camera Context · 07 Track Context · 08 Event/Correlation
//  09 Incident · 10 Evidence · 11 Observation History · 12 Provenance
import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { ExternalLink, FileCheck, AlertTriangle, Shield, Activity, Clock, RefreshCw } from 'lucide-react'
import { Badge } from '@/components/ui'
import { useANPRStore } from '@/store/anprState'
import { PlateDisplay } from './PlateDisplay'
import { PlateCandidatePanel } from './PlateCandidatePanel'
import { VehicleClassBadge } from './VehicleClassBadge'
import { CameraHealthContext } from './CameraHealthContext'
import { VehicleHistoryTimeline } from './VehicleHistoryTimeline'
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
    <section className="rounded-xl border border-border bg-surface p-4">
      <h3 className="text-[10px] font-mono uppercase tracking-wider text-slate-500 mb-3 border-b border-slate-800/60 pb-1.5">
        {title}
      </h3>
      {children}
    </section>
  )
}

// §14/§15 — crops render only where actually available; otherwise an explicit
// CONTENT UNAVAILABLE placeholder. No synthetic imagery is ever substituted.
function CropBlock({ label, url, alt }: { label: string; url: string | null; alt: string }) {
  return (
    <div>
      <div className="text-[9px] font-mono uppercase tracking-wider text-slate-600 mb-1">{label}</div>
      {url ? (
        <img
          src={url}
          alt={alt}
          loading="lazy"
          className="w-full h-24 object-cover rounded-lg border border-border bg-bg"
        />
      ) : (
        <div className="h-24 rounded-lg border border-dashed border-border bg-bg flex items-center justify-center">
          <span className="text-[10px] font-mono text-slate-600">CONTENT UNAVAILABLE</span>
        </div>
      )}
    </div>
  )
}

function EmptyRow({ text }: { text: string }) {
  return <div className="text-xs font-mono text-slate-600 italic">{text}</div>
}

export function SightingDetail({ sighting }: SightingDetailProps) {
  const { vehicleHistory, vehicleHistoryState, vehicleHistoryError, fetchVehicleHistory } = useANPRStore()

  // §16 — related sightings for this recorded vehicle identifier (separate from
  // track continuity, which is Component 6 authority).
  useEffect(() => {
    fetchVehicleHistory(sighting.vehicleId)
  }, [sighting.vehicleId, fetchVehicleHistory])

  const historyForThisVehicle =
    vehicleHistory && vehicleHistory.vehicleId === sighting.vehicleId ? vehicleHistory : null

  return (
    <div className="space-y-4 p-4 overflow-y-auto h-full">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="font-mono text-xs text-slate-500 uppercase tracking-wider">Sighting Record</div>
          <div className="font-mono text-lg font-bold text-cyan-300 mt-0.5">{sighting.sightingId}</div>
        </div>
        <div className="flex flex-col items-end gap-1">
          {watchlistBadge(sighting.watchlistStatus)}
          <span className="text-[10px] font-mono text-slate-500">
            Plate observation — decision support, not identity verification
          </span>
        </div>
      </div>

      {/* 01 — Observation Summary */}
      <Section title="01 · Observation Summary">
        <dl className="grid grid-cols-2 gap-3 text-xs font-mono">
          <div>
            <dt className="text-[9px] text-slate-600 uppercase">Observed At</dt>
            <dd className="text-slate-300">{fmtDateTime(sighting.observedAt)}</dd>
          </div>
          <div>
            <dt className="text-[9px] text-slate-600 uppercase">Received At</dt>
            <dd className="text-slate-400">{fmtDateTime(sighting.receivedAt)}</dd>
          </div>
          <div>
            <dt className="text-[9px] text-slate-600 uppercase">Camera</dt>
            <dd className="text-slate-300">{sighting.cameraId}</dd>
          </div>
          <div>
            <dt className="text-[9px] text-slate-600 uppercase">Read Confidence</dt>
            <dd className="text-slate-300">
              {sighting.plateRead ? Math.round(sighting.plateRead.confidence * 100) + '%' : '—'}
            </dd>
          </div>
          <div>
            <dt className="text-[9px] text-slate-600 uppercase">Vehicle Class</dt>
            <dd><VehicleClassBadge vehicleClass={sighting.vehicleClass} /></dd>
          </div>
          <div>
            <dt className="text-[9px] text-slate-600 uppercase">Watchlist Status</dt>
            <dd>{watchlistBadge(sighting.watchlistStatus)}</dd>
          </div>
        </dl>
        <p className="mt-2 text-[9px] text-slate-600 font-mono">
          Read confidence reflects recognition quality only — it is not an identity or threat assessment.
        </p>
      </Section>

      {/* 02 — Vehicle Context */}
      <Section title="02 · Vehicle Context">
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
          <div>
            <dt className="text-[9px] text-slate-600 uppercase">Detection Confidence</dt>
            <dd className="text-slate-400">
              {sighting.confidence !== null ? Math.round(sighting.confidence * 100) + '%' : '—'}
            </dd>
          </div>
        </dl>
        <p className="mt-2 text-[9px] text-slate-600 font-mono">
          Vehicle attributes are provider-reported observations for this capture, not a physical-presence claim.
          Detection confidence is separate from plate read confidence.
        </p>
      </Section>

      {/* 03 — Plate Read (§13) — plate record only: read confidence belongs to
          the plate read; detection confidence is shown separately in §02. */}
      <Section title="03 · Plate Read">
        <PlateDisplay plateRead={sighting.plateRead} />
      </Section>

      {/* 04 — Alternative Candidates */}
      <Section title="04 · Alternative Candidates">
        <PlateCandidatePanel candidates={sighting.plateCandidates} />
      </Section>

      {/* 05 — Plate Quality (§14/§15) */}
      <Section title="05 · Plate Quality">
        <div className="grid grid-cols-2 gap-3">
          <CropBlock
            label="Plate Crop"
            url={sighting.plateCropUrl}
            alt={`Plate crop for ${sighting.sightingId}`}
          />
          <CropBlock
            label="Source Frame"
            url={sighting.thumbnailUrl}
            alt={`Source frame for ${sighting.sightingId}`}
          />
        </div>
        <p className="mt-2 text-[9px] text-slate-600 font-mono">
          Capture quality states (glare, dirt, motion, low light) reduce read reliability. Media is shown only where actually available.
        </p>
      </Section>

      {/* 06 — Camera Context (§19) */}
      <Section title="06 · Camera Context">
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
        <p className="mt-2 text-[9px] text-slate-600 font-mono">
          Camera health state is reported by the camera registry — it is displayed here, not recalculated.
        </p>
      </Section>

      {/* 07 — Track Context (§17) */}
      <Section title="07 · Track Context">
        {sighting.vehicleTrackId ? (
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
        ) : (
          <EmptyRow text="No track association recorded for this observation." />
        )}
        <p className="mt-2 text-[9px] text-slate-600 font-mono">
          Track continuity and association are owned by Component 6 (Tracking) — not evaluated in this view.
        </p>
      </Section>

      {/* 08 — Event / Correlation */}
      <Section title="08 · Event / Correlation">
        <div className="space-y-2">
          {sighting.eventRef ? (
            <div className="flex items-center justify-between p-2 rounded-lg bg-bg border border-border">
              <div className="flex items-center gap-2">
                <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
                <span className="font-mono text-slate-200 text-xs">{sighting.eventRef}</span>
              </div>
              <Link to={'/events?ref=' + sighting.eventRef} className="text-xs font-mono text-amber-400 hover:underline">
                View Event →
              </Link>
            </div>
          ) : (
            <EmptyRow text="No event reference recorded." />
          )}
          {sighting.correlationRef ? (
            <div className="flex items-center justify-between p-2 rounded-lg bg-bg border border-border">
              <div className="flex items-center gap-2">
                <Activity className="h-3.5 w-3.5 text-purple-400" />
                <span className="font-mono text-slate-200 text-xs">{sighting.correlationRef}</span>
              </div>
              <Link to={'/incident/' + sighting.correlationRef} className="text-xs font-mono text-purple-400 hover:underline">
                View Activity →
              </Link>
            </div>
          ) : (
            <EmptyRow text="No correlation reference recorded." />
          )}
        </div>
        <p className="mt-2 text-[9px] text-slate-600 font-mono">
          Event and correlation references are produced by upstream intelligence components — displayed here, not recalculated.
        </p>
      </Section>

      {/* 09 — Incident */}
      <Section title="09 · Incident">
        {sighting.incidentRef ? (
          <div className="flex items-center justify-between p-2 rounded-lg bg-bg border border-border">
            <div className="flex items-center gap-2">
              <Shield className="h-3.5 w-3.5 text-red-400" />
              <span className="font-mono text-slate-200 text-xs">{sighting.incidentRef}</span>
            </div>
            <Link to={'/incident/' + sighting.incidentRef} className="text-xs font-mono text-red-400 hover:underline">
              View Incident →
            </Link>
          </div>
        ) : (
          <EmptyRow text="No incident link recorded for this observation." />
        )}
      </Section>

      {/* 10 — Evidence (§22) */}
      <Section title="10 · Evidence">
        {sighting.evidenceRef ? (
          <div className="flex items-center justify-between p-2 rounded-lg bg-bg border border-border">
            <div className="flex items-center gap-2">
              <FileCheck className="h-3.5 w-3.5 text-emerald-400" />
              <span className="font-mono text-slate-200 text-xs">{sighting.evidenceRef}</span>
            </div>
            <Link to="/evidence" className="text-xs font-mono text-emerald-400 hover:underline">
              View Evidence →
            </Link>
          </div>
        ) : (
          <EmptyRow text="No evidence record linked to this observation." />
        )}
        <p className="mt-2 text-[9px] text-slate-600 font-mono">
          Evidence records are owned by the Evidence Ledger (Component 3).
        </p>
      </Section>

      {/* 11 — Observation History (§16) */}
      <Section title="11 · Observation History">
        <div className="flex items-center justify-between mb-3">
          <span className="font-mono text-xs text-slate-300">{sighting.vehicleId}</span>
          <Link
            to={'/vehicle/' + sighting.vehicleId}
            className="inline-flex items-center gap-1 text-xs font-mono text-cyan-400 hover:underline"
          >
            <ExternalLink className="h-3 w-3" />
            Open Vehicle Detail
          </Link>
        </div>

        {vehicleHistoryState === 'loading' && !historyForThisVehicle && (
          <div className="text-xs font-mono text-slate-500">Loading observation history…</div>
        )}

        {vehicleHistoryState === 'error' && (
          <div className="flex items-center gap-2 text-xs font-mono text-amber-300">
            <span>{vehicleHistoryError ?? 'Vehicle history unavailable.'}</span>
            <button
              onClick={() => fetchVehicleHistory(sighting.vehicleId)}
              className="inline-flex items-center gap-1 text-cyan-400 hover:underline"
            >
              <RefreshCw className="h-3 w-3" />
              Retry
            </button>
          </div>
        )}

        {historyForThisVehicle && (
          <>
            <div className="flex items-center gap-3 mb-3 text-[10px] font-mono text-slate-500">
              <span>{historyForThisVehicle.totalSightings} related sightings</span>
              {historyForThisVehicle.firstSeen && (
                <span>first: {fmtDateTime(historyForThisVehicle.firstSeen)}</span>
              )}
              {historyForThisVehicle.lastSeen && (
                <span>last: {fmtDateTime(historyForThisVehicle.lastSeen)}</span>
              )}
            </div>
            {historyForThisVehicle.sightings.length > 0 ? (
              <VehicleHistoryTimeline history={historyForThisVehicle} />
            ) : (
              <EmptyRow text="No prior sightings recorded for this vehicle identifier." />
            )}
          </>
        )}
      </Section>

      {/* 12 — Provenance */}
      <Section title="12 · Provenance">
        <dl className="grid grid-cols-2 gap-3 text-xs font-mono">
          <div>
            <dt className="text-[9px] text-slate-600 uppercase">Source Provider</dt>
            <dd className="text-slate-300">{sighting.sourceProvider ?? '—'}</dd>
          </div>
          <div>
            <dt className="text-[9px] text-slate-600 uppercase">Observation Record</dt>
            <dd className="text-slate-400">{sighting.sightingId}</dd>
          </div>
          <div>
            <dt className="text-[9px] text-slate-600 uppercase">Source Frame Ref</dt>
            <dd className="text-slate-400">{sighting.plateRead?.sourceFrameRef ?? '—'}</dd>
          </div>
          <div>
            <dt className="text-[9px] text-slate-600 uppercase">Crop Reference</dt>
            <dd className="text-slate-400">{sighting.plateRead?.cropReference ?? '—'}</dd>
          </div>
        </dl>
        <p className="mt-2 text-[9px] text-slate-600 font-mono">
          Provider-reported provenance. This workspace performs no inference.
          {sighting.sourceProvider === 'ANPR-DEMO' && (
            <span className="text-amber-400/80"> Demo provider — simulated observation, not a production ANPR model.</span>
          )}
        </p>
      </Section>
    </div>
  )
}
