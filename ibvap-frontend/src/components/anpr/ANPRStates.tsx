// ANPREmptyState.tsx
import { Car } from 'lucide-react'

interface ANPREmptyStateProps {
  message?: string
}

export function ANPREmptyState({ message }: ANPREmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-16 text-center">
      <div className="h-12 w-12 rounded-xl border border-[#1e2d40] bg-[#0d1117] flex items-center justify-center">
        <Car className="h-6 w-6 text-slate-600" />
      </div>
      <div>
        <p className="font-mono text-sm font-semibold text-slate-400 uppercase tracking-wider">
          No Plate Observations
        </p>
        <p className="mt-1 text-xs text-slate-600 font-mono">
          {message ?? 'No vehicle sightings found for the selected filters.'}
        </p>
      </div>
    </div>
  )
}

// ANPRErrorState.tsx
interface ANPRErrorStateProps {
  message?: string
  onRetry?: () => void
}

export function ANPRErrorState({ message, onRetry }: ANPRErrorStateProps) {
  return (
    <div className="flex flex-col items-center justify-center gap-4 py-16 text-center">
      <div className="h-12 w-12 rounded-xl border border-red-500/20 bg-red-500/5 flex items-center justify-center">
        <svg className="h-6 w-6 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
        </svg>
      </div>
      <div>
        <p className="font-mono text-sm font-semibold text-red-400 uppercase tracking-wider">
          ANPR Data Unavailable
        </p>
        <p className="mt-1 text-xs text-slate-500 font-mono">
          {message ?? 'Unable to retrieve vehicle observation data.'}
        </p>
      </div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-1.5 text-xs font-mono text-red-300 hover:bg-red-500/20 transition-colors"
        >
          Retry
        </button>
      )}
    </div>
  )
}