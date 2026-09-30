// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 6 — tracking service provider tests (§38)
//
// Covers both ITrackingService providers: the DEMO fixture provider (filter,
// sort, pagination, lifecycle, candidates, summary) and the REAL `/api/v1`
// provider (URLs, param mapping, response mapping, error surfaces). Proves the
// REAL provider never falls back to fixtures and that the mode gate switches
// providers strictly on VITE_TRACKING_MODE === 'REAL'.
// ─────────────────────────────────────────────────────────────────────────────

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { AxiosError } from 'axios'
import { mockTrackingService } from '../mockTrackingService'
import { realTrackingService } from '../RealTrackingService'
import { MOCK_TRACKS } from '@/services/tracking/mockTrackingData'
import { DEFAULT_TRACK_QUERY } from '@/types/tracking'
import type { TrackQuery } from '@/types/tracking'

const getMock = vi.hoisted(() => vi.fn())

vi.mock('axios', async () => {
  const actual = await vi.importActual<typeof import('axios')>('axios')
  return {
    ...actual,
    default: { ...actual.default, create: () => ({ get: getMock }) },
  }
})

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

function backendTrackPayload(overrides: Record<string, unknown> = {}) {
  return {
    trackId: 'TRK-BE-1',
    cameraId: 'CAM-07',
    status: 'ACTIVE',
    objectClass: 'PERSON',
    firstSeenAt: '2026-09-07T02:14:11Z',
    lastSeenAt: '2026-09-07T02:15:00Z',
    observedAt: '2026-09-07T02:15:00Z',
    detectionCount: 3,
    source: 'EDGE',
    dataSource: 'LIVE',
    ...overrides,
  }
}

function query(overrides: Partial<TrackQuery> = {}): TrackQuery {
  return { ...DEFAULT_TRACK_QUERY, ...overrides }
}

/** Reads the (url, config) pair of the first recorded GET call. */
function firstGetCall(): [string, { params?: URLSearchParams }] {
  const call = getMock.mock.calls[0] as unknown[] | undefined
  if (!call) throw new Error('expected at least one GET call')
  const [url, config] = call
  return [url as string, (config ?? {}) as { params?: URLSearchParams }]
}

