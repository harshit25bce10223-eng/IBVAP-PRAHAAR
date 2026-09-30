// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 6 — Tracking Engine canonical types
//
// Tracking represents observation continuity across time:
// "Which observations may belong to the same moving object over time?"
//
// Explicitly distinct from:
// - Detection: "An object was observed in this single frame" (Component 5)
// - Identity: "Who or what specifically this is" (NOT in Component 6)
// - Event: "Did this produce an operationally relevant signal?"
// - Correlation: "Are multiple events related?" (Component 4)
// - Risk: "What threat score applies?" (Component 1)
// - Incident: "Scored breach or violation"
// - Evidence: "Cryptographically verifiable ledger entry" (Component 3)
// ─────────────────────────────────────────────────────────────────────────────

import type { DetectionBBox, DetectionClass } from './detection'

/**
 * Canonical track lifecycle states (§19, §20).
 *
 * ACTIVE:     Recently observed moving object.
 * TENTATIVE:  Hypothesis forming; not yet confirmed continuous.
 * LOST:       Temporarily unobserved (occluded, shadow), NOT ended.
 * REACQUIRED: Resumed continuity after temporary loss.
 * ENDED:      Natural lifecycle completed (exited sector, resolved).
 * STALE:      Data age exceeds validity window; position cannot be trusted.
 * INVALID:    Rejected by upstream validation or operator override.
 * UNKNOWN:    Insufficient telemetry.
 */
export type TrackStatus =
  | 'ACTIVE'
  | 'TENTATIVE'
  | 'LOST'
  | 'REACQUIRED'
  | 'ENDED'
  | 'STALE'
  | 'INVALID'
  | 'UNKNOWN'

export const TRACK_STATUSES: readonly TrackStatus[] = [
  'ACTIVE',
  'TENTATIVE',
  'LOST',
  'REACQUIRED',
  'ENDED',
  'STALE',
  'INVALID',
  'UNKNOWN',
] as const

/** Continuity quality reported by tracking service (§25). Not a fake percentage. */
export type TrackContinuityQuality = 'STRONG' | 'MODERATE' | 'WEAK' | 'UNKNOWN'

/** Where track telemetry originated (§74). */
export type TrackSource = 'LIVE' | 'EDGE' | 'CENTRAL' | 'DEMO' | 'UNKNOWN'

/** Tracking feed freshness and availability (§83). */
export type TrackingFeedState =
  | 'READY'
  | 'PROCESSING'
  | 'DEGRADED'
  | 'UNAVAILABLE'
  | 'STALE'
  | 'OFFLINE'
  | 'UNKNOWN'

/** Single 2D trajectory point in normalized [0, 1] image space. */
export interface TrackPoint {
  x: number
  y: number
  timestamp?: string
  observationId?: string
  sequence?: number
  speed?: number | null
}

/**
 * Track observation record (§17) — links a single detection observation
 * into this track's historical sequence.
 */
export interface TrackObservation {
  observationId: string
  trackId: string
  detectionId: string | null
  cameraId: string
  observedAt: string
  receivedAt?: string | null
  bbox: DetectionBBox | null
  velocity?: number | null // in m/s if available (§37)
  speed?: number | null
  direction?: string | null // e.g. 'NE', 'MOVING EAST' (§36)
  quality?: TrackContinuityQuality | null
  confidence?: number | null // detector confidence for this observation
  sequence?: number | null
  source: TrackSource
  frameNumber?: number | null
  frameId?: string | null
  evidenceId?: string | null
}

/** Alias to avoid collisions with Component 1 simulation TrackObservation. */
export type TrackObservationRecord = TrackObservation

/** Cross-camera transition hypothesis (§61–§68). Never "SAME PERSON". */
export interface CrossCameraCandidate {
  targetCameraId: string
  candidateTrackId: string
  continuityConfidence?: number | null
  gapDurationSec?: number | null
  sequenceNumber?: number
  note?: string
}

/**
 * Single lifecycle transition record (§8–§10) as persisted by the backend
 * (TrackHistory). Real recorded transitions only — never synthesized by the
 * frontend. `oldStatus` is null for the first entry of a track.
 */
export interface TrackLifecycleEvent {
  historyId: string
  trackId: string
  /** Monotonic record revision assigned by the lifecycle engine. */
  revision: number
  oldStatus: TrackStatus | null
  newStatus: TrackStatus
  /** Recorded reason for the transition when the backend supplies one. */
  reason: string | null
  triggerDetectionId?: string | null
  provider?: string | null
  providerVersion?: string | null
  configurationVersion?: string | null
  /** When the transition was recorded (backend clock). */
  timestamp: string
}

