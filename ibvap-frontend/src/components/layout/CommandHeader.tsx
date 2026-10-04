// ─────────────────────────────────────────────────────────────────────────────
// CommandHeader — प्रहार top command strip (spec §7).
//
// Left:   PRAHAAR logo + brand + current operational section descriptor
// Center: interactive global command-search bar (Ctrl+K shortcut)
// Right:  SystemStatus · Clock · Notifications · UserMenu
// ─────────────────────────────────────────────────────────────────────────────

import { useState, useEffect } from 'react'
import { useLocation } from 'react-router-dom'
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
  const { pathname } = useLocation()
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
      {/* Animated top accent gradient strip */}
      <div className="h-[2px] flex-shrink-0 bg-gradient-to-r from-transparent via-brand/50 to-transparent" aria-hidden />

      <header className="h-14 flex-shrink-0 flex items-center justify-between gap-4 bg-gradient-to-b from-[#0a1826] to-[#071118] border-b border-white/[0.06] px-4 z-20 shadow-[0_1px_12px_rgba(0,0,0,0.6)]">
        {/* Left: PRAHAAR brand + operational section context */}
        <div className="flex items-center gap-3 min-w-0">
          {/* Logo with subtle glow ring */}
          <div className="flex-shrink-0 h-9 w-9 rounded-lg overflow-hidden border border-brand/40 shadow-[0_0_10px_rgba(194,203,153,0.15)] ring-1 ring-brand/10">
            <img src={prahaarLogo} alt="PRAHAAR" className="h-full w-full object-cover" />
          </div>

          {/* Thin vertical separator */}
          <span className="h-8 w-px bg-white/10" aria-hidden />

          {/* Brand + section */}
          <div className="flex flex-col justify-center min-w-0 leading-tight">
            <div className="flex items-center gap-2">
              <span className="font-mono text-[13px] font-bold tracking-[0.24em] text-brand uppercase drop-shadow-[0_0_8px_rgba(194,203,153,0.4)]">
                PRAHAAR
              </span>
              <span className="hidden sm:inline text-[9px] font-mono tracking-[0.15em] text-brand/50 border border-brand/20 px-1.5 py-px rounded bg-brand/5">
                प्रहार
              </span>
            </div>
            <span className="truncate font-mono text-[10px] text-white/30 tracking-[0.16em] uppercase">
              {context.section}
            </span>
          </div>
        </div>

        {/* Center: interactive command-search bar */}
        <button
          type="button"
          onClick={() => setSearchOpen(true)}
          className="hidden md:flex items-center gap-2.5 rounded-lg border border-white/10 hover:border-cyan-400/40 bg-white/[0.03] hover:bg-white/[0.06] px-3.5 h-9 transition-all cursor-pointer group shadow-inner hover:shadow-[0_0_12px_rgba(34,211,238,0.06)]"
          title="Search cameras, tracks, incidents, or modules (Ctrl + K)"
        >
          <Search size={14} className="text-white/40 group-hover:text-cyan-400 transition-colors" aria-hidden />
          <span className="text-[11px] font-mono tracking-[0.12em] text-white/30 group-hover:text-white/60 transition-colors">
            SEARCH CAMERAS · TRACKS · INCIDENTS
          </span>
          <div className="flex items-center gap-0.5 ml-2">
            <span className="rounded border border-white/10 group-hover:border-cyan-400/30 px-1.5 py-0.5 text-[9px] font-mono font-semibold tracking-widest text-white/25 group-hover:text-cyan-400/70 bg-black/30 transition-all">
              CTRL
            </span>
            <span className="text-[9px] text-white/20 group-hover:text-cyan-400/50 font-mono">+</span>
            <span className="rounded border border-white/10 group-hover:border-cyan-400/30 px-1.5 py-0.5 text-[9px] font-mono font-semibold tracking-widest text-white/25 group-hover:text-cyan-400/70 bg-black/30 transition-all">
              K
            </span>
          </div>
        </button>

        {/* Right: system state + clock + notifications + profile */}
        <div className="flex items-center gap-3">
          {pathname === '/demo' ? (
            <span className="rounded-md border border-brand/40 bg-brand/10 px-2.5 py-1 text-[11px] font-semibold text-brand whitespace-nowrap">
              Demo · Simulated data
            </span>
          ) : status && (
            <SystemStatus state={status.state} label={status.label} detail={status.detail} />
          )}
          <span className="h-7 w-px bg-white/[0.08]" aria-hidden />
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
