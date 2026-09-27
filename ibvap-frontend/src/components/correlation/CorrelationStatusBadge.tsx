import { clsx } from 'clsx'
import { Badge } from '@/components/ui'
import {
  CORRELATION_BLURB,
  CORRELATION_LABEL,
  INCIDENT_STATE_LABEL,
  toneForCorrelation,
  toneForIncidentState,
  TONE,
} from './correlationTone'
import type { CorrelationStatus, IncidentState } from '@/types/eventCorrelation'

/**
 * Correlation status badge. Correlation is never a severity: even CORRELATED
 * groups use accent/neutral styling; severity is rendered separately by
 * SeverityBadge. Text label is always present so color is never the only
 * affordance (§153).
 */
export function CorrelationStatusBadge({ status }: { status: CorrelationStatus }) {
  const tone = toneForCorrelation(status)
  return (
    <Badge variant={TONE[tone].badge} size="sm">
      <span className={clsx('uppercase tracking-wider', TONE[tone].text)} title={CORRELATION_BLURB[status]}>
        {CORRELATION_LABEL[status]}
      </span>
    </Badge>
  )
}

/** Incident lifecycle badge — kept separate from correlation semantics. */
export function IncidentStateBadge({ state }: { state: IncidentState | null }) {
  if (!state) return null
  const tone = toneForIncidentState(state)
  return (
    <Badge variant={TONE[tone].badge} size="sm" dot>
      {INCIDENT_STATE_LABEL[state]}
    </Badge>
  )
}