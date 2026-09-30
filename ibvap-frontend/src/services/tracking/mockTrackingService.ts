// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 6 — mock tracking provider (DEMO ONLY)
//
// Serves isolated fixtures from `mockTrackingData.ts` over the canonical
// `ITrackingService` interface. Implements query filtering, sorting, pagination,
// observation histories and structural summaries with an async delay (250ms).
// Never computes tracking algorithms or fabricates threats.
// ─────────────────────────────────────────────────────────────────────────────

import type {
  Track,
  TrackCandidate,
  TrackLifecycleEvent,
  TrackingFeed,
  TrackObservation,
  TrackQuery,
  TrackResultPage,
  TrackSummary,
} from '@/types/tracking'
import type { ITrackingService } from './ITrackingService'
import {
  DEMO_NOW,
  getMockTrack,
  getMockTrackCandidates,
  getMockTrackFeed,
  getMockTrackHistory,
  getMockTrackLifecycle,
  MOCK_TRACKS,
} from './mockTrackingData'
import { buildTrackSummary } from './trackingSummary'

const PROVIDER_DELAY_MS = 250

function delay(ms: number): Promise<void> {
  return new Promise<void>(resolve => setTimeout(resolve, ms))
}

function withinTimeRange(iso: string, range: TrackQuery['timeRange']): boolean {
  if (range === 'all') return true
  const ref = new Date(DEMO_NOW).getTime()
  const t = new Date(iso).getTime()
  const minutes = range === '15m' ? 15 : range === '1h' ? 60 : range === 'today' ? 24 * 60 : 0
  if (minutes === 0) return true
  return ref - t <= minutes * 60_000
}

function matchesQuery(t: Track, q: TrackQuery): boolean {
  const s = q.search.trim().toLowerCase()
  const searchHit =
    s === '' ||
    t.trackId.toLowerCase().includes(s) ||
    t.cameraId.toLowerCase().includes(s) ||
    t.objectClass.toLowerCase().includes(s) ||
    (t.currentDetectionId?.toLowerCase().includes(s) ?? false) ||
    (t.eventId?.toLowerCase().includes(s) ?? false) ||
    (t.incidentId?.toLowerCase().includes(s) ?? false) ||
    (t.evidenceId?.toLowerCase().includes(s) ?? false) ||
    (t.correlationId?.toLowerCase().includes(s) ?? false) ||
    (t.candidateEntityId?.toLowerCase().includes(s) ?? false)

  if (!searchHit) return false
  if (q.cameraId !== 'ALL' && t.cameraId !== q.cameraId) return false
  if (q.class !== 'ALL' && t.objectClass !== q.class) return false
  if (q.status !== 'ALL' && t.status !== q.status) return false
  if (q.source !== 'ALL' && t.source !== q.source) return false
  if (!withinTimeRange(t.lastSeenAt, q.timeRange)) return false

  return true
}

function compareTracks(a: Track, b: Track, q: TrackQuery): number {
  const dir = q.order === 'asc' ? 1 : -1
  switch (q.sort) {
    case 'longest': {
      const da = a.durationSec ?? 0
      const db = b.durationSec ?? 0
      return (da - db) * dir
    }
    case 'observations':
      return (a.detectionCount - b.detectionCount) * dir
    case 'camera':
      return a.cameraId.localeCompare(b.cameraId) * dir
    case 'oldest':
      return (new Date(a.firstSeenAt).getTime() - new Date(b.firstSeenAt).getTime()) * dir
    case 'latest':
    default:
      return (new Date(b.lastSeenAt).getTime() - new Date(a.lastSeenAt).getTime()) * dir
  }
}

class MockTrackingService implements ITrackingService {
  readonly source = 'DEMO' as const

  async getTrack(trackId: string): Promise<Track> {
    await delay(PROVIDER_DELAY_MS)
    const track = getMockTrack(trackId)
    if (!track) {
      throw new Error(`Track ${trackId} was not found.`)
    }
    return track
  }

  async listTracks(query: TrackQuery): Promise<TrackResultPage> {
    await delay(PROVIDER_DELAY_MS)
    const filtered = MOCK_TRACKS.filter(t => matchesQuery(t, query)).sort((a, b) =>
      compareTracks(a, b, query)
    )
    const pageSize = query.pageSize
    const start = (query.page - 1) * pageSize
    return {
      tracks: filtered.slice(start, start + pageSize),
      total: filtered.length,
      page: query.page,
      pageSize,
    }
  }

  async listCameraTracks(cameraId: string): Promise<Track[]> {
    await delay(PROVIDER_DELAY_MS)
    const feed = getMockTrackFeed(cameraId)
    if (!feed) {
      throw new Error(`Tracking data unavailable for camera ${cameraId}.`)
    }
    return feed.tracks
  }

  async getTrackHistory(trackId: string): Promise<TrackObservation[]> {
    await delay(PROVIDER_DELAY_MS)
    const track = getMockTrack(trackId)
    if (!track) {
      throw new Error(`Track ${trackId} was not found.`)
    }
    return getMockTrackHistory(trackId)
  }

  async getTrackLifecycleHistory(trackId: string): Promise<TrackLifecycleEvent[]> {
    await delay(PROVIDER_DELAY_MS)
    const track = getMockTrack(trackId)
    if (!track) {
      throw new Error(`Track ${trackId} was not found.`)
    }
    // Fixtures only — tracks without recorded transitions return an empty list
    // (the workspace then states "no transitions recorded", never synthesizes).
    return getMockTrackLifecycle(trackId)
  }

  async getTrackCandidates(trackId: string): Promise<TrackCandidate[]> {
    await delay(PROVIDER_DELAY_MS)
    const track = getMockTrack(trackId)
    if (!track) {
      throw new Error(`Track ${trackId} was not found.`)
    }
    return getMockTrackCandidates(trackId)
  }

  async getTrackFeed(cameraId: string): Promise<TrackingFeed> {
    await delay(PROVIDER_DELAY_MS)
    const feed = getMockTrackFeed(cameraId)
    if (!feed) {
      throw new Error(`Tracking data unavailable for camera ${cameraId}.`)
    }
    return feed
  }

  async getTrackSummary(cameraId: string): Promise<TrackSummary> {
    const feed = await this.getTrackFeed(cameraId)
    return buildTrackSummary(feed.cameraId, feed.tracks, feed.lastUpdatedAt)
  }

  async getActiveTracks(): Promise<Track[]> {
    await delay(PROVIDER_DELAY_MS)
    return MOCK_TRACKS.filter(t => t.status === 'ACTIVE' || t.status === 'REACQUIRED')
  }
}

export const mockTrackingService = new MockTrackingService()
