// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 6 — Real tracking provider seam (Phase 2 backend integration)
//
// Strictly separates real tracking pipeline from demo fixtures (§80, §81, §257).
// When active, any failure throws a clean tracking error; NEVER falls back to demo data.
// ─────────────────────────────────────────────────────────────────────────────

import axios from 'axios'
import type {
  Track,
  TrackingFeed,
  TrackObservation,
  TrackQuery,
  TrackResultPage,
  TrackSummary,
} from '@/types/tracking'
import type { ITrackingService } from './ITrackingService'

const API_BASE = '/api/v1'

interface ApiTrackResponse {
  trackId: string
  cameraId: string
  status: string
  objectClass: string
  firstSeenAt: string
  lastSeenAt: string
  observedAt: string
  updatedAt?: string | null
  ageMs?: number | null
  durationSec?: number | null
  detectionCount: number
  currentDetectionId?: string | null
  currentBoundingBox?: { x: number; y: number; width: number; height: number } | null
  trajectory?: { x: number; y: number; timestamp?: string; observationId?: string; sequence?: number; speed?: number | null }[] | null
  speed?: number | null
  velocity?: number | null
  direction?: string | null
  confidence?: number | null
  continuityQuality?: string | null
  source: string
  dataSource: string
  provider?: string | null
  trackerName?: string | null
  trackerVersion?: string | null
  eventId?: string | null
  correlationId?: string | null
  incidentId?: string | null
  evidenceId?: string | null
  candidateEntityId?: string | null
  crossCameraCandidate?: {
    targetCameraId: string
    candidateTrackId: string
    continuityConfidence?: number | null
    gapDurationSec?: number | null
    sequenceNumber?: number
    note?: string
  } | null
  cameraHealthContext?: {
    status: string
    reliability: string
    viewpointShiftDetected?: boolean
    note?: string | null
  } | undefined
  regionProfile?: string | null
  sectorId?: string | null
  revision?: number | null
  schemaVersion?: string | null
  previousClass?: string | null
  classRevisionReason?: string | null
  classRevisedAt?: string | null
  dataCompleteness?: string | null
  missingObservationsNote?: string | null
}

interface ApiTrackObservationResponse {
  observationId: string
  trackId: string
  detectionId?: string | null
  cameraId: string
  observedAt: string
  receivedAt?: string | null
  bbox?: { x: number; y: number; width: number; height: number } | null
  velocity?: number | null
  speed?: number | null
  direction?: string | null
  quality?: string | null
  confidence?: number | null
  sequence?: number | null
  source: string
  frameNumber?: number | null
  frameId?: string | null
  evidenceId?: string | null
}

interface ApiTrackingFeedResponse {
  cameraId: string
  state: string
  lastUpdatedAt?: string | null
  tracks: ApiTrackResponse[]
  providerHealth?: string | null
}

interface ApiTrackSummaryResponse {
  cameraId: string
  totalActive: number
  totalTracks: number
  byClass: Record<string, number>
  byStatus: Record<string, number>
  lastUpdatedAt?: string | null
}

interface ApiTrackResultPageResponse {
  tracks: ApiTrackResponse[]
  total: number
  page: number
  pageSize: number
}

class RealTrackingService implements ITrackingService {
  readonly source = 'REAL' as const

  private client = axios.create({
    baseURL: API_BASE,
    timeout: 30_000,
    headers: { 'Content-Type': 'application/json' },
  })

  private handleError(error: unknown): never {
    if (axios.isAxiosError(error)) {
      if (!error.response) {
        throw new Error('TRACKING DATA UNAVAILABLE: backend unreachable')
      }
      const detail = error.response.data?.detail ?? error.message
      throw new Error(`Tracking API Error (${error.response.status}): ${detail}`)
    }
    throw error
  }

