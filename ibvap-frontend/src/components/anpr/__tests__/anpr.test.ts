// ─────────────────────────────────────────────────────────────────────────────
// Component 7 — ANPR + Vehicle Intelligence Unit & Contract Tests
// ─────────────────────────────────────────────────────────────────────────────
import { describe, expect, it } from 'vitest'
import {
  ALL_MOCK_SIGHTINGS,
} from '@/services/anpr/mockData'
import { MockANPRService, RealANPRService, getANPRService } from '@/services/anpr'

describe('Component 7 — ANPR Domain Contract', () => {
  it('covers all required mock scenarios with deterministic IDs', () => {
    expect(ALL_MOCK_SIGHTINGS.length).toBe(14)

    const ids = ALL_MOCK_SIGHTINGS.map(s => s.sightingId)
    const uniqueIds = new Set(ids)
    expect(uniqueIds.size).toBe(ids.length) // All deterministic unique IDs
  })

  it('includes scenario with clear readable plate and high confidence', () => {
    const s1 = ALL_MOCK_SIGHTINGS.find(s => s.sightingId === 'SGT-0001')
    expect(s1).toBeDefined()
    expect(s1?.plateRead?.quality).toBe('GOOD')
    expect(s1?.plateRead?.displayRead).toBe('HR26AK4521')
    expect(s1?.plateRead?.confidence).toBeGreaterThanOrEqual(0.9)
    expect(s1?.vehicleClass).toBe('PERSONAL_CAR')
  })

  it('includes scenario with low-confidence OCR', () => {
    const s2 = ALL_MOCK_SIGHTINGS.find(s => s.sightingId === 'SGT-0002')
    expect(s2).toBeDefined()
    expect(s2?.plateRead?.quality).toBe('FAIR')
    expect(s2?.confidence).toBeLessThan(0.6)
  })

  it('includes scenario with multiple ranked OCR candidates', () => {
    const s3 = ALL_MOCK_SIGHTINGS.find(s => s.sightingId === 'SGT-0003')
    expect(s3).toBeDefined()
    expect(s3?.plateCandidates.length).toBeGreaterThanOrEqual(2)
    // First candidate has higher confidence than second
    expect(s3!.plateCandidates[0].confidence).toBeGreaterThan(s3!.plateCandidates[1].confidence)
  })

  it('includes scenario with UNREADABLE plate (null plateRead)', () => {
    const s4 = ALL_MOCK_SIGHTINGS.find(s => s.sightingId === 'SGT-0004')
    expect(s4).toBeDefined()
    expect(s4?.plateRead).toBeNull()
    expect(s4?.plateCandidates.length).toBe(0)
  })

  it('includes motorcycle scenario', () => {
    const s4 = ALL_MOCK_SIGHTINGS.find(s => s.vehicleClass === 'MOTORCYCLE')
    expect(s4).toBeDefined()
  })

  it('includes truck with motion blur scenario', () => {
    const s5 = ALL_MOCK_SIGHTINGS.find(s => s.sightingId === 'SGT-0005')
    expect(s5?.vehicleClass).toBe('TRUCK')
    expect(s5?.plateRead?.quality).toBe('MOTION_BLUR')
  })

  it('includes night scene with degraded camera health', () => {
    const s6 = ALL_MOCK_SIGHTINGS.find(s => s.sightingId === 'SGT-0006')
    expect(s6?.plateRead?.quality).toBe('LOW_LIGHT')
    expect(s6?.cameraHealthState).toBe('DEGRADED')
  })

  it('includes partial plate scenario', () => {
    const s7 = ALL_MOCK_SIGHTINGS.find(s => s.sightingId === 'SGT-0007')
    expect(s7?.plateRead?.quality).toBe('PARTIAL')
  })

  it('includes low-sun glare capture scenario (§29)', () => {
    const s11 = ALL_MOCK_SIGHTINGS.find(s => s.sightingId === 'SGT-0011')
    expect(s11).toBeDefined()
    expect(s11?.plateRead?.quality).toBe('GLARE')
    expect(s11?.plateRead?.displayRead).toBe('HR51BR8842')
    expect(s11?.confidence).toBe(0.57)
  })

  it('includes dirty-plate capture scenario (§29)', () => {
    const s12 = ALL_MOCK_SIGHTINGS.find(s => s.sightingId === 'SGT-0012')
    expect(s12).toBeDefined()
    expect(s12?.plateRead?.quality).toBe('DIRTY')
    expect(s12?.vehicleClass).toBe('TRACTOR')
    expect(s12?.confidence).toBe(0.42)
  })

  it('includes multi-camera sightings for the same vehicle', () => {
    const vehSightings = ALL_MOCK_SIGHTINGS.filter(s => s.vehicleId === 'VEH-A001')
    expect(vehSightings.length).toBeGreaterThanOrEqual(2)
    const cameras = new Set(vehSightings.map(s => s.cameraId))
    expect(cameras.size).toBeGreaterThanOrEqual(2) // Seen on at least 2 distinct cameras
  })

  it('includes incident-linked sighting', () => {
    const incSighting = ALL_MOCK_SIGHTINGS.find(s => s.incidentRef !== null)
    expect(incSighting).toBeDefined()
    expect(incSighting?.incidentRef).toBe('INC-024')
  })

  it('includes evidence-linked sighting', () => {
    const evdSighting = ALL_MOCK_SIGHTINGS.find(s => s.evidenceRef !== null)
    expect(evdSighting).toBeDefined()
    expect(evdSighting?.evidenceRef).toBe('EVD-0091')
  })
})

