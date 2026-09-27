// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 2 — Elevated Camera Health Details Inspector
// 12-Section Comprehensive Operational Surveillance Decision Support View
// ─────────────────────────────────────────────────────────────────────────────

import { useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import type { CameraHealth } from '@/types/cameraHealth'
import { CameraHealthBadge } from './CameraHealthBadge'
import { CameraHealthMetric } from './CameraHealthMetric'
import { CameraHealthTrend } from './CameraHealthTrend'
import { CameraHealthIssueList } from './CameraHealthIssueList'
import { CoverageImpact } from './CoverageImpact'
import { ViewpointStability } from './ViewpointStability'
import { HealthTimeline } from './HealthTimeline'
import { STREAM_LABEL } from './healthTone'
import { formatAge, formatClock, formatMetricValue } from './healthFormat'
import {
  Video,
  Waypoints,
  Crosshair,
  Car,
  Cpu,
  ShieldAlert,
  PauseCircle,
  EyeOff,
} from 'lucide-react'

export interface CameraHealthDetailsProps {
  health: CameraHealth
  onOpenDiagnostics?: () => void
}

export function CameraHealthDetails({ health, onOpenDiagnostics }: CameraHealthDetailsProps) {
  const [nowMs] = useState(() => Date.now())
  const region = health.regionProfile

  // Baseline comparisons
  const sharpnessMetric = health.image.metrics.find(m => m.metric === 'sharpness')
  const brightnessMetric = health.image.metrics.find(m => m.metric === 'brightness')

  const sharpnessVal = typeof sharpnessMetric?.value === 'number' ? sharpnessMetric.value : null
  const sharpnessBaseline = 0.85
  const sharpnessDiff = sharpnessVal !== null ? Math.round((sharpnessVal - sharpnessBaseline) * 100) : null

  const brightnessVal = typeof brightnessMetric?.value === 'number' ? brightnessMetric.value : null
  const brightnessBaseline = 0.70
  const brightnessDiff = brightnessVal !== null ? Math.round((brightnessVal - brightnessBaseline) * 100) : null

  // Operational State Explanation ("Why" was it flagged?)
  const operationalExplanation = useMemo(() => {
    if (health.status === 'ONLINE') {
      if (health.operationalImpact?.coverage === 'COMPROMISED') {
        return 'Camera hardware is ONLINE and streaming, but boundary sector coverage is COMPROMISED due to external visibility factors (such as heavy fog or optical occlusion).'
      }
      return 'All operational dimensions are within nominal thresholds. Sensor stream and optics are fully aligned.'
    }
    if (health.status === 'OFFLINE') {
      return `Camera telemetry connection dropped. ${health.statusReason ?? 'No heartbeat or video frames received.'}`
    }
    if (health.status === 'FROZEN') {
      return `Camera video feed is frozen. Temporal variance detection identified identical frames persisting beyond threshold limit.`
    }
    if (health.status === 'STALE') {
      return `Video telemetry is stale. Frame delivery latency exceeds configured real-time observation thresholds.`
    }
    if (health.status === 'DEGRADED') {
      const parts: string[] = []
      if (health.viewpoint.shiftDetected) parts.push('reference viewpoint shift')
      if (health.image.status === 'DEGRADED') parts.push('image sharpness/contrast degradation')
      if (health.network.status === 'DEGRADED') parts.push('network packet loss / jitter')
      return `Sensor performance is degraded due to ${parts.join(' and ') || 'multiple telemetry threshold anomalies'}.`
    }
    if (health.status === 'MAINTENANCE') {
      return 'Sensor is in scheduled maintenance mode. Operational parameters temporarily diverted for calibration.'
    }
    return 'Health telemetry is currently insufficient to establish definitive operational state.'
  }, [health])

  return (
    <div className="space-y-4 text-[12px] pb-6">
      {/* ── 1. CURRENT STATE HEADER ────────────────────────────────────────── */}
      <div className="rounded-xl border border-white/[0.08] bg-[#0A0D14] p-3.5 space-y-2">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="font-mono text-base font-bold text-slate-100">{health.cameraId}</span>
            <CameraHealthBadge status={health.status} cameraId={health.cameraId} />
          </div>
          <span className="font-mono text-[10px] text-slate-500">
            {health.lastUpdated ? `Telemetry ${formatAge(health.lastUpdated, nowMs)}` : 'No telemetry'}
          </span>
        </div>

        {health.statusReason && (
          <p className="text-[11px] font-mono text-amber-400/90 bg-amber-950/20 border border-amber-500/20 rounded p-2">
            {health.statusReason}
          </p>
        )}

        <div className="grid grid-cols-2 gap-2 text-[10px] font-mono pt-1 text-slate-400 border-t border-white/[0.04]">
          <div>
            <span className="text-slate-500">Since: </span>
            <span className="text-slate-300">
              {health.lastUpdated ? formatClock(health.lastUpdated) : '—'}
            </span>
          </div>
          <div>
            <span className="text-slate-500">Last Verified Healthy: </span>
            <span className="text-slate-300">
              {health.lastKnown?.at ? formatClock(health.lastKnown.at) : 'Active baseline'}
            </span>
          </div>
        </div>
      </div>

      {/* ── ACTION DEEP LINKS ──────────────────────────────────────────────── */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <Link
          to={`/camera/${health.cameraId}`}
          className="flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-md border border-white/10 bg-[#0F141C] text-[11px] text-slate-300 hover:text-cyan-300 hover:border-cyan-500/40 transition-colors"
        >
          <Video size={12} />
          <span>View Feed</span>
        </Link>
        <Link
          to="/incident-intel"
          className="flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-md border border-white/10 bg-[#0F141C] text-[11px] text-slate-300 hover:text-cyan-300 hover:border-cyan-500/40 transition-colors"
        >
          <Waypoints size={12} />
          <span>Incidents</span>
        </Link>
        <Link
          to="/events"
          className="flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-md border border-white/10 bg-[#0F141C] text-[11px] text-slate-300 hover:text-cyan-300 hover:border-cyan-500/40 transition-colors"
        >
          <Crosshair size={12} />
          <span>Tracks</span>
        </Link>
        <Link
          to={`/camera/${health.cameraId}/vehicles`}
          className="flex items-center justify-center gap-1.5 py-1.5 px-2 rounded-md border border-white/10 bg-[#0F141C] text-[11px] text-slate-300 hover:text-cyan-300 hover:border-cyan-500/40 transition-colors"
        >
          <Car size={12} />
          <span>Vehicles</span>
        </Link>
      </div>

      {/* ── 2. STATE EXPLANATION ("WHY") ───────────────────────────────────── */}
      <DetailSection title="Operational State Explanation">
        <div className="rounded-lg border border-white/[0.06] bg-[#0A0D14] p-3 text-[11px] text-slate-300 leading-relaxed">
          {operationalExplanation}
        </div>
      </DetailSection>

      {/* ── 8. COVERAGE IMPACT (CAMERA HEALTH ≠ BORDER COVERAGE) ───────────── */}
      <DetailSection title="Border Coverage Impact">
        <div className="rounded-lg border border-white/[0.06] bg-[#0F141C] p-3 space-y-2">
          <CoverageImpact impact={health.operationalImpact} />
          {health.status === 'ONLINE' && health.operationalImpact?.coverage === 'COMPROMISED' && (
            <div className="flex items-center gap-2 p-2 rounded bg-rose-500/10 border border-rose-500/20 text-rose-300 text-[11px]">
              <EyeOff size={14} className="shrink-0 text-rose-400" />
              <span>
                <strong>Coverage Compromised:</strong> Camera is streaming normally, but sector
                border line cannot be reliably defended due to atmospheric conditions.
              </span>
            </div>
          )}
        </div>
      </DetailSection>

      {/* ── 3. LIVE / RECENT QUALITY METRICS ─────────────────────────────────── */}
      <DetailSection title="Stream & Live Telemetry Quality">
        <div className="grid grid-cols-2 gap-2">
          <div className="rounded-lg border border-white/[0.06] bg-[#0F141C] p-2.5">
            <span className="text-[10px] text-slate-500 font-mono uppercase">Stream State</span>
            <div className="font-mono text-xs font-semibold text-slate-200 mt-0.5">
              {STREAM_LABEL[health.stream.state]}
            </div>
          </div>
          <div className="rounded-lg border border-white/[0.06] bg-[#0F141C] p-2.5">
            <span className="text-[10px] text-slate-500 font-mono uppercase">Delivered FPS</span>
            <div className="font-mono text-xs font-semibold text-slate-200 mt-0.5">
              {health.stream.fps !== null ? `${health.stream.fps} fps` : 'N/A'}
              <span className="text-[10px] text-slate-500 font-normal">
                {' '}
                / {health.stream.expectedFps ?? 25} exp
              </span>
            </div>
          </div>
          <div className="rounded-lg border border-white/[0.06] bg-[#0F141C] p-2.5">
            <span className="text-[10px] text-slate-500 font-mono uppercase">Frame Drop Rate</span>
            <div className="font-mono text-xs font-semibold text-slate-200 mt-0.5">
              {formatMetricValue(health.stream.frameDropPercent, '%')}
            </div>
          </div>
          <div className="rounded-lg border border-white/[0.06] bg-[#0F141C] p-2.5">
            <span className="text-[10px] text-slate-500 font-mono uppercase">Network Latency</span>
            <div className="font-mono text-xs font-semibold text-slate-200 mt-0.5">
              {formatMetricValue(health.network.latencyMs, 'ms')}
            </div>
          </div>
        </div>

        {health.image.metrics.length > 0 && (
          <div className="mt-2 rounded-lg border border-white/[0.06] bg-[#0F141C] p-2.5">
            <span className="text-[10px] text-slate-500 font-mono uppercase block mb-1">
              Optical Quality Factors
            </span>
            <dl className="divide-y divide-white/[0.04]">
              {health.image.metrics.map(m => (
                <CameraHealthMetric key={m.metric} metric={m} />
              ))}
            </dl>
          </div>
        )}
      </DetailSection>

      {/* ── 7. BASELINE COMPARISON ─────────────────────────────────────────── */}
      <DetailSection title="Baseline Comparison & Trend">
        <div className="rounded-lg border border-white/[0.06] bg-[#0F141C] p-3 space-y-2.5">
          <div className="flex items-center justify-between text-[11px] pb-2 border-b border-white/[0.04]">
            <span className="text-slate-400">Sharpness vs Expected Baseline</span>
            <div className="flex items-center gap-2 font-mono">
              <span className="text-slate-200">{sharpnessVal ?? 'N/A'}</span>
              <span className="text-slate-500">/ 0.85 base</span>
              {sharpnessDiff !== null && (
                <span
                  className={`text-[10px] font-semibold ${
                    sharpnessDiff < -15 ? 'text-prhaar-degraded' : 'text-prhaar-good'
                  }`}
                >
                  {sharpnessDiff > 0 ? `+${sharpnessDiff}%` : `${sharpnessDiff}%`}
                </span>
              )}
            </div>
          </div>

          <div className="flex items-center justify-between text-[11px]">
            <span className="text-slate-400">Illumination (Brightness)</span>
            <div className="flex items-center gap-2 font-mono">
              <span className="text-slate-200">{brightnessVal ?? 'N/A'}</span>
              <span className="text-slate-500">/ 0.70 base</span>
              {brightnessDiff !== null && (
                <span
                  className={`text-[10px] font-semibold ${
                    brightnessDiff < -20 ? 'text-prhaar-degraded' : 'text-slate-400'
                  }`}
                >
                  {brightnessDiff > 0 ? `+${brightnessDiff}%` : `${brightnessDiff}%`}
                </span>
              )}
            </div>
          </div>

          {health.trends.length > 0 && (
            <div className="pt-2 border-t border-white/[0.04] space-y-2">
              {health.trends.map(t => (
                <CameraHealthTrend key={t.metric} trend={t} />
              ))}
            </div>
          )}
        </div>
      </DetailSection>

      {/* ── 5. VIEWPOINT & 6. FREEZE STATUS ────────────────────────────────── */}
      <DetailSection title="Viewpoint Stability & Freeze Analysis">
        <div className="space-y-2">
          <div className="rounded-lg border border-white/[0.06] bg-[#0F141C] p-3">
            <ViewpointStability viewpoint={health.viewpoint} nowMs={nowMs} />
          </div>

          <div className="rounded-lg border border-white/[0.06] bg-[#0F141C] p-3 flex items-center justify-between text-[11px]">
            <div className="flex items-center gap-2">
              <PauseCircle
                size={14}
                className={health.stream.state === 'FROZEN' ? 'text-cyan-400' : 'text-slate-500'}
              />
              <span className="text-slate-300 font-medium">Temporal Freeze Detector</span>
            </div>
            <span className="font-mono text-slate-400">
              {health.stream.state === 'FROZEN'
                ? 'FROZEN (120s duplicate persistence)'
                : 'Nominal (dynamic frames)'}
            </span>
          </div>
        </div>
      </DetailSection>

      {/* ── 4. HEALTH TIMELINE ─────────────────────────────────────────────── */}
      <DetailSection title="Health State Transitions">
        <HealthTimeline health={health} />
      </DetailSection>

      {/* ── 9. & 10. DOWNSTREAM IMPACT ─────────────────────────────────────── */}
      <DetailSection title="Downstream Module Impact">
        <div className="rounded-lg border border-white/[0.06] bg-[#0F141C] p-3 space-y-2 text-[11px]">
          <div className="flex items-start gap-2">
            <ShieldAlert size={14} className="shrink-0 text-amber-400 mt-0.5" />
            <div>
              <span className="font-semibold text-slate-200">Incident & Detection Reliability:</span>
              <p className="text-slate-400 mt-0.5">
                {health.status === 'ONLINE'
                  ? 'Nominal reliability. Analytical detections and tracking state are uninhibited.'
                  : `Observations on this camera carry ${health.status} uncertainty penalty in C1 Risk Engine.`}
              </p>
            </div>
          </div>
        </div>
      </DetailSection>

      {/* ── 11. CONFIGURATION & PROFILE ───────────────────────────────────── */}
      <DetailSection title="Deployment Profile & Configuration">
        <div className="rounded-lg border border-white/[0.06] bg-[#0F141C] p-3 space-y-1.5">
          <KeyRow label="Sector Region" value={region.region ?? 'INDO-NEPAL'} />
          <KeyRow label="Terrain Class" value={region.terrain ?? 'FOOTHILL / PLAINS'} />
          <KeyRow label="Location" value={region.location ?? 'Perimeter observation post'} />
          <KeyRow
            label="Offline Timeout"
            value="60s (automatic heartbeat threshold)"
          />
          <KeyRow label="Stale Timeout" value="30s (real-time video threshold)" />
        </div>
      </DetailSection>

      {/* ── 12. ISSUE HISTORY ──────────────────────────────────────────────── */}
      <DetailSection title="Issue History">
        <CameraHealthIssueList issues={health.issues} />
      </DetailSection>

      {/* ── TECHNICAL DIAGNOSTICS ACTION ───────────────────────────────────── */}
      {onOpenDiagnostics && (
        <div className="pt-2">
          <button
            type="button"
            onClick={onOpenDiagnostics}
            className="w-full flex items-center justify-center gap-2 py-2 rounded-lg border border-cyan-500/30 bg-cyan-950/20 text-cyan-400 font-mono text-xs hover:bg-cyan-950/40 hover:border-cyan-400/50 transition-colors"
          >
            <Cpu size={14} />
            <span>Open Technical Diagnostics & CV Parameters →</span>
          </button>
        </div>
      )}
    </div>
  )
}

function DetailSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section aria-label={title} className="border-t border-white/[0.06] pt-3 first:border-0 first:pt-0">
      <h4 className="mb-1 text-[11px] font-semibold uppercase tracking-wider text-slate-400">
        {title}
      </h4>
      {children}
    </section>
  )
}

function KeyRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-2 py-0.5">
      <dt className="text-[11px] text-slate-500">{label}</dt>
      <dd className="text-right font-mono text-[11px] text-slate-200 tabular-nums">{value}</dd>
    </div>
  )
}
