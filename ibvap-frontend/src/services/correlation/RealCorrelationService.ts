// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 4 — Real Event Correlation Service
//
// Implements IEventCorrelationService against the live /api/v1 backend.
// When in REAL mode and the backend is unreachable, every method throws a
// typed "EVENT/CORRELATION DATA UNAVAILABLE" error — it NEVER silently falls
// back to mock fixtures (§63). Backend snake_case payloads are mapped to the
// canonical frontend camelCase; unknown/missing fields stay null, never
// fabricated.
// ─────────────────────────────────────────────────────────────────────────────
import axios from 'axios'
import type {
  CameraReliabilityContext,
  CorrelationConfidence,
  CorrelationEventKind,
  CorrelationEventMember,
  CorrelationExplanation,
  CorrelationGroup,
  CorrelationGroupPage,
  CorrelationHistory,
  CorrelationModality,
  CorrelationRelationship,
  CorrelationSource,
  CorrelationStatus,
  CorrelationTransition,
  EventLogQuery,
  Reliability,
  TrackCandidate,
} from '@/types/eventCorrelation'
import type { Severity } from '@/types/risk'
import type { IEventCorrelationService } from './IEventCorrelationService'

const API_BASE = '/api/v1'

class RealCorrelationService implements IEventCorrelationService {
  readonly source = 'LIVE' as const

  private client = axios.create({
    baseURL: API_BASE,
    timeout: 30_000,
    headers: { 'Content-Type': 'application/json' },
  })

  private handleError(error: unknown): never {
    if (axios.isAxiosError(error)) {
      if (!error.response) {
        throw new Error('EVENT/CORRELATION DATA UNAVAILABLE: backend unreachable')
      }
      const detail = error.response.data?.detail ?? error.message
      throw new Error(`Correlation API Error (${error.response.status}): ${detail}`)
    }
    throw error
  }

  private parseMember(raw: any): CorrelationEventMember {
    return {
      eventId: raw.event_id ?? '',
      kind: (raw.kind as CorrelationEventKind) ?? 'UNKNOWN',
      source: (raw.source as CorrelationSource) ?? 'UNKNOWN',
      modality: (raw.modality as CorrelationModality) ?? 'UNKNOWN',
      cameraId: raw.camera_id ?? '',
      zoneId: raw.zone_id ?? null,
      sectorId: raw.sector_id ?? null,
      regionProfile: raw.region_profile ?? null,
      trackId: raw.track_id ?? null,
      timestamp: raw.timestamp ?? null,
      severity: (raw.severity as Severity) ?? null,
      reliability: (raw.reliability as Reliability) ?? null,
      confidence: raw.confidence ?? null,
      evidenceIds: Array.isArray(raw.evidence_ids) ? raw.evidence_ids : [],
      healthContext: raw.health_context ?? null,
      // C5/C6/C7 downstream references surfaced verbatim (Task 5)
      detectionId: raw.detection_id ?? null,
      anprPlate: raw.anpr_plate ?? null,
      anprPlateConfidence: raw.anpr_plate_confidence ?? null,
      anprQuality: raw.anpr_quality ?? null,
      anprSightingId: raw.anpr_sighting_id ?? null,
    } as CorrelationEventMember
  }

  private parseRelationship(raw: any): CorrelationRelationship {
    return {
      fromEventId: raw.from_event_id ?? '',
      toEventId: raw.to_event_id ?? '',
      type: (raw.type as CorrelationRelationship['type']) ?? 'CONTEXTUAL',
      strength: raw.strength ?? null,
      explanation: raw.explanation ?? '',
    }
  }

  private parseHistory(raw: any): CorrelationHistory {
    const rawHistory = Array.isArray(raw) ? raw : []
    // rawHistory is ordered by revision asc; the newest is the last row.
    const transitions: CorrelationTransition[] = rawHistory.map(h => ({
      status: (h.status as CorrelationStatus) ?? 'UNKNOWN',
      at: h.timestamp ?? h.created_at ?? '',
      note: h.reason ?? null,
    }))
    const created = rawHistory[0]?.created_at ?? ''
    const updated = rawHistory[rawHistory.length - 1]?.created_at ?? created
    return { createdAt: created, updatedAt: updated, transitions }
  }

