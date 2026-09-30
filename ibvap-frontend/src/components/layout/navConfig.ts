// ─────────────────────────────────────────────────────────────────────────────
// Navigation config — प्रहार command-center sidebar (role-aware)
//
// Sections follow the SSB command console structure. Only routes backed by a
// real page are wired; unimplemented modules render disabled ("SOON") using
// the existing comingSoon convention so no navigation link is ever broken.
// ─────────────────────────────────────────────────────────────────────────────

import {
  LayoutDashboard,
  Video,
  Monitor,
  Crosshair,
  AlertTriangle,
  Map as MapIcon,
  FileSearch,
  Waypoints,
  RadioTower,
  Activity,
  BarChart3,
  Radar,
  ShieldCheck,
  BookOpen,
  Settings,
  Navigation,
  Car,
  type LucideIcon,
} from 'lucide-react'
import type { CommandSectionContext, Role } from '@/types'

export interface NavItem {
  id: string
  label: string
  href: string
  icon: LucideIcon
  badge?: string        // e.g. "LIVE"
  badgeVariant?: 'critical' | 'warning' | 'info' | 'safe' | 'cyan'
  minRole?: Role        // minimum role required to see this item
  section?: string      // group heading
  comingSoon?: boolean
}

export const NAV_ITEMS: NavItem[] = [
  {
    id: 'guided-demo', label: 'Start here · Guided Demo', href: '/demo',
    icon: BookOpen, badge: 'DEMO', badgeVariant: 'cyan', section: 'GET STARTED',
  },
  // ── COMMAND CENTER ────────────────────────────────────────────────────────
  {
    id: 'dashboard', label: 'Command Dashboard', href: '/dashboard',
    icon: LayoutDashboard, section: 'COMMAND CENTER',
  },

  // ── LIVE SURVEILLANCE ─────────────────────────────────────────────────────
  {
    id: 'single-camera', label: 'PARAKH · Virtual Fence', href: '/virtual-fence',
    icon: Video, badge: 'PARAKH', badgeVariant: 'safe', section: 'LIVE SURVEILLANCE',
  },
  {
    id: 'wall', label: 'Live Camera Wall', href: '/wall',
    icon: Monitor, section: 'LIVE SURVEILLANCE',
  },

  // ── TRACKING ──────────────────────────────────────────────────────────────
  {
    id: 'tracking', label: 'Tracking · TRK-1042', href: '/track/TRK-1042',
    icon: Crosshair, section: 'TRACKING',
  },

  // ── INCIDENTS ─────────────────────────────────────────────────────────────
  {
    id: 'incident-intel', label: 'SUTRA · Incident Intel', href: '/incident-intel',
    icon: Waypoints, badge: 'SUTRA', badgeVariant: 'critical', section: 'INCIDENTS',
  },
  {
    id: 'events', label: 'Incident / Event Log', href: '/events',
    icon: AlertTriangle, section: 'INCIDENTS',
  },

  // ── GIS / DIGITAL TWIN ────────────────────────────────────────────────────
  {
    id: 'map', label: 'GIS / Digital Twin', href: '/gis',
    icon: MapIcon, section: 'GIS / DIGITAL TWIN',
  },

  // ── FIELD OPERATIONS ──────────────────────────────────────────────────────
  {
    id: 'field', label: 'SAKSHAM · Field Resilience', href: '/field',
    icon: RadioTower, badge: 'SAKSHAM', badgeVariant: 'info', section: 'FIELD OPERATIONS',
  },

  // ── ROUTE ANALYSIS ─────────────────────────────────────────────────────────
  {
    id: 'route-analysis', label: 'MARGDARSHAN · Route Intel', href: '/route-analysis',
    icon: Navigation, badge: 'MARGDARSHAN', badgeVariant: 'info', section: 'ROUTE ANALYSIS',
  },

  // ── VEHICLE INTELLIGENCE ──────────────────────────────────────────────────
  {
    id: 'anpr', label: 'ANPR / Vehicle Intel', href: '/anpr',
    icon: Car, badge: 'C7', badgeVariant: 'cyan', section: 'VEHICLE INTELLIGENCE',
  },

  // ── EVIDENCE ──────────────────────────────────────────────────────────────
  {
    id: 'evidence', label: 'PRAMAAN · Evidence Ledger', href: '/evidence',
    icon: FileSearch, badge: 'PRAMAAN', badgeVariant: 'cyan', section: 'EVIDENCE',
  },

  // ── CAMERA HEALTH ─────────────────────────────────────────────────────────
  {
    id: 'health', label: 'SAKSHAM · Camera Health', href: '/health',
    icon: Activity, badge: 'SAKSHAM', badgeVariant: 'cyan', section: 'CAMERA HEALTH',
  },

  // ── ANALYTICS ─────────────────────────────────────────────────────────────
  // AI Detections is the C5 observation workspace — a read-only detector
  // output log, comparable to the C4 event log, so it is not role-gated.
  {
    id: 'detections', label: 'Detection Intelligence', href: '/detections',
    icon: Radar, badge: 'C5', badgeVariant: 'cyan', section: 'ANALYTICS',
  },
  {
    id: 'analytics', label: 'AI Performance Analytics', href: '/analytics',
    icon: BarChart3, section: 'ANALYTICS', minRole: 'commander', comingSoon: true,
  },

  // ── SYSTEM INTEGRATION ────────────────────────────────────────────────────
  {
    id: 'audit', label: 'Audit Trail', href: '/audit',
    icon: BookOpen, section: 'SYSTEM INTEGRATION', minRole: 'auditor', comingSoon: true,
  },
  {
    id: 'blockchain', label: 'Chain of Custody', href: '/blockchain',
    icon: ShieldCheck, section: 'SYSTEM INTEGRATION', minRole: 'auditor', comingSoon: true,
  },
  {
    id: 'settings', label: 'System Settings', href: '/admin/settings',
    icon: Settings, section: 'SYSTEM INTEGRATION', minRole: 'admin', comingSoon: true,
  },
]

