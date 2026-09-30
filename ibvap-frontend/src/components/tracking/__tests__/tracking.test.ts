// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 6 — Track Intelligence logic & fixture-contract tests (§38)
//
// Pure-derivation and fixture-contract tests only: no DOM, no rendering.
// Every expectation is derived from recorded fixture facts (DEMO corpus):
// lifecycle helpers must never synthesize a transition, formatting must never
// invent a value, and fixture payloads must never carry identity claims or
// threat vocabulary. DOM-level behavior is covered by browser QA (disclosed).
// ─────────────────────────────────────────────────────────────────────────────

import { describe, expect, it } from 'vitest'
import type { TrackLifecycleEvent, TrackStatus } from '@/types/tracking'
import { TRACK_STATUSES } from '@/types/tracking'
import type { CorrelationGroup } from '@/types/eventCorrelation'
import {
  DEMO_NOW,
  MOCK_CANDIDATES,
  MOCK_FEEDS,
  MOCK_LIFECYCLE,
  MOCK_OBSERVATIONS,
  MOCK_TRACKS,
  TRK_1042,
  TRK_1052,
  TRK_1061,
} from '@/services/tracking/mockTrackingData'
import {
  findLatestReacquisition,
  findLatestTransition,
  lifecycleStateAt,
  sortNewestFirst,
} from '../trackLifecycle'
import { correlationStatusText, relationLabel, trajectoryQualityNotes } from '../trackDetailDerive'
import type { TrackTone } from '../trackTone'
import {
  FEED_STATE_TONE,
  QUALITY_TONE,
  SOURCE_TONE,
  STATUS_TONE,
  badgeTone,
  toneForCameraHealth,
  toneForFeedState,
  toneForQuality,
  toneForSource,
  toneForStatus,
} from '../trackTone'
import {
  describeConfidence,
  describeTrack,
  formatBBox,
  formatClock,
  formatConfidence,
  formatContinuityQuality,
  formatDate,
  formatDuration,
  formatObservationCount,
  formatSourceLabel,
  formatSpeed,
  formatTrackClassLabel,
  formatTrackStatus,
  formatVelocity,
} from '../trackFormat'

/** Fixture access treated as possibly-absent — helpers must cope with no records. */
function historyFor(trackId: string): TrackLifecycleEvent[] {
  return MOCK_LIFECYCLE[trackId] ?? []
}

/** Synthetic recorded-transition factory used only for helper edge cases. */
function ev(id: string, newStatus: TrackStatus, timestamp: string): TrackLifecycleEvent {
  return {
    historyId: id,
    trackId: 'TRK-SYN',
    revision: 1,
    oldStatus: null,
    newStatus,
    reason: null,
    timestamp,
  }
}

function groupFixture(overrides: Partial<CorrelationGroup> = {}): CorrelationGroup {
  return {
    correlationId: 'COR-1042',
    incidentId: 'INC-1042',
    incidentState: 'NEW',
    status: 'CORRELATED',
    state: 'ACTIVE',
    startedAt: '2026-09-07T02:14:11Z',
    endedAt: null,
    eventCount: 2,
    cameraCount: 2,
    memberEventsLoaded: null,
    memberEvents: [],
    primaryEventId: null,
    relationships: [],
    explanation: [],
    explanationSummary: null,
    correlationStrength: 'MEDIUM',
    confidence: null,
    temporalWindowSec: 300,
    risk: { score: null, severity: null, incidentIds: [] },
    uncertainty: { reliability: 'MEDIUM', note: null },
    trackCandidate: null,
    cameraChain: null,
    modalities: [],
    sectorId: null,
    regionProfile: null,
    sources: [],
    healthContext: [],
    evidenceCount: 0,
    connectivity: 'LIVE',
    duplicatedOrSuppressed: false,
    history: {
      createdAt: '2026-09-07T02:14:11Z',
      updatedAt: '2026-09-07T02:20:00Z',
      transitions: [],
    },
    updatedAt: '2026-09-07T02:20:00Z',
    ...overrides,
  }
}

