import { clsx } from 'clsx'

type StatusType = 'online' | 'offline' | 'alert' | 'degraded' | 'maintenance' | 'idle'

interface StatusIndicatorProps {
  status: StatusType
  label?: string
  size?: 'sm' | 'md'
  className?: string
}

const STATUS_STYLES: Record<StatusType, { dot: string; label: string }> = {
  online:      { dot: 'bg-emerald-400 animate-pulse-dot',  label: 'text-emerald-400' },
  offline:     { dot: 'bg-slate-500',                      label: 'text-slate-500'   },
  alert:       { dot: 'bg-red-400 animate-pulse-dot',      label: 'text-red-400'     },
  degraded:    { dot: 'bg-amber-400 animate-pulse-dot',    label: 'text-amber-400'   },
  maintenance: { dot: 'bg-blue-400',                       label: 'text-blue-400'    },
  idle:        { dot: 'bg-slate-600',                      label: 'text-slate-500'   },
}

export function StatusIndicator({ status, label, size = 'sm', className }: StatusIndicatorProps) {
  const styles = STATUS_STYLES[status]
  return (
    <span className={clsx('inline-flex items-center gap-1.5', className)}>
      <span
        className={clsx(
          'rounded-full flex-shrink-0',
          size === 'sm' ? 'h-1.5 w-1.5' : 'h-2 w-2',
          styles.dot
        )}
      />
      {label && (
        <span className={clsx('font-medium', size === 'sm' ? 'text-[11px]' : 'text-xs', styles.label)}>
          {label}
        </span>
      )}
    </span>
  )
}
