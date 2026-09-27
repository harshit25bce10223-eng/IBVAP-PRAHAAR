// ─────────────────────────────────────────────────────────────────────────────
// NotificationsButton — command notification control (spec §9).
//
// Prototype panel showing example operational alerts; read-state is handled
// locally until the backend delivers live notifications. Unread count is
// rendered as a numeric badge, never colour alone.
// ─────────────────────────────────────────────────────────────────────────────

import { useEffect, useRef, useState } from 'react'
import { Bell, CheckCheck } from 'lucide-react'
import { clsx } from 'clsx'
import { useNotifications } from '@/hooks'
import type { CommandNotificationSeverity } from '@/types'

const TIME_FORMATTER = new Intl.DateTimeFormat('en-GB', {
  timeZone: 'Asia/Kolkata',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
})

const SEVERITY_BAR: Record<CommandNotificationSeverity, string> = {
  critical: 'bg-ssb-red',
  warning:  'bg-ssb-amber',
  info:     'bg-ssb-green-bright',
}

const SEVERITY_LABEL: Record<CommandNotificationSeverity, string> = {
  critical: 'bg-ssb-red/15    text-ssb-red-bright    border-ssb-red/40',
  warning:  'bg-ssb-amber/15  text-ssb-amber-bright  border-ssb-amber/40',
  info:     'bg-ssb-green/25  text-ssb-green-bright  border-ssb-green-bright/40',
}

function formatIST(iso: string): string {
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return ''
  return `${TIME_FORMATTER.format(date)} IST`
}

export function NotificationsButton() {
  const { notifications, notifState, unreadCount, markAllRead } = useNotifications()
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

  return (
    <div className="relative">
      <button
        ref={buttonRef}
        onClick={() => setOpen(o => !o)}
        aria-expanded={open}
        aria-haspopup="true"
        aria-label={`Notifications${unreadCount > 0 ? `, ${unreadCount} unread` : ''}`}
        title={unreadCount > 0 ? `${unreadCount} unread notifications` : 'Notifications'}
        className={clsx(
          'relative flex h-9 w-9 items-center justify-center rounded-md',
          'border border-ssb-border bg-ssb-navy-deep/60',
          'text-ssb-text-muted hover:text-ssb-white hover:bg-ssb-white/5 transition-colors'
        )}
      >
        <Bell size={16} aria-hidden />
        {unreadCount > 0 && (
          <span className="absolute -right-1.5 -top-1.5 flex h-4.5 min-w-[18px] items-center justify-center rounded-full bg-ssb-red px-1 text-[10px] font-bold text-ssb-white">
            {unreadCount > 99 ? '99+' : String(unreadCount).padStart(2, '0')}
          </span>
        )}
      </button>

      {open && (
        <>
          <div className="fixed inset-0 z-30" onClick={() => setOpen(false)} aria-hidden />
          <div
            role="region"
            aria-label="Command notifications"
            className="absolute right-0 top-11 z-40 w-[340px] rounded-lg border border-ssb-border bg-ssb-navy-raised shadow-2xl"
          >
            <div className="flex items-center justify-between border-b border-ssb-border px-3 py-2.5">
              <span className="text-[11px] font-semibold uppercase tracking-wider text-ssb-text">
                Command Notifications
              </span>
              {unreadCount > 0 && (
                <button
                  onClick={markAllRead}
                  className="flex items-center gap-1 text-[11px] text-ssb-green-bright hover:text-ssb-white transition-colors"
                >
                  <CheckCheck size={13} aria-hidden /> Mark all read
                </button>
              )}
            </div>

            <ul className="max-h-[360px] overflow-y-auto py-1">
              {notifState === 'loading' && notifications.length === 0 && (
                <li className="px-3 py-6 text-center text-xs text-ssb-text-muted" role="status">
                  Loading notifications…
                </li>
              )}
              {notifState === 'error' && notifications.length === 0 && (
                <li className="px-3 py-6 text-center text-xs text-ssb-red-bright" role="status">
                  Notifications unavailable
                </li>
              )}
              {notifications.map(n => (
                <li
                  key={n.id}
                  className="relative flex gap-2.5 rounded-md px-3 py-2.5 hover:bg-ssb-white/5 transition-colors"
                >
                  <span aria-hidden className={clsx('mt-1 h-8 w-[3px] flex-shrink-0 rounded-full', SEVERITY_BAR[n.severity])} />
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-semibold text-ssb-text leading-snug">{n.title}</p>
                    {n.meta && <p className="mt-0.5 text-[10px] font-mono text-ssb-text-muted">{n.meta}</p>}
                    <p className="mt-1 text-[10px] uppercase tracking-wider text-ssb-text-muted">
                      {formatIST(n.occurredAt)}
                    </p>
                  </div>
                  <span
                    className={clsx(
                      'h-fit rounded-full border px-1.5 py-0.5 text-[9px] font-semibold uppercase tracking-wider',
                      SEVERITY_LABEL[n.severity]
                    )}
                  >
                    {n.severity}
                  </span>
                </li>
              ))}
            </ul>

            <div className="border-t border-ssb-border px-3 py-2">
              <p className="text-[10px] text-ssb-text-muted">
                Live alerts arrive from the backend (Phase 2).
              </p>
            </div>
          </div>
        </>
      )}
    </div>
  )
}