// ─────────────────────────────────────────────────────────────────────────────
// Clock — live IST date/time (spec §11, §12).
//
// Updates only this leaf component each second, so the rest of the command
// header is never re-rendered. Proper browser time APIs, consistent format:
//   "15 SEP 2026" / "17:45:12 IST"
// ─────────────────────────────────────────────────────────────────────────────

import { useEffect, useState } from 'react'
import { clsx } from 'clsx'

const DATE_FORMATTER = new Intl.DateTimeFormat('en-GB', {
  timeZone: 'Asia/Kolkata',
  day: '2-digit',
  month: 'short',
  year: 'numeric',
})

const TIME_FORMATTER = new Intl.DateTimeFormat('en-GB', {
  timeZone: 'Asia/Kolkata',
  hour12: false,
  hour: '2-digit',
  minute: '2-digit',
  second: '2-digit',
})

export function Clock({ className }: { className?: string }) {
  const [now, setNow] = useState(() => new Date())

  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 1000)
    return () => clearInterval(timer)
  }, [])

  const date = DATE_FORMATTER.format(now).toUpperCase()
  const time = TIME_FORMATTER.format(now)

  return (
    <div
      className={clsx('flex flex-col items-end leading-tight font-mono', className)}
      aria-label={`Current time and date, Indian Standard Time: ${time}, ${date}`}
    >
      <span className="text-[10px] tracking-[0.14em] text-ssb-text-muted uppercase whitespace-nowrap">
        {date}
      </span>
      <span className="text-sm font-semibold text-ssb-white tabular-nums whitespace-nowrap">
        {time} <span className="text-[10px] font-medium text-ssb-text-muted tracking-wider">IST</span>
      </span>
    </div>
  )
}