describe('mock provider (DEMO fixtures)', () => {
  it('declares itself as the DEMO source', () => {
    expect(mockTrackingService.source).toBe('DEMO')
  })

  it('serves a known track and rejects an unknown one', async () => {
    const track = await mockTrackingService.getTrack('TRK-1042')
    expect(track.trackId).toBe('TRK-1042')
    expect(track.cameraId).toBe('CAM-07')
    expect(track.status).toBe('ACTIVE')

    await expect(mockTrackingService.getTrack('TRK-9999')).rejects.toThrow(
      /Track TRK-9999 was not found/
    )
  })

  it('filters by camera, class and status', async () => {
    const cameraPage = await mockTrackingService.listTracks(query({ cameraId: 'CAM-07' }))
    expect(cameraPage.total).toBe(9)
    expect(cameraPage.tracks.every(t => t.cameraId === 'CAM-07')).toBe(true)

    const vehiclePage = await mockTrackingService.listTracks(query({ class: 'VEHICLE' }))
    expect(vehiclePage.total).toBe(5)
    expect(vehiclePage.tracks.every(t => t.objectClass === 'VEHICLE')).toBe(true)

    const lostPage = await mockTrackingService.listTracks(query({ status: 'LOST' }))
    expect(lostPage.total).toBe(1)
    expect(lostPage.tracks.map(t => t.trackId)).toEqual(['TRK-1071'])
  })

  it('pages without overlap or loss', async () => {
    const page1 = await mockTrackingService.listTracks(query({ pageSize: 5, page: 1 }))
    const page2 = await mockTrackingService.listTracks(query({ pageSize: 5, page: 2 }))

    expect(page1.total).toBe(21)
    expect(page1.tracks.length).toBe(5)
    expect(page2.tracks.length).toBe(5)

    const ids1 = new Set(page1.tracks.map(t => t.trackId))
    const ids2 = new Set(page2.tracks.map(t => t.trackId))
    for (const id of ids2) expect(ids1.has(id)).toBe(false)
  })

  it('applies the 1h window against DEMO_NOW', async () => {
    const page = await mockTrackingService.listTracks(query({ timeRange: '1h', pageSize: 50 }))
    const cutoff = new Date('2026-09-07T03:00:00Z').getTime()

    expect(page.total).toBe(17)
    expect(page.tracks.every(t => new Date(t.lastSeenAt).getTime() >= cutoff)).toBe(true)
    const ids = page.tracks.map(t => t.trackId)
    // The four tracks last seen before 03:00Z are excluded.
    for (const excluded of ['TRK-1042', 'TRK-1081', 'TRK-1092', 'TRK-1096']) {
      expect(ids).not.toContain(excluded)
    }
  })

  it('searches identifiers case-insensitively across track fields', async () => {
    // TRK-1081 references TRK-1042 via candidateEntityId, so a bare
    // 'TRK-1042' search matches both; incident/correlation ids are exact.
    const byIncident = await mockTrackingService.listTracks(query({ search: 'inc-1042' }))
    expect(byIncident.tracks.map(t => t.trackId)).toEqual(['TRK-1042'])

    const byCorrelation = await mockTrackingService.listTracks(query({ search: 'cor-1042' }))
    expect(byCorrelation.tracks.map(t => t.trackId)).toEqual(['TRK-1042'])
  })

  it('serves camera feeds, rejects unknown cameras and reports summaries', async () => {
    const feed = await mockTrackingService.getTrackFeed('CAM-19')
    expect(feed.state).toBe('DEGRADED')
    expect(feed.tracks.map(t => t.trackId)).toEqual(['TRK-1061', 'TRK-1092', 'TRK-1093'])

    const unavailable = await mockTrackingService.getTrackFeed('CAM-21')
    expect(unavailable.state).toBe('UNAVAILABLE')
    expect(unavailable.tracks).toEqual([])
    expect(unavailable.lastUpdatedAt).toBeNull()

    await expect(mockTrackingService.listCameraTracks('CAM-99')).rejects.toThrow(
      /Tracking data unavailable for camera CAM-99/
    )

    const camTracks = await mockTrackingService.listCameraTracks('CAM-19')
    expect(camTracks.map(t => t.trackId)).toEqual(['TRK-1061', 'TRK-1092', 'TRK-1093'])
  })

  it('summarizes CAM-07 structurally (counts only)', async () => {
    const summary = await mockTrackingService.getTrackSummary('CAM-07')
    expect(summary.cameraId).toBe('CAM-07')
    expect(summary.totalTracks).toBe(9)
    expect(summary.totalActive).toBe(8)
    // Zero-initialized canonical unions: absent classes/statuses are counted as 0,
    // never omitted or invented (trackingSummary.ts buildTrackSummary contract).
    expect(summary.byClass).toEqual({ PERSON: 5, VEHICLE: 2, ANIMAL: 2, OBJECT: 0, UNKNOWN: 0 })
    expect(summary.byStatus).toEqual({
      ACTIVE: 7,
      REACQUIRED: 1,
      TENTATIVE: 1,
      LOST: 0,
      ENDED: 0,
      STALE: 0,
      INVALID: 0,
      UNKNOWN: 0,
    })
    expect(summary.lastUpdatedAt).toBe('2026-09-07T03:59:55Z')
  })

  it('lists active tracks as ACTIVE plus REACQUIRED only', async () => {
    const active = await mockTrackingService.getActiveTracks()
    expect(active.length).toBe(15)
    expect(active.every(t => t.status === 'ACTIVE' || t.status === 'REACQUIRED')).toBe(true)
    const ids = active.map(t => t.trackId)
    expect(ids).toContain('TRK-1045')
    for (const excluded of ['TRK-1061', 'TRK-1071', 'TRK-1055', 'TRK-1092', 'TRK-1096', 'TRK-1098']) {
      expect(ids).not.toContain(excluded)
    }
  })

  it('serves observation history from fixtures or the recorded trajectory', async () => {
    const obs = await mockTrackingService.getTrackHistory('TRK-1042')
    expect(obs.length).toBe(9)
    expect(obs[0]?.observationId).toBe('OBS-1042-01')
    expect(obs.every(o => o.trackId === 'TRK-1042')).toBe(true)

    // TRK-1092 has no dedicated observation fixtures; its single recorded
    // trajectory point is rendered as one observation — never more.
    const stale = await mockTrackingService.getTrackHistory('TRK-1092')
    expect(stale.length).toBe(1)
    expect(stale[0]?.observationId).toBe('OBS-TRK-1092-01')
    expect(stale[0]?.source).toBe('CENTRAL')
    expect(stale[0]?.quality).toBe('WEAK')
  })

  it('serves recorded lifecycle transitions only', async () => {
    const lifecycle = await mockTrackingService.getTrackLifecycleHistory('TRK-1045')
    expect(lifecycle.map(h => h.historyId)).toEqual([
      'HST-1045-01',
      'HST-1045-02',
      'HST-1045-03',
      'HST-1045-04',
    ])
    expect(lifecycle[3]?.newStatus).toBe('REACQUIRED')

    // TRK-1043 is ACTIVE with no recorded transitions — empty, never synthesized.
    expect(await mockTrackingService.getTrackLifecycleHistory('TRK-1043')).toEqual([])

    await expect(mockTrackingService.getTrackLifecycleHistory('TRK-9999')).rejects.toThrow(
      /Track TRK-9999 was not found/
    )
  })

  it('serves cross-camera candidates as hypotheses only', async () => {
    const candidates = await mockTrackingService.getTrackCandidates('TRK-1042')
    expect(candidates.length).toBe(1)
    const cand = candidates[0]
    if (!cand) throw new Error('CAND-1042-01 fixture missing')
    expect(cand.candidateId).toBe('CAND-1042-01')
    expect(cand.relationType).toBe('POSSIBLE_CONTINUATION')
    expect(cand.targetCameraId).toBe('CAM-08')
    expect(cand.candidateTrackId).toBe('TRK-1081')
    expect(cand.strength).toBe(0.76)
    expect(cand.gapDurationSec).toBe(19)

    expect(await mockTrackingService.getTrackCandidates('TRK-1061')).toEqual([])
  })
})

