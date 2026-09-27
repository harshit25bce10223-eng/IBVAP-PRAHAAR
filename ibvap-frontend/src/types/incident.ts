// ─────────────────────────────────────────────────────────────────────────────
// IBVAP Component 1 — Incident & event domain types
// ─────────────────────────────────────────────────────────────────────────────

import type { RiskFactor, Severity } from './risk'
import type { ZoneEvaluation } from './zone'

export type EventType = 'ZONE_ENTRY' | 'ZONE_EXIT'

export interface RiskEngineEvent {
  created: boolean
  event_id: string | null
  multiple?: string[]
}

export interface IncidentSummary {
  created: boolean
  incident_id: string | null
  risk_score: number | null
  severity: Severity | null
  factors: RiskFactor[]
}

export interface TrackEvaluationResponse {
  track: {
    track_id: string
    camera_id: string
    object_type: string
  }
  evaluation: {
    representative_point: { x: number; y: number }
    zones: ZoneEvaluation[]
  }
  event: RiskEngineEvent
  exit_event: RiskEngineEvent
  incident: IncidentSummary
}

export interface IncidentRecord {
  incident_id: string
  risk_score: number
  severity: Severity
  factors: RiskFactor[]
  event_id: string
  camera_id: string
  track_id: string
  zone_id: string
  created_at: string
}

export interface EventRecord {
  event_id: string
  event_type: EventType
  camera_id: string
  track_id: string
  zone_id: string
  payload: Record<string, unknown> | null
  ts: string
}