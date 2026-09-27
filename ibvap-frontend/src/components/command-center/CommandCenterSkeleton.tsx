// ─────────────────────────────────────────────────────────────────────────────
// CommandCenterSkeleton — प्रहार-styled loading placeholder.
//
// Mirrors the final grid so the Command Center never flashes a blank surface
// while the first fetch resolves.
// ─────────────────────────────────────────────────────────────────────────────

import { Skeleton } from '@/components/ui'

export function CommandCenterSkeleton() {
  return (
    <div className="h-full flex flex-col gap-3 overflow-hidden">
      {/* KPI row */}
      <div className="flex gap-3 min-h-0">
        {[...Array(4)].map((_, i) => (
          <Skeleton key={i} className="flex-1 h-[76px]" />
        ))}
      </div>

      {/* Map + incidents */}
      <div className="flex-1 flex gap-3 min-h-0">
        <Skeleton className="flex-1 h-full" />
        <Skeleton className="w-[300px] h-full" />
      </div>

      {/* Bottom row */}
      <div className="flex gap-3 h-[150px] min-h-0">
        <Skeleton className="flex-[2] h-full" />
        <Skeleton className="flex-1 h-full" />
      </div>
    </div>
  )
}