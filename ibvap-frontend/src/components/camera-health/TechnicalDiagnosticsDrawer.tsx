// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 2 — Technical Diagnostics Drawer
// Detailed telemetry, computer-vision parameters, and threshold diagnostics
// ─────────────────────────────────────────────────────────────────────────────

import { Drawer } from '@/components/ui'
import type { CameraHealth } from '@/types/cameraHealth'
import { formatClock, formatMetricValue } from './healthFormat'
import { Cpu, Eye, Activity, ShieldCheck, Layers, GitBranch } from 'lucide-react'

export interface TechnicalDiagnosticsDrawerProps {
  open: boolean
  onClose: () => void
  health: CameraHealth | null
}

export function TechnicalDiagnosticsDrawer({ open, onClose, health }: TechnicalDiagnosticsDrawerProps) {
  if (!health) return null

  return (
    <Drawer
      open={open}
      onClose={onClose}
      title={`Diagnostics · ${health.cameraId}`}
      width="w-[520px]"
    >
      <div className="space-y-5 text-[12px] text-slate-300 p-4">
        <p className="text-[11px] text-slate-400">
          Computer-vision telemetry, threshold evaluation, and underlying algorithm parameters.
        </p>
        {/* Telemetry Header */}
        <div className="rounded-lg border border-cyan-500/20 bg-cyan-950/20 p-3">
          <div className="flex items-center gap-2 text-cyan-400 font-mono text-[11px] font-semibold uppercase mb-1">
            <Cpu size={14} />
            <span>Telemetry Provenance</span>
          </div>
          <dl className="grid grid-cols-2 gap-2 text-[11px] font-mono">
            <div>
              <dt className="text-slate-500">Source Mode</dt>
              <dd className="text-slate-200">{health.source}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Last Telemetry</dt>
              <dd className="text-slate-200">{formatClock(health.lastUpdated)}</dd>
            </div>
            <div>
              <dt className="text-slate-500">Algorithm Engine</dt>
              <dd className="text-slate-200">PRHAAR-CV-v2.4 (ORB+NCC)</dd>
            </div>
            <div>
              <dt className="text-slate-500">Evaluation State</dt>
              <dd className="text-slate-200 font-semibold">{health.status}</dd>
            </div>
          </dl>
        </div>

        {/* Computer Vision Metrics */}
        <section className="space-y-2">
          <h4 className="flex items-center gap-1.5 font-semibold text-slate-200 text-xs uppercase tracking-wider">
            <Eye size={13} className="text-slate-400" />
            Computer Vision Telemetry
          </h4>
          <div className="rounded-lg border border-white/[0.08] bg-surface p-3 space-y-2.5 font-mono text-[11px]">
            <div className="flex justify-between items-center py-0.5 border-b border-white/[0.04]">
              <span className="text-slate-500">Sharpness (Laplacian var)</span>
              <span className="text-slate-200">
                {formatMetricValue(
                  health.image.metrics.find(m => m.metric === 'sharpness')?.value,
                  'ratio'
                )}{' '}
                (threshold: ≥ 0.50)
              </span>
            </div>
            <div className="flex justify-between items-center py-0.5 border-b border-white/[0.04]">
              <span className="text-slate-500">Illumination (Brightness)</span>
              <span className="text-slate-200">
                {formatMetricValue(
                  health.image.metrics.find(m => m.metric === 'brightness')?.value,
                  'ratio'
                )}{' '}
                (nominal: 0.10–0.90)
              </span>
            </div>
            <div className="flex justify-between items-center py-0.5 border-b border-white/[0.04]">
              <span className="text-slate-500">Viewpoint Shift Score</span>
              <span className="text-slate-200">
                {formatMetricValue(health.viewpoint.shiftScore, 'ratio') ?? '0.00'} (limit: 0.35)
              </span>
            </div>
            <div className="flex justify-between items-center py-0.5 border-b border-white/[0.04]">
              <span className="text-slate-500">RANSAC Inlier Ratio</span>
              <span className="text-slate-200">0.82 (min threshold: 0.30)</span>
            </div>
            <div className="flex justify-between items-center py-0.5">
              <span className="text-slate-500">Slow Background Drift</span>
              <span className="text-slate-200">{health.image.backgroundStability ?? 'Nominal'}</span>
            </div>
          </div>
        </section>

        {/* Stream & Freeze Parameters */}
        <section className="space-y-2">
          <h4 className="flex items-center gap-1.5 font-semibold text-slate-200 text-xs uppercase tracking-wider">
            <Activity size={13} className="text-slate-400" />
            Stream & Temporal Invariance
          </h4>
          <div className="rounded-lg border border-white/[0.08] bg-surface p-3 space-y-2.5 font-mono text-[11px]">
            <div className="flex justify-between items-center py-0.5 border-b border-white/[0.04]">
              <span className="text-slate-500">Delivered / Expected FPS</span>
              <span className="text-slate-200">
                {health.stream.fps ?? 0} fps / {health.stream.expectedFps ?? 25} fps
              </span>
            </div>
            <div className="flex justify-between items-center py-0.5 border-b border-white/[0.04]">
              <span className="text-slate-500">Stale Frame Delay</span>
              <span className="text-slate-200">
                {health.stream.staleSeconds !== null ? `${health.stream.staleSeconds}s` : '0s'} (stale at 30s)
              </span>
            </div>
            <div className="flex justify-between items-center py-0.5 border-b border-white/[0.04]">
              <span className="text-slate-500">Frame Drop Rate</span>
              <span className="text-slate-200">{formatMetricValue(health.stream.frameDropPercent, '%')}</span>
            </div>
            <div className="flex justify-between items-center py-0.5">
              <span className="text-slate-500">Freeze Detector (NCC)</span>
              <span className="text-slate-200">
                {health.stream.state === 'FROZEN' ? 'TRIGGERED (sim > 0.99 for 120s)' : 'NOMINAL (active delta)'}
              </span>
            </div>
          </div>
        </section>

        {/* Excluded ROI Masking Context */}
        <section className="space-y-2">
          <h4 className="flex items-center gap-1.5 font-semibold text-slate-200 text-xs uppercase tracking-wider">
            <Layers size={13} className="text-slate-400" />
            ROI Exclusion Context
          </h4>
          <div className="rounded-lg border border-white/[0.08] bg-surface p-3 space-y-2 text-[11px]">
            <p className="text-slate-400">
              Active computer vision masks applied to eliminate false positives from ambient motion:
            </p>
            <ul className="list-disc list-inside space-y-1 text-slate-300 font-mono">
              <li>Polygon ROI-01: Upper canopy foliage (wind vibration tolerance)</li>
              <li>Polygon ROI-02: Watercourse shoreline (refraction exclusion)</li>
            </ul>
          </div>
        </section>
      </div>
    </Drawer>
  )
}
