// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 4 — Event Correlation service boundary
//
// Phase 1 (current): the exported provider is a mock serving isolated
// development fixtures. No axios, no fake endpoint, no synthetic real-time
// pretending to be a backend.
//
// Phase 2 (planned): implement this interface against the real Event Engine
// and swap the singleton in `services/correlation/index.ts`. Pages, hooks,
// stores and components consume ONLY this interface, so no UI redesign is
// required. No component directly imports mock data except demo/test infra.
//
// Planned contract (follows existing `/api/v1` conventions; final names TBD):
//   GET /api/v1/events/correlation?...filters&sort=&page=   → CorrelationGroupPage
//   GET /api/v1/events/correlation/{correlation_id}         → CorrelationGroup
//   GET /api/v1/events/correlation/{id}/relationships       → CorrelationRelationship[]
//   GET /api/v1/events/{event_id}                           → CorrelationEventMember
//   GET /api/v1/events/correlation/recent?limit=            → CorrelationGroup[]
// ─────────────────────────────────────────────────────────────────────────────

import type {
  CorrelationEventMember,
  CorrelationGroup,
  CorrelationGroupPage,
  CorrelationRelationship,
  EventLogQuery,
} from '@/types/eventCorrelation'

export interface IEventCorrelationService {
  /** Paginated, filtered Event/Incident Log (server-side in Phase 2). */
  listGroups(query: EventLogQuery): Promise<CorrelationGroupPage>
  /** Recent groups for the Dashboard feed (§59/§161). */
  listRecent(limit: number): Promise<CorrelationGroup[]>
  /** Groups involving a given camera (Single Camera context, §164). */
  listForCamera(cameraId: string, limit: number): Promise<CorrelationGroup[]>
  /** Full group for the Incident/Event detail view. */
  getGroup(correlationId: string): Promise<CorrelationGroup>
  /** Relationship list for the group inspection panel (§65/§127). */
  getRelationships(correlationId: string): Promise<CorrelationRelationship[]>
  /** A single member signal (§64/§128). */
  getMemberEvent(eventId: string): Promise<CorrelationEventMember>
  /** Data provenance of this provider: 'DEMO' (fixtures) or 'LIVE'. */
  readonly source: 'DEMO' | 'LIVE'
}
