// ─────────────────────────────────────────────────────────────────────────────
// Dashboard — COMMAND CENTER (Main Command Dashboard, Sub-Component 2)
//
// Unified operational picture at 1920×1080 without scrolling:
//   KPI strip → GIS digital twin (dominant) + Active Incidents
//            → Camera intelligence / Human-Animal + System Health / Activity.
//
// Spec §7 title discipline: "COMMAND CENTER" — not LIVE SURVEILLANCE (that is
// a different operational view).
// ─────────────────────────────────────────────────────────────────────────────

import { useCommandDashboard } from '@/hooks'
import {
  KpiSummaryRow,
  CommandMap,
  ActiveIncidentPanel,
  CameraIntelRow,
  HumanAnimalCard,
  SystemHealthPanel,
  ActivityFeed,
  EvidenceTrustCard,
  CommandCenterSkeleton,
} from '@/components/command-center'

export function Dashboard() {
  const { data, loadState, refetch } = useCommandDashboard()

  if (loadState === 'error' && !data) {
    return (
      <div className="h-full flex items-center justify-center">
        <button
          onClick={() => refetch().catch(() => {})}
          className="text-xs text-ssb-amber-bright underline underline-offset-2"
        >
          Failed to load Command Center — try again
        </button>
      </div>
    )
  }

  if (!data) {
    return <CommandCenterSkeleton />
  }

  const { kpis, goldenIncident, incidents, cameras, humanAnimal, systemHealth, activity, evidence } = data

  return (
    <div className="h-full flex flex-col gap-3 overflow-hidden p-4">
      {/* Page identity */}
      <header className="flex items-end justify-between flex-shrink-0">
        <div>
          <h1 className="text-lg font-semibold tracking-[0.12em] text-ssb-white uppercase">
            Command Center
          </h1>
          <p className="text-[11px] text-ssb-text-muted mt-0.5 tracking-wide">
            Integrated Border Surveillance &amp; Incident Intelligence
          </p>
        </div>
        {/* Prototype data badge — this workspace runs on the mock command
            dashboard service until the real API phase (§25/§26). */}
        <div className="flex flex-col items-end gap-1">
          <span className="rounded border border-cyan-500/30 bg-cyan-500/10 px-1.5 py-0.5 font-mono text-[9px] uppercase tracking-wider text-cyan-400">
            Demo mode
          </span>
          <span className="text-[9px] font-mono tracking-[0.2em] text-ssb-text-muted/60 uppercase">
            SSB Border Surveillance · Sector Operations
          </span>
        </div>
      </header>

      {/* KPI / intelligence summary */}
      <KpiSummaryRow kpis={kpis} />

      {/* Main grid: GIS + Active Incidents */}
      <div className="flex-1 min-h-0 grid grid-cols-[minmax(0,1fr)_320px] gap-3">
        <CommandMap goldenIncident={goldenIncident} cameras={cameras} />
        <ActiveIncidentPanel incidents={incidents} goldenIncident={goldenIncident} />
      </div>

      {/* Bottom strip: camera intel / context + health / evidence */}
      <div className="h-[188px] min-h-0 grid grid-cols-[minmax(0,1fr)_320px] gap-3">
        <div className="min-w-0 flex gap-3">
          <CameraIntelRow cameras={cameras} className="flex-[2]" />
          <HumanAnimalCard data={humanAnimal} className="flex-1" />
          <ActivityFeed events={activity} className="flex-1" />
        </div>
        <div className="min-w-0 flex flex-col gap-2">
          <SystemHealthPanel entries={systemHealth} className="flex-1" />
          <EvidenceTrustCard data={evidence} />
        </div>
      </div>
    </div>
  )
}