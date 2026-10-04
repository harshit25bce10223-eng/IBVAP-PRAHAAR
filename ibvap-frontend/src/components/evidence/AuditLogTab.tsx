import type { AuditEntry } from '@/types/evidence'
import { formatClock } from '@/components/camera-health/healthFormat'

/**
 * Audit trail tab: timestamp, actor, action, target, result, reason.
 * Entries come from the service only — the UI never fabricates rows, and
 * secrets never appear here by construction (typed fields only).
 */
export function AuditLogTab({ entries }: { entries: AuditEntry[] }) {
  if (entries.length === 0) {
    return (
      <p className="rounded-xl border border-dashed border-slate-700 p-6 text-center text-[11px] text-slate-500">
        No audit entries available.
      </p>
    )
  }
  return (
    <div className="overflow-x-auto rounded-xl border border-border bg-surface">
      <table className="w-full min-w-[760px] border-collapse text-left">
        <caption className="sr-only">Evidence audit log</caption>
        <thead>
          <tr className="border-b border-border text-[10px] uppercase tracking-wider text-slate-500">
            {['Timestamp', 'Actor', 'Action', 'Target', 'Result', 'Reason'].map(h => (
              <th key={h} scope="col" className="px-3 py-2 font-medium">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {entries.map(e => (
            <tr key={e.auditId} className="border-b border-white/[0.04] last:border-0">
              <td className="px-3 py-2 font-mono text-[11px] text-slate-400 tabular-nums">{formatClock(e.at)}</td>
              <td className="px-3 py-2 text-[11px] text-slate-200">{e.actor}</td>
              <td className="px-3 py-2 font-mono text-[11px] text-cyan-400/90">{e.action}</td>
              <td className="px-3 py-2 font-mono text-[11px] text-slate-300">{e.target}</td>
              <td className="px-3 py-2 font-mono text-[11px] text-slate-300">{e.result}</td>
              <td className="px-3 py-2 text-[11px] text-slate-500">{e.reason ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
