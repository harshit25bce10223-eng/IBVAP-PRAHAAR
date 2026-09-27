import { clsx } from 'clsx'
import type { ReactNode } from 'react'
import { ChevronRight } from 'lucide-react'

export interface BreadcrumbItem {
  label: string
  href?: string
}

interface PageHeaderProps {
  title: string
  subtitle?: string
  breadcrumbs?: BreadcrumbItem[]
  actions?: ReactNode
  badge?: ReactNode
  className?: string
}

export function PageHeader({ title, subtitle, breadcrumbs, actions, badge, className }: PageHeaderProps) {
  return (
    <div className={clsx('flex flex-col gap-1 mb-6', className)}>
      {/* Breadcrumbs */}
      {breadcrumbs && breadcrumbs.length > 0 && (
        <nav className="flex items-center gap-1 text-xs text-slate-500">
          {breadcrumbs.map((crumb, i) => (
            <span key={i} className="flex items-center gap-1">
              {i > 0 && <ChevronRight size={12} />}
              {crumb.href ? (
                <a href={crumb.href} className="hover:text-slate-300 transition-colors">
                  {crumb.label}
                </a>
              ) : (
                <span className={i === breadcrumbs.length - 1 ? 'text-slate-400' : ''}>
                  {crumb.label}
                </span>
              )}
            </span>
          ))}
        </nav>
      )}
      {/* Title row */}
      <div className="flex items-center justify-between gap-4">
        <div className="flex items-center gap-3 min-w-0">
          <h1 className="text-xl font-bold text-slate-100 truncate">{title}</h1>
          {badge}
        </div>
        {actions && <div className="flex items-center gap-2 flex-shrink-0">{actions}</div>}
      </div>
      {subtitle && <p className="text-sm text-slate-500">{subtitle}</p>}
    </div>
  )
}