describe('trackLifecycle — recorded transitions only', () => {
  it('sortNewestFirst returns a newest-first copy without mutating the input', () => {
    const history = historyFor('TRK-1045')
    const sorted = sortNewestFirst(history)

    expect(sorted.map(h => h.historyId)).toEqual([
      'HST-1045-04',
      'HST-1045-03',
      'HST-1045-02',
      'HST-1045-01',
    ])
    // Fixture order is oldest-first; the sort must not touch the source array.
    expect(history.map(h => h.historyId)).toEqual([
      'HST-1045-01',
      'HST-1045-02',
      'HST-1045-03',
      'HST-1045-04',
    ])
  })

  it('findLatestTransition returns the latest record for a status, else null', () => {
    const history = historyFor('TRK-1045')

    expect(findLatestTransition(history, 'LOST')?.historyId).toBe('HST-1045-03')
    expect(findLatestTransition(history, 'ACTIVE')?.historyId).toBe('HST-1045-02')
    expect(findLatestTransition(history, 'ENDED')).toBeNull()
    expect(findLatestTransition([], 'ACTIVE')).toBeNull()
  })

  it('lifecycleStateAt derives the state at an instant and null when uncovered', () => {
    const history = historyFor('TRK-1045')

    expect(lifecycleStateAt(history, '2026-09-07T03:52:30Z')).toBe('TENTATIVE')
    expect(lifecycleStateAt(history, '2026-09-07T03:53:10Z')).toBe('ACTIVE')
    expect(lifecycleStateAt(history, '2026-09-07T03:54:00Z')).toBe('LOST')
    expect(lifecycleStateAt(history, '2026-09-07T03:56:40Z')).toBe('REACQUIRED')

    // Before the first recorded transition, or with no usable instant: null.
    expect(lifecycleStateAt(history, '2026-09-07T03:51:59Z')).toBeNull()
    expect(lifecycleStateAt(history, '')).toBeNull()
    expect(lifecycleStateAt(history, null)).toBeNull()
    expect(lifecycleStateAt(history, 'not-a-timestamp')).toBeNull()
    expect(lifecycleStateAt([], DEMO_NOW)).toBeNull()
  })

  it('findLatestReacquisition reads the recorded TRK-1045 LOST → REACQUIRED pair', () => {
    const ctx = findLatestReacquisition(historyFor('TRK-1045'))
    if (!ctx) throw new Error('expected a recorded reacquisition for TRK-1045')

    expect(ctx.lost.historyId).toBe('HST-1045-03')
    expect(ctx.reacquired.historyId).toBe('HST-1045-04')
    expect(ctx.gapSec).toBe(180)
  })

  it('findLatestReacquisition returns null when no pair was recorded', () => {
    // TRK-1071 is LOST and was never reacquired — LOST is not ENDED, and a
    // reacquisition context must never be invented.
    expect(findLatestReacquisition(historyFor('TRK-1071'))).toBeNull()
    expect(findLatestReacquisition(historyFor('TRK-1042'))).toBeNull()
    expect(findLatestReacquisition([])).toBeNull()
  })

  it('findLatestReacquisition picks the latest pair from unsorted input', () => {
    const pair1 = [
      ev('L1', 'LOST', '2026-09-07T01:00:00Z'),
      ev('R1', 'REACQUIRED', '2026-09-07T01:01:00Z'),
    ]
    const pair2 = [
      ev('L2', 'LOST', '2026-09-07T02:00:00Z'),
      ev('R2', 'REACQUIRED', '2026-09-07T02:02:00Z'),
    ]

    const ctx = findLatestReacquisition([...pair2, ...pair1])
    if (!ctx) throw new Error('expected the later pair to be detected')

    expect(ctx.lost.historyId).toBe('L2')
    expect(ctx.reacquired.historyId).toBe('R2')
    expect(ctx.gapSec).toBe(120)
  })

  it('findLatestReacquisition ignores a REACQUIRED with no preceding LOST', () => {
    const history = [
      ev('A1', 'ACTIVE', '2026-09-07T00:00:00Z'),
      ev('R1', 'REACQUIRED', '2026-09-07T00:05:00Z'),
    ]
    expect(findLatestReacquisition(history)).toBeNull()
  })
})

