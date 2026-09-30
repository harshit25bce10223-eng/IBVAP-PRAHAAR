// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 4 — Event Correlation domain types (canonical, render-only)
//
// The Event Engine is a backend/domain capability. This module is the single
// canonical frontend model that renders its output. The backend (Phase 2) is
// authoritative for every semantic field: correlation status, grouping,
// relationships, explanation, risk, severity, identity candidates.
//
// The frontend MUST NOT compute correlation, risk, severity, entity identity
// or causality. It renders authoritative fields verbatim and never fabricates
// a confidence, score, distance or identity that the backend did not supply.
// ─────────────────────────────────────────────────────────────────────────────

import type { Severity } from './risk'

/** Overall correlation standing of a group/event. Correlation is NEVER severity. */
export type CorrelationStatus =
  | 'STANDALONE'
  | 'RELATED'
  | 'CORRELATED'
  | 'UNCERTAIN'
  | 'DISSOLVED'
  | 'UNKNOWN'

/** Lifecycle state of a correlation group (backend-provided when available). */
export type CorrelationGroupState =
  | 'OPEN'
  | 'ACTIVE'
  | 'STABLE'
  | 'RESOLVED'
  | 'DISSOLVED'
  | 'UNKNOWN'

/** Heterogeneous signal source. Unknown beats a fabricated attribution. */
export type CorrelationSource =
  | 'VIRTUAL_FENCE'
  | 'DETECTION'
  | 'TRACKING'
  | 'ANPR'
  | 'AUDIO'
  | 'SURFACE_ANOMALY'
  | 'SUSPICIOUS_ACTIVITY'
  | 'RE_ID'
  | 'CAMERA_HEALTH'
  | 'SYSTEM'
  | 'UNKNOWN'

/**
 * Relationship kind an arrow may carry. An arrow signals backend-defined
 * sequence/direction — it is NEVER interpreted as causality.
 */
export type CorrelationRelationType =
  | 'TEMPORAL'
  | 'SPATIAL'
  | 'ENTITY'
  | 'CAMERA'
  | 'ZONE'
  | 'SEQUENCE'
  | 'SUPPORTING'
  | 'CONTEXTUAL'

/** Concise per-event kind. Distinct from the source that produced it. */
export type CorrelationEventKind =
  | 'DETECTION'
  | 'ZONE_ENTRY'
  | 'ZONE_EXIT'
  | 'ANPR_READ'
  | 'AUDIO_ANOMALY'
  | 'SURFACE_ANOMALY'
  | 'SUSPICIOUS_ACTIVITY'
  | 'REID_CANDIDATE'
  | 'TRACK'
  | 'CAMERA_CONTEXT'
  | 'SYSTEM'
  | 'UNKNOWN'

/** Broad observation modality, shown as source context (never decorative). */
export type CorrelationModality =
  | 'VIDEO'
  | 'ANPR'
  | 'AUDIO'
  | 'RF'
  | 'THERMAL'
  | 'SYSTEM'
  | 'UNKNOWN'

/** Per-event reliability, reported verbatim. Frontend never averages it. */
export type Reliability = 'HIGH' | 'MEDIUM' | 'LOW' | 'UNKNOWN'

/** Data freshness of a source. DELAYED is never labelled as real-time. */
export type Connectivity = 'LIVE' | 'DELAYED' | 'LAST_SYNCED' | 'UNKNOWN'

/** Correlation group lifecycle status for the log/incident (backend contract). */
export type IncidentState = 'NEW' | 'REVIEWED' | 'CLOSED' | 'UNKNOWN'

/** A structured reason facet used by the "WHY RELATED" panel (§96–97). */
export interface CorrelationExplanation {
  facet: 'TEMPORAL' | 'SPATIAL' | 'ENTITY' | 'SEQUENCE' | 'CAMERA' | 'ZONE' | 'CONTEXTUAL'
  /** Short value, e.g. '32 sec', 'same zone', 'possible continuation'. */
  label: string
  /** Human description of the support, e.g. 'Within configured window'. */
  detail: string
}

/** One member signal of a group. Every source type is heterogeneous by design. */
export interface CorrelationEventMember {
  eventId: string
  kind: CorrelationEventKind
  source: CorrelationSource
  modality: CorrelationModality
  cameraId: string
  zoneId: string | null
  sectorId: string | null
  regionProfile: string | null
  trackId: string | null
  timestamp: string
  /** Payload severity only when the backend supplies one — never fabricated. */
  severity: Severity | null
  reliability: Reliability | null
  /** Detection/ANPR/Re-ID confidence when the backend supplies one — never computed. */
  confidence: number | null
  /** Evidence record ids linked to this signal (§75). Not evidence UI. */
  evidenceIds: string[]
  /** Camera-health reliability context, if backend flags it (§40/§89). */
  healthContext: CameraReliabilityContext | null
  /** Downstream DET-* reference surfaced verbatim when the payload supplies it (C5). */
  detectionId: string | null
  /** ANPR plate candidate surfaced verbatim when supplied (C7) — not OCR logic. */
  anprPlate: string | null
  /** ANPR plate confidence (0–1) when the backend supplies it (C7). */
  anprPlateConfidence: number | null
  /** ANPR quality label when the backend supplies it (C7). */
  anprQuality: string | null
  /** ANPR sighting reference surfaced verbatim when supplied (C7). */
  anprSightingId: string | null
}

/** Camera reliability context — context only, never alters risk (§40/§89). */
export interface CameraReliabilityContext {
  cameraId: string
  reliability: Reliability
  note: string | null
}

