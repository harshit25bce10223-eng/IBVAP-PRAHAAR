// ─────────────────────────────────────────────────────────────────────────────
// IBVAP Component 1 — Incident / Event Service
// ─────────────────────────────────────────────────────────────────────────────

import { api, qs } from './api'
import type { EventRecord, IncidentRecord } from '@/types'

export interface IncidentService {
  list(cameraId?: string, limit?: number): Promise<IncidentRecord[]>
  get(incidentId: string): Promise<IncidentRecord>
  listEvents(cameraId?: string, limit?: number): Promise<EventRecord[]>
}

export const incidentService: IncidentService = {
  async list(cameraId, limit = 50) {
    const { data } = await api.get<IncidentRecord[]>(`/incidents${qs({ camera_id: cameraId, limit })}`)
    return data
  },

  async get(incidentId) {
    const { data } = await api.get<IncidentRecord>(`/incidents/${incidentId}`)
    return data
  },

  async listEvents(cameraId, limit = 50) {
    const { data } = await api.get<EventRecord[]>(`/events${qs({ camera_id: cameraId, limit })}`)
    return data
  },
}