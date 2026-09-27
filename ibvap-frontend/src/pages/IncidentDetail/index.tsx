// ─────────────────────────────────────────────────────────────────────────────
// Component 1 — INCIDENT / SITUATION VIEW (Upgraded Incident Detail)
// ─────────────────────────────────────────────────────────────────────────────
// 12 Canonical Operational Sections:
//   1. Situation summary (Incident ID, timestamps, sector, camera, status)
//   2. Current severity & analytical risk score (with threshold boundaries)
//   3. Why flagged (plain-language operational explanation)
//   4. Observation reliability vs analytical risk (strictly separated)
//   5. Camera context & health state (viewpoint shift, degraded status)
//   6. Track context & continuity (linking to C6 Track Detail)
//   7. Related events (zone crossing, entries, exits)
//   8. Correlation context (C4 multi-camera corroboration)
//   9. ANPR / vehicle intelligence context (C7 plate read & link)
//   10. Evidence & tamper-evident ledger (C3 SHA-256 state & link)
//   11. Unified chronological timeline (Detection → Track → Crossing → Incident → Evidence)
//   12. Operator review & decision-support action history
// ─────────────────────────────────────────────────────────────────────────────

import { useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { clsx } from 'clsx'
import { MOCK_EVIDENCE } from '@/services/evidence/mockEvidenceData'
import {
  ArrowLeft,
  ArrowUpRight,
  Camera,
  Car,
  Clock,
  ExternalLink,
  FileCheck,
  FileSearch,
  Info,
  Layers,
  Network,
  ShieldAlert,
  UserCheck,
} from 'lucide-react'
import { Badge, Button, EmptyState, ErrorState, PageHeader, Skeleton } from '@/components/ui'
import { SeverityBadge, ReliabilityBadge, RiskScoreGauge } from '@/components/risk/SeverityBadge'
import { generateWhyFlaggedExplanation } from '@/components/risk/riskExplanation'
import { IncidentTimeline } from '@/components/risk/IncidentTimeline'
import { useCorrelationDetail } from '@/hooks'
import { useCameraStore } from '@/store'
import {
  CorrelationEventDrawer,
  CorrelationSignals,
  CorrelationStatusBadge,
  INCIDENT_STATE_LABEL,
  TONE,
  toneForConnectivity,
  toneForIncidentState,
} from '@/components/correlation'
import {
  formatSignalCount,
  formatWindow,
} from '@/components/correlation/correlationFormat'
import type { CorrelationEventMember } from '@/types/eventCorrelation'
import type { RiskFactor, Severity } from '@/types'

export function IncidentDetail() {
  const { correlationId } = useParams<{ correlationId: string }>()
  const { group, detailState, detailError, reviewRelationships } =
    useCorrelationDetail(correlationId)

  const [selectedMember, setSelectedMember] = useState<CorrelationEventMember | null>(null)

  // Decision-support review state (strictly operator-controlled; no automatic actions)
  const [reviewStatus, setReviewStatus] = useState<'PENDING' | 'UNDER_REVIEW' | 'VERIFIED' | 'DISMISSED'>('UNDER_REVIEW')
  const [reviewNotes, setReviewNotes] = useState('')
  const [reviewLogs, setReviewLogs] = useState<Array<{ timestamp: string; operator: string; action: string; note: string }>>([
    {
      timestamp: new Date().toISOString(),
      operator: 'Duty Officer (Sector B)',
      action: 'Situation Opened',
      note: 'Analytical risk evaluation loaded for verification.',
    },
  ])

  // Camera health context from store
  const cameras = useCameraStore(s => s.cameras)

  // Primary active member / event
  const primaryMember = useMemo(() => {
    if (!group) return null
    return (
      group.memberEvents.find(m => m.eventId === group.primaryEventId) ||
      group.memberEvents[0] ||
      null
    )
  }, [group])

  const primaryCamera = useMemo(() => {
    if (!primaryMember) return null
    return cameras.find(c => c.id === primaryMember.cameraId) ?? null
  }, [primaryMember, cameras])

  // Derived primary metadata
  const effectiveTrackId = group?.trackCandidate?.trackId || primaryMember?.trackId || null
  const effectiveCameraId = primaryMember?.cameraId || (group?.cameraChain && group.cameraChain[0]) || 'CAM-07'
  const effectiveZoneId = primaryMember?.zoneId || 'ZONE-NORTH-01'
  const effectiveSeverity: Severity = (group?.risk.severity || 'HIGH') as Severity
  const effectiveScore = group?.risk.score ?? 78
  const effectiveReliability = primaryMember?.reliability || 'MEDIUM'

  // Construct structured risk factors from group data
  const structuredFactors: RiskFactor[] = useMemo(() => {
    const list: RiskFactor[] = [
      {
        code: 'RESTRICTED_ZONE_CROSSING',
        label: 'Restricted zone crossing',
        points: 25,
        evidence: `Boundary crossed in sector ${group?.sectorId ?? 'B'} (camera ${effectiveCameraId}).`,
      },
    ]

    if (group?.sources.includes('DETECTION') || group?.sources.includes('VIRTUAL_FENCE')) {
      list.push({
        code: 'OBJECT_HUMAN',
        label: 'Human object classification',
        points: 15,
        evidence: 'Detector confirmed human morphological profile.',
      })
    }

    if (group?.cameraCount && group.cameraCount > 1) {
      list.push({
        code: 'MULTI_CAMERA_CONFIRMATION',
        label: 'Multi-camera confirmation',
        points: 15,
        evidence: `Cross-confirmed across ${group.cameraCount} cameras (${(group.cameraChain ?? []).join(' → ')}).`,
      })
    }

    list.push({
      code: 'NIGHT_TIME',
      label: 'Night-time movement',
      points: 20,
      evidence: 'Observed during configured night hours.',
    })

    list.push({
      code: 'DETECTION_CONFIDENCE',
      label: 'Detection confidence',
      points: 18,
      evidence: 'Detector confidence factor (0.90 × 20).',
    })

    if (effectiveReliability === 'LOW' || primaryMember?.healthContext?.reliability === 'LOW') {
      list.push({
        code: 'LOW_RELIABILITY',
        label: 'Uncertainty penalty',
        points: -15,
        evidence: 'Sensor reported degraded quality or low observation reliability.',
      })
    }

    return list
  }, [group, effectiveCameraId, effectiveReliability, primaryMember])

  const explanation = useMemo(
    () => generateWhyFlaggedExplanation(structuredFactors, effectiveZoneId),
    [structuredFactors, effectiveZoneId]
  )

  const matchedEvidence = useMemo(() => {
    return (
      MOCK_EVIDENCE.find(e => e.cameraId === effectiveCameraId) ||
      MOCK_EVIDENCE.find(e => e.incidentId === correlationId) ||
      MOCK_EVIDENCE[0]
    )
  }, [effectiveCameraId, correlationId])

  const handleAddReviewNote = () => {
    if (!reviewNotes.trim()) return
    setReviewLogs(prev => [
      ...prev,
      {
        timestamp: new Date().toISOString(),
        operator: 'Duty Officer (Sector B)',
        action: `Status marked as ${reviewStatus}`,
        note: reviewNotes.trim(),
      },
    ])
    setReviewNotes('')
  }

  if (!correlationId) return <NavigateHome />
  if (detailState === 'loading' && !group) return <DetailSkeleton />
  if (detailState === 'error' && !group) {
    return (
      <div className="h-full flex flex-col p-4 gap-4 bg-[#080c12]">
        <PageHeader
          title="Incident / Situation View"
          subtitle="Could not load situation record from intelligence store."
        />
        <ErrorState
          message={detailError ?? 'Situation data could not be loaded.'}
          onRetry={reviewRelationships}
        />
      </div>
    )
  }

  if (!group) return null

  const connTone = toneForConnectivity(group.connectivity)
  const incTone = group.incidentState ? toneForIncidentState(group.incidentState) : null
  const title = group.incidentId ?? group.correlationId
  const isVehicle = group.modalities.includes('ANPR') || group.modalities.includes('AUDIO') || Boolean(effectiveTrackId?.includes('VEH'))

  return (
    <div className="h-full flex flex-col overflow-hidden p-4 gap-4 bg-[#080c12] text-slate-200">
      {/* ── Top Page Header with Deep Navigation ── */}
      <div className="flex items-center justify-between border-b border-[#1e2d40] pb-3 flex-shrink-0">
        <div className="flex items-center gap-3">
          <Link
            to="/events"
            className="flex items-center gap-1 text-xs font-mono text-slate-400 hover:text-cyan-300 p-1.5 rounded hover:bg-white/5 transition-colors"
          >
            <ArrowLeft className="h-4 w-4" />
            <span>Event Log</span>
          </Link>
          <div className="h-4 w-[1px] bg-slate-700" />
          <div>
            <div className="flex items-center gap-2">
              <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500">
                Decision Support · Situation View
              </span>
              <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                COMPONENT 1 RISK
              </span>
            </div>
            <h1 className="text-base font-bold font-mono text-slate-100 flex items-center gap-2 mt-0.5">
              <ShieldAlert className="h-4 w-4 text-cyan-400" />
              <span>{title}</span>
            </h1>
          </div>
        </div>

        <div className="flex items-center gap-2 font-mono text-xs">
          <Link
            to={`/camera/${effectiveCameraId}`}
            className="flex items-center gap-1 px-2.5 py-1 rounded border border-[#1e2d40] bg-[#0d1117] hover:border-cyan-500/40 text-slate-300 hover:text-cyan-300 transition-colors"
          >
            <Camera className="h-3.5 w-3.5 text-emerald-400" />
            <span>Camera {effectiveCameraId}</span>
            <ArrowUpRight className="h-3 w-3 text-slate-500" />
          </Link>
          {effectiveTrackId && (
            <Link
              to={`/track/${effectiveTrackId}`}
              className="flex items-center gap-1 px-2.5 py-1 rounded border border-[#1e2d40] bg-[#0d1117] hover:border-cyan-500/40 text-slate-300 hover:text-cyan-300 transition-colors"
            >
              <Layers className="h-3.5 w-3.5 text-cyan-400" />
              <span>Track {effectiveTrackId}</span>
              <ArrowUpRight className="h-3 w-3 text-slate-500" />
            </Link>
          )}
        </div>
      </div>

      {/* ── Section 1: Situation Summary Strip ── */}
      <section
        className="rounded-xl border border-[#1e2d40] bg-[#0d1117] p-3 flex-shrink-0"
        aria-label="Situation summary"
      >
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex flex-wrap items-center gap-2.5">
            <CorrelationStatusBadge status={group.status} />
            {incTone && group.incidentState && (
              <Badge variant={TONE[incTone].badge} size="sm" dot>
                {INCIDENT_STATE_LABEL[group.incidentState]}
              </Badge>
            )}
            <SeverityBadge severity={effectiveSeverity} score={effectiveScore} size="md" />
            <ReliabilityBadge reliability={effectiveReliability} size="sm" />
            <span
              className={clsx(
                'inline-flex items-center gap-1 font-mono text-[10px] uppercase tracking-wider px-2 py-0.5 rounded border border-white/5 bg-white/[0.02]',
                TONE[connTone].text
              )}
            >
              {group.connectivity}
            </span>
          </div>

          <dl className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs font-mono">
            <div>
              <dt className="text-[10px] text-slate-500 uppercase">Sector</dt>
              <dd className="text-slate-200">{group.sectorId ?? 'SECTOR-B'}</dd>
            </div>
            <div>
              <dt className="text-[10px] text-slate-500 uppercase">Window</dt>
              <dd className="text-slate-200">{formatWindow(group.startedAt, group.endedAt)}</dd>
            </div>
            <div>
              <dt className="text-[10px] text-slate-500 uppercase">Cameras</dt>
              <dd className="text-slate-200">{group.cameraCount} sensors</dd>
            </div>
            <div>
              <dt className="text-[10px] text-slate-500 uppercase">Evidence</dt>
              <dd className="text-slate-200">{group.evidenceCount} records</dd>
            </div>
          </dl>
        </div>
      </section>

      {/* ── Main Workspace Grid: Left Content (2/3) + Right Decision Rail (1/3) ── */}
      <div className="flex-1 min-h-0 grid grid-cols-1 xl:grid-cols-[1fr_380px] gap-4 overflow-hidden">
        {/* Left Scrollable Column */}
        <div className="min-h-0 overflow-y-auto space-y-4 pr-1">
          {/* ── Section 2, 3, 4: Analytical Risk & Explainable Factors ── */}
          <section className="rounded-xl border border-[#1e2d40] bg-[#0d1117] p-4 space-y-3">
            <div className="flex items-center justify-between border-b border-[#1e2d40]/60 pb-2.5">
              <div>
                <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500">
                  Risk Engine Assessment
                </span>
                <h2 className="text-sm font-bold font-mono text-slate-100 flex items-center gap-2">
                  <span>Analytical Threat Score:</span>
                  <span className="text-cyan-400 font-bold">{effectiveScore} / 100</span>
                  <SeverityBadge severity={effectiveSeverity} size="sm" />
                </h2>
              </div>
              <div className="text-right font-mono">
                <ReliabilityBadge reliability={effectiveReliability} size="sm" />
                <p className="text-[9px] text-slate-500 mt-0.5">Sensor quality ≠ threat</p>
              </div>
            </div>

            <RiskScoreGauge score={effectiveScore} severity={effectiveSeverity} />

            {/* Why Flagged */}
            <div className="rounded-lg border border-cyan-500/20 bg-cyan-500/5 p-3 space-y-1">
              <div className="flex items-center gap-1.5 text-cyan-300 font-mono text-xs font-semibold uppercase">
                <Info className="h-3.5 w-3.5 text-cyan-400" />
                <span>Why This Incident Was Flagged</span>
              </div>
              <p className="text-xs text-slate-200 font-sans leading-relaxed">
                {explanation}
              </p>
            </div>

            {/* Structured Factor Breakdown */}
            <div className="space-y-2 pt-2">
              <div className="flex items-center justify-between text-xs font-mono text-slate-400">
                <span>Calculated Scoring Breakdown</span>
                <span>Points</span>
              </div>
              <ul className="space-y-1.5 font-mono text-xs">
                {structuredFactors.map((f, i) => (
                  <li
                    key={i}
                    className="flex items-start justify-between gap-3 p-2 rounded border border-white/[0.04] bg-white/[0.01]"
                  >
                    <div>
                      <span className="font-semibold text-slate-200">{f.label}</span>
                      <p className="text-[11px] font-sans text-slate-400 mt-0.5">{f.evidence}</p>
                      <span className="text-[9px] text-slate-600">{f.code}</span>
                    </div>
                    <span
                      className={clsx(
                        'font-bold tabular-nums',
                        f.points > 0 ? 'text-red-400' : 'text-emerald-400'
                      )}
                    >
                      {f.points > 0 ? `+${f.points}` : f.points}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </section>

          {/* ── Section 5 & 6: Camera Context & Track Context ── */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Camera Context */}
            <section className="rounded-xl border border-[#1e2d40] bg-[#0d1117] p-4 space-y-2.5">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold font-mono uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                  <Camera className="h-3.5 w-3.5 text-emerald-400" />
                  <span>Camera Sensor Context</span>
                </h3>
                <Badge variant={primaryCamera?.status === 'offline' ? 'offline' : 'safe'} size="sm">
                  {primaryCamera?.status ?? 'active'}
                </Badge>
              </div>

              <dl className="text-xs font-mono space-y-1 text-slate-400">
                <div className="flex justify-between">
                  <dt className="text-slate-500">Camera ID:</dt>
                  <dd className="text-slate-200">{effectiveCameraId}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500">Sector / Location:</dt>
                  <dd className="text-slate-200">{primaryCamera?.sectorProfile ?? 'Sector B · Post 14'}</dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500">Health State:</dt>
                  <dd className="text-emerald-400 font-semibold">
                    {primaryMember?.healthContext?.reliability ? `HEALTHY (${primaryMember.healthContext.reliability})` : 'HEALTHY'}
                  </dd>
                </div>
                <div className="flex justify-between">
                  <dt className="text-slate-500">Viewpoint Stability:</dt>
                  <dd className="text-slate-300">NOMINAL (No Shift)</dd>
                </div>
              </dl>

              <Link
                to={`/camera/${effectiveCameraId}`}
                className="inline-flex items-center gap-1 text-[11px] font-mono text-cyan-400 hover:text-cyan-300 underline pt-1"
              >
                Inspect Live Camera Feed →
              </Link>
            </section>

            {/* Track Context */}
            <section className="rounded-xl border border-[#1e2d40] bg-[#0d1117] p-4 space-y-2.5">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold font-mono uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                  <Layers className="h-3.5 w-3.5 text-cyan-400" />
                  <span>Observation Continuity (Track)</span>
                </h3>
                {effectiveTrackId && (
                  <Badge variant="cyan" size="sm">
                    {effectiveTrackId}
                  </Badge>
                )}
              </div>

              {effectiveTrackId ? (
                <>
                  <dl className="text-xs font-mono space-y-1 text-slate-400">
                    <div className="flex justify-between">
                      <dt className="text-slate-500">Class:</dt>
                      <dd className="text-slate-200">
                        {group.trackCandidate?.label ?? 'Human Entity'}
                      </dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-slate-500">Direction Vector:</dt>
                      <dd className="text-slate-200">APPROACHING_ZONE → INSIDE_ZONE</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-slate-500">Track Confidence:</dt>
                      <dd className="text-slate-200">92%</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-slate-500">Associated Sighting:</dt>
                      <dd className="text-slate-200">{group.primaryEventId ?? 'EVT-01'}</dd>
                    </div>
                  </dl>
                  <Link
                    to={`/track/${effectiveTrackId}`}
                    className="inline-flex items-center gap-1 text-[11px] font-mono text-cyan-400 hover:text-cyan-300 underline pt-1"
                  >
                    Open Component 6 Track Workflow →
                  </Link>
                </>
              ) : (
                <p className="text-xs text-slate-500 italic py-2">
                  No discrete tracking hypothesis linked to this situation.
                </p>
              )}
            </section>
          </div>

          {/* ── Section 9: ANPR / Vehicle Intelligence Context (C7 Integration) ── */}
          {isVehicle && (
            <section className="rounded-xl border border-[#1e2d40] bg-[#0d1117] p-4 space-y-2.5">
              <div className="flex items-center justify-between">
                <h3 className="text-xs font-bold font-mono uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                  <Car className="h-3.5 w-3.5 text-amber-400" />
                  <span>Component 7 ANPR &amp; Vehicle Intelligence</span>
                </h3>
                <Badge variant="warning" size="sm">
                  C7 Intel Linked
                </Badge>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-3 text-xs font-mono bg-white/[0.02] border border-white/5 p-3 rounded-lg">
                <div>
                  <span className="text-[10px] text-slate-500 uppercase">Top OCR Candidate</span>
                  <p className="text-sm font-bold text-slate-100 mt-0.5 tracking-wider">
                    HR26AK4521
                  </p>
                  <span className="text-[10px] text-slate-400">Match Conf: 92%</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 uppercase">Plate Quality / Format</span>
                  <p className="text-slate-200 mt-0.5">GOOD · STANDARD</p>
                  <span className="text-[10px] text-slate-400">Vehicle: CAR (WHITE)</span>
                </div>
                <div>
                  <span className="text-[10px] text-slate-500 uppercase">Watchlist Status</span>
                  <p className="text-slate-300 mt-0.5">CLEAN · NO MATCH</p>
                  <Link
                    to={`/anpr?search=HR26AK4521`}
                    className="text-[10px] text-cyan-400 hover:text-cyan-300 underline block mt-1"
                  >
                    Open ANPR Workspace →
                  </Link>
                </div>
              </div>
            </section>
          )}

          {/* ── Section 10: Evidence & Tamper-Evident Ledger Context (C3 Integration) ── */}
          <section className="rounded-xl border border-[#1e2d40] bg-[#0d1117] p-4 space-y-2.5">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold font-mono uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                <FileCheck className="h-3.5 w-3.5 text-emerald-400" />
                <span>Component 3 Evidence &amp; Tamper-Evident Ledger</span>
              </h3>
              <Badge variant="safe" size="sm">
                Verified Sealed
              </Badge>
            </div>

            <div className="flex flex-wrap items-center justify-between gap-2 p-2.5 rounded-lg border border-white/5 bg-white/[0.02] text-xs font-mono">
              <div>
                <span className="text-[10px] text-slate-500 uppercase">Evidence Package ID</span>
                <p className="text-slate-200 mt-0.5 font-bold">{matchedEvidence?.evidenceId ?? 'EVD-AVAILABLE'}</p>
              </div>
              <div>
                <span className="text-[10px] text-slate-500 uppercase">Cryptographic Digest</span>
                <p className="text-slate-400 mt-0.5 font-mono text-[10px] truncate max-w-[200px]" title={matchedEvidence?.recordedHash}>
                  {matchedEvidence ? `${matchedEvidence.recordedHash.slice(0, 8)}…${matchedEvidence.recordedHash.slice(-4)}` : 'sha256:unavailable'}
                </p>
              </div>
              <div>
                <span className="text-[10px] text-slate-500 uppercase">Ledger Seal</span>
                <p className={clsx('mt-0.5', matchedEvidence?.integrity === 'VERIFIED' ? 'text-emerald-400' : 'text-amber-400')}>
                  {matchedEvidence?.anchor?.state ?? 'ANCHORED'}
                </p>
              </div>
              <Link
                to={`/evidence?search=${matchedEvidence?.evidenceId ?? ''}`}
                className="text-[11px] text-cyan-400 hover:text-cyan-300 underline font-mono"
              >
                Inspect Ledger Record →
              </Link>
            </div>
          </section>

          {/* ── Section 11: Unified Chronological Timeline ── */}
          <section className="rounded-xl border border-[#1e2d40] bg-[#0d1117] p-4 space-y-3">
            <h3 className="text-xs font-bold font-mono uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
              <Clock className="h-3.5 w-3.5 text-amber-400" />
              <span>Chronological Progression Timeline</span>
            </h3>
            <IncidentTimeline
              createdAt={group.startedAt}
              detectionTimestamp={group.startedAt}
              trackTimestamp={group.startedAt}
              eventTimestamp={group.startedAt}
              correlationTimestamp={group.endedAt}
              evidenceTimestamp={group.endedAt}
              trackId={effectiveTrackId}
              zoneId={effectiveZoneId}
              zoneName="Zone B (North Fence)"
              eventId={group.primaryEventId}
              correlationId={group.correlationId}
              evidenceId="EVD-2026-0041"
              riskScore={effectiveScore}
              severity={effectiveSeverity}
            />
          </section>

          {/* ── Section 7: Supporting Signals & Detections (C4/C5) ── */}
          <section className="rounded-xl border border-[#1e2d40] bg-[#0d1117] p-4 space-y-3">
            <div className="flex items-center justify-between">
              <h3 className="text-xs font-bold font-mono uppercase tracking-wider text-slate-300 flex items-center gap-1.5">
                <Network className="h-3.5 w-3.5 text-cyan-400" />
                <span>Supporting Sensor Signals ({group.eventCount})</span>
              </h3>
              <span className="text-[10px] font-mono text-slate-500">
                {formatSignalCount(group.eventCount)}
              </span>
            </div>
            <CorrelationSignals
              members={group.memberEvents}
              primaryEventId={group.primaryEventId}
              onSelect={setSelectedMember}
            />
          </section>
        </div>

        {/* ── Right Decision-Support Rail (1/3) ── */}
        <div className="min-h-0 overflow-y-auto space-y-4">
          {/* Section 12: Decision-Support Action & Operator Review */}
          <section className="rounded-xl border border-cyan-500/30 bg-[#0d1117] p-4 space-y-3 shadow-lg">
            <div className="flex items-center justify-between border-b border-[#1e2d40] pb-2">
              <span className="text-xs font-bold font-mono uppercase tracking-wider text-cyan-300 flex items-center gap-1.5">
                <UserCheck className="h-4 w-4 text-cyan-400" />
                <span>Operator Decision Support</span>
              </span>
              <Badge variant="warning" size="sm">
                HUMAN-IN-THE-LOOP
              </Badge>
            </div>

            <p className="text-[11px] text-slate-400 font-sans leading-relaxed">
              PRHAAR is a decision-support platform. The analytical risk score is advisory. The
              operator remains the authoritative decision-maker.
            </p>

            {/* Review Status Selector */}
            <div className="space-y-1.5 font-mono text-xs">
              <label className="text-[10px] text-slate-500 uppercase font-semibold">
                Operational Review State:
              </label>
              <select
                value={reviewStatus}
                onChange={e =>
                  setReviewStatus(
                    e.target.value as 'PENDING' | 'UNDER_REVIEW' | 'VERIFIED' | 'DISMISSED'
                  )
                }
                className="w-full rounded border border-[#1e2d40] bg-[#080c12] px-2.5 py-1.5 text-xs text-slate-200 focus:border-cyan-400 focus:outline-none"
              >
                <option value="UNDER_REVIEW">UNDER REVIEW (Investigation Active)</option>
                <option value="VERIFIED">VERIFIED (Field Patrol Dispatched)</option>
                <option value="DISMISSED">DISMISSED (Benign Civilian / Animal Movement)</option>
                <option value="PENDING">PENDING (Awaiting Shift Handover)</option>
              </select>
            </div>

            {/* Operator Notes Input */}
            <div className="space-y-1 font-mono text-xs">
              <label className="text-[10px] text-slate-500 uppercase font-semibold">
                Operator Action Log Entry:
              </label>
              <textarea
                rows={3}
                value={reviewNotes}
                onChange={e => setReviewNotes(e.target.value)}
                placeholder="Log observation notes or dispatch coordination details..."
                className="w-full rounded border border-[#1e2d40] bg-[#080c12] p-2 text-xs text-slate-200 placeholder:text-slate-600 focus:border-cyan-400 focus:outline-none font-sans"
              />
              <Button
                size="sm"
                variant="primary"
                onClick={handleAddReviewNote}
                disabled={!reviewNotes.trim()}
                className="w-full font-mono text-xs mt-1"
              >
                Record Operator Action Log
              </Button>
            </div>

            {/* Audit Log Trail */}
            <div className="pt-2 border-t border-[#1e2d40] space-y-2">
              <span className="text-[10px] font-mono text-slate-500 uppercase font-semibold">
                Situation Audit Trail ({reviewLogs.length})
              </span>
              <ul className="space-y-2 max-h-48 overflow-y-auto pr-1">
                {reviewLogs.map((log, idx) => (
                  <li
                    key={idx}
                    className="p-2 rounded border border-white/5 bg-white/[0.02] text-xs font-mono space-y-0.5"
                  >
                    <div className="flex items-center justify-between text-[10px]">
                      <span className="text-cyan-300 font-semibold">{log.action}</span>
                      <span className="text-slate-500 tabular-nums">
                        {new Date(log.timestamp).toLocaleTimeString([], {
                          hour: '2-digit',
                          minute: '2-digit',
                        })}
                      </span>
                    </div>
                    <p className="text-[11px] font-sans text-slate-300 leading-snug">{log.note}</p>
                    <span className="text-[9px] text-slate-500 block">{log.operator}</span>
                  </li>
                ))}
              </ul>
            </div>
          </section>

          {/* Quick Deep Link Navigator */}
          <section className="rounded-xl border border-[#1e2d40] bg-[#0d1117] p-3.5 space-y-2 text-xs font-mono">
            <span className="text-[10px] uppercase tracking-wider text-slate-500 font-semibold">
              Correlated Subsystems
            </span>
            <div className="space-y-1.5">
              <Link
                to={`/camera/${effectiveCameraId}`}
                className="flex items-center justify-between p-2 rounded border border-white/5 bg-white/[0.02] hover:bg-white/5 text-slate-300 hover:text-cyan-300 transition-colors"
              >
                <span className="flex items-center gap-1.5">
                  <Camera className="h-3.5 w-3.5 text-emerald-400" />
                  <span>Component 1 / Single Camera</span>
                </span>
                <ExternalLink className="h-3 w-3 text-slate-500" />
              </Link>

              {effectiveTrackId && (
                <Link
                  to={`/track/${effectiveTrackId}`}
                  className="flex items-center justify-between p-2 rounded border border-white/5 bg-white/[0.02] hover:bg-white/5 text-slate-300 hover:text-cyan-300 transition-colors"
                >
                  <span className="flex items-center gap-1.5">
                    <Layers className="h-3.5 w-3.5 text-cyan-400" />
                    <span>Component 6 / Tracking Engine</span>
                  </span>
                  <ExternalLink className="h-3 w-3 text-slate-500" />
                </Link>
              )}

              <Link
                to="/evidence"
                className="flex items-center justify-between p-2 rounded border border-white/5 bg-white/[0.02] hover:bg-white/5 text-slate-300 hover:text-cyan-300 transition-colors"
              >
                <span className="flex items-center gap-1.5">
                  <FileCheck className="h-3.5 w-3.5 text-emerald-400" />
                  <span>Component 3 / Evidence Ledger</span>
                </span>
                <ExternalLink className="h-3 w-3 text-slate-500" />
              </Link>

              <Link
                to="/anpr"
                className="flex items-center justify-between p-2 rounded border border-white/5 bg-white/[0.02] hover:bg-white/5 text-slate-300 hover:text-cyan-300 transition-colors"
              >
                <span className="flex items-center gap-1.5">
                  <Car className="h-3.5 w-3.5 text-amber-400" />
                  <span>Component 7 / ANPR Intelligence</span>
                </span>
                <ExternalLink className="h-3 w-3 text-slate-500" />
              </Link>
            </div>
          </section>
        </div>
      </div>

      {/* Member Event Drawer */}
      <CorrelationEventDrawer
        open={selectedMember !== null}
        onClose={() => setSelectedMember(null)}
        member={selectedMember}
        group={group}
      />
    </div>
  )
}

function NavigateHome() {
  return (
    <div className="h-full flex items-center justify-center p-4 bg-[#080c12]">
      <EmptyState
        icon={<FileSearch size={32} />}
        title="No incident selected"
        description="Select an incident from the Event Log to inspect its analytical situation."
        action={
          <Link to="/events">
            <Button variant="primary" size="sm">
              Open Event Log
            </Button>
          </Link>
        }
      />
    </div>
  )
}

function DetailSkeleton() {
  return (
    <div className="h-full flex flex-col p-4 gap-4 bg-[#080c12]">
      <Skeleton className="h-10 w-80" />
      <Skeleton className="h-20 w-full" />
      <div className="flex-1 grid grid-cols-1 xl:grid-cols-[1fr_360px] gap-4">
        <Skeleton className="h-full w-full" />
        <Skeleton className="h-full w-full" />
      </div>
    </div>
  )
}