describe('Component 7 — MockANPRService', () => {
  const service = new MockANPRService()

  it('returns valid ANPR summary metrics', async () => {
    const summary = await service.getSummary()
    expect(summary.totalReads).toBeGreaterThan(0)
    expect(summary.readablePlates).toBeGreaterThanOrEqual(0)
    expect(summary.camerasReporting).toBeGreaterThan(0)
  })

  it('summary counts are internally consistent (no fabricated metrics)', async () => {
    const summary = await service.getSummary()
    expect(summary.totalReads).toBe(14)
    expect(summary.readablePlates + summary.partialReads + summary.unreadablePlates).toBe(summary.totalReads)
  })

  it('filters sightings by camera_id', async () => {
    const page = await service.listSightings({ cameraId: 'CAM-07' })
    expect(page.sightings.length).toBeGreaterThan(0)
    for (const s of page.sightings) {
      expect(s.cameraId).toBe('CAM-07')
    }
  })

  it('filters sightings by vehicle class', async () => {
    const page = await service.listSightings({ vehicleClass: 'TRUCK' })
    expect(page.sightings.length).toBeGreaterThan(0)
    for (const s of page.sightings) {
      expect(s.vehicleClass).toBe('TRUCK')
    }
  })

  it('filters sightings by trackId', async () => {
    const page = await service.listSightings({ trackId: 'TRK-1042' })
    expect(page.sightings.length).toBe(2) // SGT-0001 + SGT-0008A
    for (const s of page.sightings) {
      expect(s.vehicleTrackId).toBe('TRK-1042')
    }
  })

  it('applies confidenceMin threshold', async () => {
    const page = await service.listSightings({ confidenceMin: 0.9 })
    expect(page.sightings.length).toBe(4)
    for (const s of page.sightings) {
      expect(s.confidence).toBeGreaterThanOrEqual(0.9)
    }
  })

  it('applies observed-time window', async () => {
    const page = await service.listSightings({ from: '2026-09-19T22:00:00Z' })
    const ids = page.sightings.map(s => s.sightingId).sort()
    expect(ids).toEqual(['SGT-0004', 'SGT-0006'])
  })

  it('filters sightings by search query matching plate', async () => {
    const page = await service.listSightings({ search: 'HR26' })
    expect(page.sightings.length).toBeGreaterThan(0)
    expect(page.sightings[0].plateRead?.displayRead).toContain('HR26')
  })

  it('returns vehicle history for known vehicleId', async () => {
    const history = await service.getVehicleHistory('VEH-A001')
    expect(history.vehicleId).toBe('VEH-A001')
    expect(history.totalSightings).toBe(3)
  })

  it('returns single sighting by id', async () => {
    const s = await service.getSighting('SGT-0001')
    expect(s.sightingId).toBe('SGT-0001')
  })

  it('throws error for non-existent sighting', async () => {
    await expect(service.getSighting('NON-EXISTENT')).rejects.toThrow('not found')
  })
})

