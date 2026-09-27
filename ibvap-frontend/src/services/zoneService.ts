// ─────────────────────────────────────────────────────────────────────────────
// IBVAP Component 1 — Zone Service
// ─────────────────────────────────────────────────────────────────────────────

import { api, qs } from './api'
import type { Zone, ZoneCreatePayload } from '@/types'

export interface ZoneService {
  list(cameraId?: string, activeOnly?: boolean): Promise<Zone[]>
  get(zoneId: string): Promise<Zone>
  create(payload: ZoneCreatePayload): Promise<Zone>
  update(zoneId: string, patch: Partial<ZoneCreatePayload>): Promise<Zone>
  remove(zoneId: string): Promise<void>
}

export const zoneService: ZoneService = {
  async list(cameraId, activeOnly) {
    const { data } = await api.get<Zone[]>(`/zones${qs({ camera_id: cameraId, active_only: activeOnly })}`)
    return data
  },

  async get(zoneId) {
    const { data } = await api.get<Zone>(`/zones/${zoneId}`)
    return data
  },

  async create(payload) {
    const { data } = await api.post<Zone>('/zones', payload)
    return data
  },

  async update(zoneId, patch) {
    const { data } = await api.put<Zone>(`/zones/${zoneId}`, patch)
    return data
  },

  async remove(zoneId) {
    await api.delete(`/zones/${zoneId}`)
  },
}