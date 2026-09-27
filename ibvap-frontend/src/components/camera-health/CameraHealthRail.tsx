import { useState } from 'react'
import type { CameraHealth } from '@/types/cameraHealth'
import { CameraHealthBadge } from './CameraHealthBadge'
import { CameraHealthMetric } from './CameraHealthMetric'
import { CameraHealthTrend } from './CameraHealthTrend'
import { CoverageImpact } from './CoverageImpact'
import { ViewpointStability } from './ViewpointStability'
import { STREAM_LABEL, TONE, toneForNetwork, toneForStream } from './healthTone'
import { formatAge, formatMetricValue } from './healthFormat'

/**
 * DETAILED presentation for Single Camera Detail (right rail).
 * Information order: id → status → impact → key dimensions → viewpoint →
 * trend preview → issues → details action. Progressive disclosure: the
 * full trend set, issue history and freshness live in the details drawer.
 */
export function CameraHealthRail({ health, onOpenDetails }: {
  health: CameraHealth
  onOpenDetails: () => void
}) {
  const [nowMs] = useState(() => Date.now())
  const streamTone = TONE[toneForStream(health.stream.state)]
  const netTone = TONE[toneForNetwork(health.network.status)]

  return (
    <section aria-label={`Camera health for ${health.cameraId}`} className="rounded-xl border border-[#1e2d40] bg-[#0d1117]">
      <div className="flex items-center justify-between px-4 pt-3">
        <h3 className="text-sm font-semibold text-slate-200">Camera Health</h3>
        <CameraHealthBadge status={health.status} cameraId={health.cameraId} />
      </div>
      {health.statusReason && (
        <p className="px-4 pt-1 text-[11px] text-slate-500">{health.statusReason}</p>
      )}

      <div className="divide-y divide-white/[0.05] px-4 pb-2">
        <div className="py-1">
          <CoverageImpact impact={health.operationalImpact} />
        </div>

        <dl>
          <div className="flex items-baseline justify-between gap-2 py-1">
            <dt className="text-[11px] text-slate-500">Stream</dt>
            <dd className={`font-mono text-[11px] uppercase ${streamTone.text}`}>
              {STREAM_LABEL[health.stream.state]}
            </dd>
          </div>
          <KeyRow
            label="FPS"
            value={health.stream.fps !== null && health.stream.expectedFps !== null
              ? `${formatMetricValue(health.stream.fps, 'fps')} / ${health.stream.expectedFps}`
              : formatMetricValue(health.stream.fps, 'fps')}
          />
          <KeyRow label="Frame drop" value={formatMetricValue(health.stream.frameDropPercent, '%')} />
          <KeyRow
            label="Last frame"
            value={health.stream.staleSeconds !== null ? `${health.stream.staleSeconds} sec ago` : 'N/A'}
          />
          <KeyRow label="Latency" value={formatMetricValue(health.network.latencyMs, 'ms')} />
          <KeyRow label="Packet loss" value={formatMetricValue(health.network.packetLossPercent, '%')} />
          <div className="flex items-baseline justify-between gap-2 py-1">
            <dt className="text-[11px] text-slate-500">Network</dt>
            <dd className={`font-mono text-[11px] uppercase ${netTone.text}`}>{health.network.status}</dd>
          </div>
        </dl>

        <div className="py-1">
          <ViewpointStability viewpoint={health.viewpoint} nowMs={nowMs} />
        </div>

        {health.image.metrics.slice(0, 2).map(m => (
          <CameraHealthMetric key={m.metric} metric={m} />
        ))}

        {health.trends.length > 0 && (
          <div className="py-1">
            <CameraHealthTrend trend={health.trends[0]} />
          </div>
        )}
      </div>

      <div className="flex items-center justify-between border-t border-white/[0.05] px-4 py-2">
        <span className="font-mono text-[10px] text-slate-600" title="Telemetry source">
          {health.source === 'DEMO' ? 'DEMO MODE' : health.source === 'LAST_KNOWN' ? 'LAST KNOWN' : 'LIVE TELEMETRY'}
          {health.lastUpdated ? ` · ${formatAge(health.lastUpdated, nowMs)}` : ''}
        </span>
        <button
          onClick={onOpenDetails}
          className="text-[11px] font-medium text-cyan-400 hover:text-cyan-300 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/60 rounded"
        >
          View details →
        </button>
      </div>
    </section>
  )
}

function KeyRow({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-baseline justify-between gap-2 py-1">
      <dt className="text-[11px] text-slate-500">{label}</dt>
      <dd className="font-mono text-[11px] text-slate-200 tabular-nums">{value}</dd>
    </div>
  )
}
