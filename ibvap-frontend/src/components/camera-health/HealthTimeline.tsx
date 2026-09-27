// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 2 — Chronological Health Transition Timeline
// ─────────────────────────────────────────────────────────────────────────────

import { useMemo } from 'react'
import { ArrowRight, CheckCircle2, AlertTriangle, AlertOctagon, PauseCircle, Clock, Wrench } from 'lucide-react'
import type { CameraHealth, CameraHealthStatus } from '@/types/cameraHealth'
import { formatClock, formatAge } from './healthFormat'
import { toneForStatus, TONE } from './healthTone'

export interface HealthTransition {
  timestamp: string | null
  fromStatus: CameraHealthStatus | null
  toStatus: CameraHealthStatus
  reason: string
  durationLabel?: string | null
}

export function HealthTimeline({ health }: { health: CameraHealth }) {
  const transitions: HealthTransition[] = useMemo(() => {
    const list: HealthTransition[] = []

    // 1. Current state transition
    list.push({
      timestamp: health.lastUpdated,
      fromStatus: health.lastKnown?.status ?? (health.status === 'ONLINE' ? null : 'ONLINE'),
      toStatus: health.status,
      reason: health.statusReason ?? 'Telemetry updated nominal state.',
      durationLabel: health.issues[0]?.durationLabel ?? null,
    })

    // 2. Historical issue transitions if present
    for (const issue of health.issues) {
      if (issue.firstSeen && issue.firstSeen !== health.lastUpdated) {
        list.push({
          timestamp: issue.firstSeen,
          fromStatus: 'ONLINE',
          toStatus: issue.impact === 'HIGH' ? (health.status === 'OFFLINE' ? 'OFFLINE' : 'DEGRADED') : 'DEGRADED',
          reason: `${issue.title}: ${issue.impactNote ?? 'State anomaly observed.'}`,
          durationLabel: issue.durationLabel,
        })
      }
    }

    // 3. Last known baseline transition if offline or stale
    if (health.lastKnown?.at) {
      list.push({
        timestamp: health.lastKnown.at,
        fromStatus: null,
        toStatus: health.lastKnown.status,
        reason: 'Last verified operational baseline prior to telemetry loss.',
      })
    }

    return list
  }, [health])

  if (transitions.length === 0) {
    return <p className="text-[11px] text-slate-500">No transition history recorded for this camera.</p>
  }

  return (
    <div className="relative pl-4 space-y-3 before:absolute before:left-1.5 before:top-2 before:bottom-2 before:w-[1px] before:bg-white/10">
      {transitions.map((t, idx) => {
        const tone = TONE[toneForStatus(t.toStatus)]
        return (
          <div key={idx} className="relative flex items-start gap-2.5 text-[11px]">
            {/* Timeline node */}
            <div
              className={`absolute -left-4 top-1 w-3 h-3 rounded-full border border-[#080B10] ${tone.dot} flex items-center justify-center`}
            />

            <div className="flex-1 bg-[#0F141C] border border-white/[0.06] rounded-md p-2.5">
              <div className="flex items-center justify-between gap-2 mb-1">
                <div className="flex items-center gap-1.5">
                  {t.fromStatus && (
                    <>
                      <span className="font-mono text-[10px] text-slate-400">{t.fromStatus}</span>
                      <ArrowRight size={10} className="text-slate-600" />
                    </>
                  )}
                  <span className={`font-mono text-[10px] font-semibold uppercase ${tone.text}`}>
                    {t.toStatus}
                  </span>
                </div>
                <div className="flex items-center gap-1 font-mono text-[10px] text-slate-500">
                  <Clock size={10} />
                  <span>{formatClock(t.timestamp)}</span>
                  {t.durationLabel && (
                    <span className="text-slate-600">({t.durationLabel})</span>
                  )}
                </div>
              </div>
              <p className="text-slate-300 text-[11px] leading-relaxed">{t.reason}</p>
            </div>
          </div>
        )
      })}
    </div>
  )
}
