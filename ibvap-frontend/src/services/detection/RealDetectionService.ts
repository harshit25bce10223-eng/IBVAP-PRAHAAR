// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 5 — Real Detection Service
//
// Implements IDetectionService against the live /api/v1 backend.
// When VITE_DETECTION_MODE=REAL and the backend is unreachable, all methods
// throw a typed error "DETECTION DATA UNAVAILABLE" — they NEVER fall back to
// mock fixtures.
// ─────────────────────────────────────────────────────────────────────────────
import axios from 'axios'
import type {
  DetectionFeed,
  DetectionQuery,
  DetectionResult,
  DetectionResultPage,
  DetectionSummary,
} from '@/types/detection'
import type { IDetectionService } from './IDetectionService'

const API_BASE = '/api/v1'

class RealDetectionService implements IDetectionService {
  readonly source = 'REAL' as const

  private client = axios.create({
    baseURL: API_BASE,
    timeout: 30_000,
    headers: { 'Content-Type': 'application/json' },
  })

  private handleError(error: unknown): never {
    if (axios.isAxiosError(error)) {
      if (!error.response) {
        throw new Error('DETECTION DATA UNAVAILABLE: backend unreachable')
      }
      const detail = error.response.data?.detail ?? error.message
      throw new Error(`Detection API Error (${error.response.status}): ${detail}`)
    }
    throw error
  }

  // ─── IDetectionService ────────────────────────────────────────────────────

  async listDetections(query: DetectionQuery): Promise<DetectionResultPage> {
    try {
      const params = new URLSearchParams()
      if (query.search) params.set('search', query.search)
      if (query.cameraId !== 'ALL') params.set('camera_id', query.cameraId)
      if (query.class !== 'ALL') params.set('class_name', query.class)
      if (query.quality !== 'ALL') params.set('quality', query.quality)
      if (query.source !== 'ALL') params.set('source', query.source)
      if (query.timeRange !== 'all') {
        const minutes =
          query.timeRange === '15m' ? 15 : query.timeRange === '1h' ? 60 : 24 * 60
        params.set('from_time', new Date(Date.now() - minutes * 60_000).toISOString())
      }
      if (query.confidenceMin !== null) params.set('min_confidence', String(query.confidenceMin))
      params.set('sort', query.sort)
      params.set('order', query.order)
      params.set('page', String(query.page))
      params.set('page_size', String(query.pageSize))

      const response = await this.client.get<DetectionResultPage>('/detections/', { params })
      return response.data
    } catch (error) {
      this.handleError(error)
    }
  }

  async getDetection(detectionId: string): Promise<DetectionResult> {
    try {
      const response = await this.client.get<DetectionResult>(`/detections/${detectionId}`)
      return response.data
    } catch (error) {
      this.handleError(error)
    }
  }

  async getFeed(cameraId: string): Promise<DetectionFeed> {
    try {
      const response = await this.client.get<DetectionFeed>(`/detections/cameras/${cameraId}`)
      return response.data
    } catch (error) {
      this.handleError(error)
    }
  }

  async getSummary(cameraId: string): Promise<DetectionSummary> {
    try {
      const response = await this.client.get<DetectionSummary>(
        `/detections/cameras/${cameraId}/summary`,
      )
      return response.data
    } catch (error) {
      this.handleError(error)
    }
  }
}

export const realDetectionService = new RealDetectionService()
