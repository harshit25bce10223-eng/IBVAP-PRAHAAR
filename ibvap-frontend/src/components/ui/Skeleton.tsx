import { clsx } from 'clsx'

interface SkeletonProps {
  className?: string
  lines?: number
  circle?: boolean
}

export function Skeleton({ className, lines = 1, circle = false }: SkeletonProps) {
  if (lines > 1) {
    return (
      <div className="flex flex-col gap-2">
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className={clsx(
              'animate-pulse rounded bg-white/5',
              i === lines - 1 ? 'w-3/4 h-3' : 'h-3',
              className
            )}
          />
        ))}
      </div>
    )
  }
  return (
    <div
      className={clsx(
        'animate-pulse bg-white/5',
        circle ? 'rounded-full' : 'rounded',
        !className?.includes('h-') && 'h-4',
        className
      )}
    />
  )
}

export function StatCardSkeleton() {
  return (
    <div className="rounded-xl border border-border bg-surface p-5 space-y-3">
      <div className="flex items-center justify-between">
        <Skeleton className="h-3 w-24" />
        <Skeleton className="h-8 w-8" circle />
      </div>
      <Skeleton className="h-8 w-20" />
      <Skeleton className="h-2.5 w-32" />
    </div>
  )
}