  private mapApiTrack(api: ApiTrackResponse): Track {
    return {
      trackId: api.trackId,
      cameraId: api.cameraId,
      status: api.status as Track['status'],
      objectClass: api.objectClass as Track['objectClass'],
      firstSeenAt: api.firstSeenAt,
      lastSeenAt: api.lastSeenAt,
      ageMs: api.ageMs ?? null,
      durationSec: api.durationSec ?? null,
      detectionCount: api.detectionCount,
      currentDetectionId: api.currentDetectionId ?? null,
      currentBoundingBox: api.currentBoundingBox ?? null,
      trajectory: api.trajectory ?? null,
      speed: api.speed ?? null,
      velocity: api.velocity ?? null,
      direction: api.direction ?? null,
      confidence: api.confidence ?? null,
      continuityQuality: api.continuityQuality as Track['continuityQuality'] ?? null,
      source: api.source as Track['source'],
      provider: api.provider ?? null,
      trackerName: api.trackerName ?? null,
      trackerVersion: api.trackerVersion ?? null,
      eventId: api.eventId ?? null,
      correlationId: api.correlationId ?? null,
      incidentId: api.incidentId ?? null,
      evidenceId: api.evidenceId ?? null,
      candidateEntityId: api.candidateEntityId ?? null,
      crossCameraCandidate: api.crossCameraCandidate ? {
        targetCameraId: api.crossCameraCandidate.targetCameraId,
        candidateTrackId: api.crossCameraCandidate.candidateTrackId,
        continuityConfidence: api.crossCameraCandidate.continuityConfidence ?? null,
        gapDurationSec: api.crossCameraCandidate.gapDurationSec ?? null,
        sequenceNumber: api.crossCameraCandidate.sequenceNumber,
        note: api.crossCameraCandidate.note,
      } : null,
      cameraHealthContext: (() => {
        const ctx = api.cameraHealthContext
        if (!ctx) return undefined
        // Type assertion needed because TS doesn't narrow properly
        const healthCtx = ctx as { status: string; reliability: string; viewpointShiftDetected?: boolean; note?: string | null }
        return {
          status: healthCtx.status as 'ONLINE' | 'DEGRADED' | 'OFFLINE' | 'UNKNOWN',
          reliability: healthCtx.reliability as 'HIGH' | 'MEDIUM' | 'LOW' | 'UNKNOWN',
          viewpointShiftDetected: healthCtx.viewpointShiftDetected,
          note: healthCtx.note ?? null,
        }
      })(),
      regionProfile: api.regionProfile ?? null,
      sectorId: api.sectorId ?? null,
      observedAt: api.observedAt,
      updatedAt: api.updatedAt ?? undefined,
      dataSource: api.dataSource as Track['dataSource'],
      revision: api.revision ?? undefined,
      schemaVersion: api.schemaVersion ?? undefined,
      previousClass: api.previousClass as Track['previousClass'] ?? undefined,
      classRevisionReason: api.classRevisionReason ?? undefined,
      classRevisedAt: api.classRevisedAt ?? undefined,
      dataCompleteness: (() => {
        const dc = api.dataCompleteness
        return dc != null ? dc as Track['dataCompleteness'] : undefined
      })(),
      missingObservationsNote: api.missingObservationsNote ?? undefined,
    }
  }

  private mapApiObservation(api: ApiTrackObservationResponse): TrackObservation {
    return {
      observationId: api.observationId,
      trackId: api.trackId,
      detectionId: api.detectionId ?? null,
      cameraId: api.cameraId,
      observedAt: api.observedAt,
      receivedAt: api.receivedAt ?? null,
      bbox: api.bbox ?? null,
      velocity: api.velocity ?? null,
      speed: api.speed ?? null,
      direction: api.direction ?? null,
      quality: api.quality as TrackObservation['quality'] ?? null,
      confidence: api.confidence ?? null,
      sequence: api.sequence ?? null,
      source: api.source as TrackObservation['source'],
      frameNumber: api.frameNumber ?? null,
      frameId: api.frameId ?? null,
      evidenceId: api.evidenceId ?? null,
    }
  }

