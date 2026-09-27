// ─────────────────────────────────────────────────────────────────────────────
// RouteSkeleton — loading skeleton for route analysis (USP 5).
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'

interface Props {
  className?: string
}

export function RouteSkeleton({ className }: Props) {
  return (
    <div className={clsx('h-full flex flex-col gap-3', className)}>
      {/* Input panel skeleton */}
      <div className="rounded-md border border-ssb-border/70 bg-ssb-navy/60 px-4 py-3 flex-shrink-0 animate-pulse">
        <div className="flex items-end gap-3 flex-wrap">
          <div className="flex-1 min-w-[140px]">
            <div className="h-3 w-24 rounded bg-ssb-border/30 mb-1" />
            <div className="h-9 w-full rounded bg-ssb-border/30" />
          </div>
          <div className="flex-1 min-w-[140px]">
            <div className="h-3 w-24 rounded bg-ssb-border/30 mb-1" />
            <div className="h-9 w-full rounded bg-ssb-border/30" />
          </div>
          <div className="flex-1 min-w-[160px] max-w-[200px]">
            <div className="h-3 w-32 rounded bg-ssb-border/30 mb-1" />
            <div className="h-9 w-full rounded bg-ssb-border/30" />
          </div>
        </div>
        <div className="flex items-center justify-between gap-3 pt-1 border-t border-ssb-border/40 mt-3">
          <div className="h-10 w-40 rounded bg-ssb-border/30" />
          <div className="h-6 w-32 rounded bg-ssb-border/30" />
        </div>
      </div>

      {/* Main content area skeleton */}
      <div className="flex-1 min-h-0 flex gap-3 overflow-hidden">
        {/* Map skeleton */}
        <div className="flex-1 min-w-0 rounded-md border border-ssb-border/70 bg-ssb-navy-deep animate-pulse relative overflow-hidden">
          <div className="absolute inset-0 bg-gradient-to-b from-ssb-navy-deep via-ssb-navy to-ssb-navy-deep" />
          <div className="absolute top-2 right-2 rounded bg-ssb-navy/90 border border-ssb-border/50 px-2 py-1">
            <div className="h-3 w-24 bg-ssb-border/30 rounded" />
          </div>
        </div>

        {/* Right panel skeleton */}
        <div className="w-80 flex-shrink-0 flex flex-col gap-3 overflow-auto pr-1">
          <div className="h-6 w-40 rounded bg-ssb-border/30" />
          <div className="flex flex-col gap-2">
            {[1, 2, 3].map(i => (
              <div key={i} className="rounded-lg border border-ssb-border/60 bg-ssb-navy/50 p-3 animate-pulse">
                <div className="flex items-center justify-between gap-2 mb-2">
                  <div className="h-4 w-24 rounded bg-ssb-border/30" />
                  <div className="h-5 w-20 rounded bg-ssb-border/30" />
                </div>
                <div className="h-8 w-16 rounded bg-ssb-border/30 mb-2" />
                <div className="grid grid-cols-2 gap-1.5">
                  {[1, 2, 3, 4, 5, 6].map(j => (
                    <div key={j} className="h-12 rounded bg-ssb-border/30" />
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Bottom bars skeleton */}
      <div className="grid grid-cols-4 gap-3">
        {[1, 2, 3, 4].map(i => (
          <div key={i} className="rounded-lg border border-ssb-border/60 bg-ssb-navy/50 p-3 flex-shrink-0 animate-pulse">
            <div className="h-3 w-20 rounded bg-ssb-border/30 mb-2" />
            <div className="h-4 w-full rounded bg-ssb-border/30" />
          </div>
        ))}
      </div>
    </div>
  )
}