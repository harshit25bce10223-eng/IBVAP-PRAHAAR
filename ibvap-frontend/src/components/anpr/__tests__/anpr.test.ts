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
    expect(ALL_MOCK_SIGHTINGS.length).toBeGreaterThanOrEqual(10)

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

  it('filters sightings by search query matching plate', async () => {
    const page = await service.listSightings({ search: 'HR26' })
    expect(page.sightings.length).toBeGreaterThan(0)
    expect(page.sightings[0].plateRead?.displayRead).toContain('HR26')
  })

  it('returns vehicle history for known vehicleId', async () => {
    const history = await service.getVehicleHistory('VEH-A001')
    expect(history.vehicleId).toBe('VEH-A001')
    expect(history.totalSightings).toBeGreaterThanOrEqual(3)
  })

  it('returns single sighting by id', async () => {
    const s = await service.getSighting('SGT-0001')
    expect(s.sightingId).toBe('SGT-0001')
  })

  it('throws error for non-existent sighting', async () => {
    await expect(service.getSighting('NON-EXISTENT')).rejects.toThrow('not found')
  })

  it('performs plate search returning ranked results', async () => {
    const results = await service.searchPlate('RJ14')
    expect(results.length).toBeGreaterThan(0)
    expect(['EXACT_NORMALIZED_MATCH', 'TOP_CANDIDATE_MATCH', 'PARTIAL_MATCH']).toContain(
      results[0].matchType
    )
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
