// ─────────────────────────────────────────────────────────────────────────────
// Component 7 — ANPR Service (Mock + Real + Interface)
//
// REAL mode talks exclusively to /api/v1/anpr/... (§42) and NEVER falls back
// to demo data. When the backend is unreachable it throws
// 'ANPR DATA UNAVAILABLE: backend unreachable' so the UI can surface the
// spec-required unavailable state (§30/§44) instead of fake sightings.
//
// Search classification mirrors the backend repository phases exactly (§24):
// exact normalized → raw read → partial → candidate text → related sighting.
// ─────────────────────────────────────────────────────────────────────────────
import axios from 'axios'
import { api, qs } from '@/services/api'
import type {
  ANPRCameraFeed,
  ANPRCameraSummary,
  ANPRFilter,
  ANPRProviderHealth,
  ANPRSummary,
  PlateCandidate,
  VehicleHistory,
  VehicleSearchResult,
  VehicleSighting,
} from '@/types/anpr'
import {
  ALL_MOCK_SIGHTINGS,
  MOCK_PROVIDER_HEALTH,
  MOCK_SUMMARY,
  MOCK_VEHICLE_HISTORY_VEH_A001,
} from './mockData'

export interface SightingPage {
  sightings: VehicleSighting[]
  hasMore: boolean
  nextCursor: string | null
}

export interface IANPRService {
  getSummary(): Promise<ANPRSummary>
  getProviderHealth(): Promise<ANPRProviderHealth>
  listSightings(filter: Partial<ANPRFilter>): Promise<SightingPage>
  getSighting(sightingId: string): Promise<VehicleSighting>
  getSightingCandidates(sightingId: string): Promise<PlateCandidate[]>
  getVehicle(vehicleId: string): Promise<VehicleSighting>
  getVehicleHistory(vehicleId: string): Promise<VehicleHistory>
  searchPlate(query: string, filter?: Partial<ANPRFilter>): Promise<VehicleSearchResult[]>
  getCameraSightings(cameraId: string, filter?: Partial<ANPRFilter>): Promise<SightingPage>
  getCameraFeed(cameraId: string): Promise<ANPRCameraFeed>
  getCameraSummary(cameraId: string): Promise<ANPRCameraSummary>
}

function delay(ms = 400): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

/** Mirror of the backend _norm_plate: uppercase, alphanumeric only. */
function normPlate(text: string): string {
  return text.toUpperCase().replace(/[^A-Z0-9]/g, '')
}

export class MockANPRService implements IANPRService {
  async getSummary(): Promise<ANPRSummary> {
    await delay()
    return { ...MOCK_SUMMARY }
  }

  async getProviderHealth(): Promise<ANPRProviderHealth> {
    await delay(120)
    return { ...MOCK_PROVIDER_HEALTH }
  }

  async listSightings(filter: Partial<ANPRFilter>): Promise<SightingPage> {
    await delay()
    let results = [...ALL_MOCK_SIGHTINGS]
    if (filter.cameraId) results = results.filter(s => s.cameraId === filter.cameraId)
    if (filter.vehicleId) results = results.filter(s => s.vehicleId === filter.vehicleId)
    if (filter.trackId) results = results.filter(s => s.vehicleTrackId === filter.trackId)
    if (filter.vehicleClass) results = results.filter(s => s.vehicleClass === filter.vehicleClass)
    if (filter.quality) results = results.filter(s => s.plateRead?.quality === filter.quality)
    if (filter.search) {
      const q = filter.search.toUpperCase()
      results = results.filter(s =>
        s.plateRead?.displayRead?.toUpperCase().includes(q) ||
        s.plateCandidates.some(c => c.rawRead.toUpperCase().includes(q)) ||
        s.vehicleId.toUpperCase().includes(q) ||
        s.sightingId.toUpperCase().includes(q) ||
        // Track linkage (mirrors the backend search which covers track_id) —
        // lets /anpr?track_id=TRK-... resolve in DEMO mode too.
        (s.vehicleTrackId?.toUpperCase().includes(q) ?? false)
      )
    }
    if (filter.direction) results = results.filter(s => s.vehicleDirection === filter.direction)
    if (filter.watchlistStatus) results = results.filter(s => s.watchlistStatus === filter.watchlistStatus)
    if (typeof filter.confidenceMin === 'number' && filter.confidenceMin > 0) {
      results = results.filter(s => (s.confidence ?? 0) >= filter.confidenceMin!)
    }
    if (typeof filter.confidenceMax === 'number' && filter.confidenceMax < 1) {
      results = results.filter(s => (s.confidence ?? 0) <= filter.confidenceMax!)
    }
    if (filter.from) {
      const fromMs = Date.parse(filter.from)
      if (!Number.isNaN(fromMs)) results = results.filter(s => Date.parse(s.observedAt) >= fromMs)
    }
    if (filter.to) {
      const toMs = Date.parse(filter.to)
      if (!Number.isNaN(toMs)) results = results.filter(s => Date.parse(s.observedAt) <= toMs)
    }
    return { sightings: results, hasMore: false, nextCursor: null }
  }

