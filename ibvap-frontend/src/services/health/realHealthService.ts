// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 2 — Real Health Service (Backend API Integration)
// ─────────────────────────────────────────────────────────────────────────────

import { api, qs, asApiError } from '@/services/api'
import type { CameraHealth } from '@/types/cameraHealth'
import type { IHealthService } from './IHealthService'

export class RealHealthService implements IHealthService {
  readonly source = 'LIVE' as const

  async get(cameraId: string): Promise<CameraHealth> {
    try {
      const response = await api.get<CameraHealth>(`/cameras/${encodeURIComponent(cameraId)}/health`)
      return response.data
    } catch (err) {
      const apiErr = asApiError(err)
      throw new Error(`[RealHealthService] Failed to load telemetry for ${cameraId}: ${apiErr.message}`)
    }
  }

  async list(cameraIds?: string[]): Promise<CameraHealth[]> {
    try {
      const params = qs({ ids: cameraIds && cameraIds.length > 0 ? cameraIds.join(',') : undefined })
      const response = await api.get<CameraHealth[]>(`/cameras/health${params}`)
      return response.data
    } catch (err) {
      const apiErr = asApiError(err)
      throw new Error(`[RealHealthService] Failed to list camera health: ${apiErr.message}`)
    }
  }
}

export const realHealthService = new RealHealthService()
