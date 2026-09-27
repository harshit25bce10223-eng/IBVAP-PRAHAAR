// ─────────────────────────────────────────────────────────────────────────────
// Sidebar — प्रहार command navigation
//
// Deep Navy structural surface, Deep Security Green active state. Only routes
// that exist are clickable; unimplemented modules render disabled ("SOON").
// ─────────────────────────────────────────────────────────────────────────────

import { clsx } from 'clsx'
import { NavLink } from 'react-router-dom'
import { ChevronLeft, ChevronRight } from 'lucide-react'
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
        'bg-ssb-navy border-r border-ssb-border',
        'transition-all duration-300 ease-in-out',
        sidebarCollapsed ? 'w-[60px]' : 'w-[230px]'
      )}
      aria-label="Primary navigation"
    >
      {/* Branding — official प्रहार logo */}
      <div className={clsx(
        'flex items-center border-b border-ssb-border h-16 flex-shrink-0',
        sidebarCollapsed ? 'justify-center px-0' : 'px-4 gap-3'
      )}>
        <img
          src={prahaarLogo}
          alt="प्रहार — Intelligent Border Surveillance"
          className={clsx(
            'flex-shrink-0 object-contain',
            sidebarCollapsed ? 'h-8 w-8' : 'h-10 w-auto'
          )}
        />
        {!sidebarCollapsed && (
          <div className="min-w-0 leading-tight">
            <span className="block text-[8px] font-semibold tracking-[0.2em] text-ssb-green-bright uppercase">
              Intelligent Border Surveillance
            </span>
            <span className="block text-[7.5px] font-medium tracking-[0.16em] text-ssb-text-muted/70 uppercase">
              SSB Command &amp; Control
            </span>
          </div>
        )}
      </div>

      {/* Zone indicator */}
      {!sidebarCollapsed && (
        <div className="px-4 py-2.5 border-b border-ssb-border flex-shrink-0">
          {hasFullSectorAccess ? (
            <div className="flex items-center gap-1.5 text-[11px]">
              <span className="h-1.5 w-1.5 rounded-full bg-ssb-green-bright" aria-hidden />
              <span className="text-ssb-text-muted font-medium tracking-wide">Full Sector View</span>
            </div>
          ) : (
            <div className="text-[11px] text-ssb-text-muted">
              <span className="text-ssb-text font-medium block">{user.assignedZone?.code}</span>
              <span className="truncate block">{user.assignedZone?.name}</span>
            </div>
          )}
        </div>
      )}

      {/* Nav items */}
      <nav className="flex-1 overflow-y-auto py-2 space-y-0.5">
        {Array.from(grouped.entries()).map(([section, items]) => (
          <div key={section}>
            {!sidebarCollapsed && (
              <div className="px-4 pt-3.5 pb-1">
                <span className="text-[9px] font-semibold uppercase tracking-[0.16em] text-ssb-text-muted/70">
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
        <div className="border-t border-ssb-border px-3 py-3 flex-shrink-0">
          <DeviceCertStatus status={user.deviceCert.status} />
        </div>
      )}

      {/* Collapse toggle */}
      <button
        onClick={toggleSidebar}
        className={clsx(
          'border-t border-ssb-border flex items-center justify-center py-3 flex-shrink-0',
          'text-ssb-text-muted hover:text-ssb-white hover:bg-ssb-white/5 transition-colors'
        )}
        title={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        aria-label={sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
      >
        {sidebarCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
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
      title={collapsed ? item.label : undefined}
      className={({ isActive }) =>
        clsx(
          'flex items-center mx-2 rounded-md transition-colors duration-150 group',
          collapsed ? 'justify-center p-2.5' : 'gap-3 px-3 py-2',
          item.comingSoon && 'pointer-events-none opacity-40',
          isActive
            ? 'bg-ssb-green text-ssb-white border border-ssb-green-bright/40'
            : 'text-ssb-text-muted hover:text-ssb-white hover:bg-ssb-white/5 border border-transparent'
        )
      }
      aria-disabled={item.comingSoon || undefined}
    >
      <Icon size={16} className="flex-shrink-0" aria-hidden />
      {!collapsed && (
        <>
          <span className="flex-1 text-xs font-medium truncate">{item.label}</span>
          {item.badge && (
            <Badge variant={item.badgeVariant ?? 'default'} size="sm">
              {item.badge}
            </Badge>
          )}
          {item.comingSoon && (
            <span className="text-[9px] text-ssb-text-muted/70 font-mono">SOON</span>
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
    <div className="flex items-center gap-2 rounded-md bg-ssb-navy-deep/60 px-2.5 py-1.5 border border-ssb-border/60">
      <StatusIndicator status={statusMap[status]} />
      <span className={clsx('text-[11px] font-medium truncate', cfg.className)}>
        {cfg.label}
      </span>
    </div>
  )
}