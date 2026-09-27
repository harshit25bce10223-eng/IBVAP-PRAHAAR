// ─────────────────────────────────────────────────────────────────────────────
// Component 1 — RiskFactorsPanel (Elevated Explainable Decision Support)
// ─────────────────────────────────────────────────────────────────────────────
// Structure:
//   1. FINAL SCORE & SEVERITY (e.g. CRITICAL · 93 / 100)
//   2. OBSERVATION RELIABILITY (separate from risk)
//   3. "WHY THIS WAS FLAGGED" (plain-language operational explanation)
//   4. CONTRIBUTING FACTORS (+ points)
//   5. MITIGATING FACTORS (- points)
//   6. CONTEXT & UNCERTAINTY (Camera Health, Viewpoint Shift, Night)
//   7. SOURCE REFERENCES (Track, Camera, Event, Evidence, Correlation)
// ─────────────────────────────────────────────────────────────────────────────

import { useMemo } from 'react'
import { Link } from 'react-router-dom'
import { clsx } from 'clsx'
import {
  AlertTriangle,
  ShieldAlert,
  ArrowUpRight,
  Info,
  Clock,
  Camera,
  Layers,
  FileCheck,
} from 'lucide-react'
import { SeverityBadge, ReliabilityBadge, RiskScoreGauge } from './SeverityBadge'
import type { RiskFactor, Severity } from '@/types'

export interface RiskFactorsPanelProps {
  score: number
  severity: Severity
  factors: RiskFactor[]
  reliability?: string | null
  cameraHealthState?: string | null
  viewpointShiftDetected?: boolean
  cameraId?: string | null
  trackId?: string | null
  eventId?: string | null
  evidenceId?: string | null
  correlationId?: string | null
  zoneName?: string | null
  className?: string
  compact?: boolean
}

import { generateWhyFlaggedExplanation } from './riskExplanation'



