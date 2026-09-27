import { clsx } from 'clsx'
import type { ReactNode } from 'react'
import { AlertTriangle } from 'lucide-react'

interface EmptyStateProps {
  icon?: ReactNode
  title: string
  description?: string
  action?: ReactNode
  className?: string
}

export function EmptyState({ icon, title, description, action, className }: EmptyStateProps) {
  return (
    <div className={clsx('flex flex-col items-center justify-center py-16 text-center gap-4', className)}>
      {icon && <div className="text-slate-600">{icon}</div>}
      <div className="space-y-1">
        <p className="text-sm font-medium text-slate-400">{title}</p>
        {description && <p className="text-xs text-slate-600 max-w-xs">{description}</p>}
      </div>
      {action}
    </div>
  )
}

interface ErrorStateProps {
  message?: string
  onRetry?: () => void
  className?: string
}

export function ErrorState({ message = 'Something went wrong.', onRetry, className }: ErrorStateProps) {
  return (
    <div className={clsx('flex flex-col items-center justify-center py-16 gap-4', className)}>
      <AlertTriangle size={32} className="text-red-500/70" />
      <p className="text-sm text-slate-400">{message}</p>
      {onRetry && (
        <button
          onClick={onRetry}
          className="text-xs text-cyan-400 hover:text-cyan-300 underline underline-offset-2"
        >
          Try again
        </button>
      )}
    </div>
  )
}