describe('trajectoryQualityNotes — §12 notes only from recorded conditions', () => {
  it('yields no notes for an unremarkable STRONG/COMPLETE track', () => {
    expect(trajectoryQualityNotes(TRK_1042)).toEqual([])
  })

  it('yields MODERATE continuity, DEGRADED camera and viewpoint-shift notes for TRK-1052 in order', () => {
    expect(trajectoryQualityNotes(TRK_1052)).toEqual([
      'Moderate continuity — some recorded observations may not connect cleanly; movement between them is not represented.',
      'Camera is reporting DEGRADED — feed quality may have limited observation availability for this track.',
      'Viewpoint shift detected for this camera — stored positions may not align with earlier observations until the view is re-anchored.',
    ])
  })

  it('yields WEAK continuity plus the recorded missing-observations note for TRK-1061', () => {
    const notes = trajectoryQualityNotes(TRK_1061)

    expect(notes).toEqual([
      'Limited continuity (WEAK) — recorded observations are sparse or unreliable; movement between them is not represented.',
      'Tentative hypothesis; insufficient consecutive hits to confirm continuous trajectory.',
    ])
    // A recorded note must not be supplemented by the generic PARTIAL wording.
    expect(notes).not.toContain(
      'Data completeness PARTIAL — some observations of this track are not represented.'
    )
  })

  it('falls back to the generic PARTIAL note only when no note was recorded', () => {
    const partial = { ...TRK_1042, dataCompleteness: 'PARTIAL' as const }
    expect(trajectoryQualityNotes(partial)).toEqual([
      'Data completeness PARTIAL — some observations of this track are not represented.',
    ])
  })

  it('prefers the recorded missing-observations note over the generic PARTIAL note', () => {
    const both = {
      ...TRK_1042,
      missingObservationsNote: 'Recorded gap between observations 4 and 5.',
      dataCompleteness: 'PARTIAL' as const,
    }
    expect(trajectoryQualityNotes(both)).toEqual(['Recorded gap between observations 4 and 5.'])
  })

  it('yields an OFFLINE camera note from the attached health context', () => {
    const offline = {
      ...TRK_1042,
      cameraHealthContext: { status: 'OFFLINE' as const, reliability: 'LOW' as const },
    }
    expect(trajectoryQualityNotes(offline)).toEqual([
      'Camera is reporting OFFLINE — no further observations can be recorded while it is offline.',
    ])
  })

  it('treats WEAK and MODERATE continuity as mutually exclusive', () => {
    expect(trajectoryQualityNotes({ ...TRK_1042, continuityQuality: 'WEAK' })).toEqual([
      'Limited continuity (WEAK) — recorded observations are sparse or unreliable; movement between them is not represented.',
    ])
    expect(trajectoryQualityNotes({ ...TRK_1042, continuityQuality: 'MODERATE' })).toEqual([
      'Moderate continuity — some recorded observations may not connect cleanly; movement between them is not represented.',
    ])
  })
})

describe('relationLabel — hypothesis vocabulary, §20', () => {
  it('renders the two candidate relations as explicit possibilities', () => {
    expect(relationLabel('POSSIBLE_CONTINUATION')).toBe('Possible continuation')
    expect(relationLabel('POSSIBLE_SAME_ENTITY')).toBe('Possible same entity')
  })

  it('degrades unknown relation types to a neutral lowercase label', () => {
    expect(relationLabel('SEQUENCE_GROUP')).toBe('sequence group')
  })
})

