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
    <div className="h-full flex flex-col gap-3 overflow-y-auto p-4">
      {/* Page identity — military command center header */}
      <header className="flex items-center justify-between flex-shrink-0 pb-3 border-b border-white/[0.06]">
        {/* Left: glowing status dot + title + subtitle */}
        <div className="flex items-start gap-3">
          <div className="flex flex-col items-center gap-1 pt-0.5">
            <span className="h-2.5 w-2.5 rounded-full bg-emerald-400 shadow-[0_0_8px_rgba(52,211,153,0.8),0_0_20px_rgba(52,211,153,0.3)]" aria-hidden />
            <span className="h-5 w-px bg-gradient-to-b from-emerald-400/30 to-transparent" aria-hidden />
          </div>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-[18px] font-bold tracking-[0.18em] text-white uppercase font-mono drop-shadow-[0_0_12px_rgba(255,255,255,0.15)]">
                Command Center
              </h1>
              <span className="rounded border border-cyan-500/30 bg-cyan-500/10 px-2 py-0.5 font-mono text-[8px] uppercase tracking-[0.16em] text-cyan-400">
                Demo mode
              </span>
            </div>
            <p className="text-[10px] font-mono text-white/30 mt-0.5 tracking-[0.14em] uppercase">
              Integrated Border Surveillance &amp; Incident Intelligence
            </p>
          </div>
        </div>

        {/* Right: sector info + threat level indicator */}
        <div className="flex items-center gap-3">
          <div className="flex flex-col items-end gap-0.5">
            <span className="text-[9px] font-mono tracking-[0.2em] text-white/35 uppercase font-semibold">
              SSB Border Surveillance
            </span>
            <span className="text-[8px] font-mono text-white/20 uppercase tracking-[0.12em]">
              Sector Operations · Indo-Nepal Frontier
            </span>
          </div>
          {/* Threat level badge */}
          <div className="flex flex-col items-center gap-0.5 rounded-lg border border-emerald-500/25 bg-emerald-500/8 px-3 py-1.5">
            <span className="text-[7px] font-mono font-bold tracking-[0.22em] text-emerald-400/60 uppercase">Threat</span>
            <span className="text-[13px] font-mono font-bold tracking-[0.1em] text-emerald-400 leading-none">LOW</span>
          </div>
        </div>
      </header>

      {/* KPI / intelligence summary */}
      <KpiSummaryRow kpis={kpis} />

      {/* Main grid: GIS + Active Incidents */}
      <div className="flex-1 min-h-[440px] grid grid-cols-[minmax(0,1fr)_320px] gap-3">
        <CommandMap goldenIncident={goldenIncident} cameras={cameras} />
        <ActiveIncidentPanel incidents={incidents} goldenIncident={goldenIncident} />
      </div>

      {/* Bottom strip: camera intel / context + health / evidence */}
      <div className="h-[190px] min-h-[190px] flex-shrink-0 grid grid-cols-[minmax(0,1fr)_320px] gap-3">
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