describe('real provider (REAL /api/v1)', () => {
  beforeEach(() => {
    getMock.mockReset()
  })

  it('declares itself as the REAL source', () => {
    expect(realTrackingService.source).toBe('REAL')
  })

  it('fetches a track and maps absent optionals to null/undefined', async () => {
    getMock.mockResolvedValue({ data: backendTrackPayload() })
    const track = await realTrackingService.getTrack('TRK-BE-1')

    expect(getMock).toHaveBeenCalledWith('/tracks/TRK-BE-1')
    expect(track.trackId).toBe('TRK-BE-1')
    expect(track.status).toBe('ACTIVE')
    expect(track.objectClass).toBe('PERSON')
    expect(track.source).toBe('EDGE')
    expect(track.dataSource).toBe('LIVE')

    expect(track.ageMs).toBeNull()
    expect(track.durationSec).toBeNull()
    expect(track.currentBoundingBox).toBeNull()
    expect(track.trajectory).toBeNull()
    expect(track.speed).toBeNull()
    expect(track.velocity).toBeNull()
    expect(track.direction).toBeNull()
    expect(track.confidence).toBeNull()
    expect(track.continuityQuality).toBeNull()
    expect(track.crossCameraCandidate).toBeNull()
    expect(track.cameraHealthContext).toBeUndefined()
    expect(track.updatedAt).toBeUndefined()
    expect(track.revision).toBeUndefined()
    expect(track.dataCompleteness).toBeUndefined()
    expect(track.missingObservationsNote).toBeUndefined()
  })

  it('maps supplied optionals verbatim', async () => {
    getMock.mockResolvedValue({
      data: backendTrackPayload({
        confidence: 0.88,
        continuityQuality: 'STRONG',
        speed: 1.4,
        velocity: 1.4,
        direction: 'NE',
        crossCameraCandidate: {
          targetCameraId: 'CAM-08',
          candidateTrackId: 'TRK-BE-2',
          continuityConfidence: 0.7,
          gapDurationSec: 19,
          sequenceNumber: 2,
          note: 'Possible continuation across sector boundary.',
        },
        cameraHealthContext: {
          status: 'DEGRADED',
          reliability: 'LOW',
          viewpointShiftDetected: true,
          note: 'View re-anchoring pending.',
        },
      }),
    })

    const track = await realTrackingService.getTrack('TRK-BE-1')
    expect(track.confidence).toBe(0.88)
    expect(track.continuityQuality).toBe('STRONG')
    expect(track.velocity).toBe(1.4)
    expect(track.direction).toBe('NE')
    expect(track.crossCameraCandidate?.targetCameraId).toBe('CAM-08')
    expect(track.crossCameraCandidate?.continuityConfidence).toBe(0.7)
    expect(track.cameraHealthContext?.status).toBe('DEGRADED')
    expect(track.cameraHealthContext?.reliability).toBe('LOW')
    expect(track.cameraHealthContext?.viewpointShiftDetected).toBe(true)
  })

  it('maps camera track lists, active tracks and feeds', async () => {
    getMock.mockResolvedValue({ data: [backendTrackPayload()] })
    const camTracks = await realTrackingService.listCameraTracks('CAM-07')
    expect(getMock).toHaveBeenCalledWith('/cameras/CAM-07/tracks')
    expect(camTracks[0]?.trackId).toBe('TRK-BE-1')

    getMock.mockResolvedValue({ data: [backendTrackPayload()] })
    const active = await realTrackingService.getActiveTracks()
    expect(getMock).toHaveBeenCalledWith('/tracks/recent')
    expect(active[0]?.trackId).toBe('TRK-BE-1')

    getMock.mockResolvedValue({
      data: {
        cameraId: 'CAM-07',
        state: 'READY',
        tracks: [backendTrackPayload()],
        lastUpdatedAt: '2026-09-07T03:00:00Z',
      },
    })
    const feed = await realTrackingService.getTrackFeed('CAM-07')
    expect(getMock).toHaveBeenCalledWith('/cameras/CAM-07/tracks/feed')
    expect(feed.cameraId).toBe('CAM-07')
    expect(feed.state).toBe('READY')
    expect(feed.lastUpdatedAt).toBe('2026-09-07T03:00:00Z')
    expect(feed.tracks[0]?.trackId).toBe('TRK-BE-1')
    expect(feed.providerHealth).toBeUndefined()
  })

  it('fetches lifecycle history with the canonical paging parameters', async () => {
    const h1 = {
      historyId: 'HST-BE-01',
      trackId: 'TRK-BE-1',
      revision: 1,
      oldStatus: null,
      newStatus: 'TENTATIVE',
      reason: null,
      timestamp: '2026-09-07T02:00:00Z',
    }
    const h2 = {
      ...h1,
      historyId: 'HST-BE-02',
      revision: 2,
      oldStatus: 'TENTATIVE',
      newStatus: 'ACTIVE',
      reason: 'Continuity confirmed across consecutive observations.',
      triggerDetectionId: 'DET-BE-9',
      provider: 'tracker-provider',
      providerVersion: '1.0.0',
      configurationVersion: 'cfg-1',
    }
    getMock.mockResolvedValue({ data: { history: [h2, h1], total: 2, page: 1, pageSize: 50 } })

    const events = await realTrackingService.getTrackLifecycleHistory('TRK-BE-1')
    expect(getMock).toHaveBeenCalledWith('/tracks/TRK-BE-1/history', {
      params: { page: 1, pageSize: 50 },
    })
    expect(events.length).toBe(2)
    expect(events[0]?.oldStatus).toBe('TENTATIVE')
    expect(events[1]?.oldStatus).toBeNull()
    expect(events[1]?.reason).toBeNull()
    expect(events[0]?.provider).toBe('tracker-provider')
  })

  it('fetches observations from the observations envelope', async () => {
    getMock.mockResolvedValue({
      data: {
        observations: [
          {
            observationId: 'OBS-BE-1',
            trackId: 'TRK-BE-1',
            cameraId: 'CAM-07',
            observedAt: '2026-09-07T02:14:11Z',
            source: 'EDGE',
          },
        ],
      },
    })

    const obs = await realTrackingService.getTrackHistory('TRK-BE-1')
    expect(getMock).toHaveBeenCalledWith('/tracks/TRK-BE-1/observations')
    expect(obs.length).toBe(1)
    expect(obs[0]?.observationId).toBe('OBS-BE-1')
    expect(obs[0]?.detectionId).toBeNull()
    expect(obs[0]?.bbox).toBeNull()
    expect(obs[0]?.quality).toBeNull()
    expect(obs[0]?.confidence).toBeNull()
    expect(obs[0]?.sequence).toBeNull()
    expect(obs[0]?.source).toBe('EDGE')
  })

  it('fetches candidates from the bare array response', async () => {
    getMock.mockResolvedValue({
      data: [
        {
          candidateId: 'CAND-BE-01',
          sourceTrackId: 'TRK-BE-1',
          targetCameraId: 'CAM-08',
          relationType: 'POSSIBLE_CONTINUATION',
          status: 'OPEN',
          createdAt: '2026-09-07T02:30:00Z',
        },
      ],
    })

    const candidates = await realTrackingService.getTrackCandidates('TRK-BE-1')
    expect(getMock).toHaveBeenCalledWith('/tracks/TRK-BE-1/candidates')
    const cand = candidates[0]
    if (!cand) throw new Error('expected one candidate')
    expect(cand.candidateTrackId).toBeNull()
    expect(cand.strength).toBeNull()
    expect(cand.reason).toBeNull()
    expect(cand.expiresAt).toBeNull()
    expect(cand.gapDurationSec).toBeNull()
    expect(cand.relationType).toBe('POSSIBLE_CONTINUATION')
  })

  it('fetches the structural summary and preserves a null lastUpdatedAt', async () => {
    getMock.mockResolvedValue({
      data: {
        cameraId: 'CAM-07',
        totalActive: 2,
        totalTracks: 3,
        byClass: { PERSON: 2, VEHICLE: 1 },
        byStatus: { ACTIVE: 2, ENDED: 1 },
        lastUpdatedAt: null,
      },
    })

    const summary = await realTrackingService.getTrackSummary('CAM-07')
    expect(getMock).toHaveBeenCalledWith('/cameras/CAM-07/tracks/summary')
    expect(summary.cameraId).toBe('CAM-07')
    expect(summary.totalTracks).toBe(3)
    expect(summary.totalActive).toBe(2)
    expect(summary.byClass.PERSON).toBe(2)
    expect(summary.byStatus.ACTIVE).toBe(2)
    expect(summary.lastUpdatedAt).toBeNull()
  })

  it('maps the frontend query contract onto backend parameters', async () => {
    getMock.mockResolvedValue({ data: { tracks: [], total: 0, page: 2, pageSize: 20 } })
    await realTrackingService.listTracks(
      query({
        search: 'trk',
        cameraId: 'CAM-07',
        class: 'PERSON',
        status: 'LOST',
        source: 'EDGE',
        timeRange: '1h',
        sort: 'oldest',
        order: 'asc',
        page: 2,
        pageSize: 20,
      })
    )

    const [url, config] = firstGetCall()
    expect(url).toBe('/tracks')
    const params = config.params
    if (!params) throw new Error('expected URLSearchParams')
    expect(params.get('search')).toBe('trk')
    expect(params.get('camera_id')).toBe('CAM-07')
    expect(params.get('class')).toBe('PERSON')
    expect(params.get('status')).toBe('LOST')
    expect(params.get('source')).toBe('EDGE')
    expect(params.get('sort')).toBe('first_seen')
    expect(params.get('order')).toBe('asc')
    expect(params.get('page')).toBe('2')
    expect(params.get('pageSize')).toBe('20')
    const fromTime = params.get('from_time')
    expect(fromTime).toBeTruthy()
    expect(Number.isNaN(new Date(fromTime ?? '').getTime())).toBe(false)
  })

  it('omits ALL-typed filters and time windows by default', async () => {
    getMock.mockResolvedValue({
      data: { tracks: [backendTrackPayload()], total: 1, page: 1, pageSize: 20 },
    })
    const result = await realTrackingService.listTracks(query())

    const [url, config] = firstGetCall()
    expect(url).toBe('/tracks')
    const params = config.params
    if (!params) throw new Error('expected URLSearchParams')
    expect(params.has('search')).toBe(false)
    expect(params.has('camera_id')).toBe(false)
    expect(params.has('class')).toBe(false)
    expect(params.has('status')).toBe(false)
    expect(params.has('source')).toBe(false)
    expect(params.has('from_time')).toBe(false)
    expect(params.get('sort')).toBe('last_seen')
    expect(params.get('order')).toBe('desc')

    expect(result.total).toBe(1)
    expect(result.tracks[0]?.trackId).toBe('TRK-BE-1')
  })

  it('surfaces unreachable backends as TRACKING DATA UNAVAILABLE on every read', async () => {
    getMock.mockRejectedValue(new AxiosError('Network Error', 'ERR_NETWORK'))

    const calls: Array<Promise<unknown>> = [
      realTrackingService.getTrack('TRK-BE-1'),
      realTrackingService.listTracks(query()),
      realTrackingService.listCameraTracks('CAM-07'),
      realTrackingService.getTrackHistory('TRK-BE-1'),
      realTrackingService.getTrackLifecycleHistory('TRK-BE-1'),
      realTrackingService.getTrackCandidates('TRK-BE-1'),
      realTrackingService.getTrackFeed('CAM-07'),
      realTrackingService.getTrackSummary('CAM-07'),
      realTrackingService.getActiveTracks(),
    ]
    for (const call of calls) {
      await expect(call).rejects.toThrow(/TRACKING DATA UNAVAILABLE/)
    }
  })

  it('never substitutes fixture tracks when the backend is unreachable', async () => {
    // The DEMO corpus is non-empty, so a silent fallback would be observable.
    expect(MOCK_TRACKS.length).toBe(21)
    getMock.mockRejectedValue(new AxiosError('Network Error', 'ERR_NETWORK'))

    const outcome = await realTrackingService.getActiveTracks().then(
      () => 'resolved' as const,
      () => 'rejected' as const
    )
    expect(outcome).toBe('rejected')
  })

  it('treats proxy gateway statuses (502/504) as backend-unavailable', async () => {
    // Found live in §27 QA: with the backend stopped, vite's dev proxy
    // answers 502, so the browser sees a response — the old code emitted a
    // generic "Tracking API Error (502)" instead of the spec-required
    // TRACKING DATA UNAVAILABLE surface (§28).
    getMock.mockRejectedValue(httpError(502, 'Bad Gateway'))

    await expect(realTrackingService.getTrack('TRK-BE-1')).rejects.toThrow(
      /TRACKING DATA UNAVAILABLE/
    )
    await expect(realTrackingService.getTrackFeed('CAM-07')).rejects.toThrow(
      /TRACKING DATA UNAVAILABLE/
    )
    await expect(realTrackingService.getActiveTracks()).rejects.toThrow(
      /TRACKING DATA UNAVAILABLE/
    )
  })

  it('surfaces HTTP errors with status and backend detail', async () => {
    getMock.mockRejectedValue(httpError(404, 'track not found'))

    await expect(realTrackingService.getTrack('TRK-BE-1')).rejects.toThrow(
      /Tracking API Error \(404\): track not found/
    )
  })

  it("surfaces the C6 structured error envelope's message, not [object Object]", async () => {
    // Real backend shape: {"detail": {"error": {"code", "message"}}} (routes.py).
    // Found live in §27 QA: the track detail page rendered "[object Object]".
    const err = new AxiosError('Request failed', 'ERR_BAD_RESPONSE')
    err.response = {
      status: 404,
      data: {
        detail: {
          error: { code: 'TRACK_NOT_FOUND', message: "Track 'TRK-NOPE' not found." },
        },
      },
      statusText: '',
      headers: {},
      config: { headers: {} } as never,
    }
    getMock.mockRejectedValue(err)

    await expect(realTrackingService.getTrack('TRK-NOPE')).rejects.toThrow(
      /Tracking API Error \(404\): Track 'TRK-NOPE' not found\./
    )
  })
})

describe('mode gate (VITE_TRACKING_MODE)', () => {
  afterEach(() => {
    vi.unstubAllEnvs()
    vi.resetModules()
  })

  it('serves the DEMO provider by default', async () => {
    vi.resetModules()
    const mod = await import('@/services/tracking')
    expect(mod.trackingService.source).toBe('DEMO')
  })

  it('serves the REAL provider only when VITE_TRACKING_MODE=REAL', async () => {
    vi.stubEnv('VITE_TRACKING_MODE', 'REAL')
    vi.resetModules()
    const mod = await import('@/services/tracking')
    expect(mod.trackingService.source).toBe('REAL')
  })
})
