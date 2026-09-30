// ─────────────────────────────────────────────────────────────────────────────
// CommandHeader — प्रहार top command strip (spec §7).
//
// Left:   PRAHAAR logo + brand + current operational section descriptor
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
import prahaarLogo from '@/assets/branding/prahaar-logo.jpg'

export function CommandHeader({ context }: { context: CommandSectionContext }) {
  const { status } = useSystemStatus()

  return (
    <header className="h-16 flex-shrink-0 flex items-center justify-between gap-4 bg-ssb-navy border-b border-ssb-border px-4 z-20">
      {/* Left: PRAHAAR brand + operational section context */}
      <div className="flex items-center gap-3 min-w-0">
        {/* Logo */}
        <div className="flex-shrink-0 h-10 w-10 rounded-lg overflow-hidden border border-[#2FD5E0]/30 shadow-[0_0_8px_rgba(47,213,224,0.25)]">
          <img src={prahaarLogo} alt="PRAHAAR" className="h-full w-full object-cover" />
        </div>
        {/* Brand + section */}
        <div className="flex flex-col justify-center min-w-0 leading-tight">
          <div className="flex items-center gap-2">
            <span className="font-mono text-[13px] font-bold tracking-[0.22em] text-[#2FD5E0] uppercase">PRAHAAR</span>
            <span className="hidden sm:inline text-[9px] font-mono tracking-[0.15em] text-[#2FD5E0]/50 border border-[#2FD5E0]/20 px-1.5 py-px rounded">प्रहार</span>
          </div>
          <span className="truncate font-mono text-[11px] text-ssb-text-muted tracking-wide uppercase">
            {context.section}
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