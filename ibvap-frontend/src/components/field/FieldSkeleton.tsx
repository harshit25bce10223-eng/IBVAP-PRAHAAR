// ─────────────────────────────────────────────────────────────────────────────
// FieldSkeleton — render while the field dataset resolves.
// ─────────────────────────────────────────────────────────────────────────────

export function FieldSkeleton() {
  return (
    <div className="h-full flex flex-col gap-3 p-4">
      <div className="h-11 w-1/3 animate-pulse rounded bg-ssb-white/5" />
      <div className="flex-1 grid grid-cols-[minmax(0,1fr)_350px] gap-3">
        <div className="animate-pulse rounded-md bg-ssb-white/5" />
        <div className="animate-pulse rounded-md bg-ssb-white/5" />
      </div>
    </div>
  )
}