export function RiskFactorsPanel({
  score,
  severity,
  factors,
  reliability,
  cameraHealthState,
  viewpointShiftDetected,
  cameraId,
  trackId,
  eventId,
  evidenceId,
  correlationId,
  zoneName,
  className,
  compact = false,
}: RiskFactorsPanelProps) {
  const { contributing, mitigating, rawTotal } = useMemo(() => {
    const pos: RiskFactor[] = []
    const neg: RiskFactor[] = []
    let total = 0
    for (const f of factors) {
      total += f.points
      if (f.points < 0) neg.push(f)
      else pos.push(f)
    }
    return { contributing: pos, mitigating: neg, rawTotal: total }
  }, [factors])

  const explanation = useMemo(
    () => generateWhyFlaggedExplanation(factors, zoneName),
    [factors, zoneName]
  )

  const isDegradedCamera =
    cameraHealthState === 'DEGRADED' ||
    cameraHealthState === 'OFFLINE' ||
    Boolean(viewpointShiftDetected)

  return (
    <div
      className={clsx(
        'rounded-xl border border-[#1e2d40] bg-[#0d1117] p-4 flex flex-col gap-4 text-slate-200',
        className
      )}
      role="region"
      aria-label="Risk Assessment Panel"
    >
      {/* ── 1. Top Header: Score, Severity & Reliability ── */}
      <div className="flex items-start justify-between gap-3 border-b border-[#1e2d40]/60 pb-3">
        <div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] font-mono uppercase tracking-wider text-slate-400">
              Analytical Risk Score
            </span>
            <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-white/5 text-slate-400 border border-white/10">
              DECISION-SUPPORT
            </span>
          </div>
          <div className="flex items-baseline gap-2 mt-1">
            <span className="text-2xl font-bold font-mono text-slate-100 tabular-nums">
              {score}
            </span>
            <span className="text-xs font-mono text-slate-500">/ 100</span>
            <SeverityBadge severity={severity} size="md" />
          </div>
        </div>

        {/* Reliability indicator (Separated explicitly from Risk) */}
        <div className="flex flex-col items-end gap-1">
          <ReliabilityBadge reliability={reliability ?? 'HIGH'} size="sm" />
          <span className="text-[9px] font-mono text-slate-500">
            Sensor data quality
          </span>
        </div>
      </div>

      {/* ── 2. Risk Score Gauge with Threshold Markers ── */}
      <RiskScoreGauge score={score} severity={severity} />

      {/* ── 3. Why Flagged Section (Plain Language) ── */}
      <section className="rounded-lg border border-cyan-500/20 bg-cyan-500/5 p-3 space-y-1.5">
        <div className="flex items-center gap-1.5 text-cyan-300 font-mono text-xs font-semibold uppercase tracking-wider">
          <Info className="h-3.5 w-3.5 text-cyan-400" />
          <span>Why This Was Flagged</span>
        </div>
        <p className="text-xs text-slate-300 leading-relaxed font-sans">
          {explanation}
        </p>
      </section>

      {/* ── 4. Camera Health / Uncertainty Context (When Applicable) ── */}
      {isDegradedCamera && (
        <section className="rounded-lg border border-amber-500/30 bg-amber-500/10 p-2.5 flex items-start gap-2">
          <AlertTriangle className="h-4 w-4 text-amber-400 flex-shrink-0 mt-0.5" />
          <div className="text-xs">
            <div className="font-semibold text-amber-300 font-mono">
              Uncertainty Context: Sensor Degraded
            </div>
            <p className="text-[11px] text-amber-200/80 mt-0.5">
              {viewpointShiftDetected
                ? 'Camera viewpoint shift detected. Virtual boundary alignment may be offset.'
                : `Camera state is reported as ${cameraHealthState}. Treat geometric boundaries with appropriate caution.`}
            </p>
          </div>
        </section>
      )}

      {/* ── 5. Contributing Factors List ── */}
      <section className="space-y-2">
        <div className="flex items-center justify-between text-xs font-mono">
          <span className="text-slate-400 uppercase tracking-wider text-[11px] font-semibold">
            Contributing Factors ({contributing.length})
          </span>
          <span className="text-slate-500 text-[10px]">Points Added</span>
        </div>

        {contributing.length === 0 ? (
          <p className="text-xs text-slate-500 italic p-2 border border-dashed border-slate-800 rounded">
            No active contributing factors.
          </p>
        ) : (
          <ul className="space-y-1.5">
            {contributing.map((factor, i) => (
              <li
                key={`${factor.code}-${i}`}
                className="flex items-start justify-between gap-3 rounded-lg border border-white/[0.06] bg-white/[0.02] p-2 hover:bg-white/[0.04] transition-colors"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    <span className="h-1.5 w-1.5 rounded-full bg-red-400 flex-shrink-0" />
                    <span className="text-xs font-medium text-slate-200 truncate">
                      {factor.label || factor.code}
                    </span>
                  </div>
                  <p className="text-[11px] text-slate-400 mt-0.5 leading-snug">
                    {factor.evidence || 'Evidence detail unavailable.'}
                  </p>
                  <span className="font-mono text-[9px] text-slate-600">
                    {factor.code}
                  </span>
                </div>
                <span className="font-mono text-xs font-bold text-red-400 tabular-nums">
                  +{factor.points}
                </span>
              </li>
            ))}
          </ul>
        )}
      </section>

      {/* ── 6. Mitigating Factors List (If Any) ── */}
      {mitigating.length > 0 && (
        <section className="space-y-2">
          <div className="flex items-center justify-between text-xs font-mono">
            <span className="text-emerald-400 uppercase tracking-wider text-[11px] font-semibold">
              Mitigating Factors ({mitigating.length})
            </span>
            <span className="text-emerald-500 text-[10px]">Uncertainty Deduction</span>
          </div>
          <ul className="space-y-1.5">
            {mitigating.map((factor, i) => (
              <li
                key={`${factor.code}-${i}`}
                className="flex items-start justify-between gap-3 rounded-lg border border-emerald-500/20 bg-emerald-500/5 p-2"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5">
                    <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 flex-shrink-0" />
                    <span className="text-xs font-medium text-emerald-200 truncate">
                      {factor.label || factor.code}
                    </span>
                  </div>
                  <p className="text-[11px] text-emerald-300/80 mt-0.5 leading-snug">
                    {factor.evidence || 'Sensor reliability penalty.'}
                  </p>
                  <span className="font-mono text-[9px] text-emerald-500/60">
                    {factor.code}
                  </span>
                </div>
                <span className="font-mono text-xs font-bold text-emerald-400 tabular-nums">
                  {factor.points}
                </span>
              </li>
            ))}
          </ul>
        </section>
      )}

      {/* ── 7. Raw Score Summary ── */}
      <div className="pt-2 border-t border-[#1e2d40]/60 flex items-center justify-between text-xs font-mono text-slate-400">
        <span>Aggregate Raw Score</span>
        <span className="text-slate-200 font-semibold tabular-nums">
          {rawTotal} {rawTotal !== score ? `(clamped to ${score})` : ''}
        </span>
      </div>

      {/* ── 8. Source References & Deep Links ── */}
      {!compact && (
        <section className="pt-2 border-t border-[#1e2d40]/60 space-y-1.5">
          <span className="text-[10px] font-mono uppercase tracking-wider text-slate-500 font-semibold">
            Intelligence Traceability
          </span>
          <div className="grid grid-cols-2 gap-1.5 text-xs font-mono">
            {trackId && (
              <Link
                to={`/track/${trackId}`}
                className="flex items-center justify-between p-1.5 rounded border border-white/5 bg-white/[0.02] hover:bg-white/5 text-slate-300 hover:text-cyan-300 transition-colors"
                title="View C6 Track Details"
              >
                <span className="flex items-center gap-1 truncate">
                  <Layers className="h-3 w-3 text-cyan-400 flex-shrink-0" />
                  <span className="truncate">{trackId}</span>
                </span>
                <ArrowUpRight className="h-3 w-3 flex-shrink-0 text-slate-500" />
              </Link>
            )}

            {cameraId && (
              <Link
                to={`/camera/${cameraId}`}
                className="flex items-center justify-between p-1.5 rounded border border-white/5 bg-white/[0.02] hover:bg-white/5 text-slate-300 hover:text-cyan-300 transition-colors"
                title="View Camera Feed"
              >
                <span className="flex items-center gap-1 truncate">
                  <Camera className="h-3 w-3 text-emerald-400 flex-shrink-0" />
                  <span className="truncate">{cameraId}</span>
                </span>
                <ArrowUpRight className="h-3 w-3 flex-shrink-0 text-slate-500" />
              </Link>
            )}

            {eventId && (
              <Link
                to={`/events?search=${eventId}`}
                className="flex items-center justify-between p-1.5 rounded border border-white/5 bg-white/[0.02] hover:bg-white/5 text-slate-300 hover:text-cyan-300 transition-colors"
                title="View Event Log"
              >
                <span className="flex items-center gap-1 truncate">
                  <Clock className="h-3 w-3 text-amber-400 flex-shrink-0" />
                  <span className="truncate">{eventId}</span>
                </span>
                <ArrowUpRight className="h-3 w-3 flex-shrink-0 text-slate-500" />
              </Link>
            )}

            {evidenceId && (
              <Link
                to={`/evidence?search=${evidenceId}`}
                className="flex items-center justify-between p-1.5 rounded border border-white/5 bg-white/[0.02] hover:bg-white/5 text-slate-300 hover:text-cyan-300 transition-colors"
                title="View Tamper-Evident Ledger"
              >
                <span className="flex items-center gap-1 truncate">
                  <FileCheck className="h-3 w-3 text-emerald-400 flex-shrink-0" />
                  <span className="truncate">{evidenceId}</span>
                </span>
                <ArrowUpRight className="h-3 w-3 flex-shrink-0 text-slate-500" />
              </Link>
            )}

            {correlationId && (
              <Link
                to={`/incident/${correlationId}`}
                className="col-span-2 flex items-center justify-between p-1.5 rounded border border-white/5 bg-white/[0.02] hover:bg-white/5 text-slate-300 hover:text-cyan-300 transition-colors"
                title="View Correlated Situation"
              >
                <span className="flex items-center gap-1 truncate">
                  <ShieldAlert className="h-3 w-3 text-red-400 flex-shrink-0" />
                  <span className="truncate">Correlated Group: {correlationId}</span>
                </span>
                <ArrowUpRight className="h-3 w-3 flex-shrink-0 text-slate-500" />
              </Link>
            )}
          </div>
        </section>
      )}
    </div>
  )
}