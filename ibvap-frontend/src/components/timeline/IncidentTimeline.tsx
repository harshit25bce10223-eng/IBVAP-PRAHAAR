import { BellRing, ShieldAlert, Video, LogIn } from 'lucide-react'
import { clsx } from 'clsx'
import { SeverityBadge } from '@/components/risk/SeverityBadge'
import type { EventRecord, IncidentRecord, Severity } from '@/types'

interface TimelineItem {
  id: string
  kind: 'incident' | 'entry' | 'exit'
  title: string
  detail: string
  severity?: Severity
  score?: number
  ts: string
  cameraId: string
  trackId: string
}

/** Merge incidents + zone events into a single chronological feed. */
function toItems(incidents: IncidentRecord[], events: EventRecord[]): TimelineItem[] {
  const incidentItems: TimelineItem[] = incidents.map(i => ({
    id: i.incident_id,
    kind: 'incident',
    title: 'Zone breach — incident raised',
    detail: (i.factors ?? []).slice(0, 2).map(f => f.label).join(' · ') || 'Risk engine evaluation',
    severity: i.severity,
    score: i.risk_score,
    ts: i.created_at,
    cameraId: i.camera_id,
    trackId: i.track_id,
  }))

  const eventItems: TimelineItem[] = events.map(e => ({
    id: e.event_id,
    kind: e.event_type === 'ZONE_ENTRY' ? 'entry' : 'exit',
    title: e.event_type === 'ZONE_ENTRY' ? 'Object entered zone' : 'Object left zone',
    detail: typeof e.payload?.zone === 'string' ? e.payload.zone : e.zone_id,
    ts: e.ts,
    cameraId: e.camera_id,
    trackId: e.track_id,
  }))

  return [...incidentItems, ...eventItems].sort((a, b) => new Date(b.ts).getTime() - new Date(a.ts).getTime())
}

export function IncidentTimeline({
  incidents,
  events,
}: {
  incidents: IncidentRecord[]
  events: EventRecord[]
}) {
  const items = toItems(incidents, events)

  return (
    <div className="rounded-xl border border-border bg-surface p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="flex items-center gap-2 text-sm font-semibold text-slate-200">
          <ShieldAlert className="h-4 w-4 text-red-400" />
          Live Incident &amp; Event Feed
        </h3>
        <span className="font-mono text-[10px] text-slate-500">{items.length} items</span>
      </div>

      <div className="max-h-[420px] space-y-1 overflow-y-auto pr-1">
        {items.length === 0 && (
          <p className="rounded-md border border-dashed border-slate-700 p-3 text-center text-[11px] text-slate-500">
            No events yet. Simulated tracks will raise zone breaches here.
          </p>
        )}

        {items.map(item => (
          <div
            key={item.id}
            className="flex items-start gap-3 rounded-lg border border-white/[0.05] bg-white/[0.02] px-3 py-2"
          >
            <span
              className={clsx(
                'mt-0.5 flex h-6 w-6 shrink-0 items-center justify-center rounded-full',
                item.kind === 'incident'
                  ? 'bg-red-500/15 text-red-400'
                  : item.kind === 'entry'
                    ? 'bg-amber-500/15 text-amber-400'
                    : 'bg-slate-500/15 text-slate-400'
              )}
            >
              {item.kind === 'incident' ? (
                <BellRing className="h-3.5 w-3.5" />
              ) : item.kind === 'entry' ? (
                <LogIn className="h-3.5 w-3.5" />
              ) : (
                <Video className="h-3.5 w-3.5" />
              )}
            </span>

            <div className="min-w-0 flex-1">
              <div className="flex items-center justify-between gap-2">
                <span className="truncate text-xs font-medium text-slate-200">{item.title}</span>
                <span className="shrink-0 font-mono text-[10px] text-slate-500">{formatTs(item.ts)}</span>
              </div>
              <p className="mt-0.5 truncate text-[11px] text-slate-500">{item.detail}</p>
              <div className="mt-1 flex items-center gap-2">
                {item.kind === 'incident' && item.severity && (
                  <SeverityBadge severity={item.severity} score={item.score} />
                )}
                <span className="font-mono text-[10px] text-slate-600">
                  {item.cameraId} · {item.trackId}
                </span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

function formatTs(iso: string) {
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return iso
  return d.toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' })
}