// Role hierarchy for comparisons
const ROLE_LEVEL: Record<Role, number> = {
  officer: 1, commander: 2, auditor: 2, admin: 3,
}

export function filterNavItems(role: Role): NavItem[] {
  return NAV_ITEMS.filter(item => {
    if (!item.minRole) return true
    return ROLE_LEVEL[role] >= ROLE_LEVEL[item.minRole]
  })
}

export function groupNavItems(items: NavItem[]): Map<string, NavItem[]> {
  const groups = new Map<string, NavItem[]>()
  for (const item of items) {
    const section = item.section ?? 'OTHER'
    if (!groups.has(section)) groups.set(section, [])
    groups.get(section)!.push(item)
  }
  return groups
}

// ─── Route → command context (header + breadcrumb) ──────────────────────────

/**
 * Resolve the current pathname to an operational section context. Pure
 * function (no React) so it can be unit-tested and reused by the header,
 * breadcrumb and any future nested page.
 */
export function resolveNavContext(pathname: string): CommandSectionContext {
  if (pathname === '/demo') {
    return { section: 'GET STARTED', label: 'PRAHAAR Guided Demo', sub: '4 Scenarios · 10 Capabilities' }
  }
  if (pathname === '/virtual-fence') {
    return { section: 'LIVE SURVEILLANCE', label: 'PARAKH · Virtual Fence', sub: 'Virtual Fence & Risk Engine' }
  }
  if (pathname.startsWith('/camera/')) {
    const cameraId = pathname.split('/')[2]?.toUpperCase() ?? 'CAM'
    return { section: 'LIVE SURVEILLANCE', label: 'Live Camera Feed', sub: cameraId }
  }
  if (pathname === '/wall') {
    return { section: 'LIVE SURVEILLANCE', label: 'Live Camera Wall', sub: 'All Cameras' }
  }
  if (pathname.startsWith('/track/')) {
    const trackId = pathname.split('/')[2]?.toUpperCase() ?? 'TRK'
    return { section: 'TRACKING', label: 'Tracking Viewer', sub: trackId }
  }
  if (pathname.startsWith('/incident/')) {
    const ref = pathname.split('/')[2]?.toUpperCase() ?? 'INC'
    return { section: 'INCIDENTS', label: 'Incident Detail', sub: ref }
  }
  if (pathname === '/events') {
    return { section: 'INCIDENTS', label: 'Incident / Event Log', sub: 'Operational Log' }
  }
  if (pathname === '/incident-intel') {
    return { section: 'INCIDENTS', label: 'Incident Intelligence', sub: 'INC-024 · Risk & Evidence' }
  }
  if (pathname === '/detections') {
    return { section: 'ANALYTICS', label: 'Detection Intelligence', sub: 'Fleet-Wide Detector Output' }
  }
  if (pathname === '/gis') {
    return { section: 'GIS / DIGITAL TWIN', label: 'GIS / Digital Twin', sub: 'Live Operational Map' }
  }
  if (pathname === '/field') {
    return { section: 'FIELD OPERATIONS', label: 'Field Intelligence & Resilience', sub: 'Human/Animal + Offline-First' }
  }
  if (pathname === '/route-analysis') {
    return { section: 'ROUTE ANALYSIS', label: 'GIS / Operational Route Analysis', sub: 'Risk-Aware Route Recommendation' }
  }
  if (pathname === '/anpr') {
    return { section: 'VEHICLE INTELLIGENCE', label: 'ANPR / Vehicle Intelligence', sub: 'Plate & Sighting Telemetry' }
  }
  if (pathname.startsWith('/vehicle/')) {
    const vehId = pathname.split('/')[2]?.toUpperCase() ?? 'VEHICLE'
    return { section: 'VEHICLE INTELLIGENCE', label: 'Vehicle Investigation', sub: vehId }
  }
  if (pathname.includes('/vehicles')) {
    const camId = pathname.split('/')[2]?.toUpperCase() ?? 'CAM'
    return { section: 'VEHICLE INTELLIGENCE', label: 'Camera Vehicle Feed', sub: camId }
  }
  if (pathname === '/health' || pathname === '/camera-health') {
    return { section: 'CAMERA HEALTH', label: 'Sensor Health & Fleet Coverage', sub: 'Surveillance Infrastructure Intelligence' }
  }
  if (pathname === '/evidence') {
    return { section: 'EVIDENCE', label: 'Evidence Ledger', sub: 'Chain of Custody' }
  }
  return { section: 'COMMAND CENTER', label: 'Command Dashboard', sub: 'Overview' }
}
