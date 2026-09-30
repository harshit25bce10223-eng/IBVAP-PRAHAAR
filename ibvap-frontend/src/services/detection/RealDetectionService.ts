// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 5 — Real Detection Service
//
// Implements IDetectionService against the live /api/v1 backend. Every
// response is normalized through `mapDetection.ts` — raw snake_case payloads
// never reach the UI. When VITE_DETECTION_MODE=REAL and the backend is
// unreachable, all methods throw a typed error "DETECTION DATA UNAVAILABLE" —
// they NEVER fall back to mock fixtures (§22).
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
import {
  confidencePercentToRatioParam,
  mapCameraDetectionSummary,
  mapDetection,
  mapDetectionFeed,
  mapDetectionPage,
  sortToBackendParams,
  timeRangeFromIso,
} from './mapDetection'

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
      const fromTime = timeRangeFromIso(query.timeRange, new Date())
      if (fromTime) params.set('from_time', fromTime)
      if (query.confidenceMin !== null) {
        params.set('min_confidence', confidencePercentToRatioParam(query.confidenceMin))
      }
      const { sort, order } = sortToBackendParams(query.sort, query.order)
      params.set('sort', sort)
      params.set('order', order)
      params.set('page', String(query.page))
      params.set('page_size', String(query.pageSize))

      const response = await this.client.get<unknown>('/detections/', { params })
      return mapDetectionPage(response.data)
    } catch (error) {
      this.handleError(error)
    }
  }

  async getDetection(detectionId: string): Promise<DetectionResult> {
    try {
      const response = await this.client.get<unknown>(`/detections/${detectionId}`)
      const detection = mapDetection(response.data)
      if (!detection) {
        throw new Error(`Detection ${detectionId} was not found or unavailable.`)
      }
      return detection
    } catch (error) {
      this.handleError(error)
    }
  }

  async getFeed(cameraId: string): Promise<DetectionFeed> {
    try {
      const response = await this.client.get<unknown>(`/detections/cameras/${cameraId}/feed`)
      return mapDetectionFeed(response.data, cameraId)
    } catch (error) {
      this.handleError(error)
    }
  }

  async getSummary(cameraId: string): Promise<DetectionSummary> {
    try {
      const response = await this.client.get<unknown>(`/detections/cameras/${cameraId}/summary`)
      const summary = mapCameraDetectionSummary(response.data, cameraId)
      if (!summary) {
        throw new Error('DETECTION SUMMARY UNAVAILABLE: backend returned no summary.')
      }
      return summary
    } catch (error) {
      this.handleError(error)
    }
  }
}

export const realDetectionService = new RealDetectionService()