  async getSighting(sightingId: string): Promise<VehicleSighting> {
    await delay(200)
    const s = ALL_MOCK_SIGHTINGS.find(x => x.sightingId === sightingId)
    if (!s) throw new Error('Sighting ' + sightingId + ' not found in mock data.')
    return { ...s }
  }

  async getSightingCandidates(sightingId: string): Promise<PlateCandidate[]> {
    await delay(150)
    const s = ALL_MOCK_SIGHTINGS.find(x => x.sightingId === sightingId)
    if (!s) throw new Error('Sighting ' + sightingId + ' not found in mock data.')
    return s.plateCandidates.map(c => ({ ...c }))
  }

  async getVehicle(vehicleId: string): Promise<VehicleSighting> {
    await delay(200)
    const sightings = ALL_MOCK_SIGHTINGS.filter(s => s.vehicleId === vehicleId)
    if (!sightings.length) throw new Error('Vehicle ' + vehicleId + ' not found in mock data.')
    const newest = [...sightings].sort((a, b) => b.observedAt.localeCompare(a.observedAt))[0]
    return { ...newest }
  }

  async getVehicleHistory(vehicleId: string): Promise<VehicleHistory> {
    await delay()
    if (vehicleId === 'VEH-A001') return { ...MOCK_VEHICLE_HISTORY_VEH_A001 }
    const sightings = ALL_MOCK_SIGHTINGS.filter(s => s.vehicleId === vehicleId)
    if (!sightings.length) throw new Error('No sightings for vehicle ' + vehicleId + '.')
    const times = sightings.map(s => s.observedAt).sort()
    return {
      vehicleId,
      sightings,
      firstSeen: times[0],
      lastSeen: times[times.length - 1],
      totalSightings: sightings.length,
    }
  }

  async searchPlate(query: string, filter?: Partial<ANPRFilter>): Promise<VehicleSearchResult[]> {
    await delay()
    const qRaw = query.toUpperCase().trim()
    const qNorm = normPlate(query)
    if (!qRaw || !qNorm) return []

    const inCamera = (s: VehicleSighting) => !filter?.cameraId || s.cameraId === filter.cameraId
    const results: VehicleSearchResult[] = []
    const seen = new Set<string>()
    const collect = (rows: VehicleSighting[], matchType: VehicleSearchResult['matchType']) => {
      for (const s of rows) {
        if (seen.has(s.sightingId)) continue
        seen.add(s.sightingId)
        results.push({ sighting: s, matchType })
      }
    }

    // A — exact normalized read
    collect(
      ALL_MOCK_SIGHTINGS.filter(s => inCamera(s) && (s.plateRead?.normalizedRead?.toUpperCase() ?? '') === qNorm),
      'EXACT_NORMALIZED_MATCH'
    )
    // B — raw read text (contains)
    collect(
      ALL_MOCK_SIGHTINGS.filter(s => inCamera(s) && (s.plateRead?.rawRead?.toUpperCase() ?? '').includes(qRaw)),
      'RAW_READ_MATCH'
    )
    // C — partial normalized/raw read
    collect(
      ALL_MOCK_SIGHTINGS.filter(s => {
        if (!inCamera(s)) return false
        const norm = s.plateRead?.normalizedRead?.toUpperCase() ?? ''
        const raw = s.plateRead?.rawRead?.toUpperCase() ?? ''
        return norm.includes(qNorm) || raw.includes(qNorm)
      }),
      'PARTIAL_MATCH'
    )
    // D — plate candidate text
    collect(
      ALL_MOCK_SIGHTINGS.filter(s =>
        inCamera(s) &&
        s.plateCandidates.some(c =>
          c.rawRead.toUpperCase().includes(qRaw) ||
          c.rawRead.toUpperCase().includes(qNorm) ||
          (c.normalizedRead?.toUpperCase() ?? '').includes(qNorm)
        )
      ),
      'CANDIDATE_MATCH'
    )
    // E — related sightings (same vehicle as an already-matched sighting)
    const matchedVehicleIds = new Set(results.map(r => r.sighting.vehicleId))
    if (matchedVehicleIds.size) {
      collect(
        ALL_MOCK_SIGHTINGS.filter(s => inCamera(s) && matchedVehicleIds.has(s.vehicleId)),
        'RELATED_SIGHTING'
      )
    }
    return results
  }

