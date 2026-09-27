// ─────────────────────────────────────────────────────────────────────────────
// IBVAP Component 1 — Zone domain types
// ─────────────────────────────────────────────────────────────────────────────

import type { ObjectType } from './track'

/** A single vertex of a zone polygon, normalized to [0, 1]. */
export interface ZonePoint {
  x: number
  y: number
}

/** Zone rule set. Empty object means "always allowed". */
export interface ZoneRules {
  allowed_object_types?: ObjectType[]
  /** HH:MM 24h (may cross midnight, e.g. 18:00 → 06:00). */
  active_start?: string
  active_end?: string
  dwell_time_seconds?: number
}

export type ZoneTransition = 'ENTRY' | 'EXIT' | 'STABLE_INSIDE' | 'STABLE_OUTSIDE' | 'FIRST' | 'INACTIVE'

export interface Zone {
  zone_id: string
  camera_id: string
  name: string
  polygon: ZonePoint[]
  rules: ZoneRules
  active: boolean
  created_at: string
  updated_at: string
}

export interface ZoneCreatePayload {
  zone_id?: string
  camera_id: string
  name?: string
  polygon: ZonePoint[]
  rules?: ZoneRules
  active?: boolean
}

export interface ZoneEvaluation {
  zone_id: string
  zone_name: string
  is_inside: boolean
  previously_inside: boolean
  transition: ZoneTransition
  rule_passed: boolean
  event: { created: boolean; event_id: string | null }
  incident: { created: boolean; incident_id?: string }
  polygon?: ZonePoint[]
}

export interface ZoneMembershipState {
  /** per-zone membership boolean, keyed by zone_id */
  current: Record<string, boolean>
  previous: Record<string, boolean>
}