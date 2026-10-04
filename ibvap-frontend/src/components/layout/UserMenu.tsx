// ─────────────────────────────────────────────────────────────────────────────
// UserMenu — officer profile control (spec A§10).
// ─────────────────────────────────────────────────────────────────────────────

import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { ChevronDown, LogOut, ShieldCheck, Settings, User, MapPin, BadgeCheck } from 'lucide-react'
import { useAuth } from '@/hooks'
import { ROLE_LABELS } from '@/types'

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
      {/* Trigger button */}
      <button
        ref={buttonRef}
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
        aria-haspopup="true"
        aria-label={`Account menu, ${user.displayName}, ${ROLE_LABELS[user.role]}`}
        className="flex items-center gap-2 rounded-lg border border-white/10 bg-white/5 hover:bg-white/10 px-2.5 py-1.5 transition-all duration-150 text-left group"
      >
        {/* Avatar */}
        <span className="flex h-7 w-7 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-emerald-600 to-emerald-800 text-white text-[11px] font-bold shadow-[0_0_10px_rgba(52,211,153,0.2)] border border-emerald-500/30">
          {initialsOf(user.displayName)}
        </span>
        <span className="hidden md:block min-w-0">
          <span className="block truncate text-[12px] font-semibold text-white/90 leading-tight">
            {user.displayName}
          </span>
          <span className="block truncate text-[9px] font-mono text-emerald-400/80 uppercase tracking-wider leading-none mt-0.5">
            {ROLE_LABELS[user.role]}
          </span>
        </span>
        <ChevronDown
          size={13}
          className={`text-white/30 transition-transform duration-200 ${open ? 'rotate-180' : ''}`}
          aria-hidden
        />
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-30" onClick={() => setOpen(false)} aria-hidden />
          <div
            role="menu"
            aria-label="Account menu"
            className="absolute right-0 top-12 z-40 w-72 rounded-xl border border-white/10 bg-[#0a1a14] shadow-[0_20px_60px_rgba(0,0,0,0.8),0_0_0_1px_rgba(255,255,255,0.04)] overflow-hidden"
            style={{ backdropFilter: 'blur(20px)' }}
          >
            {/* Header gradient strip */}
            <div className="h-0.5 w-full bg-gradient-to-r from-transparent via-emerald-500/40 to-transparent" />

            {/* User identity */}
            <div className="px-4 pt-4 pb-3 border-b border-white/[0.06]">
              <div className="flex items-center gap-3">
                <span className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-emerald-600 to-emerald-900 text-white text-sm font-bold shadow-[0_0_16px_rgba(52,211,153,0.25)] border border-emerald-500/30">
                  {initialsOf(user.displayName)}
                </span>
                <div className="min-w-0">
                  <p className="text-sm font-semibold text-white/90">{user.displayName}</p>
                  <p className="text-[11px] font-mono text-white/35 truncate">{user.email}</p>
                </div>
                <BadgeCheck size={16} className="text-emerald-400 flex-shrink-0 ml-auto" />
              </div>

              {/* Zone + badge row */}
              <div className="flex items-center gap-2 mt-3">
                <div className="flex items-center gap-1.5 rounded-md bg-cyan-500/10 border border-cyan-500/20 px-2.5 py-1 flex-1 min-w-0">
                  <MapPin size={10} className="text-cyan-400 flex-shrink-0" />
                  <span className="text-[10px] font-mono text-cyan-300 truncate">
                    {hasFullSectorAccess ? 'Full Sector View' : (user.assignedZone?.name || 'Assigned Zone')}
                  </span>
                </div>
                {user.badge && (
                  <div className="rounded-md bg-white/5 border border-white/10 px-2.5 py-1 flex-shrink-0">
                    <span className="text-[10px] font-mono text-white/50">{user.badge}</span>
                  </div>
                )}
              </div>
            </div>

            {/* Menu items */}
            <div className="py-1.5 px-1.5 space-y-0.5">
              {[
                { icon: User, label: 'Profile' },
                { icon: Settings, label: 'System Preferences' },
                { icon: ShieldCheck, label: 'Security' },
              ].map(({ icon: Icon, label }) => (
                <a
                  key={label}
                  role="menuitem"
                  aria-disabled="true"
                  title="Available in a later phase"
                  className="flex cursor-not-allowed items-center gap-2.5 rounded-lg px-3 py-2 text-xs text-white/30 hover:bg-white/5 transition-colors"
                >
                  <Icon size={13} aria-hidden className="flex-shrink-0" />
                  <span>{label}</span>
                  <span className="ml-auto text-[8px] font-mono uppercase tracking-widest text-white/20 border border-white/10 px-1.5 py-0.5 rounded">
                    SOON
                  </span>
                </a>
              ))}
            </div>

            {/* Sign out */}
            <div className="border-t border-white/[0.06] p-1.5">
              <button
                role="menuitem"
                onClick={handleLogout}
                className="flex w-full items-center gap-2.5 rounded-lg px-3 py-2 text-xs font-semibold text-red-400 hover:bg-red-500/10 hover:text-red-300 transition-all duration-150"
              >
                <LogOut size={13} aria-hidden />
                Sign Out
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  )
}