// ─────────────────────────────────────────────────────────────────────────────
// BreadcrumbBar — slim context strip below the command header (spec §12).
//
// Orients the officer ("COMMAND CENTER / OVERVIEW") with minimal vertical
// cost and supports future nested pages.
// ─────────────────────────────────────────────────────────────────────────────

import { ChevronRight } from 'lucide-react'
import { useAuth } from '@/hooks'
import type { CommandSectionContext } from '@/types'

export function BreadcrumbBar({ context }: { context: CommandSectionContext }) {
  const { user, hasFullSectorAccess } = useAuth()

  return (
    <nav
      aria-label="Breadcrumb"
      className="h-9 flex-shrink-0 flex items-center justify-between gap-3 border-b border-ssb-border/60 bg-ssb-navy/80 px-4"
    >
      <div className="flex items-center gap-1.5 font-mono text-[10px] uppercase tracking-wider whitespace-nowrap overflow-hidden">
        <span lang="hi" className="text-ssb-text-muted">प्रहार</span>
        <ChevronRight size={11} className="text-ssb-text-muted" aria-hidden />
        <span className="text-ssb-text-muted">{context.section}</span>
        <ChevronRight size={11} className="text-ssb-text-muted" aria-hidden />
        <span className="text-ssb-green-bright font-semibold">{context.sub}</span>
      </div>

      <div className="flex items-center gap-2 text-[10px] font-mono uppercase tracking-wider text-ssb-text-muted">
        {user?.badge && <span className="hidden sm:inline">{user.badge}</span>}
        <span className="hidden sm:inline text-ssb-border">|</span>
        <span>{hasFullSectorAccess ? 'FULL SECTOR' : user?.assignedZone?.code ?? 'SECTOR'}</span>
      </div>
    </nav>
  )
}