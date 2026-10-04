// ─────────────────────────────────────────────────────────────────────────────
// SystemStatus — single reusable command-level status element (spec §8).
//
// States: OPERATIONAL / DEGRADED / CRITICAL / OFFLINE mapped ONLY to the
// approved प्रहार palette. Status is always conveyed as text + dot, never by
// colour alone. Reusable later by camera health, backend, AI service, network
// and ledger status without duplicating badge logic.
// ─────────────────────────────────────────────────────────────────────────────

import type { SystemOperationState } from '@/types'

export interface SystemStatusProps {
  state: SystemOperationState
  label?: string
  detail?: string
  size?: 'sm' | 'md'
  className?: string
}

const STATE_STYLES: Record<SystemOperationState, { dot: string; text: string; border: string; bg: string }> = {
  OPERATIONAL: { dot: 'bg-emerald-400 shadow-[0_0_6px_rgba(52,211,153,0.7)]', text: 'text-emerald-400', border: 'border-emerald-500/25', bg: 'bg-emerald-500/8' },
  DEGRADED:    { dot: 'bg-amber-400 animate-pulse shadow-[0_0_6px_rgba(245,158,11,0.6)]', text: 'text-amber-400', border: 'border-amber-500/25', bg: 'bg-amber-500/8' },
  CRITICAL:    { dot: 'bg-red-400 animate-pulse shadow-[0_0_6px_rgba(248,113,113,0.7)]', text: 'text-red-400', border: 'border-red-500/25', bg: 'bg-red-500/8' },
  OFFLINE:     { dot: 'bg-white/20', text: 'text-white/30', border: 'border-white/10', bg: 'bg-white/5' },
}

export function SystemStatus({ state, label, detail, size = 'sm', className }: SystemStatusProps) {
  const styles = STATE_STYLES[state]
  const textSize = size === 'sm' ? 'text-[10px]' : 'text-xs'
  const dotSize  = size === 'sm' ? 'h-1.5 w-1.5' : 'h-2 w-2'

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border ${styles.border} ${styles.bg} px-2.5 py-1 ${className ?? ''}`}
      title={detail}
    >
      <span aria-hidden className={`rounded-full flex-shrink-0 ${dotSize} ${styles.dot}`} />
      <span className={`font-mono font-semibold tracking-widest uppercase whitespace-nowrap ${textSize} ${styles.text}`}>
        {label ?? state}
      </span>
    </span>
  )
}