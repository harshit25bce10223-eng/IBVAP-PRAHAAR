// ─────────────────────────────────────────────────────────────────────────────
// CommandHeader — प्रहार top command strip (spec §7).
//
// Left:   PRAHAAR logo + brand + current operational section descriptor
// Center: interactive global command-search bar (Ctrl+K shortcut)
// Right:  SystemStatus · Clock · Notifications · UserMenu
// ─────────────────────────────────────────────────────────────────────────────

import { useState, useEffect } from 'react'
import { Search } from 'lucide-react'
import { useSystemStatus } from '@/hooks'
import type { CommandSectionContext } from '@/types'
import { SystemStatus } from './SystemStatus'
import { Clock } from './Clock'
import { NotificationsButton } from './NotificationsButton'
import { UserMenu } from './UserMenu'
import { CommandSearchModal } from './CommandSearchModal'
import prahaarLogo from '@/assets/branding/prahaar-logo.jpg'

export function CommandHeader({ context }: { context: CommandSectionContext }) {
  const { status } = useSystemStatus()
  const [searchOpen, setSearchOpen] = useState(false)

  // Global Ctrl+K / Cmd+K or '/' shortcut to open command search
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault()
        setSearchOpen(prev => !prev)
      } else if (e.key === '/' && document.activeElement?.tagName !== 'INPUT' && document.activeElement?.tagName !== 'TEXTAREA') {
        e.preventDefault()
        setSearchOpen(true)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [])

  return (
    <>
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

        {/* Center: interactive command-search bar */}
        <button
          type="button"
          onClick={() => setSearchOpen(true)}
          className="hidden md:flex items-center gap-2.5 rounded-lg border border-ssb-border hover:border-[#2FD5E0]/50 bg-ssb-navy-deep/70 hover:bg-[#121c2a] px-3.5 h-9 transition-all cursor-pointer group shadow-inner"
          title="Search cameras, tracks, incidents, or modules (Ctrl + K)"
        >
          <Search size={14} className="text-[#2FD5E0] group-hover:scale-110 transition-transform" aria-hidden />
          <span className="text-[11px] font-mono tracking-wider text-slate-300 group-hover:text-white transition-colors">
            SEARCH CAMERAS · TRACKS · INCIDENTS
          </span>
          <div className="flex items-center gap-1 ml-2">
            <span className="rounded border border-ssb-border group-hover:border-[#2FD5E0]/40 px-1.5 py-0.5 text-[9px] font-mono font-semibold tracking-wider text-slate-400 group-hover:text-[#2FD5E0] bg-black/40">
              CTRL + K
            </span>
          </div>
        </button>

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

      {/* Global Command Search Modal */}
      <CommandSearchModal isOpen={searchOpen} onClose={() => setSearchOpen(false)} />
    </>
  )
}