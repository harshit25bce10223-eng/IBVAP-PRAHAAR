// PRHAAR Component 2 — contract + formatting tests (logic only, no DOM)
//
// These guard the integration seams a Phase-2 backend must satisfy:
// fixtures carry only renderable statuses, tones map every status, and
// missing values format as N/A/Unknown — never zero, never ONLINE.

import { describe, expect, it } from 'vitest'
import { HEALTH_STATUSES } from '@/types/cameraHealth'
import type { CameraHealth, CameraHealthStatus } from '@/types/cameraHealth'
import { MOCK_HEALTH } from '@/services/health/mockHealthData'
import { mockHealthService } from '@/services/health/mockHealthService'
import { toneForStatus, toneForTrend, TONE } from '../healthTone'
import { ageSec, formatAge, formatClock, formatMetricValue } from '../healthFormat'

const NOW = new Date('2026-09-07T12:00:00Z').getTime()

describe('fixture contract (what Phase 2 must also satisfy)', () => {
  it('covers ONLINE, DEGRADED, OFFLINE and UNKNOWN cameras', () => {
    const statuses = new Set(Object.values(MOCK_HEALTH).map(h => h.status))
    for (const s of ['ONLINE', 'DEGRADED', 'OFFLINE', 'UNKNOWN'] as const) {
      expect(statuses.has(s)).toBe(true)
    }
  })

  it('every status in fixtures is a canonical CameraHealthStatus', () => {
    for (const h of Object.values(MOCK_HEALTH)) {
      expect(HEALTH_STATUSES).toContain(h.status)
      for (const t of h.trends) {
        expect(['IMPROVING', 'STABLE', 'DEGRADING', 'UNKNOWN']).toContain(t.direction)
      }
    }
  })

  it('degraded camera exposes viewpoint shift with fence impact (CAM-12 scenario)', () => {
    const cam12 = MOCK_HEALTH['CAM-12']
    expect(cam12.status).toBe('DEGRADED')
    expect(cam12.viewpoint.shiftDetected).toBe(true)
    expect(cam12.viewpoint.fenceConfidenceNote).toMatch(/fence/i)
    expect(cam12.operationalImpact.affectedModules).toContain('Virtual Fence')
  })

  it('offline camera carries last-known state, not live metrics (CAM-19 scenario)', () => {
    const cam19 = MOCK_HEALTH['CAM-19']
    expect(cam19.status).toBe('OFFLINE')
    expect(cam19.stream.fps).toBeNull()
    expect(cam19.lastKnown?.status).toBe('ONLINE')
    expect(cam19.operationalImpact.coverage).toBe('COMPROMISED')
  })

  it('unavailable telemetry is UNKNOWN with nulls, never zeros (CAM-03 scenario)', () => {
    const cam03 = MOCK_HEALTH['CAM-03']
    expect(cam03.status).toBe('UNKNOWN')
    expect(cam03.stream.fps).toBeNull()
    expect(cam03.network.latencyMs).toBeNull()
    expect(cam03.lastUpdated).toBeNull()
  })

  it('all fixtures are labelled DEMO or UNAVAILABLE — never LIVE', () => {
    for (const h of Object.values(MOCK_HEALTH)) {
      expect(['DEMO', 'UNAVAILABLE']).toContain(h.source)
    }
  })

  it('mock provider resolves known cameras and rejects unknown ones', async () => {
    const got: CameraHealth = await mockHealthService.get('CAM-07')
    expect(got.cameraId).toBe('CAM-07')
    await expect(mockHealthService.get('CAM-99')).rejects.toThrow()
    const list = await mockHealthService.list(['CAM-07', 'CAM-12'])
    expect(list.map(h => h.cameraId)).toEqual(['CAM-07', 'CAM-12'])
  })
})

describe('tone map (single source for every surface)', () => {
  it('maps every canonical status without inventing colors', () => {
    const seen = new Map(Object.entries(TONE).map(([k, v]) => [v.text + v.dot, k]))
    expect(seen.size).toBe(Object.keys(TONE).length)
    const tones = new Set<string>()
    for (const s of HEALTH_STATUSES as CameraHealthStatus[]) tones.add(toneForStatus(s))
    expect(tones.has('good')).toBe(true)
    expect(tones.has('degraded')).toBe(true)
    expect(tones.has('failed')).toBe(true)
    // UNKNOWN must never render as healthy.
    expect(toneForStatus('UNKNOWN')).not.toBe('good')
    expect(toneForStatus('OFFLINE')).toBe('failed')
    expect(toneForStatus('DEGRADED')).toBe('degraded')
    expect(toneForStatus('ONLINE')).toBe('good')
  })

  it('trend tones stay within the token set', () => {
    for (const d of ['IMPROVING', 'STABLE', 'DEGRADING', 'UNKNOWN'] as const) {
      expect(TONE[toneForTrend(d)]).toBeDefined()
    }
  })
})

