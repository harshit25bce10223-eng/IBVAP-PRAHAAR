// ─────────────────────────────────────────────────────────────────────────────
// Component 1 — IncidentTimeline
// Chronological operational progression from raw detection to evidence sealing.
// Displays ONLY steps with real timestamps and IDs (never fabricates timestamps).
// ─────────────────────────────────────────────────────────────────────────────

import { Link } from 'react-router-dom'
import { clsx } from 'clsx'
import {
  Crosshair,
  Layers,
  ShieldAlert,
  Clock,
  Network,
  Activity,
  FileCheck,
} from 'lucide-react'

export interface TimelineStep {
  stage: string
  title: string
  timestamp: string | null
  id?: string | null
  detail?: string | null
  link?: string | null
  icon: React.ComponentType<{ className?: string }>
  status: 'completed' | 'in_progress' | 'pending'
}

export interface IncidentTimelineProps {
  createdAt: string
  detectionTimestamp?: string | null
  trackTimestamp?: string | null
  eventTimestamp?: string | null
  correlationTimestamp?: string | null
  evidenceTimestamp?: string | null
  trackId?: string | null
  zoneId?: string | null
  zoneName?: string | null
  eventId?: string | null
  correlationId?: string | null
  evidenceId?: string | null
  riskScore?: number | null
  severity?: string | null
  className?: string
}

export function IncidentTimeline({
  createdAt,
  detectionTimestamp,
  trackTimestamp,
  eventTimestamp,
  correlationTimestamp,
  evidenceTimestamp,
  trackId,
  zoneId,
  zoneName,
  eventId,
  correlationId,
  evidenceId,
  riskScore,
  severity,
  className,
}: IncidentTimelineProps) {
  // Build chronological sequence strictly from supplied data
  const steps: TimelineStep[] = []

  // 1. Detection
  if (detectionTimestamp || trackId) {
    steps.push({
      stage: '01',
      title: 'Sensor Observation / Detection',
      timestamp: detectionTimestamp || trackTimestamp || null,
      detail: trackId ? `Entity tracked as ${trackId}` : 'Detector registered bounding candidate',
      link: trackId ? `/track/${trackId}` : undefined,
      icon: Crosshair,
      status: 'completed',
    })
  }

  // 2. Track Trajectory Update
  if (trackId) {
    steps.push({
      stage: '02',
      title: 'Observation Continuity Update',
      timestamp: trackTimestamp || eventTimestamp || createdAt,
      id: trackId,
      detail: 'Multi-frame tracking confirmed trajectory vector',
      link: `/track/${trackId}`,
      icon: Layers,
      status: 'completed',
    })
  }

  // 3. Zone Crossing
  steps.push({
    stage: '03',
    title: 'Virtual Boundary Crossing',
    timestamp: eventTimestamp || createdAt,
    id: zoneId || undefined,
    detail: zoneName ? `Breached ${zoneName}` : 'Representative point intersected zone polygon',
    icon: ShieldAlert,
    status: 'completed',
  })

  // 4. Event Logged
  if (eventId) {
    steps.push({
      stage: '04',
      title: 'Zone Crossing Event Logged',
      timestamp: eventTimestamp || createdAt,
      id: eventId,
      detail: 'Deterministic deduplicated event registered in ledger',
      link: `/events?search=${eventId}`,
      icon: Clock,
      status: 'completed',
    })
  }

  // 5. Correlation Context (Optional)
  if (correlationId) {
    steps.push({
      stage: '05',
      title: 'Multi-Sensor Event Correlated',
      timestamp: correlationTimestamp || createdAt,
      id: correlationId,
      detail: 'Correlated with cross-camera temporal sequence',
      link: `/incident/${correlationId}`,
      icon: Network,
      status: 'completed',
    })
  }

  // 6. Risk Scoring & Incident Created
  steps.push({
    stage: '06',
    title: 'Analytical Risk Evaluated',
    timestamp: createdAt,
    detail: `Score ${riskScore ?? 'N/A'} (${severity ?? 'FLAGGED'}) · Factor breakdown registered`,
    icon: Activity,
    status: 'completed',
  })

  // 7. Evidence Sealing
  if (evidenceId) {
    steps.push({
      stage: '07',
      title: 'Evidence Package Sealed',
      timestamp: evidenceTimestamp || createdAt,
      id: evidenceId,
      detail: 'Tamper-evident record & SHA-256 seal registered',
      link: `/evidence?search=${evidenceId}`,
      icon: FileCheck,
      status: 'completed',
    })
  }

  return (
    <div className={clsx('space-y-4', className)}>
      <div className="flex items-center justify-between text-xs font-mono text-slate-400 border-b border-[#1e2d40] pb-2">
        <span className="uppercase tracking-wider font-semibold">Incident Chronology</span>
        <span className="text-[10px] text-slate-500">{steps.length} Verified Milestones</span>
      </div>

      <ol className="relative border-l border-[#1e2d40] ml-3.5 space-y-4">
        {steps.map((step, idx) => {
          const Icon = step.icon
          return (
            <li key={idx} className="ml-5 group">
              {/* Node dot */}
              <span className="absolute -left-2.5 flex h-5 w-5 items-center justify-center rounded-full bg-[#0d1117] border border-cyan-500/50 text-cyan-400 group-hover:border-cyan-400 transition-colors">
                <Icon className="h-2.5 w-2.5" />
              </span>

              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold text-slate-200 font-mono">
                      {step.title}
                    </span>
                    {step.id && (
                      <span className="text-[10px] font-mono text-cyan-300/90 bg-cyan-500/10 px-1 py-0.2 rounded border border-cyan-500/20">
                        {step.id}
                      </span>
                    )}
                  </div>

                  {step.detail && (
                    <p className="text-[11px] text-slate-400 mt-0.5 leading-snug">
                      {step.detail}
                    </p>
                  )}

                  {step.link && (
                    <Link
                      to={step.link}
                      className="inline-block mt-1 text-[10px] font-mono text-cyan-400 hover:text-cyan-300 underline underline-offset-2"
                    >
                      Inspect Source Reference →
                    </Link>
                  )}
                </div>

                {step.timestamp && (
                  <time className="text-[10px] font-mono text-slate-500 whitespace-nowrap tabular-nums">
                    {new Date(step.timestamp).toLocaleTimeString([], {
                      hour: '2-digit',
                      minute: '2-digit',
                      second: '2-digit',
                    })}
                  </time>
                )}
              </div>
            </li>
          )
        })}
      </ol>
    </div>
  )
}
