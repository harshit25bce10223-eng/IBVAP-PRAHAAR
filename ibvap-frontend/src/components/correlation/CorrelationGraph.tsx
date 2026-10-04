import { clsx } from 'clsx'
import { compareByObservedTime, formatClockShort } from './correlationFormat'
import { humanizeEventKind } from './CorrelationSummary'
import type { CorrelationEventMember, CorrelationGroup, CorrelationRelationship, CorrelationRelationType } from '@/types/eventCorrelation'

const EDGE_LABEL: Record<CorrelationRelationType, string> = {
  TEMPORAL: 'temporal',
  SPATIAL: 'spatial',
  ENTITY: 'entity',
  CAMERA: 'camera',
  ZONE: 'zone',
  SEQUENCE: 'sequence',
  SUPPORTING: 'supporting',
  CONTEXTUAL: 'context',
}

interface CorrelationGraphProps {
  group: CorrelationGroup
  relationships: CorrelationRelationship[]
  onSelect?: (eventId: string) => void
}

/**
 * Compact relationship flow (§27/§80). Nodes are member events in
 * chronological order; between them a single subtle connector shows the
 * backend-defined relationship type. This reads top-down like the spec, is
 * cheap to scan, and never grows into a giant circular graph. An arrow shows
 * sequence/direction, never causality (§82). The timeline remains the
 * alternative scan surface (§175).
 */
export function CorrelationGraph({ group, relationships, onSelect }: CorrelationGraphProps) {
  const nodes = [...group.memberEvents].sort(compareByObservedTime)
  const edges = (relationships.length > 0 ? relationships : group.relationships).slice(0, 24)
  const byId = new Map(nodes.map(n => [n.eventId, n]))

  if (nodes.length === 0) {
    return <p className="text-[11px] text-slate-500">No relationship data available.</p>
  }

  const primary = group.primaryEventId

  return (
    <ol className="relative" aria-label="Related event flow">
      {nodes.map((node, i) => {
        const outgoing = edges.filter(e => e.fromEventId === node.eventId)
        const isPrimary = node.eventId === primary
        return (
          <li key={node.eventId} className="pb-2">
            <GraphNode member={node} isPrimary={isPrimary} onSelect={onSelect} />
            {outgoing.map((e, j) => {
              const target = byId.get(e.toEventId)
              return (
                <div key={`${e.fromEventId}-${e.toEventId}-${j}`} className="ml-3 border-l border-border pl-3">
                  <p className="flex items-center gap-1.5 py-1 text-[9px] font-mono uppercase tracking-wider text-slate-500" title={e.explanation}>
                    <span
                      className={clsx(
                        'h-1 w-1 rounded-full',
                        i < nodes.length - 1 ? 'bg-slate-500' : 'bg-slate-700'
                      )}
                      aria-hidden
                    />
                    {EDGE_LABEL[e.type]} → {target ? humanizeEventKind(target.kind) : e.toEventId}
                  </p>
                </div>
              )
            })}
          </li>
        )
      })}
    </ol>
  )
}

function GraphNode({ member, isPrimary, onSelect }: {
  member: CorrelationEventMember
  isPrimary: boolean
  onSelect?: (eventId: string) => void
}) {
  const base =
    'rounded-md border px-2 py-1 font-mono text-[11px] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-cyan-500/60 transition-colors'
  const box = isPrimary
    ? 'border-prhaar-accent/40 bg-prhaar-accent/10 text-prhaar-accent inline-block'
    : 'border-white/10 bg-surface/40 text-slate-300 inline-block hover:border-cyan-500/40'
  const label = (
    <>
      <span className="tabular-nums">{formatClockShort(member.timestamp)}</span>{' '}
      <span className="font-sans">{humanizeEventKind(member.kind)}</span>
      <span className="text-slate-500"> {member.cameraId}</span>
    </>
  )
  return onSelect ? (
    <button type="button" onClick={() => onSelect(member.eventId)} className={clsx(base, box)}>
      {label}
    </button>
  ) : (
    <div className={clsx(base, box)}>{label}</div>
  )
}