/** Relation hypotheses only — never confirmed identity (§20, §67). */
export type TrackCandidateRelation = 'POSSIBLE_CONTINUATION' | 'POSSIBLE_SAME_ENTITY'

/**
 * Cross-camera candidate record (§20) as returned by
 * GET /api/v1/tracks/{id}/candidates. A hypothesis, not an identity link.
 */
export interface TrackCandidate {
  candidateId: string
  sourceTrackId: string
  targetCameraId: string
  candidateTrackId: string | null
  relationType: TrackCandidateRelation | string
  strength: number | null
  reason: string | null
  status: string
  provider: string | null
  gapDurationSec: number | null
  createdAt: string
  expiresAt: string | null
}

/** Component 2 Camera Health context attached to a track (§58, §85). */
export interface TrackCameraHealthContext {
  status: 'ONLINE' | 'DEGRADED' | 'OFFLINE' | 'UNKNOWN'
  reliability: 'HIGH' | 'MEDIUM' | 'LOW' | 'UNKNOWN'
  viewpointShiftDetected?: boolean
  note?: string | null
}

/**
 * Canonical Track entity (§14).
 * Represents a sequence of observations hypothesized to be the same moving entity.
 */
export interface Track {
  /** Unique track identifier (TRK-*), distinct from DET/EV/INC/EVD/COR ids (§15). */
  trackId: string
  cameraId: string
  status: TrackStatus
  objectClass: DetectionClass
  firstSeenAt: string
  lastSeenAt: string
  ageMs?: number | null
  durationSec?: number | null
  detectionCount: number
  currentDetectionId: string | null
  currentBoundingBox: DetectionBBox | null
  trajectory: TrackPoint[] | null
  speed?: number | null
  velocity?: number | null // e.g. 1.4 m/s
  direction?: string | null // e.g. 'N', 'NE', 'MOVING EAST'
  confidence?: number | null // separate from detection confidence (§26, §27)
  continuityQuality?: TrackContinuityQuality | null
  source: TrackSource
  provider?: string | null
  trackerName?: string | null
  trackerVersion?: string | null
  eventId?: string | null
  correlationId?: string | null
  incidentId?: string | null
  evidenceId?: string | null
  candidateEntityId?: string | null
  crossCameraCandidate?: CrossCameraCandidate | null
  cameraHealthContext?: TrackCameraHealthContext | null
  regionProfile?: string | null
  sectorId?: string | null
  observedAt: string
  updatedAt?: string | null
  dataSource: 'LIVE' | 'EDGE' | 'CENTRAL' | 'DEMO' | 'UNKNOWN'
  revision?: number | null
  schemaVersion?: string

  // Reclassification history (§44, §45)
  previousClass?: DetectionClass | null
  classRevisionReason?: string | null
  classRevisedAt?: string | null

  // Gaps & missing data (§142–§145)
  dataCompleteness?: 'COMPLETE' | 'PARTIAL' | 'UNKNOWN'
  missingObservationsNote?: string | null
}

/** Feed response for a single camera's tracks. */
export interface TrackingFeed {
  cameraId: string
  state: TrackingFeedState
  lastUpdatedAt: string | null
  tracks: Track[]
  providerHealth?: 'READY' | 'DEGRADED' | 'UNAVAILABLE' | 'OFFLINE' | 'UNKNOWN'
}

/** Aggregated structural track summary (counts only, never threat counts! §128, §185). */
export interface TrackSummary {
  cameraId: string
  totalActive: number
  totalTracks: number
  byClass: Partial<Record<DetectionClass, number>>
  byStatus: Partial<Record<TrackStatus, number>>
  lastUpdatedAt: string | null
}

/** Track query parameters for list / filter surfaces (§49, §251). */
export interface TrackQuery {
  search: string
  cameraId: string
  class: DetectionClass | 'ALL'
  status: TrackStatus | 'ALL'
  source: TrackSource | 'ALL'
  timeRange: '15m' | '1h' | 'today' | 'all'
  sort: 'latest' | 'oldest' | 'longest' | 'observations' | 'camera'
  order: 'asc' | 'desc'
  page: number
  pageSize: number
}

/** Paginated track response. */
export interface TrackResultPage {
  tracks: Track[]
  total: number
  page: number
  pageSize: number
}

export const DEFAULT_TRACK_QUERY: TrackQuery = {
  search: '',
  cameraId: 'ALL',
  class: 'ALL',
  status: 'ALL',
  source: 'ALL',
  timeRange: 'all',
  sort: 'latest',
  order: 'desc',
  page: 1,
  pageSize: 20,
}

/** Re-export for convenience — avoids cross-importing detection types. */
export type { DetectionClass, DetectionQuality } from './detection'
