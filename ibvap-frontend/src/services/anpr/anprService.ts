// ─────────────────────────────────────────────────────────────────────────────
// Component 7 — ANPR Service (Mock + Real + Interface)
// ─────────────────────────────────────────────────────────────────────────────
import { api, qs } from '@/services/api'
import type {
  ANPRSummary,
  ANPRFilter,
  VehicleSighting,
  VehicleHistory,
  VehicleSearchResult,
} from '@/types/anpr'
import {
  ALL_MOCK_SIGHTINGS,
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
  listSightings(filter: Partial<ANPRFilter>): Promise<SightingPage>
  getSighting(sightingId: string): Promise<VehicleSighting>
  getVehicleHistory(vehicleId: string): Promise<VehicleHistory>
  searchPlate(query: string, filter?: Partial<ANPRFilter>): Promise<VehicleSearchResult[]>
  getCameraSightings(cameraId: string, filter?: Partial<ANPRFilter>): Promise<SightingPage>
}

function delay(ms = 400): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms))
}

export class MockANPRService implements IANPRService {
  async getSummary(): Promise<ANPRSummary> {
    await delay()
    return { ...MOCK_SUMMARY }
  }

  async listSightings(filter: Partial<ANPRFilter>): Promise<SightingPage> {
    await delay()
    let results = [...ALL_MOCK_SIGHTINGS]
    if (filter.cameraId) results = results.filter(s => s.cameraId === filter.cameraId)
    if (filter.vehicleClass) results = results.filter(s => s.vehicleClass === filter.vehicleClass)
    if (filter.quality) results = results.filter(s => s.plateRead?.quality === filter.quality)
    if (filter.search) {
      const q = filter.search.toUpperCase()
      results = results.filter(s =>
        s.plateRead?.displayRead?.toUpperCase().includes(q) ||
        s.plateCandidates.some(c => c.rawRead.toUpperCase().includes(q)) ||
        s.vehicleId.toUpperCase().includes(q) ||
        s.sightingId.toUpperCase().includes(q)
      )
    }
    if (filter.direction) results = results.filter(s => s.vehicleDirection === filter.direction)
    if (filter.watchlistStatus) results = results.filter(s => s.watchlistStatus === filter.watchlistStatus)
    if (typeof filter.confidenceMin === 'number') {
      results = results.filter(s => (s.confidence ?? 0) >= filter.confidenceMin!)
    }
    return { sightings: results, hasMore: false, nextCursor: null }
  }

  async getSighting(sightingId: string): Promise<VehicleSighting> {
    await delay(200)
    const s = ALL_MOCK_SIGHTINGS.find(x => x.sightingId === sightingId)
    if (!s) throw new Error('Sighting ' + sightingId + ' not found in mock data.')
    return { ...s }
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

  async searchPlate(query: string, _filter?: Partial<ANPRFilter>): Promise<VehicleSearchResult[]> {
    await delay()
    const q = query.toUpperCase().replace(/\s/g, '')
    if (!q) return []
    const results: VehicleSearchResult[] = []
    for (const s of ALL_MOCK_SIGHTINGS) {
      const norm = s.plateRead?.normalizedRead?.toUpperCase() ?? ''
      const raw = s.plateRead?.rawRead?.toUpperCase() ?? ''
      const candidates = s.plateCandidates.map(c => c.rawRead.toUpperCase())
      if (norm === q) {
        results.push({ sighting: s, matchType: 'EXACT_NORMALIZED_MATCH' })
      } else if (raw === q || candidates[0] === q) {
        results.push({ sighting: s, matchType: 'TOP_CANDIDATE_MATCH' })
      } else if (norm.includes(q) || raw.includes(q) || candidates.some(c => c.includes(q))) {
        results.push({ sighting: s, matchType: 'PARTIAL_MATCH' })
      }
    }
    return results
  }

  async getCameraSightings(cameraId: string, filter?: Partial<ANPRFilter>): Promise<SightingPage> {
    return this.listSightings({ ...filter, cameraId })
  }
}

export class RealANPRService implements IANPRService {
  async getSummary(): Promise<ANPRSummary> {
    const r = await api.get<ANPRSummary>('/anpr/summary')
    return r.data
  }

  async listSightings(filter: Partial<ANPRFilter>): Promise<SightingPage> {
    const params = qs({
      camera_id: filter.cameraId,
      vehicle_class: filter.vehicleClass,
      quality: filter.quality,
      search: filter.search,
      direction: filter.direction,
      watchlist_status: filter.watchlistStatus,
      confidence_min: filter.confidenceMin,
      from: filter.from,
      to: filter.to,
      cursor: filter.cursor ?? undefined,
      limit: filter.limit,
    })
    const r = await api.get<SightingPage>('/anpr/sightings' + params)
    return r.data
  }

  async getSighting(sightingId: string): Promise<VehicleSighting> {
    const r = await api.get<VehicleSighting>('/anpr/sightings/' + sightingId)
    return r.data
  }

  async getVehicleHistory(vehicleId: string): Promise<VehicleHistory> {
    const r = await api.get<VehicleHistory>('/anpr/vehicles/' + vehicleId + '/history')
    return r.data
  }

  async searchPlate(query: string, filter?: Partial<ANPRFilter>): Promise<VehicleSearchResult[]> {
    const params = qs({ q: query, camera_id: filter?.cameraId, limit: filter?.limit })
    const r = await api.get<VehicleSearchResult[]>('/anpr/search' + params)
    return r.data
  }

  async getCameraSightings(cameraId: string, filter?: Partial<ANPRFilter>): Promise<SightingPage> {
    return this.listSightings({ ...filter, cameraId })
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