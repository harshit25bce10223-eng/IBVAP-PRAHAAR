import { clsx } from 'clsx'
import { useEffect, useCallback } from 'react'
import { createPortal } from 'react-dom'
import { X } from 'lucide-react'
import type { ReactNode } from 'react'

interface DrawerProps {
  open: boolean
  onClose: () => void
  title?: string
  width?: string
  children: ReactNode
  footer?: ReactNode
}

export function Drawer({ open, onClose, title, width = 'w-[480px]', children, footer }: DrawerProps) {
  const handleKey = useCallback(
    (e: KeyboardEvent) => { if (e.key === 'Escape') onClose() },
    [onClose]
  )

  useEffect(() => {
    if (open) document.addEventListener('keydown', handleKey)
    return () => document.removeEventListener('keydown', handleKey)
  }, [open, handleKey])

  return createPortal(
    <div
      className={clsx(
        'fixed inset-0 z-50 flex justify-end transition-all duration-300',
        open ? 'visible' : 'invisible'
      )}
    >
      {/* Backdrop */}
      <div
        className={clsx(
          'absolute inset-0 bg-black/60 backdrop-blur-sm transition-opacity duration-300',
          open ? 'opacity-100' : 'opacity-0'
        )}
        onClick={onClose}
      />
      {/* Panel */}
      <div
        className={clsx(
          'relative z-10 flex flex-col h-full max-w-[100vw] border-l border-border',
          'bg-surface shadow-2xl transition-transform duration-300 ease-in-out',
          width,
          open ? 'translate-x-0' : 'translate-x-full'
        )}
      >
        {/* Header */}
        {title && (
          <div className="flex items-center justify-between gap-4 border-b border-border bg-ssb-navy-raised/50 px-6 py-5 flex-shrink-0">
            <h2 className="text-base font-semibold text-slate-100">{title}</h2>
            <button
              onClick={onClose}
              aria-label="Close panel"
              className="rounded-lg p-2 text-slate-400 hover:text-slate-100 hover:bg-white/5 transition-colors"
            >
              <X size={16} />
            </button>
          </div>
        )}
        {/* Body */}
        <div className="flex-1 overflow-y-auto px-6 py-5">{children}</div>
        {/* Footer */}
        {footer && (
          <div className="border-t border-border px-6 py-4 flex-shrink-0 flex justify-end gap-3">
            {footer}
          </div>
        )}
      </div>
    </div>,
    document.body
  )
}
