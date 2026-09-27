import { clsx } from 'clsx'
import type { HealthIssue } from '@/types/cameraHealth'
import { formatClock } from './healthFormat'

const IMPACT_TONE: Record<HealthIssue['impact'], string> = {
  HIGH: 'text-prhaar-failed',
  MEDIUM: 'text-prhaar-degraded',
  LOW: 'text-slate-400',
}

/**
 * Current issues — one deduplicated record per issue (first/last seen,
 * observation count, duration). Issue impact is separate from camera status.
 */
export function CameraHealthIssueList({ issues }: { issues: HealthIssue[] }) {
  if (issues.length === 0) {
    return <p className="py-1 text-[11px] text-slate-600">No current issues.</p>
  }
  return (
    <ul className="divide-y divide-white/[0.04]">
      {issues.map(issue => (
        <li key={issue.issueId} className="py-1.5">
          <div className="flex items-baseline justify-between gap-2">
            <span className="text-[11px] font-medium text-slate-200">{issue.title}</span>
            <span className={clsx('shrink-0 font-mono text-[10px]', IMPACT_TONE[issue.impact])}>
              {issue.impact} IMPACT
            </span>
          </div>
          <div className="mt-0.5 flex flex-wrap gap-x-2 font-mono text-[10px] text-slate-600 tabular-nums">
            {issue.firstSeen && <span>first {formatClock(issue.firstSeen)}</span>}
            {issue.lastSeen && <span>last {formatClock(issue.lastSeen)}</span>}
            {issue.durationLabel && <span>dur {issue.durationLabel}</span>}
            {issue.count > 1 && <span>×{issue.count}</span>}
          </div>
          {issue.impactNote && (
            <p className="mt-0.5 text-[11px] text-slate-500">{issue.impactNote}</p>
          )}
          {issue.affectedModules.length > 0 && (
            <p className="mt-0.5 font-mono text-[10px] text-slate-600">
              affects {issue.affectedModules.join(', ')}
            </p>
          )}
        </li>
      ))}
    </ul>
  )
}
