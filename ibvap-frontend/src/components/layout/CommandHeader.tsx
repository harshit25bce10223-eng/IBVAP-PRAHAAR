// ─────────────────────────────────────────────────────────────────────────────
// CommandHeader — प्रहार top command strip (spec §7).
//
// Left:   current operational section + descriptor
// Center: reserved global command-search space (Phase 2; compact, non-fake)
// Right:  SystemStatus · Clock · Notifications · UserMenu
// ─────────────────────────────────────────────────────────────────────────────

import { Search } from 'lucide-react'
import { useSystemStatus } from '@/hooks'
import type { CommandSectionContext } from '@/types'
import { SystemStatus } from './SystemStatus'
import { Clock } from './Clock'
import { NotificationsButton } from './NotificationsButton'
import { UserMenu } from './UserMenu'

export function CommandHeader({ context }: { context: CommandSectionContext }) {
  const { status } = useSystemStatus()

  return (
    <header className="h-16 flex-shrink-0 flex items-center justify-between gap-4 bg-ssb-navy border-b border-ssb-border px-4 z-20">
      {/* Left: operational section context */}
      <div className="flex items-center gap-4 min-w-0">
        <div className="flex flex-col justify-center min-w-0 leading-tight">
          <span className="truncate font-mono text-sm font-semibold tracking-[0.18em] text-ssb-white uppercase">
            {context.section}
          </span>
          <span className="truncate text-[11px] text-ssb-text-muted tracking-wide">
            Border Surveillance Operations
          </span>
        </div>
      </div>

      {/* Center: reserved command-search space (Phase 2) */}
      <div className="hidden lg:flex items-center gap-2 rounded-md border border-ssb-border bg-ssb-navy-deep/60 px-3 h-9">
        <Search size={14} className="text-ssb-text-muted" aria-hidden />
        <span className="text-[10px] font-mono tracking-widest text-ssb-text-muted">CAMERAS · TRACKS · INCIDENTS</span>
        <span className="rounded border border-ssb-border px-1 py-px text-[8px] font-semibold tracking-widest text-ssb-text-muted/80">
          PHASE 2
        </span>
      </div>

      {/* Right: system state + clock + notifications + profile */}
      <div className="flex items-center gap-3">
        {status && (
          <SystemStatus state={status.state} label={status.label} detail={status.detail} />
        )}
        <span className="h-7 w-px bg-ssb-border" aria-hidden />
        <Clock />
        <NotificationsButton />
        <UserMenu />
      </div>
    </header>
  )
}