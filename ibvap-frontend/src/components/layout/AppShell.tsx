// ─────────────────────────────────────────────────────────────────────────────
// AppShell — प्रहार command shell (spec §1–§15, §20, §21).
//
//   ┌──────────────────────────────────────────────┐
//   │                CommandHeader                │   full width, top
//   ├────────┬─────────────────────────────────────┤
//   │Sidebar │ BreadcrumbBar                       │
//   │        │ main content (future KPI / GIS /…)  │
//   └────────┴─────────────────────────────────────┘
//
// Flex-based (no fixed positioning/offsets) so upcoming dashboard modules can
// be inserted without restructuring the shell. Full viewport, no horizontal
// overflow, single scroll surface per region.
// ─────────────────────────────────────────────────────────────────────────────

import { useEffect } from 'react'
import type { ReactNode } from 'react'
import { useLocation } from 'react-router-dom'
import { ToastContainer } from '@/components/ui'
import { useSystemStatus } from '@/hooks'
import { Sidebar } from './Sidebar'
import { CommandHeader } from './CommandHeader'
import { BreadcrumbBar } from './BreadcrumbBar'
import { resolveNavContext } from './navConfig'

export function AppShell({ children }: { children: ReactNode }) {
  const location = useLocation()
  const { refetch } = useSystemStatus()

  useEffect(() => {
    refetch().catch(() => {})
  }, [refetch])

  const context = resolveNavContext(location.pathname)

  return (
    <div className="h-screen w-screen flex flex-col overflow-hidden bg-ssb-navy-deep text-ssb-text">
      <CommandHeader context={context} />
      <div className="flex flex-1 min-h-0 overflow-hidden">
        <Sidebar />
        <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
          <BreadcrumbBar context={context} />
          <main className="flex min-w-0 flex-1 flex-col overflow-y-auto">
            {children}
          </main>
        </div>
      </div>
      <ToastContainer />
    </div>
  )
}