// §24 — five explicit match labels; classification mirrors the backend
// repository phases (exact normalized → raw read → partial → candidate →
// related). Partial/candidate results are never reported as exact.
// NOTE: in the mock dataset every multi-sighting vehicle shares one identical
// plate text, so phase E (RELATED_SIGHTING) adds no new rows in these cases;
// its behavior is exercised at the backend level instead.
describe('Component 7 — Plate Search Classification (§24)', () => {
  const service = new MockANPRService()

  it('classifies exact normalized match', async () => {
    const results = await service.searchPlate('RJ14AB1052')
    expect(results.length).toBe(1)
    expect(results[0].matchType).toBe('EXACT_NORMALIZED_MATCH')
    expect(results[0].sighting.sightingId).toBe('SGT-0003')
  })

  it('classifies raw read match (no exact read) as RAW_READ_MATCH', async () => {
    const results = await service.searchPlate('RJ14')
    expect(results.length).toBe(1)
    expect(results[0].matchType).toBe('RAW_READ_MATCH')
    expect(results[0].sighting.sightingId).toBe('SGT-0003')
  })

  it('classifies candidate-only text as CANDIDATE_MATCH, never exact', async () => {
    const results = await service.searchPlate('RJ14AB105Z')
    expect(results.length).toBe(1)
    expect(results[0].matchType).toBe('CANDIDATE_MATCH')
  })

  it('returns all exact reads for a fully repeated plate', async () => {
    const results = await service.searchPlate('HR26AK4521')
    expect(results.length).toBe(4) // SGT-0001, SGT-0008A/B/C — all VEH-A001 records
    for (const r of results) {
      expect(r.matchType).toBe('EXACT_NORMALIZED_MATCH')
      expect(r.sighting.vehicleId).toBe('VEH-A001')
    }
  })

  it('returns empty results for a non-matching query', async () => {
    const results = await service.searchPlate('ZZ99ZZ9999')
    expect(results.length).toBe(0)
  })
})

describe('Component 7 — New service surfaces (§19/§28/§42)', () => {
  const service = new MockANPRService()

  it('returns provider health without fabricated latency', async () => {
    const health = await service.getProviderHealth()
    expect(health.state).toBe('READY')
    expect(health.provider).toBe('ANPR-DEMO')
    expect(health.processingLatencyMs).toBeNull()
    expect(health.note).toContain('not a production ANPR model')
  })

  it('returns ranked candidates for a sighting', async () => {
    const candidates = await service.getSightingCandidates('SGT-0003')
    expect(candidates.length).toBe(3)
    expect(candidates[0].rank).toBe(1)
    expect(candidates[0].confidence).toBeGreaterThan(candidates[1].confidence)
    expect(candidates[2].normalizedRead).toBeNull()
  })

  it('rejects candidates for unknown sighting', async () => {
    await expect(service.getSightingCandidates('NON-EXISTENT')).rejects.toThrow('not found')
  })

  it('returns the newest sighting for a vehicle', async () => {
    const newest = await service.getVehicle('VEH-A001')
    expect(newest.sightingId).toBe('SGT-0008C') // 17:34 — latest of the four records
  })

  it('rejects unknown vehicle', async () => {
    await expect(service.getVehicle('NON-EXISTENT')).rejects.toThrow('not found')
  })

  it('returns a camera feed with reported state and provider health', async () => {
    const feed = await service.getCameraFeed('CAM-07')
    expect(feed.cameraId).toBe('CAM-07')
    expect(feed.state).toBe('READY')
    expect(feed.providerHealth).toBe('READY')
    expect(feed.sightings.length).toBe(4)
    expect(feed.sightings[0].sightingId).toBe('SGT-0004') // newest (22:41) first
    expect(feed.lastUpdatedAt).toBe('2026-09-19T22:41:08Z')
    for (const s of feed.sightings) {
      expect(s.cameraId).toBe('CAM-07')
    }
  })

  it('aggregates camera summary counts without accuracy claims', async () => {
    const summary = await service.getCameraSummary('CAM-07')
    expect(summary.totalSightings).toBe(4)
    expect(summary.byStatus['NO_MATCH']).toBe(2)
    expect(summary.byStatus['WATCHLIST_MATCH']).toBe(1)
    expect(summary.byQuality['GOOD']).toBe(3) // SGT-0004 has no read → excluded
    expect(summary.byClass['MOTORCYCLE']).toBe(1)
    expect(summary.lastUpdatedAt).toBe('2026-09-19T22:41:08Z')
  })

  it('returns an empty camera summary for an unknown camera', async () => {
    const summary = await service.getCameraSummary('CAM-99')
    expect(summary.totalSightings).toBe(0)
    expect(summary.lastUpdatedAt).toBeNull()
    expect(Object.keys(summary.byStatus).length).toBe(0)
  })
})

describe('Component 7 — Service Factory', () => {
  it('returns MockANPRService for MOCK mode', () => {
    const svc = getANPRService('MOCK')
    expect(svc).toBeInstanceOf(MockANPRService)
  })

  it('returns RealANPRService for REAL mode', () => {
    const svc = getANPRService('REAL')
    expect(svc).toBeInstanceOf(RealANPRService)
  })
})
