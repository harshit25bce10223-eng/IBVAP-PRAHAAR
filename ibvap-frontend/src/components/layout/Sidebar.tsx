// ─────────────────────────────────────────────────────────────────────────────
// Sidebar — प्रहार command navigation
//
// Deep Navy structural surface, Deep Security Green active state. Only routes
// that exist are clickable; unimplemented modules render disabled ("SOON").
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'
import { NavLink } from 'react-router-dom'
import { ChevronLeft, ChevronRight, Shield } from 'lucide-react'
import prahaarLogo from '@/assets/branding/prahaar-logo.jpg'
import { useAuth } from '@/hooks'
import { useUIStore } from '@/store'
import { Badge, StatusIndicator } from '@/components/ui'
import { filterNavItems, groupNavItems } from './navConfig'
import type { NavItem } from './navConfig'

export function Sidebar() {
  const { user, hasFullSectorAccess } = useAuth()
  const { sidebarCollapsed, toggleSidebar } = useUIStore()

  if (!user) return null

  const navItems = filterNavItems(user.role)
  const grouped  = groupNavItems(navItems)

  return (
    <aside
      className={clsx(
        'flex flex-col h-full flex-shrink-0',
        'bg-gradient-to-b from-[#0a1826] to-[#07111a] border-r border-white/[0.06]',
        'transition-all duration-300 ease-in-out',
        sidebarCollapsed ? 'w-[60px]' : 'w-[230px] xl:w-[260px]'
      )}
      aria-label="Primary navigation"
    >
      {/* Branding — official प्रहार logo */}
      <div className={clsx(
        'flex items-center border-b border-white/[0.06] h-14 flex-shrink-0',
        sidebarCollapsed ? 'justify-center px-0' : 'px-4 gap-3'
      )}>
        <div className={clsx(
          'flex-shrink-0 rounded-lg overflow-hidden border border-brand/40 shadow-[0_0_12px_rgba(194,203,153,0.12)]',
          sidebarCollapsed ? 'h-8 w-8' : 'h-9 w-9'
        )}>
          <img
            src={prahaarLogo}
            alt="प्रहार — Intelligent Border Surveillance"
            className="h-full w-full object-cover"
          />
        </div>
        {!sidebarCollapsed && (
          <div className="min-w-0 leading-tight">
            <span className="block text-[8px] font-bold tracking-[0.22em] text-brand/80 uppercase">
              Intelligent Border Surveillance
            </span>
            <span className="block text-[7px] font-medium tracking-[0.18em] text-white/25 uppercase">
              SSB Command &amp; Control
            </span>
          </div>
        )}
      </div>

      {/* Zone indicator — compact sector badge */}
      {!sidebarCollapsed && (
        <div className="px-3 py-2 border-b border-white/[0.05] flex-shrink-0">
          {hasFullSectorAccess ? (
            <div className="flex items-center gap-2 rounded-md bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1.5">
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_4px_rgba(52,211,153,0.8)]" aria-hidden />
              <span className="text-[10px] font-mono font-semibold tracking-[0.14em] text-emerald-400 uppercase">Full Sector</span>
            </div>
          ) : (
            <div className="flex items-center gap-2 rounded-md bg-cyan-500/10 border border-cyan-500/20 px-2.5 py-1.5">
              <Shield size={10} className="text-cyan-400 flex-shrink-0" aria-hidden />
              <div className="min-w-0">
                <span className="text-[10px] font-mono font-bold tracking-[0.12em] text-cyan-300 block truncate">{user.assignedZone?.code}</span>
                <span className="text-[9px] font-mono text-white/30 block truncate">{user.assignedZone?.name}</span>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Nav items */}
      <nav className="flex-1 overflow-y-auto py-2 space-y-0.5">
        {Array.from(grouped.entries()).map(([section, items]) => (
          <div key={section}>
            {!sidebarCollapsed && (
              <div className="px-4 pt-4 pb-1">
                <span className="text-[9px] font-bold uppercase tracking-[0.2em] text-white/25">
                  {section}
                </span>
              </div>
            )}
            {items.map(item => (
              <SidebarItem key={item.id} item={item} collapsed={sidebarCollapsed} />
            ))}
          </div>
        ))}
      </nav>

      {/* Device cert status */}
      {!sidebarCollapsed && user.deviceCert && (
        <div className="border-t border-white/[0.06] px-3 py-3 flex-shrink-0">
          <DeviceCertStatus status={user.deviceCert.status} />
        </div>
      )}

      {/* Collapse toggle */}
      <button
        onClick={toggleSidebar}
        className={clsx(
          'border-t border-white/[0.06] flex items-center justify-center py-3 flex-shrink-0',
          'text-white/20 hover:text-white/60 hover:bg-white/[0.04] transition-colors'
        )}
        title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {sidebarCollapsed ? <ChevronRight size={14} /> : <ChevronLeft size={14} />}
      </button>
    </aside>
  )
}

// ─── Sidebar nav item ────────────────────────────────────────────────────────

function SidebarItem({ item, collapsed }: { item: NavItem; collapsed: boolean }) {
  const Icon = item.icon

  return (
    <NavLink
      to={item.href}
      title={item.label}
      className={({ isActive }) =>
        clsx(
          'flex items-center mx-2 rounded-md transition-all duration-150 group',
          collapsed ? 'justify-center p-2.5' : 'gap-2.5 px-3 py-2.5',
          item.comingSoon && 'pointer-events-none opacity-40',
          isActive
            ? 'bg-cyan-500/10 text-cyan-300 border-l-2 border-cyan-400 shadow-[inset_0_0_12px_rgba(34,211,238,0.05)] pl-[10px]'
            : 'text-white/35 hover:text-white/80 hover:bg-white/[0.05] border border-transparent'
        )
      }
      aria-disabled={item.comingSoon || undefined}
    >
      <Icon
        size={15}
        className={clsx(
          'flex-shrink-0 transition-colors',
        )}
        aria-hidden
      />
      {!collapsed && (
        <>
          <span className="min-w-0 flex-1 text-[12px] leading-snug font-medium tracking-wide whitespace-normal break-words">{item.label}</span>
          {item.badge && !item.label.startsWith(item.badge) && (
            <Badge variant={item.badgeVariant ?? 'default'} size="sm">
              {item.badge}
            </Badge>
          )}
          {item.comingSoon && (
            <span className="text-[8px] text-white/20 font-mono tracking-widest">SOON</span>
          )}
        </>
      )}
    </NavLink>
  )
}

// ─── Device cert status pill ─────────────────────────────────────────────────

type CertStatus = 'valid' | 'expiring_soon' | 'expired' | 'revoked' | 'unknown'

function DeviceCertStatus({ status }: { status: CertStatus }) {
  const configs: Record<CertStatus, { label: string; className: string; pulse: boolean }> = {
    valid:         { label: 'Device Cert · Valid',      className: 'text-ssb-green-bright', pulse: false },
    expiring_soon: { label: 'Cert Expiring Soon',      className: 'text-ssb-amber-bright', pulse: true  },
    expired:       { label: 'Cert Expired',            className: 'text-ssb-red-bright',   pulse: true  },
    revoked:       { label: 'Cert Revoked',            className: 'text-ssb-red-bright',   pulse: true  },
    unknown:       { label: 'Cert Unknown',            className: 'text-ssb-text-muted',   pulse: false },
  }

  const cfg = configs[status]
  const statusMap: Record<CertStatus, 'online' | 'offline' | 'alert' | 'degraded' | 'maintenance' | 'idle'> = {
    valid:         'online',
    expiring_soon: 'degraded',
    expired:       'alert',
    revoked:       'alert',
    unknown:       'offline',
  }

  return (
    <div className="flex items-center gap-2 rounded-md bg-black/30 px-2.5 py-1.5 border border-white/[0.07]">
      <StatusIndicator status={statusMap[status]} />
      <span className={clsx('text-[10px] font-mono font-medium tracking-wide truncate', cfg.className)}>
        {cfg.label}
      </span>
    </div>
  )
}