  async getCameraSightings(cameraId: string, filter?: Partial<ANPRFilter>): Promise<SightingPage> {
    return this.listSightings({ ...filter, cameraId })
  }

  async getCameraFeed(cameraId: string): Promise<ANPRCameraFeed> {
    await delay()
    const sightings = ALL_MOCK_SIGHTINGS
      .filter(s => s.cameraId === cameraId)
      .sort((a, b) => b.observedAt.localeCompare(a.observedAt))
    const updated = sightings.map(s => s.observedAt).sort()
    return {
      cameraId,
      state: 'READY',
      lastUpdatedAt: updated.length ? updated[updated.length - 1] : null,
      sightings,
      providerHealth: MOCK_PROVIDER_HEALTH.state,
    }
  }

  async getCameraSummary(cameraId: string): Promise<ANPRCameraSummary> {
    await delay(200)
    const rows = ALL_MOCK_SIGHTINGS.filter(s => s.cameraId === cameraId)
    const byStatus: Record<string, number> = {}
    const byQuality: Record<string, number> = {}
    const byClass: Record<string, number> = {}
    for (const s of rows) {
      byStatus[s.watchlistStatus] = (byStatus[s.watchlistStatus] ?? 0) + 1
      if (s.plateRead?.quality) {
        byQuality[s.plateRead.quality] = (byQuality[s.plateRead.quality] ?? 0) + 1
      }
      byClass[s.vehicleClass] = (byClass[s.vehicleClass] ?? 0) + 1
    }
    const times = rows.map(s => s.observedAt).sort()
    return {
      cameraId,
      totalSightings: rows.length,
      byStatus,
      byQuality,
      byClass,
      lastUpdatedAt: times.length ? times[times.length - 1] : null,
    }
  }
}

export class RealANPRService implements IANPRService {
  /**
   * §30/§44 — REAL mode must never silently fall back to demo data. Gateway
   * statuses (502/504) or a missing response mean the backend is unreachable;
   * surface the unavailable state instead. Backend error bodies use either
   * { detail: "..." } or the structured { detail: { error: { message } } }.
   */
  private handleError(error: unknown): never {
    if (axios.isAxiosError(error)) {
      const status = error.response?.status
      if (!error.response || status === 502 || status === 504) {
        throw new Error('ANPR DATA UNAVAILABLE: backend unreachable')
      }
      const detail: unknown = (error.response.data as { detail?: unknown } | undefined)?.detail
      let message: string | undefined
      let code: string | undefined
      if (typeof detail === 'string') {
        message = detail
      } else if (detail && typeof detail === 'object') {
        const env = detail as { error?: { message?: unknown; code?: unknown }; message?: unknown }
        const inner = env.error?.message ?? env.message
        if (typeof inner === 'string') message = inner
        if (typeof env.error?.code === 'string') code = env.error.code
      }
      throw new Error(
        `ANPR API Error (${status}): ${code ? code + ' — ' : ''}${message ?? error.message}`
      )
    }
    throw error
  }

  async getSummary(): Promise<ANPRSummary> {
    try {
      const r = await api.get<ANPRSummary>('/anpr/summary')
      return r.data
    } catch (error) {
      this.handleError(error)
    }
  }

