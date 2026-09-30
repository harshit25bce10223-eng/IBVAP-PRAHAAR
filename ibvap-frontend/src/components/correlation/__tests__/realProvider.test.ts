// PRHAAR Component 4 — REAL provider contract (§63/§82)
//
// The REAL provider must never masquerade as DEMO and never fall back to
// fixtures. An unreachable backend surfaces as EVENT/CORRELATION DATA
// UNAVAILABLE; an HTTP failure surfaces with its status; and backend
// snake_case payloads map to the canonical model with absent fields staying
// null — nothing is invented at the mapping seam.

import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AxiosError } from 'axios'
import { DEFAULT_CORRELATION_QUERY } from '@/types/eventCorrelation'
import type { EventLogQuery } from '@/types/eventCorrelation'
import { realCorrelationService } from '@/services/correlation/RealCorrelationService'
import { MOCK_GROUPS } from '@/services/correlation/mockCorrelationData'

const getMock = vi.hoisted(() => vi.fn())

vi.mock('axios', async () => {
  const actual = await vi.importActual<typeof import('axios')>('axios')
  return {
    ...actual,
    default: { ...actual.default, create: () => ({ get: getMock }) },
  }
})

const QUERY: EventLogQuery = { ...DEFAULT_CORRELATION_QUERY, pageSize: 20 }

function httpError(status: number, detail: string): AxiosError {
  const err = new AxiosError('Request failed', 'ERR_BAD_RESPONSE')
  err.response = {
    status,
    data: { detail },
    statusText: '',
    headers: {},
    config: { headers: {} } as never,
  }
  return err
}

/** Faithful shape of the backend GET /correlations/{id} payload. */
function backendGroupPayload(overrides: Record<string, unknown> = {}) {
  return {
    correlation_id: 'COR-BE-1',
    incident_id: null,
    primary_event_id: 'EV-BE-1',
    status: 'CORRELATED',
    state: 'ACTIVE',
    sector_id: 'SECTOR-B',
    region_profile: 'R2',
    started_at: '2026-09-07T02:14:11+00:00',
    ended_at: null,
    event_count: 2,
    camera_count: 1,
    zone_count: 1,
    source_count: 2,
    confidence: 72,
    correlation_strength: 'MEDIUM',
    completeness: null,
    uncertainty_reliability: 'MEDIUM',
    uncertainty_note: 'One modality only.',
    track_candidate_id: 'TRK-BE-1',
    track_candidate_confidence: 0.6,
    track_candidate_label: 'possible continuation',
    camera_chain: ['CAM-07'],
    modalities: ['VIDEO'],
    sources: ['VIRTUAL_FENCE', 'ANPR'],
    health_context: { camera_id: 'CAM-07', reliability: 'LOW', note: 'Degraded at the time.' },
    evidence_count: 1,
    connectivity: 'DELAYED',
    duplicated_or_suppressed: false,
    revision: 2,
    algorithm_version: 'v1',
    configuration_version: 'v1',
    updated_at: '2026-09-07T02:15:00+00:00',
    created_at: '2026-09-07T02:14:00+00:00',
    explanation_summary: '2 signals were grouped because they occurred within 30 seconds.',
    members: [
      {
        event_id: 'EV-BE-1',
        kind: 'ZONE_ENTRY',
        source: 'VIRTUAL_FENCE',
        modality: 'VIDEO',
        camera_id: 'CAM-07',
        zone_id: 'ZONE-B',
        sector_id: 'SECTOR-B',
        region_profile: 'R2',
        track_id: null,
        timestamp: '2026-09-07T02:14:11+00:00',
        severity: 'MEDIUM',
        reliability: null,
        confidence: null,
        evidence_ids: ['EVD-1'],
        health_context: null,
        detection_id: 'DET-9',
      },
      {
        event_id: 'EV-BE-2',
        kind: 'ANPR_READ',
        source: 'ANPR',
        modality: 'ANPR',
        camera_id: 'CAM-07',
        zone_id: null,
        sector_id: 'SECTOR-B',
        region_profile: 'R2',
        track_id: 'TRK-BE-1',
        timestamp: '2026-09-07T02:14:22+00:00',
        severity: null,
        reliability: 'HIGH',
        confidence: 0.81,
        evidence_ids: [],
        health_context: null,
        anpr_plate: 'HR26AK4521',
        anpr_plate_confidence: 0.81,
        anpr_quality: 'GOOD',
        anpr_sighting_id: 'SIGHT-1',
      },
    ],
    relationships: [
      {
        from_event_id: 'EV-BE-1',
        to_event_id: 'EV-BE-2',
        type: 'TEMPORAL',
        strength: 55,
        explanation: 'Within the configured temporal window.',
      },
    ],
    history: [
      {
        revision: 1,
        status: 'STANDALONE',
        state: 'OPEN',
        reason: null,
        timestamp: '2026-09-07T02:14:12+00:00',
        created_at: '2026-09-07T02:14:12+00:00',
      },
      {
        revision: 2,
        status: 'CORRELATED',
        state: 'ACTIVE',
        reason: 'Second signal attached.',
        timestamp: '2026-09-07T02:14:23+00:00',
        created_at: '2026-09-07T02:14:23+00:00',
      },
    ],
    ...overrides,
  }
}