  private mapApiFeed(api: ApiTrackingFeedResponse): TrackingFeed {
    return {
      cameraId: api.cameraId,
      state: api.state as TrackingFeed['state'],
      lastUpdatedAt: api.lastUpdatedAt ?? null,
      tracks: api.tracks.map(t => this.mapApiTrack(t)),
      providerHealth: api.providerHealth as TrackingFeed['providerHealth'] ?? undefined,
    }
  }

  // ─── ITrackingService ────────────────────────────────────────────────────

  async getTrack(trackId: string): Promise<Track> {
    try {
      const response = await this.client.get<ApiTrackResponse>(`/tracks/${trackId}`)
      return this.mapApiTrack(response.data)
    } catch (error) {
      this.handleError(error)
    }
  }

  async listTracks(query: TrackQuery): Promise<TrackResultPage> {
    try {
      const params = new URLSearchParams()
      if (query.search) params.set('search', query.search)
      if (query.cameraId !== 'ALL') params.set('camera_id', query.cameraId)
      if (query.class !== 'ALL') params.set('class', query.class)
      if (query.status !== 'ALL') params.set('status', query.status)
      if (query.source !== 'ALL') params.set('source', query.source)
      if (query.timeRange !== 'all') {
        const minutes =
          query.timeRange === '15m' ? 15 : query.timeRange === '1h' ? 60 : 24 * 60
        params.set('from_time', new Date(Date.now() - minutes * 60_000).toISOString())
      }
      params.set('sort', query.sort)
      params.set('order', query.order)
      params.set('page', String(query.page))
      params.set('pageSize', String(query.pageSize))

      const response = await this.client.get<ApiTrackResultPageResponse>('/tracks', { params })
      return {
        tracks: response.data.tracks.map(t => this.mapApiTrack(t)),
        total: response.data.total,
        page: response.data.page,
        pageSize: response.data.pageSize,
      }
    } catch (error) {
      this.handleError(error)
    }
  }

  async listCameraTracks(cameraId: string): Promise<Track[]> {
    try {
      const response = await this.client.get<ApiTrackResponse[]>(`/cameras/${cameraId}/tracks`)
      return response.data.map(t => this.mapApiTrack(t))
    } catch (error) {
      this.handleError(error)
    }
  }

  async getTrackHistory(trackId: string): Promise<TrackObservation[]> {
    try {
      const response = await this.client.get<{ observations: ApiTrackObservationResponse[] }>(`/tracks/${trackId}/observations`)
      return response.data.observations.map(o => this.mapApiObservation(o))
    } catch (error) {
      this.handleError(error)
    }
  }

  async getTrackFeed(cameraId: string): Promise<TrackingFeed> {
    try {
      const response = await this.client.get<ApiTrackingFeedResponse>(`/cameras/${cameraId}/tracks/feed`)
      return this.mapApiFeed(response.data)
    } catch (error) {
      this.handleError(error)
    }
  }

  async getTrackSummary(cameraId: string): Promise<TrackSummary> {
    try {
      const response = await this.client.get<ApiTrackSummaryResponse>(`/cameras/${cameraId}/tracks/summary`)
      return {
        cameraId: response.data.cameraId,
        totalActive: response.data.totalActive,
        totalTracks: response.data.totalTracks,
        byClass: response.data.byClass as TrackSummary['byClass'],
        byStatus: response.data.byStatus as TrackSummary['byStatus'],
        lastUpdatedAt: response.data.lastUpdatedAt ?? null,
      }
    } catch (error) {
      this.handleError(error)
    }
  }

  async getActiveTracks(): Promise<Track[]> {
    try {
      const response = await this.client.get<ApiTrackResponse[]>('/tracks/recent')
      return response.data.map(t => this.mapApiTrack(t))
    } catch (error) {
      this.handleError(error)
    }
  }
}

export const realTrackingService = new RealTrackingService()