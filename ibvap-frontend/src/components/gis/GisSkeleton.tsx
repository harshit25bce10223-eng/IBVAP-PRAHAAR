// ─────────────────────────────────────────────────────────────────────────────
// GisSkeleton — render while the GIS dataset resolves.
// ─────────────────────────────────────────────────────────────────────────────

export function GisSkeleton() {
  return (
    <div className="h-full flex flex-col gap-3 p-4">
      <div className="h-11 w-1/3 animate-pulse rounded bg-ssb-white/5" />
      <div className="h-8 w-full animate-pulse rounded bg-ssb-white/5" />
      <div className="flex-1 animate-pulse rounded-md border border-ssb-border/40 bg-ssb-navy-deep" />
      <div className="h-[150px] animate-pulse rounded-md bg-ssb-white/5" />
    </div>
  )
}