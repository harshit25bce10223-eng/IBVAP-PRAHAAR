// ─────────────────────────────────────────────────────────────────────────────
// UserMenu — officer profile control (spec §10).
//
// Follows the existing authenticated-user store (useAuth); no invented auth
// behaviour. Only actions that already exist are wired (Sign Out); the rest
// render as non-navigating rows until their workflows land.
// ─────────────────────────────────────────────────────────────────────────────

import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronDown, LogOut, ShieldCheck, Settings, User } from 'lucide-react'
import { useAuth } from '@/hooks'
import { ROLE_LABELS } from '@/types'
import { Badge } from '@/components/ui'

function initialsOf(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map(part => part.charAt(0).toUpperCase())
    .join('')
}

export function UserMenu() {
  const { user, logout, hasFullSectorAccess } = useAuth()
  const navigate = useNavigate()
  const [open, setOpen] = useState(false)
  const buttonRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!open) return
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setOpen(false)
        buttonRef.current?.focus()
      }
    }
    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [open])

  if (!user) return null

  const handleLogout = async () => {
    await logout()
    navigate('/login', { replace: true })
  }

  return (
    <div className="relative">
      <button
        ref={buttonRef}
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
        aria-haspopup="true"
        aria-label={`Account menu, ${user.displayName}, ${ROLE_LABELS[user.role]}`}
        className="flex items-center gap-2.5 rounded-md border border-ssb-border bg-ssb-navy-deep/60 p-1.5 pl-2 hover:bg-ssb-white/5 transition-colors text-left"
      >
        <span className="flex h-6 w-6 flex-shrink-0 items-center justify-center rounded-full bg-ssb-green text-ssb-white text-[10px] font-bold">
          {initialsOf(user.displayName)}
        </span>
        <span className="hidden md:block min-w-0">
          <span className="block truncate text-xs font-medium text-ssb-white leading-tight">
            {user.displayName}
          </span>
          <span className="block truncate text-[10px] font-mono text-ssb-green-bright uppercase leading-none mt-0.5">
            {ROLE_LABELS[user.role]}
          </span>
        </span>
        <ChevronDown size={14} className="text-ssb-text-muted ml-0.5" aria-hidden />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-30" onClick={() => setOpen(false)} aria-hidden />
          <div
            role="menu"
            aria-label="Account menu"
            className="absolute right-0 top-11 z-40 w-64 rounded-lg border border-ssb-border bg-ssb-navy-raised p-2 shadow-2xl"
          >
            <div className="border-b border-ssb-border pb-2.5 mb-1.5 px-2 pt-1">
              <p className="text-xs font-semibold text-ssb-text">{user.displayName}</p>
              <p className="text-[11px] font-mono text-ssb-text-muted truncate">{user.email}</p>
              <div className="flex items-center gap-1.5 mt-2">
                <Badge variant={hasFullSectorAccess ? 'safe' : 'info'} size="sm">
                  {hasFullSectorAccess ? 'Full Sector View' : user.assignedZone?.name || 'Assigned Zone'}
                </Badge>
                {user.badge && (
                  <Badge variant="default" size="sm">
                    {user.badge}
                  </Badge>
                )}
              </div>
            </div>

            <div className="space-y-0.5">
              <a
                role="menuitem"
                aria-disabled="true"
                title="Available in a later phase"
                className="flex cursor-not-allowed items-center gap-2 rounded-md px-2.5 py-1.5 text-xs text-ssb-text-muted opacity-60"
              >
                <User size={14} aria-hidden /> Profile
                <span className="ml-auto text-[9px] font-mono uppercase tracking-wider">Soon</span>
              </a>
              <a
                role="menuitem"
                aria-disabled="true"
                title="Available in a later phase"
                className="flex cursor-not-allowed items-center gap-2 rounded-md px-2.5 py-1.5 text-xs text-ssb-text-muted opacity-60"
              >
                <Settings size={14} aria-hidden /> System Preferences
                <span className="ml-auto text-[9px] font-mono uppercase tracking-wider">Soon</span>
              </a>
              <a
                role="menuitem"
                aria-disabled="true"
                title="Available in a later phase"
                className="flex cursor-not-allowed items-center gap-2 rounded-md px-2.5 py-1.5 text-xs text-ssb-text-muted opacity-60"
              >
                <ShieldCheck size={14} aria-hidden /> Security
                <span className="ml-auto text-[9px] font-mono uppercase tracking-wider">Soon</span>
              </a>
            </div>

            <div className="border-t border-ssb-border pt-1.5 mt-1.5">
              <button
                role="menuitem"
                onClick={handleLogout}
                className="flex w-full items-center gap-2 rounded-md px-2.5 py-1.5 text-xs font-medium text-ssb-red-bright hover:bg-ssb-red/10 transition-colors"
              >
                <LogOut size={14} aria-hidden /> Sign Out
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}