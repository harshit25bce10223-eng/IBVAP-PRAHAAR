// ─────────────────────────────────────────────────────────────────────────────
// IncidentIntelSkeleton — render while the investigation dataset resolves.
// ─────────────────────────────────────────────────────────────────────────────

export function IncidentIntelSkeleton() {
  return (
    <div className="h-full flex flex-col gap-3 p-4">
      <div className="h-11 w-1/3 animate-pulse rounded bg-ssb-white/5" />
      <div className="grid flex-1 grid-cols-3 gap-3">
        <div className="animate-pulse rounded-md bg-ssb-white/5" />
        <div className="animate-pulse rounded-md bg-ssb-white/5" />
        <div className="animate-pulse rounded-md bg-ssb-white/5" />
      </div>
    </div>
  )
}