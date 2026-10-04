// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 2 — Sensor Health & Fleet Coverage Intelligence Workspace
// ─────────────────────────────────────────────────────────────────────────────

import { useEffect, useState, useMemo, useCallback } from 'react'
import {
  Activity,
  RefreshCw,
  AlertTriangle,
  ShieldCheck,
  Cpu,
  Layers,
  CheckCircle2,
} from 'lucide-react'
import { useCameraStore, useHealthStore } from '@/store'
import type { HealthEntryState } from '@/store'
import {
  CameraFleetSummary,
  CameraHealthTable,
  CameraHealthDetails,
  TechnicalDiagnosticsDrawer,
} from '@/components/camera-health'
import { Drawer, Button, EmptyState, ErrorState } from '@/components/ui'
import type { CameraHealth } from '@/types/cameraHealth'

export function CameraHealthPage() {
  const cameras = useCameraStore(s => s.cameras)
  const healthEntries = useHealthStore(s => s.entries)
  const fetchAllHealth = useHealthStore(s => s.fetchAll)
  const refreshHealth = useHealthStore(s => s.refreshHealth)

  const [selectedFilter, setSelectedFilter] = useState<string | null>(null)
  const [inspectingCameraId, setInspectingCameraId] = useState<string | null>(null)
  const [diagnosticsOpen, setDiagnosticsOpen] = useState(false)
  const [isRefreshing, setIsRefreshing] = useState(false)

  const cameraIds = useMemo(() => cameras.map(c => c.id), [cameras])

  // Fetch telemetry for all cameras on mount
  useEffect(() => {
    if (cameraIds.length > 0) {
      fetchAllHealth(cameraIds).catch(() => {})
    }
  }, [cameraIds, fetchAllHealth])

  // Map health records
  const healthRecords: Record<string, CameraHealth> = useMemo(() => {
    const map: Record<string, CameraHealth> = {}
    for (const [id, entry] of Object.entries(healthEntries)) {
      if (entry.data) {
        map[id] = entry.data
      }
    }
    return map
  }, [healthEntries])

  const healthList = useMemo(() => Object.values(healthRecords), [healthRecords])

  const inspectingHealth = inspectingCameraId ? healthRecords[inspectingCameraId] ?? null : null

  // Per-camera provider state (idle/loading/ready/error/last-known) so the
  // table can render honest unavailable / last-known presentation instead of
  // implying the camera is fine when telemetry never arrived (§35).
  const entryStates = useMemo(() => {
    const map: Record<string, { state: HealthEntryState; error: string | null }> = {}
    for (const [id, entry] of Object.entries(healthEntries)) {
      map[id] = { state: entry.state, error: entry.error }
    }
    return map
  }, [healthEntries])

  // Refresh handler
  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true)
    try {
      await Promise.all(cameraIds.map(id => refreshHealth(id)))
    } finally {
      setIsRefreshing(false)
    }
  }, [cameraIds, refreshHealth])

  // Header telemetry badge — reflects what actually arrived, never a
  // reassuring default: DEMO fixtures, full live coverage, partial coverage
  // (some cameras unavailable / last-known), or nothing at all (§36).
  const telemetryBadge = useMemo(() => {
    if (healthList.length === 0) {
      const failed = Object.values(healthEntries).filter(e => e.state === 'error').length
      return failed > 0
        ? {
            label: 'TELEMETRY UNAVAILABLE',
            dot: 'bg-rose-400',
            title: `${failed} camera(s) failed to report`,
          }
        : { label: 'AWAITING TELEMETRY', dot: 'bg-amber-400', title: 'Fetching camera health…' }
    }
    const source = healthList[0]?.source
    if (source === 'DEMO') {
      return { label: 'DEMO FIXTURES', dot: 'bg-cyan-400', title: 'Render fixtures — not live telemetry' }
    }
    if (source === 'UNAVAILABLE') {
      return { label: 'TELEMETRY UNAVAILABLE', dot: 'bg-rose-400', title: 'Backend unreachable' }
    }
    const unavailable = cameraIds.length - healthList.length
    const storeLastKnown = Object.values(healthEntries).filter(e => e.state === 'last-known').length
    // Backend may itself label a record LAST_KNOWN (>60s old) — the header
    // must not claim full live freshness in that case either.
    const apiLastKnown = healthList.filter(h => h.source === 'LAST_KNOWN').length
    const lastKnown = storeLastKnown + apiLastKnown
    if (unavailable + lastKnown > 0) {
      return {
        label: 'LIVE TELEMETRY · PARTIAL',
        dot: 'bg-amber-400',
        title: `${unavailable} unavailable · ${lastKnown} last-known`,
      }
    }
    return { label: 'LIVE TELEMETRY', dot: 'bg-prhaar-good', title: 'All cameras reporting' }
  }, [healthEntries, healthList, cameraIds.length])

  return (
    <div className="h-full flex flex-col overflow-y-auto bg-bg p-4 lg:p-6 gap-5">
      {/* ── Header ───────────────────────────────────────────────────────── */}
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-white/[0.08] pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl font-bold tracking-tight text-slate-100">
              SAKSHAM · Sensor Health &amp; Coverage Intelligence
            </h1>
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider font-semibold border border-cyan-500/30 bg-cyan-950/20 text-cyan-400">
              सक्षम · Component 2
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl leading-relaxed">
            Self-Aware &amp; Low-Network-Resilient Platform · Optical sharpness, temporal invariance,
            viewpoint drift, and sector coverage compromise detection.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-white/10 bg-surface text-[11px] font-mono text-slate-400"
            title={telemetryBadge.title}
          >
            <span className={`w-2 h-2 rounded-full ${telemetryBadge.dot}`} />
            <span className="uppercase text-slate-300">{telemetryBadge.label}</span>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={isRefreshing}
            className="flex items-center gap-1.5 text-xs text-slate-300"
          >
            <RefreshCw size={12} className={isRefreshing ? 'animate-spin' : ''} />
            <span>{isRefreshing ? 'Refreshing…' : 'Refresh Fleet'}</span>
          </Button>
        </div>
      </header>

      {/* ── Operational Summary Cards ──────────────────────────────────────── */}
      <section aria-label="Fleet operational summary">
        <CameraFleetSummary
          healthRecords={healthList}
          selectedFilter={selectedFilter}
          onSelectFilter={setSelectedFilter}
        />
      </section>

      {/* ── Fleet Surveillance Table ───────────────────────────────────────── */}
      <section aria-label="Camera health table" className="flex-1 min-h-[350px]">
        <CameraHealthTable
          cameras={cameras}
          healthRecords={healthRecords}
          entryStates={entryStates}
          selectedFilter={selectedFilter}
          selectedCameraId={inspectingCameraId}
          onSelectCamera={id => setInspectingCameraId(id)}
        />
      </section>

      {/* ── Camera Health Detail Drawer (12 Sections) ───────────────────────── */}
      <Drawer
        open={Boolean(inspectingCameraId)}
        onClose={() => setInspectingCameraId(null)}
        title={inspectingCameraId ? `Sensor Health · ${inspectingCameraId}` : 'Sensor Health'}
        width="w-[520px]"
      >
        <div className="p-4 overflow-y-auto">
          <p className="text-[11px] text-slate-400 mb-3">
            Comprehensive 12-section operational telemetry, baseline deviation, and border coverage diagnostics.
          </p>
          {inspectingHealth ? (
            <CameraHealthDetails
              health={inspectingHealth}
              onOpenDiagnostics={() => setDiagnosticsOpen(true)}
            />
          ) : (
            <div className="py-8 text-center text-slate-500 font-mono text-xs">
              No health telemetry available for this sensor.
              {inspectingCameraId && entryStates[inspectingCameraId]?.error && (
                <span className="block mt-2 text-amber-400/80">
                  {entryStates[inspectingCameraId].error}
                </span>
              )}
            </div>
          )}
        </div>
      </Drawer>

      {/* ── Technical Diagnostics Drawer ───────────────────────────────────── */}
      <TechnicalDiagnosticsDrawer
        open={diagnosticsOpen}
        onClose={() => setDiagnosticsOpen(false)}
        health={inspectingHealth}
      />
    </div>
  )
}
