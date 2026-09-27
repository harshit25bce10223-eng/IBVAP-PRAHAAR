// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 4 — correlation components barrel
// ─────────────────────────────────────────────────────────────────────────────

export { CorrelationStatusBadge, IncidentStateBadge } from './CorrelationStatusBadge'
export { CorrelationSummary, MemberSignals, humanizeEventKind, humanizeSource } from './CorrelationSummary'
export { CorrelationTimeline } from './CorrelationTimeline'
export { CorrelationExplanation } from './CorrelationExplanation'
export { CorrelationSignals } from './CorrelationSignals'
export { CorrelationGraph } from './CorrelationGraph'
export { CorrelationEventDrawer } from './CorrelationEventDrawer'
export { CorrelationRisk } from './CorrelationRisk'
export { CorrelationUncertainty } from './CorrelationUncertainty'
export { CorrelationHistory } from './CorrelationHistory'
export { SourceLegend } from './SourceLegend'
export { EventLogFilters } from './EventLogFilters'

export { TONE, CORRELATION_BLURB, CORRELATION_LABEL, CONNECTIVITY_LABEL, GROUP_STATE_LABEL, INCIDENT_STATE_LABEL, RELIABILITY_LABEL } from './correlationTone'
export { toneForConnectivity, toneForIncidentState, toneForCorrelation, toneForReliability, toneForGroupState, toneForSeverity } from './correlationTone'
export type { CorrelationTone } from './correlationTone'
export {
  formatClock,
  formatClockShort,
  formatDate,
  formatWindow,
  formatSignalCount,
  formatCameraCount,
  formatCameraList,
  formatConfidence,
  formatModalities,
  formatSec,
} from './correlationFormat'