import { clsx } from 'clsx'
import type { ReactNode } from 'react'

type BadgeVariant = 'critical' | 'warning' | 'info' | 'safe' | 'offline' | 'default' | 'cyan' | 'purple'
type BadgeSize    = 'sm' | 'md'

interface BadgeProps {
  variant?: BadgeVariant
  size?: BadgeSize
  dot?: boolean
  children: ReactNode
  className?: string
}

const variantStyles: Record<BadgeVariant, string> = {
  critical: 'bg-red-500/15    text-red-400    border border-red-500/30',
  warning:  'bg-amber-500/15  text-amber-400  border border-amber-500/30',
  info:     'bg-blue-500/15   text-blue-400   border border-blue-500/30',
  safe:     'bg-emerald-500/15 text-emerald-400 border border-emerald-500/30',
  offline:  'bg-slate-500/15  text-slate-400  border border-slate-500/30',
  cyan:     'bg-cyan-500/15   text-cyan-400   border border-cyan-500/30',
  purple:   'bg-purple-500/15 text-purple-400 border border-purple-500/30',
  default:  'bg-white/5       text-slate-300  border border-white/10',
}

const dotColors: Record<BadgeVariant, string> = {
  critical: 'bg-red-400',
  warning:  'bg-amber-400',
  info:     'bg-blue-400',
  safe:     'bg-emerald-400',
  offline:  'bg-slate-400',
  cyan:     'bg-cyan-400',
  purple:   'bg-purple-400',
  default:  'bg-slate-400',
}

export function Badge({ variant = 'default', size = 'sm', dot, children, className }: BadgeProps) {
  return (
    <span
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-full font-medium',
        size === 'sm' ? 'px-2 py-0.5 text-[11px]' : 'px-2.5 py-1 text-xs',
        variantStyles[variant],
        className
      )}
    >
      {dot && (
        <span className={clsx('h-1.5 w-1.5 rounded-full', dotColors[variant])} />
      )}
      {children}
    </span>
  )
}