  private parseGroup(raw: any): CorrelationGroup {
    const members: CorrelationEventMember[] = Array.isArray(raw.members)
      ? raw.members.map((m: unknown) => this.parseMember(m))
      : Array.isArray(raw.member_events)
        ? raw.member_events.map((m: unknown) => this.parseMember(m))
        : []
    const relationships: CorrelationRelationship[] = Array.isArray(raw.relationships)
      ? raw.relationships.map((r: unknown) => this.parseRelationship(r))
      : []
    const explanation: CorrelationExplanation[] = Array.isArray(raw.explanation)
      ? raw.explanation.map((e: any) => ({
          facet: e.facet ?? 'CONTEXTUAL',
          label: e.label ?? '',
          detail: e.detail ?? '',
        }))
      : []

    const confidence: CorrelationConfidence | null =
      raw.confidence != null
        ? { value: Number(raw.confidence), note: '' }
        : null
    const risk = {
      score: raw.risk_score ?? raw.incident_risk_score ?? null,
      severity: (raw.risk_severity as Severity) ?? null,
      incidentIds: Array.isArray(raw.risk_incident_ids) ? raw.risk_incident_ids : [],
    }
    const uncertaintyRaw = raw.uncertainty
    const uncertainty = {
      reliability: (uncertaintyRaw?.reliability ?? raw.uncertainty_reliability ?? 'UNKNOWN') as Reliability,
      note: uncertaintyRaw?.note ?? raw.uncertainty_note ?? null,
    }
    const trackCandidate: TrackCandidate | null =
      raw.track_candidate_id
        ? {
            trackId: raw.track_candidate_id,
            confidence: raw.track_candidate_confidence ?? null,
            label: raw.track_candidate_label ?? 'possible continuation',
          }
        : null
    const healthContext: CameraReliabilityContext[] = raw.health_context
      ? [raw.health_context] as CameraReliabilityContext[]
      : []

    return {
      correlationId: raw.correlation_id ?? '',
      incidentId: raw.incident_id ?? null,
      incidentState: (raw.incident_state as CorrelationGroup['incidentState']) ?? null,
      status: (raw.status as CorrelationStatus) ?? 'UNKNOWN',
      state: (raw.state as CorrelationGroup['state']) ?? 'OPEN',
      startedAt: raw.started_at ?? null,
      endedAt: raw.ended_at ?? null,
      eventCount: raw.event_count ?? members.length,
      cameraCount: raw.camera_count ?? 0,
      memberEventsLoaded: members.length === raw.event_count ? null : members.length,
      memberEvents: members,
      primaryEventId: raw.primary_event_id ?? null,
      relationships,
      explanation,
      confidence,
      temporalWindowSec: raw.temporal_window_seconds ?? null,
      risk,
      uncertainty,
      trackCandidate,
      cameraChain: raw.camera_chain ?? null,
      modalities: Array.isArray(raw.modalities) ? raw.modalities : [],
      sectorId: raw.sector_id ?? null,
      regionProfile: raw.region_profile ?? null,
      sources: Array.isArray(raw.sources) ? raw.sources : [],
      healthContext,
      evidenceCount: raw.evidence_count ?? 0,
      connectivity: (raw.connectivity as CorrelationGroup['connectivity']) ?? 'UNKNOWN',
      duplicatedOrSuppressed: raw.duplicated_or_suppressed ?? false,
      history: this.parseHistory(raw.history),
      updatedAt: raw.updated_at ?? raw.created_at ?? '',
      // Extra human-readable backend fields (Task 5) kept available.
      explanationSummary: raw.explanation_summary ?? null,
      correlationStrength: (raw.correlation_strength as CorrelationGroup['correlationStrength']) ?? null,
    }
  }

  // ─── IEventCorrelationService ──────────────────────────────────────────────

  async listGroups(query: EventLogQuery): Promise<CorrelationGroupPage> {
    try {
      const params: Record<string, string> = {
        page: String(query.page),
        page_size: String(query.pageSize),
      }
      if (query.search) params['search'] = query.search
      if (query.correlation !== 'ALL') params['status'] = query.correlation
      if (query.severity !== 'ALL') params['severity'] = query.severity
      if (query.cameraId !== 'ALL') params['camera_id'] = query.cameraId
      if (query.sectorId !== 'ALL') params['sector_id'] = query.sectorId
      if (query.source !== 'ALL') params['source'] = query.source
      if (query.timeRange !== 'all') params['time_range'] = query.timeRange
      if (query.order !== 'desc') params['order'] = query.order
      if (query.sort !== 'time') params['sort'] = query.sort

      const response = await this.client.get<{ groups: any[]; total: number }>('/correlations/', { params })
      return {
        groups: (response.data.groups ?? []).map(g => this.parseGroup(g)),
        total: response.data.total ?? 0,
      }
    } catch (error) {
      this.handleError(error)
    }
  }

  async listRecent(limit: number): Promise<CorrelationGroup[]> {
    try {
      const response = await this.client.get<{ groups: any[]; total: number }>('/correlations/', {
        params: { page: '1', page_size: String(limit), sort: 'started_at', order: 'desc' },
      })
      return (response.data.groups ?? []).map(g => this.parseGroup(g))
    } catch (error) {
      this.handleError(error)
    }
  }

  async listForCamera(cameraId: string, limit: number): Promise<CorrelationGroup[]> {
    try {
      const response = await this.client.get<{ groups: any[]; total: number }>('/correlations/', {
        params: { page: '1', page_size: String(limit), camera_id: cameraId, sort: 'started_at', order: 'desc' },
      })
      return (response.data.groups ?? []).map(g => this.parseGroup(g))
    } catch (error) {
      this.handleError(error)
    }
  }

  async getGroup(correlationId: string): Promise<CorrelationGroup> {
    try {
      const response = await this.client.get<any>(`/correlations/${correlationId}`)
      return this.parseGroup(response.data)
    } catch (error) {
      this.handleError(error)
    }
  }

  async getRelationships(correlationId: string): Promise<CorrelationRelationship[]> {
    try {
      const response = await this.client.get<{ relationships: any[] }>(`/correlations/${correlationId}/relationships`)
      return (response.data.relationships ?? []).map(r => this.parseRelationship(r))
    } catch (error) {
      this.handleError(error)
    }
  }

  async getMemberEvent(eventId: string): Promise<CorrelationEventMember> {
    try {
      const response = await this.client.get<any>(`/correlations/events/${eventId}`)
      return this.parseMember(response.data.member ?? response.data)
    } catch (error) {
      this.handleError(error)
    }
  }
}

export const realCorrelationService = new RealCorrelationService()