// ─────────────────────────────────────────────────────────────────────────────
// ANPRProviderStatus.tsx — §28 provider status strip
//
// Shows only provider-reported values. Latency shows "—" when the provider
// does not measure it; never invents READY or latency numbers.
// ─────────────────────────────────────────────────────────────────────────────
import { Activity, AlertTriangle, RefreshCw } from 'lucide-react'
import { clsx } from 'clsx'
import type { ANPRProviderHealth } from '@/types/anpr'

interface ANPRProviderStatusProps {
  health: ANPRProviderHealth | null
  state: 'idle' | 'loading' | 'ready' | 'error'
  error?: string | null
  onRefresh?: () => void
  className?: string
}

function stateBadgeClass(s: string): string {
  switch (s.toUpperCase()) {
    case 'READY':
      return 'text-emerald-300 border-emerald-500/40 bg-emerald-500/10'
    case 'DEGRADED':
      return 'text-amber-300 border-amber-500/40 bg-amber-500/10'
    case 'OFFLINE':
    case 'UNAVAILABLE':
      return 'text-red-300 border-red-500/40 bg-red-500/10'
    default:
      return 'text-slate-300 border-slate-600/50 bg-slate-500/10'
  }
}

function fmtTs(ts: string | null): string {
  if (!ts) return '—'
  const d = new Date(ts)
  if (Number.isNaN(d.getTime())) return ts
  return d.toLocaleString('en-IN', { hour12: false, day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' })
}

export function ANPRProviderStatus({
  health,
  state,
  error,
  onRefresh,
  className,
}: ANPRProviderStatusProps) {
  return (
    <div
      className={clsx(
        'flex flex-wrap items-center gap-x-4 gap-y-1 px-3 py-1.5 border border-[#1e2d40] rounded-lg bg-[#0d1117] text-[11px] font-mono',
        className
      )}
    >
      <span className="flex items-center gap-1.5">
        <Activity className="h-3.5 w-3.5 text-cyan-400 flex-shrink-0" />
        <span className="text-slate-400 uppercase">ANPR Provider</span>
      </span>

      {state === 'loading' && !health && (
        <span className="text-slate-500">Checking provider status…</span>
      )}

      {state === 'error' && (
        <>
          <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />
          <span className="text-amber-300">
            {error ?? 'Provider status unavailable.'}
          </span>
        </>
      )}

      {state === 'idle' && !health && (
        <span className="text-slate-500">Provider status not loaded.</span>
      )}

      {health && (
        <>
          <span className="flex items-center gap-1.5">
            <span className="text-slate-200">{health.provider}</span>
            {health.providerVersion && (
              <span className="text-slate-500">v{health.providerVersion}</span>
            )}
          </span>
          <span className={clsx('px-1.5 py-0.5 rounded border', stateBadgeClass(health.state))}>
            {health.state}
          </span>
          <span className="text-slate-400">
            Last inference: <span className="text-slate-200">{fmtTs(health.lastSuccessfulUpdate)}</span>
          </span>
          <span
            className="text-slate-400"
            title={
              health.processingLatencyMs == null
                ? 'Provider does not measure inference latency'
                : undefined
            }
          >
            Latency:{' '}
            <span className="text-slate-200">
              {health.processingLatencyMs != null ? `${health.processingLatencyMs} ms` : '—'}
            </span>
          </span>
          <span className="text-slate-400">
            Failures: <span className="text-slate-200">{health.failureCount}</span>
          </span>
          <span className="text-slate-400">
            Queue: <span className="text-slate-200">{health.queueDepth}</span>
          </span>
          <span className="text-slate-400">
            Cameras active: <span className="text-slate-200">{health.camerasActive}</span>
          </span>
          {health.note && (
            <span className="text-slate-500 italic min-w-0 truncate" title={health.note}>
              {health.note}
            </span>
          )}
        </>
      )}

      {onRefresh && (
        <button
          onClick={onRefresh}
          className="ml-auto p-1 rounded text-slate-500 hover:text-slate-200 hover:bg-slate-800/60 transition-colors"
          title="Refresh provider status"
        >
          <RefreshCw className={clsx('h-3 w-3', state === 'loading' && 'animate-spin')} />
        </button>
      )}
    </div>
  )
}
