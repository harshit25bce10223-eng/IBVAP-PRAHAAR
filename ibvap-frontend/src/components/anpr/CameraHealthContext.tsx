// CameraHealthContext.tsx — Inline camera health state indicator
import { AlertTriangle, XCircle, CheckCircle, HelpCircle } from 'lucide-react'
import { clsx } from 'clsx'

interface CameraHealthContextProps {
  cameraId: string
  healthState: string | null
  className?: string
}

type HealthInfo = {
  icon: React.ComponentType<{ className?: string }>
  label: string
  color: string
  subtext: string
}

function resolveHealth(state: string | null): HealthInfo {
  const s = state?.toUpperCase() ?? 'UNKNOWN'
  switch (s) {
    case 'HEALTHY':
    case 'GOOD':
    case 'OPERATIONAL':
      return { icon: CheckCircle, label: 'HEALTHY', color: 'text-emerald-400', subtext: 'Camera operating normally' }
    case 'DEGRADED':
    case 'PARTIAL':
      return { icon: AlertTriangle, label: 'DEGRADED', color: 'text-amber-400', subtext: 'Observation conditions degraded' }
    case 'OFFLINE':
    case 'FAILED':
    case 'ERROR':
      return { icon: XCircle, label: 'OFFLINE', color: 'text-red-400', subtext: 'Camera feed unavailable' }
    default:
      return { icon: HelpCircle, label: 'UNKNOWN', color: 'text-slate-500', subtext: 'Health state unknown' }
  }
}

export function CameraHealthContext({ cameraId, healthState, className }: CameraHealthContextProps) {
  const health = resolveHealth(healthState)
  const Icon = health.icon

  return (
    <div className={clsx('flex items-center gap-1.5 text-xs font-mono', className)}>
      <span className="text-slate-400">{cameraId}</span>
      <Icon className={clsx('h-3.5 w-3.5', health.color)} />
      <span className={health.color}>{health.label}</span>
      {(healthState === 'DEGRADED' || healthState === 'OFFLINE' || healthState === 'FAILED') && (
        <span className="text-slate-500 text-[10px]">— {health.subtext}</span>
      )}
    </div>
  )
}