beforeEach(() => {
  getMock.mockReset()
})

describe('real provider failure handling — never a silent fallback (§63)', () => {
  it('maps an unreachable backend to EVENT/CORRELATION DATA UNAVAILABLE', async () => {
    getMock.mockRejectedValue(new AxiosError('Network Error', 'ERR_NETWORK'))
    await expect(realCorrelationService.listGroups(QUERY)).rejects.toThrow(
      /EVENT\/CORRELATION DATA UNAVAILABLE/
    )
    await expect(realCorrelationService.getGroup('COR-1042')).rejects.toThrow(
      /EVENT\/CORRELATION DATA UNAVAILABLE/
    )
    await expect(realCorrelationService.listRecent(6)).rejects.toThrow(
      /EVENT\/CORRELATION DATA UNAVAILABLE/
    )
    await expect(realCorrelationService.listForCamera('CAM-07', 4)).rejects.toThrow(
      /EVENT\/CORRELATION DATA UNAVAILABLE/
    )
    await expect(realCorrelationService.getRelationships('COR-1042')).rejects.toThrow(
      /EVENT\/CORRELATION DATA UNAVAILABLE/
    )
    await expect(realCorrelationService.getMemberEvent('EV-1')).rejects.toThrow(
      /EVENT\/CORRELATION DATA UNAVAILABLE/
    )
  })

  it('never resolves with demo fixtures on failure', async () => {
    getMock.mockRejectedValue(new AxiosError('Network Error', 'ERR_NETWORK'))
    const fixtureIds = new Set(MOCK_GROUPS.map(g => g.correlationId))
    const outcome = await realCorrelationService.listGroups(QUERY).then(
      page => page.groups.map(g => g.correlationId),
      () => 'rejected' as const
    )
    expect(outcome).toBe('rejected')
    expect(fixtureIds.size).toBeGreaterThan(0)
  })

  it('surfaces HTTP failures with their status and detail', async () => {
    getMock.mockRejectedValue(httpError(500, 'db down'))
    await expect(realCorrelationService.getGroup('COR-1')).rejects.toThrow(
      /Correlation API Error \(500\): db down/
    )
  })
})

describe('real provider request parameters', () => {
  it('sends only non-default filters and never time_range=all', async () => {
    getMock.mockResolvedValue({ data: { groups: [], total: 0 } })
    await realCorrelationService.listGroups({ ...QUERY, severity: 'HIGH', timeRange: '1h', sort: 'signals' })
    const [, opts] = getMock.mock.calls[0]
    expect(opts.params.severity).toBe('HIGH')
    expect(opts.params.time_range).toBe('1h')
    expect(opts.params.sort).toBe('signals')
    expect(opts.params).not.toHaveProperty('source')
    expect(opts.params).not.toHaveProperty('sector_id')

    getMock.mockClear()
    await realCorrelationService.listGroups({ ...QUERY, timeRange: 'all' })
    expect(getMock.mock.calls[0][1].params).not.toHaveProperty('time_range')
  })
})

