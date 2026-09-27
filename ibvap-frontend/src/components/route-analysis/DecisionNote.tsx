// ─────────────────────────────────────────────────────────────────────────────
// DecisionNote — mandatory decision support disclaimer (USP 5).
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'
import { Shield, AlertTriangle } from 'lucide-react'

interface Props {
  className?: string
}

export function DecisionNote({ className }: Props) {
  return (
    <div className={clsx('rounded-lg border border-ssb-border/60 bg-ssb-navy/50 p-3 flex-shrink-0', className)}>
      <div className="flex items-start gap-2">
        <Shield size={14} className="text-ssb-text-muted/60 flex-shrink-0 mt-0.5" aria-hidden="true" />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5 mb-1">
            <span className="text-[9px] font-semibold uppercase tracking-[0.16em] text-ssb-text-muted/70">
              DECISION SUPPORT
            </span>
            <AlertTriangle size={10} className="text-ssb-amber-bright" aria-hidden="true" />
          </div>
          <p className="text-[11px] text-ssb-text-muted/90 leading-relaxed">
            Route recommendations are comparative risk analysis based on available
            surveillance, historical, geographic and operational inputs.
          </p>
          <p className="text-[11px] text-ssb-text-muted/90 leading-relaxed mt-1">
            Final operational route selection remains with the authorized
            officer/commander.
          </p>
        </div>
      </div>
    </div>
  )
}