  async getProviderHealth(): Promise<ANPRProviderHealth> {
    try {
      const r = await api.get<ANPRProviderHealth>('/anpr/health')
      return r.data
    } catch (error) {
      this.handleError(error)
    }
  }

  async listSightings(filter: Partial<ANPRFilter>): Promise<SightingPage> {
    try {
      const params = qs({
        camera_id: filter.cameraId,
        vehicle_id: filter.vehicleId,
        track_id: filter.trackId,
        vehicle_class: filter.vehicleClass,
        quality: filter.quality,
        search: filter.search,
        direction: filter.direction,
        watchlist_status: filter.watchlistStatus,
        // Only send confidence bounds when they actually restrict — a bound of
        // 0/1 would otherwise exclude rows with a null confidence.
        confidence_min: filter.confidenceMin && filter.confidenceMin > 0 ? filter.confidenceMin : undefined,
        confidence_max: filter.confidenceMax !== undefined && filter.confidenceMax < 1 ? filter.confidenceMax : undefined,
        from: filter.from,
        to: filter.to,
        cursor: filter.cursor ?? undefined,
        limit: filter.limit,
      })
      const r = await api.get<SightingPage>('/anpr/sightings' + params)
      return r.data
    } catch (error) {
      this.handleError(error)
    }
  }

  async getSighting(sightingId: string): Promise<VehicleSighting> {
    try {
      const r = await api.get<VehicleSighting>('/anpr/sightings/' + encodeURIComponent(sightingId))
      return r.data
    } catch (error) {
      this.handleError(error)
    }
  }

  async getSightingCandidates(sightingId: string): Promise<PlateCandidate[]> {
    try {
      const r = await api.get<PlateCandidate[]>(
        '/anpr/sightings/' + encodeURIComponent(sightingId) + '/candidates'
      )
      return r.data
    } catch (error) {
      this.handleError(error)
    }
  }

  async getVehicle(vehicleId: string): Promise<VehicleSighting> {
    try {
      const r = await api.get<VehicleSighting>('/anpr/vehicles/' + encodeURIComponent(vehicleId))
      return r.data
    } catch (error) {
      this.handleError(error)
    }
  }

  async getVehicleHistory(vehicleId: string): Promise<VehicleHistory> {
    try {
      const r = await api.get<VehicleHistory>(
        '/anpr/vehicles/' + encodeURIComponent(vehicleId) + '/history'
      )
      return r.data
    } catch (error) {
      this.handleError(error)
    }
  }

  async searchPlate(query: string, filter?: Partial<ANPRFilter>): Promise<VehicleSearchResult[]> {
    try {
      const params = qs({ q: query, camera_id: filter?.cameraId, limit: filter?.limit })
      const r = await api.get<VehicleSearchResult[]>('/anpr/search' + params)
      return r.data
    } catch (error) {
      this.handleError(error)
    }
  }

  async getCameraSightings(cameraId: string): Promise<SightingPage> {
    try {
      const r = await api.get<VehicleSighting[]>(
        '/anpr/cameras/' + encodeURIComponent(cameraId) + '/vehicles'
      )
      return { sightings: r.data, hasMore: false, nextCursor: null }
    } catch (error) {
      this.handleError(error)
    }
  }

  async getCameraFeed(cameraId: string): Promise<ANPRCameraFeed> {
    try {
      const r = await api.get<ANPRCameraFeed>(
        '/anpr/cameras/' + encodeURIComponent(cameraId) + '/vehicles/feed'
      )
      return r.data
    } catch (error) {
      this.handleError(error)
    }
  }

  async getCameraSummary(cameraId: string): Promise<ANPRCameraSummary> {
    try {
      const r = await api.get<ANPRCameraSummary>(
        '/anpr/cameras/' + encodeURIComponent(cameraId) + '/vehicles/summary'
      )
      return r.data
    } catch (error) {
      this.handleError(error)
    }
  }
}

let _mock: MockANPRService | null = null
let _real: RealANPRService | null = null

export function getANPRService(mode: 'MOCK' | 'REAL'): IANPRService {
  if (mode === 'MOCK') {
    if (!_mock) _mock = new MockANPRService()
    return _mock
  }
  if (!_real) _real = new RealANPRService()
  return _real
}
