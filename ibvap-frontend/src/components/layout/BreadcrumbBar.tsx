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
      className="h-8 flex-shrink-0 flex items-center justify-between gap-3 border-b border-white/[0.05] bg-[#060e18]/90 px-4"
    >
      {/* Left: breadcrumb path in clean mono */}
      <div className="flex items-center gap-1.5 font-mono text-[9px] uppercase tracking-[0.16em] whitespace-nowrap overflow-hidden">
        <span lang="hi" className="text-white/20">प्रहार</span>
        <ChevronRight size={9} className="text-white/15" aria-hidden />
        <span className="text-white/25">{context.section}</span>
        <ChevronRight size={9} className="text-white/15" aria-hidden />
        <span className="text-brand/70 font-semibold">{context.sub}</span>
      </div>

      {/* Right: badge + sector info */}
      <div className="flex items-center gap-2 text-[9px] font-mono uppercase tracking-[0.14em]">
        {user?.badge && (
          <span className="hidden sm:inline text-white/25">{user.badge}</span>
        )}
        <span className="hidden sm:inline text-white/10">·</span>
        <span className="rounded bg-cyan-500/10 border border-cyan-500/20 px-2 py-0.5 text-cyan-400/70 font-semibold">
          {hasFullSectorAccess ? 'FULL SECTOR' : (user?.assignedZone?.code ?? 'SECTOR')}
        </span>
      </div>
    </nav>
  )
}