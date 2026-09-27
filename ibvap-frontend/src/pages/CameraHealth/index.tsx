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

  // Refresh handler
  const handleRefresh = useCallback(async () => {
    setIsRefreshing(true)
    try {
      await Promise.all(cameraIds.map(id => refreshHealth(id)))
    } finally {
      setIsRefreshing(false)
    }
  }, [cameraIds, refreshHealth])

  const overallSource = healthList[0]?.source ?? 'DEMO'

  return (
    <div className="h-full flex flex-col overflow-y-auto bg-[#080B10] p-4 lg:p-6 gap-5">
      {/* ── Header ───────────────────────────────────────────────────────── */}
      <header className="flex flex-wrap items-start justify-between gap-4 border-b border-white/[0.08] pb-4">
        <div>
          <div className="flex items-center gap-2.5">
            <h1 className="text-xl font-bold tracking-tight text-slate-100">
              Sensor Health & Coverage Intelligence
            </h1>
            <span className="inline-flex items-center px-2 py-0.5 rounded text-[10px] font-mono uppercase tracking-wider font-semibold border border-cyan-500/30 bg-cyan-950/20 text-cyan-400">
              Component 2
            </span>
          </div>
          <p className="text-xs text-slate-400 mt-1 max-w-2xl leading-relaxed">
            Operational surveillance control center monitoring hardware streams, optical
            sharpness, temporal invariance, viewpoint drift, and sector coverage reliability.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-md border border-white/10 bg-[#0F141C] text-[11px] font-mono text-slate-400">
            <span className="w-2 h-2 rounded-full bg-prhaar-good animate-pulse" />
            <span className="uppercase text-slate-300">
              {overallSource === 'DEMO' ? 'DEMO FIXTURES' : 'LIVE TELEMETRY'}
            </span>
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
          selectedFilter={selectedFilter}
          selectedCameraId={inspectingCameraId}
          onSelectCamera={id => setInspectingCameraId(id)}
        />
      </section>

      {/* ── Camera Health Detail Drawer (12 Sections) ───────────────────────── */}
      <Drawer
        open={Boolean(inspectingCameraId && inspectingHealth)}
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