describe('correlationStatusText — §17 display-only relation status', () => {
  it('renders counts, verbatim strength and lowercased group status when ready', () => {
    expect(correlationStatusText('ready', groupFixture())).toBe(
      '2 correlated events · strength MEDIUM · group status correlated'
    )
    expect(correlationStatusText('ready', groupFixture({ status: 'DISSOLVED' }))).toBe(
      '2 correlated events · strength MEDIUM · group status dissolved'
    )
    expect(correlationStatusText('ready', groupFixture({ eventCount: 1 }))).toBe(
      '1 correlated event · strength MEDIUM · group status correlated'
    )
  })

  it('reports a missing strength as not recorded', () => {
    expect(correlationStatusText('ready', groupFixture({ correlationStrength: null }))).toBe(
      '2 correlated events · strength not recorded · group status correlated'
    )
  })

  it('states load failure instead of inventing a relation', () => {
    expect(correlationStatusText('error', null)).toBe(
      'Relation status unavailable — correlation data could not be loaded.'
    )
  })

  it('shows a loading state before data arrives', () => {
    expect(correlationStatusText('loading', null)).toBe('Loading relation status…')
    expect(correlationStatusText('idle', null)).toBe('Loading relation status…')
  })
})

describe('tone maps — complete coverage of the canonical unions', () => {
  it('maps every TrackStatus', () => {
    const expected: Record<TrackStatus, TrackTone> = {
      ACTIVE: 'cyan',
      TENTATIVE: 'warning',
      LOST: 'warning',
      REACQUIRED: 'info',
      ENDED: 'default',
      STALE: 'default',
      INVALID: 'critical',
      UNKNOWN: 'default',
    }
    for (const status of TRACK_STATUSES) {
      expect(STATUS_TONE[status]).toBe(expected[status])
      expect(toneForStatus(status)).toBe(expected[status])
    }
  })

  it('maps continuity quality, feed state and source', () => {
    expect(QUALITY_TONE).toEqual({
      STRONG: 'cyan',
      MODERATE: 'warning',
      WEAK: 'critical',
      UNKNOWN: 'default',
    })
    expect(FEED_STATE_TONE).toEqual({
      READY: 'cyan',
      PROCESSING: 'cyan',
      DEGRADED: 'warning',
      UNAVAILABLE: 'critical',
      STALE: 'warning',
      OFFLINE: 'critical',
      UNKNOWN: 'default',
    })
    expect(SOURCE_TONE).toEqual({
      LIVE: 'cyan',
      EDGE: 'emerald',
      CENTRAL: 'cyan',
      DEMO: 'amber',
      UNKNOWN: 'default',
    })
    expect(toneForQuality('WEAK')).toBe('critical')
    expect(toneForFeedState('UNAVAILABLE')).toBe('critical')
    expect(toneForSource('EDGE')).toBe('emerald')
  })

  it('maps camera health as camera context, never track severity', () => {
    expect(toneForCameraHealth('ONLINE')).toBe('emerald')
    expect(toneForCameraHealth('DEGRADED')).toBe('warning')
    expect(toneForCameraHealth('OFFLINE')).toBe('critical')
    expect(toneForCameraHealth('UNKNOWN')).toBe('default')
  })

  it('maps tones onto valid badge variants', () => {
    const pairs: Array<[TrackTone, ReturnType<typeof badgeTone>]> = [
      ['emerald', 'safe'],
      ['amber', 'warning'],
      ['info', 'info'],
      ['warning', 'warning'],
      ['critical', 'critical'],
      ['cyan', 'cyan'],
      ['default', 'default'],
    ]
    for (const [tone, expected] of pairs) {
      expect(badgeTone(tone)).toBe(expected)
    }
  })
})