describe('formatting honesty', () => {
  it('null metrics are N/A, never 0', () => {
    expect(formatMetricValue(null, 'ms')).toBe('N/A')
    expect(formatMetricValue(undefined, '%')).toBe('N/A')
    expect(formatMetricValue(0, 'ms')).toBe('0 ms')
  })

  it('keeps backend precision (no fake decimals)', () => {
    expect(formatMetricValue(42, 'ms')).toBe('42 ms')
    expect(formatMetricValue(0.91, 'ratio')).toBe('0.91')
    expect(formatMetricValue(0.4, '%')).toBe('0.4%')
  })

  it('ages unknown timestamps honestly', () => {
    expect(formatAge(null, NOW)).toBe('Unknown')
    expect(formatAge('not-a-date', NOW)).toBe('Unknown')
    expect(formatAge(new Date(NOW - 2000).toISOString(), NOW)).toBe('just now')
    expect(formatAge(new Date(NOW - 37_000).toISOString(), NOW)).toBe('37 sec ago')
    expect(formatAge(new Date(NOW - 11 * 60_000).toISOString(), NOW)).toBe('11 min ago')
    expect(ageSec(NOW + 60_000, NOW)).toBe(0)
  })

  it('clocks invalid input as em-dash', () => {
    expect(formatClock(null)).toBe('—')
    expect(formatClock('bogus')).toBe('—')
    expect(formatClock(new Date(NOW).toISOString())).toMatch(/^\d{2}:\d{2}:\d{2}$/)
  })
})

describe('Component 2 — Fleet Operations & Coverage Intelligence', () => {
  it('covers FROZEN, STALE, MAINTENANCE, and COVERAGE COMPROMISED scenarios', () => {
    const cam05 = MOCK_HEALTH['CAM-05']
    expect(cam05.status).toBe('FROZEN')
    expect(cam05.stream.state).toBe('FROZEN')
    expect(cam05.operationalImpact.coverage).toBe('COMPROMISED')

    const cam08 = MOCK_HEALTH['CAM-08']
    expect(cam08.status).toBe('STALE')
    expect(cam08.stream.state).toBe('STALE')

    const cam09 = MOCK_HEALTH['CAM-09']
    expect(cam09.status).toBe('MAINTENANCE')
    expect(cam09.stream.state).toBe('CONNECTED')

    const cam14 = MOCK_HEALTH['CAM-14']
    expect(cam14.status).toBe('ONLINE')
    expect(cam14.operationalImpact.coverage).toBe('COMPROMISED')
  })

  it('verifies camera health vs border coverage distinction', () => {
    // CAM-14 is ONLINE hardware, but coverage is COMPROMISED due to fog
    const cam14 = MOCK_HEALTH['CAM-14']
    expect(cam14.status).toBe('ONLINE')
    expect(cam14.operationalImpact.coverage).toBe('COMPROMISED')
    expect(cam14.statusReason).toMatch(/fog/i)
  })

  it('derives accurate fleet summary counters across full fleet', () => {
    const records = Object.values(MOCK_HEALTH)
    let healthy = 0
    let degraded = 0
    let offline = 0
    let frozen = 0
    let stale = 0
    let maintenance = 0
    let coverageCompromised = 0

    for (const h of records) {
      if (h.status === 'ONLINE') healthy++
      else if (h.status === 'DEGRADED') degraded++
      else if (h.status === 'OFFLINE') offline++
      else if (h.status === 'FROZEN') frozen++
      else if (h.status === 'STALE') stale++
      else if (h.status === 'MAINTENANCE') maintenance++

      if (h.operationalImpact.coverage === 'COMPROMISED') {
        coverageCompromised++
      }
    }

    expect(healthy).toBe(2) // CAM-07, CAM-14
    expect(degraded).toBe(1) // CAM-12
    expect(offline).toBe(1) // CAM-19
    expect(frozen).toBe(1) // CAM-05
    expect(stale).toBe(1) // CAM-08
    expect(maintenance).toBe(1) // CAM-09
    expect(coverageCompromised).toBe(3) // CAM-19, CAM-05, CAM-14
  })
})

