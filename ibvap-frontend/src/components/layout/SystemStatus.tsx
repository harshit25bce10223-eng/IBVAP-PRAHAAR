// ─────────────────────────────────────────────────────────────────────────────
// SystemStatus — single reusable command-level status element (spec §8).
//
// States: OPERATIONAL / DEGRADED / CRITICAL / OFFLINE mapped ONLY to the
// approved प्रहार palette. Status is always conveyed as text + dot, never by
// colour alone. Reusable later by camera health, backend, AI service, network
// and ledger status without duplicating badge logic.
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'
import type { SystemOperationState } from '@/types'

export interface SystemStatusProps {
  state: SystemOperationState
  label?: string
  detail?: string
  size?: 'sm' | 'md'
  className?: string
}

const STATE_STYLES: Record<SystemOperationState, { dot: string; text: string }> = {
  OPERATIONAL: { dot: 'bg-ssb-green',            text: 'text-ssb-green-bright'   },
  DEGRADED:    { dot: 'bg-ssb-amber animate-pulse-dot', text: 'text-ssb-amber-bright' },
  CRITICAL:    { dot: 'bg-ssb-red animate-pulse-dot',   text: 'text-ssb-red-bright'   },
  OFFLINE:     { dot: 'bg-ssb-text-muted/60',    text: 'text-ssb-text-muted'      },
}

export function SystemStatus({ state, label, detail, size = 'sm', className }: SystemStatusProps) {
  const styles = STATE_STYLES[state]
  const textSize = size === 'sm' ? 'text-[11px]' : 'text-xs'
  const dotSize  = size === 'sm' ? 'h-2 w-2' : 'h-2.5 w-2.5'

  return (
    <span
      className={clsx(
        'inline-flex items-center gap-2 rounded-md border border-ssb-border bg-ssb-navy-deep/60 px-2.5 py-1',
        className
      )}
      title={detail}
    >
      <span
        aria-hidden
        className={clsx('rounded-full flex-shrink-0', dotSize, styles.dot)}
      />
      <span className={clsx('font-mono font-semibold tracking-wider uppercase whitespace-nowrap', textSize, styles.text)}>
        {label ?? state}
      </span>
    </span>
  )
}