describe('trackFormat — display-only formatting', () => {
  it('formats confidence from ratio or percent, N/A when absent', () => {
    expect(formatConfidence(0.91)).toBe('91%')
    expect(formatConfidence(91)).toBe('91%')
    expect(formatConfidence(false)).toBe('N/A')
    expect(formatConfidence(null)).toBe('N/A')
    expect(formatConfidence(undefined)).toBe('N/A')
    expect(describeConfidence(0.92)).toBe('92 percent confidence')
    expect(describeConfidence(null)).toBe('confidence not provided')
  })

  it('formats clock and date for valid ISO, dash otherwise', () => {
    expect(formatClock('2026-09-07T02:14:11Z')).toMatch(/^\d{2}:\d{2}:\d{2}$/)
    expect(formatClock(null)).toBe('—')
    expect(formatClock('not-a-timestamp')).toBe('—')
    // Month abbreviation length is environment-locale dependent ('Sep' vs 'Sept');
    // assert the 'DD Mon' structure + the '—' fallback, not an exact locale string.
    expect(formatDate('2026-09-07T02:14:11Z')).toMatch(/^\d{2} [A-Z][a-z]{2,4}$/)
    expect(formatDate(null)).toBe('—')
  })

  it('formats durations without inventing precision', () => {
    expect(formatDuration(18000)).toBe('18s')
    expect(formatDuration(60000)).toBe('1m')
    expect(formatDuration(150000)).toBe('2m 30s')
    expect(formatDuration(390000)).toBe('6m 30s')
    expect(formatDuration(3600000)).toBe('1h')
    expect(formatDuration(4500000)).toBe('1h 15m')
    expect(formatDuration(null)).toBe('—')
  })

  it('formats speed and velocity with units, N/A when absent', () => {
    expect(formatSpeed(1.4)).toBe('1.4 m/s')
    expect(formatSpeed(null)).toBe('N/A')
    expect(formatVelocity(1.4, 'NE')).toBe('1.4 m/s NE')
    expect(formatVelocity(1.4, null)).toBe('1.4 m/s')
    expect(formatVelocity(null, null)).toBe('N/A')
  })

  it('formats observation counts, geometry and labels', () => {
    expect(formatObservationCount(1)).toBe('1 observation')
    expect(formatObservationCount(9)).toBe('9 observations')
    expect(formatBBox(0.38, 0.44, 0.09, 0.21)).toBe('0.380 · 0.440 · 0.090 · 0.210')
    expect(formatBBox(null, 0.44, 0.09, 0.21)).toBe('N/A')
    expect(formatSourceLabel('EDGE')).toBe('Edge')
    expect(formatSourceLabel('UNKNOWN')).toBe('Unknown')
    expect(formatSourceLabel(null)).toBe('Unknown')
    expect(formatTrackClassLabel('PERSON')).toBe('Person')
    expect(formatTrackClassLabel(null)).toBe('Unknown')
    expect(formatTrackStatus('REACQUIRED')).toBe('Reacquired')
    expect(formatTrackStatus(null)).toBe('Unknown')
    expect(formatContinuityQuality('WEAK')).toBe('Weak')
    expect(formatContinuityQuality('UNKNOWN')).toBe('Unknown')
  })

  it('describes a track for screen readers without identity language', () => {
    const text = describeTrack('TRK-1042', 'PERSON', 'ACTIVE', 0.92, 'CAM-07', '2026-09-07T02:14:11Z')
    expect(text).toMatch(
      /^Track TRK-1042, Person, active, 92 percent confidence, camera CAM-07, \d{2}:\d{2}:\d{2}\.$/
    )
  })
})