/** One backend-defined relationship between two member events (§26). */
export interface CorrelationRelationship {
  fromEventId: string
  toEventId: string
  type: CorrelationRelationType
  /** Relationship strength only when the backend exposes it (§20/§53). */
  strength: number | null
  explanation: string
}

/** Confidence — only rendered when the backend provides it (§20/§95). */
export interface CorrelationConfidence {
  /** 0–100 when supplied. Never fabricated. */
  value: number
  note: string
}

/** What remains uncertain about a correlation, kept visible (§39/§70). */
export interface CorrelationUncertainty {
  reliability: Reliability
  note: string | null
}

/** Backend-scored risk on the combined event (Component 1 is authoritative). */
export interface CorrelationRisk {
  score: number | null
  severity: Severity | null
  /** C1 incident ids referencing this group's member events (by reference). */
  incidentIds: string[]
}

/** Possible same-entity candidate from Tracking/Re-ID (§19/§84). Not identity. */
export interface TrackCandidate {
  trackId: string
  confidence: number | null
  /** Always 'possible' language, never 'same person' without authority. */
  label: string
}

/** A status transition in the group's history (§45/§136–137). */
export interface CorrelationTransition {
  status: CorrelationStatus
  at: string
  note: string | null
}

export interface CorrelationHistory {
  createdAt: string
  updatedAt: string
  transitions: CorrelationTransition[]
}

/**
 * Canonical correlation group. A STANDALONE event is represented as a group
 * with status STANDALONE and one member — the log and summary render both
 * uniformly, and correlation is never forced (§71).
 */
export interface CorrelationGroup {
  correlationId: string
  incidentId: string | null
  incidentState: IncidentState | null
  status: CorrelationStatus
  state: CorrelationGroupState
  startedAt: string
  endedAt: string | null
  /** Backend-authoritative counts. memberEvents may load fewer (§43/§143). */
  eventCount: number
  cameraCount: number
  /** How many of `eventCount` member events are currently loaded. Null when all. */
  memberEventsLoaded: number | null
  memberEvents: CorrelationEventMember[]
  /** The backend-designated primary event, when one exists (§38). */
  primaryEventId: string | null
  relationships: CorrelationRelationship[]
  explanation: CorrelationExplanation[]
  /** Backend-generated human-readable summary of why the group formed (§47). */
  explanationSummary: string | null
  /** Backend correlation strength label — HIGH/MEDIUM/LOW/NONE. Never a risk label (§20). */
  correlationStrength: 'HIGH' | 'MEDIUM' | 'LOW' | 'NONE' | null
  /** Only when the backend supplies one. Never fabricated (§20/§53). */
  confidence: CorrelationConfidence | null
  /** Configured temporal relationship window (display only, §47). */
  temporalWindowSec: number | null
  risk: CorrelationRisk
  uncertainty: CorrelationUncertainty
  trackCandidate: TrackCandidate | null
  /** Camera sequence order, e.g. ['CAM-07','CAM-08'] — never claims movement. */
  cameraChain: string[] | null
  /** Source modality summary, e.g. ['VIDEO','ANPR','AUDIO'] (§94/§149). */
  modalities: CorrelationModality[]
  sectorId: string | null
  regionProfile: string | null
  /** Sources involved, for the source legend (§51/§118). */
  sources: CorrelationSource[]
  /** Reliability context for supporting cameras (§40/§89). */
  healthContext: CameraReliabilityContext[]
  /** Count of linked evidence records (§75). */
  evidenceCount: number
  connectivity: Connectivity
  /** True when backend flags transport duplication or suppression (§142). */
  duplicatedOrSuppressed: boolean
  history: CorrelationHistory
  updatedAt: string
}

/** API-ready query for the Event/Incident Log (server pagination in Phase 2). */
export interface EventLogQuery {
  search: string
  correlation: CorrelationStatus | 'ALL'
  severity: Severity | 'ALL'
  cameraId: string
  sectorId: string
  source: CorrelationSource | 'ALL'
  connectivity: Connectivity | 'ALL'
  timeRange: '15m' | '1h' | 'today' | 'all'
  sort: 'time' | 'severity' | 'signals' | 'cameras' | 'status'
  order: 'desc' | 'asc'
  page: number
  pageSize: number
}

export interface CorrelationGroupPage {
  groups: CorrelationGroup[]
  total: number
}

export const DEFAULT_CORRELATION_QUERY: EventLogQuery = {
  search: '',
  correlation: 'ALL',
  severity: 'ALL',
  cameraId: 'ALL',
  sectorId: 'ALL',
  source: 'ALL',
  connectivity: 'ALL',
  timeRange: 'all',
  sort: 'time',
  order: 'desc',
  page: 1,
  pageSize: 8,
}

export const CORRELATION_STATUSES: CorrelationStatus[] = [
  'STANDALONE',
  'RELATED',
  'CORRELATED',
  'UNCERTAIN',
  'DISSOLVED',
  'UNKNOWN',
]

export const CORRELATION_SOURCES: CorrelationSource[] = [
  'VIRTUAL_FENCE',
  'DETECTION',
  'TRACKING',
  'ANPR',
  'AUDIO',
  'SURFACE_ANOMALY',
  'SUSPICIOUS_ACTIVITY',
  'RE_ID',
  'CAMERA_HEALTH',
  'SYSTEM',
]

export const CORRELATION_RELATION_TYPES: CorrelationRelationType[] = [
  'TEMPORAL',
  'SPATIAL',
  'ENTITY',
  'CAMERA',
  'ZONE',
  'SEQUENCE',
  'SUPPORTING',
  'CONTEXTUAL',
]
