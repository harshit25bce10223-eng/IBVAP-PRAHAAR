import { Link } from 'react-router-dom'
import { ArrowRight, Camera as CameraIcon, FileSearch, Fingerprint, Network } from 'lucide-react'
import type { ReactNode } from 'react'
import type { DetectionResult } from '@/types/detection'
import { Badge, Drawer } from '@/components/ui'
import {
  describeConfidence,
  formatBBox,
  formatClock,
  formatClassLabel,
  formatDate,
  formatFrameInfo,
  formatSourceLabel,
} from './detectionFormat'
import { badgeTone, dotTone, textTone, toneForDetectionState, toneForQuality } from './detectionTone'

interface DetectionInspectorProps {
  open: boolean
  onClose: () => void
  detection: DetectionResult | null
  /** Any local additional label, e.g. camera label from the camera registry. */
  cameraLabel?: string | null
}

/**
 * Detection Inspector (Component spec §30/§96–§97). Sections are hidden when
 * their data is empty. Every displayed value is provider-supplied; missing
 * values render as N/A or a hidden section, never as a fabricated fact.
 * We NEVER display a track id unless the backend provided one, and related
 * references (event/incident/evidence) are links to existing surfaces only.
 */
export function DetectionInspector({ open, onClose, detection, cameraLabel }: DetectionInspectorProps) {
  if (!detection) return null

  const health = detection.cameraHealth
  const stateTone = toneForDetectionState(detection.state)
  const qualityTone = toneForQuality(detection.quality)
  const identifiersCount = [detection.trackId, detection.eventId, detection.incidentId, detection.evidenceId, detection.correlationId].filter(
    (v): v is string => v !== null
  ).length

  return (
    <Drawer open={open} onClose={onClose} title="Detection Inspector" width="w-[460px]">
      {/* Identity strip */}
      <div className="flex items-center justify-between gap-2">
        <div>
          <p className="font-mono text-sm text-slate-100" title="Detection id">{detection.detectionId}</p>
          <p className="text-[11px] text-slate-500">{formatDate(detection.timestamp)} · {formatClock(detection.timestamp)}</p>
        </div>
        <div className="flex flex-col items-end gap-1.5">
          <span className="font-mono text-[11px] font-semibold uppercase tracking-wider text-slate-200">
            {formatClassLabel(detection.class)}
          </span>
          <Badge variant={badgeTone(stateTone)} size="sm" dot>{detection.state}</Badge>
        </div>
      </div>

      <div className="mt-2 flex items-center gap-1 font-mono text-[11px] text-slate-400">
        <CameraIcon size={12} aria-hidden />
        <span className="uppercase">{detection.cameraId}</span>
        {cameraLabel && <span className="text-slate-500">· {cameraLabel}</span>}
        <span className="text-slate-600">· {formatSourceLabel(detection.source)} inference</span>
      </div>

      {/* Camera-health context (only when the backend flags it) */}
      {health && (
        <section className="mt-4 rounded-lg border border-amber-500/25 bg-amber-500/5 p-3" aria-label="Camera health context">
          <div className="flex items-center justify-between gap-2">
            <span className="flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-amber-300">
              <span className={dotTone(health.reliability === 'HIGH' ? 'info' : health.reliability === 'MEDIUM' ? 'warning' : 'danger')} aria-hidden />
              HEALTH · {health.reliability === 'HIGH' ? 'RELIABLE' : health.reliability === 'MEDIUM' ? 'DEGRADED' : 'LOW'}
            </span>
            {detection.cameraHealth?.note && <span className="text-[10px] text-slate-400">source reliability</span>}
          </div>
          {health.viewpointShift && (
            <p className="mt-2 text-[11px] text-amber-300/90">
              Camera viewpoint changed; detection geometry may require review.
            </p>
          )}
          {health.note && <p className="mt-1.5 text-[11px] text-slate-400">{health.note}</p>}
          <p className="mt-2 text-[10px] text-slate-500">
            Detector confidence above is separate from camera/source reliability.
          </p>
        </section>
      )}

      {/* Observation */}
      <Section title="Observation">
        <Row label="Confidence">
          <span className={badgeTone(stateTone) === 'warning' ? 'font-mono text-amber-300' : 'font-mono text-slate-200'}>
            {detection.confidence === null ? 'N/A' : describeConfidence(detection.confidence)}
          </span>
        </Row>
        <Row label="Detected at" mono>{formatClock(detection.timestamp)}</Row>
        <Row label="Received at" mono>
          {detection.receivedAt ? formatClock(detection.receivedAt) : 'N/A'}
        </Row>
        <Row label="Camera">{detection.cameraId}</Row>
        {detection.frameWidth && detection.frameHeight && (
          <Row label="Frame size" mono>{detection.frameWidth}×{detection.frameHeight}</Row>
        )}
      </Section>

      {/* Geometry — technical detail only, never shown on the box itself */}
      <Section title="Geometry">
        <Row label="Bounding box" mono>
          {formatBBox(detection.bbox?.x, detection.bbox?.y, detection.bbox?.width, detection.bbox?.height)}
        </Row>
        {detection.frameId && <Row label="Frame ID" mono>{detection.frameId}</Row>}
        <Row label="Frame" mono>{formatFrameInfo(detection.frameNumber, detection.fps)}</Row>
      </Section>

      {/* Quality / visibility */}
      <Section title="Quality">
        <Row label="Quality">
          <span className={textTone(qualityTone)}>{detection.quality}</span>
        </Row>
        {detection.occlusion && <Row label="Occlusion" mono>{detection.occlusion}</Row>}
        <Row label="State">
          <span className={textTone(stateTone)}>{detection.state}</span>
        </Row>
        <Row label="Flags">
          {detection.partial || detection.frameEdge || detection.smallTarget || detection.longRange ? (
            <span className="font-mono text-[10px] text-slate-400">
              {[
                detection.partial && 'PARTIAL',
                detection.frameEdge && 'FRAME EDGE',
                detection.smallTarget && 'SMALL TARGET',
                detection.longRange && 'LONG RANGE',
              ].filter(Boolean).join(' · ')}
            </span>
          ) : (
            <span className="text-[11px] text-slate-600">none reported</span>
          )}
        </Row>
        {detection.visibility && detection.visibility !== 'UNKNOWN' && (
          <Row label="Lighting" mono>{detection.visibility}</Row>
        )}
      </Section>

      {/* Provenance — shown only when actually provided */}
      {(detection.provider || detection.model || detection.modelVersion) && (
        <Section title="Provenance">
          {detection.provider && <Row label="Provider" mono>{detection.provider}</Row>}
          {detection.model && <Row label="Model" mono>{detection.model}</Row>}
          {detection.modelVersion && <Row label="Version" mono>{detection.modelVersion}</Row>}
          <Row label="Inference" mono>{formatSourceLabel(detection.source)}</Row>
          <Row label="Provenance">{detection.regionProfile ? detection.regionProfile : '—'}</Row>
        </Section>
      )}

      {/* Relationships — links to existing surfaces only, never created here */}
      <Section title="Relationships">
        <Row label="Track">
          {detection.trackId ? (
            <Link
              to={`/track/${detection.trackId}`}
              className="flex items-center gap-1.5 font-mono text-cyan-400 hover:text-cyan-300 underline underline-offset-2"
              title="Inspect Component 6 track continuity"
            >
              <Network size={11} className="text-cyan-400" aria-hidden />
              {detection.trackId}
              <span className="text-[9px] uppercase tracking-wider text-slate-500 no-underline">candidate</span>
            </Link>
          ) : (
            <span className="text-[11px] text-slate-500">TRACK NOT AVAILABLE</span>
          )}
        </Row>
        <Row label="Event">
          {detection.eventId ? (
            <Link to={`/events?search=${encodeURIComponent(detection.correlationId ?? detection.eventId)}`} className="font-mono text-cyan-400 hover:text-cyan-300 flex items-center gap-1">
              {detection.eventId}<ArrowRight size={10} aria-hidden />
            </Link>
          ) : (
            <span className="text-[11px] text-slate-500">EVENT NOT CREATED</span>
          )}
        </Row>
        <Row label="Incident">
          {detection.incidentId ? (
            detection.correlationId ? (
              <Link to={`/incident/${detection.correlationId}`} className="font-mono text-cyan-400 hover:text-cyan-300 flex items-center gap-1">
                {detection.incidentId}<ArrowRight size={10} aria-hidden />
              </Link>
            ) : (
              // An incident id without a correlation id is not directly
              // routable — render it verbatim instead of a broken link.
              <span className="font-mono text-slate-300">{detection.incidentId}</span>
            )
          ) : (
            <span className="text-[11px] text-slate-500">no incident linked</span>
          )}
        </Row>
        <Row label="Evidence">
          {detection.evidenceId ? (
            <Link to={`/evidence?search=${encodeURIComponent(detection.evidenceId)}`} className="flex items-center gap-1 text-cyan-400 hover:text-cyan-300">
              <FileSearch size={11} aria-hidden />
              <span className="font-mono">{detection.evidenceId}</span>
              <span className="text-[9px] uppercase tracking-wider text-slate-400">ledger</span>
            </Link>
          ) : (
            <span className="text-[11px] text-slate-500">EVIDENCE AVAILABLE: none linked</span>
          )}
        </Row>
        {/* ANPR/vehicle reference (§14): displayed verbatim when the backend
            supplies one. Component 5 performs no ANPR logic and never invents
            a plate — this is a read-only cross-reference into Component 7. */}
        {detection.anprRef && (
          <Row label="ANPR reference" mono>
            <span className="font-mono text-slate-300">{detection.anprRef}</span>
            <span className="ml-2 text-[9px] uppercase tracking-wider text-slate-500">read-only</span>
          </Row>
        )}
        {detection.correlationId && (
          <Row label="Correlation">
            <Link to={`/incident/${detection.correlationId}`} className="font-mono text-cyan-400 hover:text-cyan-300 flex items-center gap-1">
              {detection.correlationId}<ArrowRight size={10} aria-hidden />
            </Link>
          </Row>
        )}
        {detection.bbox && (
          <p className="pt-2 text-[10px] leading-relaxed text-slate-600">
            Box class {formatClassLabel(detection.class)} ({detection.class}); geometric coordinates are normalized, displayed for operator review only.
          </p>
        )}
      </Section>

      <div className="mt-4 border-t border-white/5 pt-3">
        <p className="text-[10px] text-slate-600">
          {identifiersCount > 0
            ? `${identifiersCount} related record(s) linked by the backend. No record is created by this UI.`
            : 'This observation links to no track, event, incident or evidence record.'}
        </p>
      </div>
    </Drawer>
  )
}

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="mt-5" aria-label={title}>
      <h3 className="flex items-center gap-1.5 text-[10px] font-semibold uppercase tracking-widest text-slate-500">
        <Fingerprint size={11} aria-hidden /> {title}
      </h3>
      <dl className="mt-2 space-y-1 text-[11px]">{children}</dl>
    </section>
  )
}

function Row({ label, mono, children }: { label: string; mono?: boolean; children: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-3">
      <dt className="shrink-0 text-slate-500">{label}</dt>
      <dd className={mono ? 'font-mono text-slate-200 text-right' : 'text-slate-200 text-right'}>{children}</dd>
    </div>
  )
}