describe('fixture integrity — DEMO corpus contracts', () => {
  const byId = new Map(MOCK_TRACKS.map(t => [t.trackId, t]))

  it('ships 21 unique tracks with the expected class distribution', () => {
    expect(MOCK_TRACKS.length).toBe(21)
    expect(new Set(MOCK_TRACKS.map(t => t.trackId)).size).toBe(21)

    const classCounts = new Map<string, number>()
    for (const t of MOCK_TRACKS) {
      classCounts.set(t.objectClass, (classCounts.get(t.objectClass) ?? 0) + 1)
    }
    expect(classCounts.get('PERSON')).toBe(9)
    expect(classCounts.get('VEHICLE')).toBe(5)
    expect(classCounts.get('ANIMAL')).toBe(5)
    expect(classCounts.get('OBJECT')).toBe(1)
    expect(classCounts.get('UNKNOWN')).toBe(1)
  })

  it('records linked lifecycle chains whose final state matches the track', () => {
    for (const [trackId, records] of Object.entries(MOCK_LIFECYCLE)) {
      expect(records.length).toBeGreaterThan(0)
      const track = byId.get(trackId)
      if (!track) throw new Error(`lifecycle fixture ${trackId} has no matching track`)
      expect(records[0]?.oldStatus).toBeNull()
      for (let i = 0; i < records.length; i += 1) {
        const rec = records[i]
        if (!rec) throw new Error(`missing lifecycle record ${i} for ${trackId}`)
        expect(rec.trackId).toBe(trackId)
        expect(rec.revision).toBe(i + 1)
        if (i > 0) expect(rec.oldStatus).toBe(records[i - 1]?.newStatus)
      }
      const last = records[records.length - 1]
      expect(last?.newStatus).toBe(track.status)
    }
  })

  it('keeps TRK-1071 LOST — never rewritten as ENDED', () => {
    const lost = byId.get('TRK-1071')
    if (!lost) throw new Error('TRK-1071 fixture missing')
    expect(lost.status).toBe('LOST')

    const history = historyFor('TRK-1071')
    expect(history.some(h => h.newStatus === 'LOST')).toBe(true)
    expect(history.some(h => h.newStatus === 'ENDED')).toBe(false)
  })

  it('resolves the recorded lifecycle state at DEMO_NOW for key scenarios', () => {
    expect(lifecycleStateAt(historyFor('TRK-1042'), DEMO_NOW)).toBe('ACTIVE')
    expect(lifecycleStateAt(historyFor('TRK-1055'), DEMO_NOW)).toBe('ENDED')
    expect(lifecycleStateAt(historyFor('TRK-1045'), DEMO_NOW)).toBe('REACQUIRED')
  })

  it('covers every track exactly once across camera feeds', () => {
    const feedIds: string[] = []
    for (const [cameraId, feed] of Object.entries(MOCK_FEEDS)) {
      expect(feed.cameraId).toBe(cameraId)
      for (const t of feed.tracks) {
        expect(t.cameraId).toBe(cameraId)
        feedIds.push(t.trackId)
      }
    }
    expect(feedIds.length).toBe(21)
    expect(new Set(feedIds).size).toBe(21)
    expect([...feedIds].sort()).toEqual(MOCK_TRACKS.map(t => t.trackId).sort())
  })

  it('keeps the DEGRADED and UNAVAILABLE camera states explicit', () => {
    const degraded = MOCK_FEEDS['CAM-19']
    if (!degraded) throw new Error('CAM-19 feed fixture missing')
    expect(degraded.state).toBe('DEGRADED')

    const unavailable = MOCK_FEEDS['CAM-21']
    if (!unavailable) throw new Error('CAM-21 feed fixture missing')
    expect(unavailable.state).toBe('UNAVAILABLE')
    expect(unavailable.tracks).toEqual([])
    expect(unavailable.lastUpdatedAt).toBeNull()
  })

  it('keeps cross-camera candidates hypothetical', () => {
    for (const [trackId, candidates] of Object.entries(MOCK_CANDIDATES)) {
      for (const c of candidates) {
        expect(c.sourceTrackId).toBe(trackId)
        expect(c.relationType.startsWith('POSSIBLE_')).toBe(true)
      }
    }

    const refCands = MOCK_CANDIDATES['TRK-1042'] ?? []
    expect(refCands.length).toBe(1)
    const cand = refCands[0]
    if (!cand) throw new Error('CAND-1042-01 fixture missing')
    expect(cand.candidateId).toBe('CAND-1042-01')
    expect(cand.relationType).toBe('POSSIBLE_CONTINUATION')
    expect(cand.targetCameraId).toBe('CAM-08')
    expect(cand.candidateTrackId).toBe('TRK-1081')
    expect(cand.strength).toBe(0.76)
    expect(cand.gapDurationSec).toBe(19)
    expect(cand.status).toBe('OPEN')
  })

  it('ships no identity-claim or threat vocabulary in fixture payloads', () => {
    const banned = [
      'same person',
      'same vehicle',
      'confirmed identity',
      'identity confirmed',
      'verified identity',
      'identified as',
      'is the same',
      'threat',
      'risk',
      'score',
    ]
    const corpus = JSON.stringify([
      MOCK_TRACKS,
      MOCK_OBSERVATIONS,
      MOCK_LIFECYCLE,
      MOCK_CANDIDATES,
      MOCK_FEEDS,
    ]).toLowerCase()

    const hits = banned.filter(term => corpus.includes(term))
    expect(hits).toEqual([])
  })
})