describe('real provider payload mapping — absent fields stay absent', () => {
  it('maps the backend group payload without fabricating values', async () => {
    getMock.mockResolvedValue({ data: backendGroupPayload() })
    const g = await realCorrelationService.getGroup('COR-BE-1')

    expect(g.correlationId).toBe('COR-BE-1')
    expect(g.status).toBe('CORRELATED')
    expect(g.correlationStrength).toBe('MEDIUM')
    expect(g.confidence).toEqual({ value: 72, note: '' })
    expect(g.risk.score).toBeNull()
    expect(g.risk.severity).toBeNull()
    expect(g.risk.incidentIds).toEqual([])
    expect(g.endedAt).toBeNull()
    expect(g.trackCandidate?.label).toBe('possible continuation')
    expect(g.cameraCount).toBe(1)
    expect(g.memberEvents).toHaveLength(2)
    expect(g.memberEventsLoaded).toBeNull()
    expect(g.relationships[0].strength).toBe(55)
    expect(g.history.transitions.map(t => t.status)).toEqual(['STANDALONE', 'CORRELATED'])
    expect(g.history.createdAt).toBe('2026-09-07T02:14:12+00:00')
    expect(g.healthContext).toHaveLength(1)
  })

  it('leaves an undesignated primary event undesignated', async () => {
    getMock.mockResolvedValue({ data: backendGroupPayload({ primary_event_id: null }) })
    const g = await realCorrelationService.getGroup('COR-BE-1')
    expect(g.primaryEventId).toBeNull()
  })

  it('maps C5/C7 member references verbatim and keeps missing ones null', async () => {
    getMock.mockResolvedValue({ data: backendGroupPayload() })
    const g = await realCorrelationService.getGroup('COR-BE-1')
    const [entry, anpr] = g.memberEvents
    expect(entry.detectionId).toBe('DET-9')
    expect(entry.anprPlate).toBeNull()
    expect(entry.severity).toBe('MEDIUM')
    expect(anpr.anprPlate).toBe('HR26AK4521')
    expect(anpr.anprPlateConfidence).toBe(0.81)
    expect(anpr.anprQuality).toBe('GOOD')
    expect(anpr.anprSightingId).toBe('SIGHT-1')
    expect(anpr.detectionId).toBeNull()
    expect(anpr.severity).toBeNull()
  })

  it('reads the member envelope the events route actually returns', async () => {
    getMock.mockResolvedValue({
      data: { event_id: 'EV-BE-2', correlation_id: 'COR-BE-1', member: backendGroupPayload().members[1] },
    })
    const m = await realCorrelationService.getMemberEvent('EV-BE-2')
    expect(m.eventId).toBe('EV-BE-2')
    expect(m.cameraId).toBe('CAM-07')
  })

  it('keeps an unknown status/severity unknown rather than guessing', async () => {
    getMock.mockResolvedValue({
      data: backendGroupPayload({ status: 'WAT', members: [{ event_id: 'EV-X' }] }),
    })
    const g = await realCorrelationService.getGroup('COR-BE-1')
    expect(g.status).toBe('WAT')
    expect(g.memberEvents[0].severity).toBeNull()
    expect(g.memberEvents[0].kind).toBe('UNKNOWN')
    expect(g.memberEvents[0].cameraId).toBe('')
    expect(g.memberEvents[0].evidenceIds).toEqual([])
  })

  it('maps the C1 risk reference verbatim, incident ids included (§41/§129)', async () => {
    getMock.mockResolvedValue({
      data: backendGroupPayload({
        risk_score: 88,
        risk_severity: 'CRITICAL',
        risk_incident_ids: ['INC-BE-2', 'INC-BE-1'],
      }),
    })
    const g = await realCorrelationService.getGroup('COR-BE-1')
    expect(g.risk.score).toBe(88)
    expect(g.risk.severity).toBe('CRITICAL')
    expect(g.risk.incidentIds).toEqual(['INC-BE-2', 'INC-BE-1'])
  })
})
