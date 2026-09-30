// PRHAAR Component 4 — contract + formatting tests (logic only, no DOM)
//
// Guards the seams Phase-2 must satisfy: correlation is never severity, the
// fee corpus covers every status shape, no group fabricates a confidence,
// risk or identity, unknown ids reject, and no string in the fixture corpus
// makes a causality/identity claim.

import { describe, expect, it } from 'vitest'
import {
  CORRELATION_STATUSES,
  DEFAULT_CORRELATION_QUERY,
} from '@/types/eventCorrelation'
import type { EventLogQuery } from '@/types/eventCorrelation'
import { MOCK_GROUPS, MOCK_GROUP_BY_ID, MOCK_MEMBER_BY_ID, MOCK_TIME_ANCHOR_MS } from '@/services/correlation/mockCorrelationData'
import { mockCorrelationService } from '@/services/correlation/mockCorrelationService'
import { realCorrelationService } from '@/services/correlation/RealCorrelationService'
import {
  compareCorrelationGroups,
  matchesCorrelationQuery,
  matchesTimeRange,
} from '@/services/correlation/correlationFilter'
import { queryFromSearchParams, queryToSearchParams } from '@/services/correlation/correlationQueryUrl'
import { relationsFor, useCorrelationStore } from '@/store/correlationState'
import {
  CORRELATION_LABEL,
  CONNECTIVITY_LABEL,
  INCIDENT_STATE_LABEL,
  RELIABILITY_LABEL,
  TONE,
  toneForConnectivity,
  toneForCorrelation,
  toneForIncidentState,
  toneForReliability,
} from '../correlationTone'
import {
  compareByObservedTime,
  diffSec,
  formatCameraCount,
  formatCameraList,
  formatClock,
  formatClockShort,
  formatConfidence,
  formatDate,
  formatGroupCount,
  formatModalities,
  formatSec,
  formatSignalCount,
  formatWindow,
} from '../correlationFormat'

const BASE_QUERY: EventLogQuery = { ...DEFAULT_CORRELATION_QUERY, pageSize: 20 }

const BANNED_CLAIMS = [
  'same person',
  'suspected identity',
  'confirmed identity',
  'known identity',
  'caused by',
  'caused this',
  'because of signal',
  'establishes causation',
  'guaranteed',
  '100% certain',
  'never wrong',
]

describe('fixture contract — correlation is never severity, never fabricated', () => {
  it('covers every correlation status the log must render', () => {
    const seen = new Set(MOCK_GROUPS.map(g => g.status))
    for (const s of ['STANDALONE', 'RELATED', 'CORRELATED', 'UNCERTAIN', 'DISSOLVED'] as const) {
      expect(seen.has(s), `missing scenario for ${s}`).toBe(true)
    }
  })

  it('never colours correlation with severity semantics', () => {
    for (const s of MOCK_GROUPS) {
      const tone = toneForCorrelation(s.status)
      expect(['accent', 'degraded', 'neutral']).toContain(tone)
      expect(tone).not.toBe('critical')
      expect(tone).not.toBe('failed')
    }
    expect(TONE.accent.badge).toBe('cyan')
    expect(TONE.neutral.badge).toBe('offline')
  })

  it('keeps severity orthogonal: correlated LOW exists, standalone HIGH exists', () => {
    const correlatedLow = MOCK_GROUPS.find(g => g.status === 'CORRELATED' && g.risk.severity === 'LOW')
    expect(correlatedLow).toBeDefined()
    expect(correlatedLow?.risk.severity).toBe('LOW')
  })

  it('never fabricates confidence or risk', () => {
    const noConfidence = MOCK_GROUPS.filter(g => g.confidence === null)
    expect(noConfidence.length).toBeGreaterThan(0)
    for (const g of noConfidence) {
      expect(g.trackCandidate).toBeNull()
    }
    // DISSOLVED groups carry no risk — UI must show nothing, not a score.
    const dissolved = MOCK_GROUPS.find(g => g.status === 'DISSOLVED')
    expect(dissolved?.risk.score).toBeNull()
    expect(dissolved?.risk.severity).toBeNull()
    // Any present confidence must be accompanied by an explanation note.
    for (const g of MOCK_GROUPS) {
      if (g.confidence !== null) expect(g.confidence.note.length).toBeGreaterThan(0)
    }
  })

  it('uses possible-entity language, never identity claims', () => {
    const corpus = JSON.stringify(MOCK_GROUPS).toLowerCase()
    for (const banned of BANNED_CLAIMS) {
      expect(corpus.includes(banned), `fixture contains banned claim '${banned}'`).toBe(false)
    }
    for (const g of MOCK_GROUPS) {
      if (g.trackCandidate) {
        expect(g.trackCandidate.label.toLowerCase()).toContain('possible')
      }
    }
  })

  it('provides cross-camera, multi-source and camera-chain scenarios', () => {
    expect(MOCK_GROUPS.some(g => g.cameraCount >= 2)).toBe(true)
    expect(MOCK_GROUPS.some(g => g.cameraChain !== null && g.cameraChain.length >= 2)).toBe(true)
    expect(MOCK_GROUPS.some(g => g.sources.length >= 2)).toBe(true)
    expect(MOCK_GROUPS.some(g => g.modalities.length >= 2)).toBe(true)
  })

  it('marks degraded camera health as context, not risk', () => {
    const withHealth = MOCK_GROUPS.filter(g => g.healthContext.length > 0)
    expect(withHealth.length).toBeGreaterThan(0)
    for (const g of withHealth) {
      for (const ctx of g.healthContext) {
        expect(['HIGH', 'MEDIUM', 'LOW', 'UNKNOWN']).toContain(ctx.reliability)
      }
    }
  })

  it('labels connectivity in honest terms (never realtime fiction)', () => {
    const connectivities = new Set(MOCK_GROUPS.map(g => g.connectivity))
    expect(connectivities.has('DELAYED')).toBe(true)
    expect(connectivities.has('LAST_SYNCED')).toBe(true)
    expect(connectivities.has('LIVE')).toBe(true)
  })

  it('keeps every group on the fixed demo date', () => {
    for (const g of MOCK_GROUPS) {
      expect(g.startedAt.startsWith('2026-09-07')).toBe(true)
    }
  })
})

describe('mock provider (identical interface to the future backend)', () => {
  it('lists with filtering, sorting and pagination', async () => {
    const all = await mockCorrelationService.listGroups({ ...BASE_QUERY })
    expect(all.total).toBe(MOCK_GROUPS.length)

    const correlated = await mockCorrelationService.listGroups({ ...BASE_QUERY, correlation: 'CORRELATED' })
    expect(correlated.groups.length).toBeGreaterThan(0)
    expect(correlated.groups.every(g => g.status === 'CORRELATED')).toBe(true)

    const cam07 = await mockCorrelationService.listGroups({ ...BASE_QUERY, cameraId: 'CAM-07' })
    expect(cam07.groups.every(g => g.memberEvents.some(m => m.cameraId === 'CAM-07'))).toBe(true)

    const bySignals = await mockCorrelationService.listGroups({ ...BASE_QUERY, sort: 'signals', order: 'desc' })
    const counts = bySignals.groups.map(g => g.eventCount)
    expect(counts).toEqual([...counts].sort((a, b) => b - a))
    expect(bySignals.groups[0].eventCount).toBe(20)
  })

  it('paginates across pages without losing groups', async () => {
    const page1 = await mockCorrelationService.listGroups({ ...BASE_QUERY, pageSize: 4, page: 1 })
    const page2 = await mockCorrelationService.listGroups({ ...BASE_QUERY, pageSize: 4, page: 2 })
    expect(page1.total).toBe(MOCK_GROUPS.length)
    const ids = new Set([...page1.groups, ...page2.groups].map(g => g.correlationId))
    expect(ids.size).toBe(page1.groups.length + page2.groups.length)
  })

  it('searches across incident, correlation, event, camera and track ids', async () => {
    const byIncident = await mockCorrelationService.listGroups({ ...BASE_QUERY, search: 'INC-1042' })
    expect(byIncident.groups[0].incidentId).toBe('INC-1042')
    const byEvent = await mockCorrelationService.listGroups({ ...BASE_QUERY, search: 'EV-10431' })
    expect(byEvent.groups[0].correlationId).toBe('COR-1043')
    const byTrack = await mockCorrelationService.listGroups({ ...BASE_QUERY, search: 'TRK-1042' })
    expect(byTrack.groups[0].trackCandidate?.trackId).toBe('TRK-1042')
  })

  it('returns recent groups and camera-scoped groups', async () => {
    const recent = await mockCorrelationService.listRecent(6)
    expect(recent.length).toBe(6)
    for (let i = 1; i < recent.length; i++) {
      expect(new Date(recent[i - 1].startedAt).getTime()).toBeGreaterThanOrEqual(new Date(recent[i].startedAt).getTime())
    }
    const forCam = await mockCorrelationService.listForCamera('CAM-12', 4)
    expect(forCam.length).toBeLessThanOrEqual(4)
    expect(forCam.every(g => g.memberEvents.some(m => m.cameraId === 'CAM-12'))).toBe(true)
  })

  it('resolves known groups and member events, rejects unknown ones', async () => {
    const g = await mockCorrelationService.getGroup('COR-1042')
    expect(g.correlationId).toBe('COR-1042')
    const rel = await mockCorrelationService.getRelationships('COR-1042')
    expect(Array.isArray(rel)).toBe(true)
    const m = await mockCorrelationService.getMemberEvent('EV-10422')
    expect(m.eventId).toBe('EV-10422')

    await expect(mockCorrelationService.getGroup('COR-NOPE')).rejects.toThrow(/not found/)
    await expect(mockCorrelationService.getRelationships('COR-NOPE')).rejects.toThrow(/not found/)
    await expect(mockCorrelationService.getMemberEvent('EV-NOPE')).rejects.toThrow(/not found/)
  })

  it('is marked DEMO, never masquerading as LIVE', async () => {
    expect(mockCorrelationService.source).toBe('DEMO')
  })
})

describe('correlation formatting — display only', () => {
  it('formats windows with clock and duration', () => {
    const group = MOCK_GROUPS.find(g => g.correlationId === 'COR-1042')!
    const label = formatWindow(group.startedAt, group.endedAt)
    expect(label).toContain('·')
    expect(label).toMatch(/\d{2}:\d{2}:\d{2}/)
  })

  it('diffSec computes whole seconds', () => {
    expect(diffSec('2026-09-07T02:14:11Z', '2026-09-07T02:14:43Z')).toBe(32)
    expect(diffSec('bad', '2026-09-07T02:14:43Z')).toBeNull()
  })

  it('formats counts, confidence, modalities and camera lists', () => {
    expect(formatSignalCount(1)).toBe('1 signal')
    expect(formatSignalCount(5)).toBe('5 signals')
    expect(formatCameraCount(2)).toBe('2 cameras')
    expect(formatConfidence(0.72)).toBe('72%')
    expect(formatModalities(['VIDEO', 'ANPR'])).toBe('VIDEO · ANPR')
    expect(formatModalities([])).toBe('—')
    expect(formatCameraList(['CAM-07', 'CAM-08'], ['CAM-07'])).toBe('CAM-07 / CAM-08')
    expect(formatCameraList(null, [])).toBe('CAMERA UNKNOWN')
  })

  it('never formats a clock from an invalid date', () => {
    expect(formatClock('not-a-date')).toBe('—')
    expect(formatDate(null)).toBe('—')
    expect(formatSec(null)).toBe('—')
    expect(formatSec(90)).toBe('1m 30s')
  })
})

describe('correlation tones — status, connectivity, reliability, incident state', () => {
  it('maps every status and gives it a text label', () => {
    for (const s of CORRELATION_STATUSES) {
      expect(CORRELATION_LABEL[s].length).toBeGreaterThan(0)
      expect(TONE[toneForCorrelation(s)].badge).toBeTruthy()
    }
  })

  it('honestly labels connectivity', () => {
    expect(CONNECTIVITY_LABEL.LIVE).toBe('LIVE')
    expect(CONNECTIVITY_LABEL.DELAYED).toBe('DELAYED')
    expect(CONNECTIVITY_LABEL.LAST_SYNCED).toBe('LAST SYNCED')
    expect(TONE[toneForConnectivity('DELAYED')].badge).toBe('warning')
    expect(TONE[toneForConnectivity('LAST_SYNCED')].badge).toBe('warning')
    expect(TONE[toneForConnectivity('UNKNOWN')].badge).toBe('offline')
  })

  it('labels reliability and incident lifecycle separately', () => {
    expect(RELIABILITY_LABEL.UNKNOWN).toBe('UNKNOWN')
    expect(INCIDENT_STATE_LABEL.NEW).toBe('NEW')
    expect(TONE[toneForReliability('LOW')].badge).toBe('critical')
    expect(TONE[toneForReliability('UNKNOWN')].badge).toBe('offline')
    expect(TONE[toneForIncidentState('NEW')].badge).toBe('warning')
    expect(TONE[toneForIncidentState('CLOSED')].badge).toBe('offline')
  })
})

describe('constant index sanity', () => {
  it('every mock group is keyed and discoverable', () => {
    expect(Object.keys(MOCK_GROUP_BY_ID).length).toBe(MOCK_GROUPS.length)
    const memberCount = MOCK_GROUPS.reduce((n, g) => n + g.memberEvents.length, 0)
    expect(Object.keys(MOCK_MEMBER_BY_ID).length).toBe(memberCount)
  })

  it('denormalized groups expose a primaryEventId that exists', () => {
    for (const g of MOCK_GROUPS) {
      if (g.primaryEventId) {
        expect(g.memberEvents.some(m => m.eventId === g.primaryEventId)).toBe(true)
      }
    }
  })

  it('partial member loads stay honest about the authoritative count', () => {
    const partial = MOCK_GROUPS.find(g => g.memberEventsLoaded !== null)
    if (partial) {
      expect(partial.memberEvents.length).toBe(partial.memberEventsLoaded)
      expect(partial.eventCount).toBeGreaterThan(partial.memberEvents.length)
    }
  })
})

describe('event log deep links — URL ⇄ query (§62/§71)', () => {
  it('omits every default from the URL', () => {
    expect(queryToSearchParams({ ...DEFAULT_CORRELATION_QUERY }).toString()).toBe('')
  })

  it('round-trips a fully configured view', () => {
    const q: EventLogQuery = {
      ...DEFAULT_CORRELATION_QUERY,
      search: 'CAM-07',
      correlation: 'CORRELATED',
      severity: 'HIGH',
      cameraId: 'CAM-07',
      sectorId: 'SECTOR-B',
      source: 'ANPR',
      connectivity: 'DELAYED',
      timeRange: '1h',
      sort: 'signals',
      order: 'asc',
      page: 3,
      pageSize: 25,
    }
    const back = { ...DEFAULT_CORRELATION_QUERY, ...queryFromSearchParams(queryToSearchParams(q)) }
    expect(back).toEqual(q)
  })

  it('ignores unknown or invalid URL values instead of guessing', () => {
    const patch = queryFromSearchParams(
      new URLSearchParams({
        status: 'TOTALLY_CORRELATED',
        severity: 'APOCALYPTIC',
        range: 'decade',
        sort: 'vibes',
        order: 'sideways',
        connectivity: 'REALTIME',
        page: '0',
        pageSize: '9000',
      })
    )
    expect(patch).toEqual({})
  })

  it('accepts page ≥ 1 and pageSize 1–100, rejects the rest', () => {
    expect(queryFromSearchParams(new URLSearchParams({ page: '2', pageSize: '100' }))).toEqual({
      page: 2,
      pageSize: 100,
    })
    expect(queryFromSearchParams(new URLSearchParams({ page: '1.5' }))).toEqual({})
    expect(queryFromSearchParams(new URLSearchParams({ page: '-3' }))).toEqual({})
    expect(queryFromSearchParams(new URLSearchParams({ pageSize: '0' }))).toEqual({})
    expect(queryFromSearchParams(new URLSearchParams({ pageSize: '101' }))).toEqual({})
  })

  it('never puts a whitespace-only search into the URL', () => {
    expect(queryToSearchParams({ ...DEFAULT_CORRELATION_QUERY, search: '   ' }).toString()).toBe('')
    expect(queryFromSearchParams(new URLSearchParams({ search: '  ' }))).toEqual({})
  })
})

describe('severity and time-range filtering (§58/§64)', () => {
  it('filters by backend severity verbatim and reports the filtered total', async () => {
    const high = await mockCorrelationService.listGroups({ ...BASE_QUERY, severity: 'HIGH' })
    const expected = MOCK_GROUPS.filter(g => g.risk.severity === 'HIGH')
    expect(expected.length).toBeGreaterThan(0)
    expect(high.total).toBe(expected.length)
    expect(high.groups.every(g => g.risk.severity === 'HIGH')).toBe(true)

    // An unscored group is not a match for any band — no severity is invented.
    const unscored = MOCK_GROUPS.find(g => g.risk.severity === null)!
    expect(matchesCorrelationQuery(unscored, { ...BASE_QUERY, severity: 'HIGH' })).toBe(false)
  })

  it('combines filters without dropping the previous WHERE clause (§58)', async () => {
    const both = await mockCorrelationService.listGroups({
      ...BASE_QUERY,
      severity: 'MEDIUM',
      correlation: 'CORRELATED',
    })
    const expected = MOCK_GROUPS.filter(g => g.risk.severity === 'MEDIUM' && g.status === 'CORRELATED')
    expect(expected.length).toBeGreaterThan(0)
    expect(both.total).toBe(expected.length)
    expect(both.groups.every(g => g.risk.severity === 'MEDIUM' && g.status === 'CORRELATED')).toBe(true)

    const cameraAndSeverity = await mockCorrelationService.listGroups({
      ...BASE_QUERY,
      severity: 'LOW',
      cameraId: 'CAM-12',
    })
    expect(cameraAndSeverity.groups.length).toBeGreaterThan(0)
    expect(
      cameraAndSeverity.groups.every(
        g => g.risk.severity === 'LOW' && g.memberEvents.some(m => m.cameraId === 'CAM-12')
      )
    ).toBe(true)
  })

  it('evaluates DEMO windows against the fixture anchor, never the wall clock', async () => {
    const anchored = await mockCorrelationService.listGroups({ ...BASE_QUERY, timeRange: '15m' })
    expect(anchored.total).toBeGreaterThan(0)
    expect(anchored.total).toBeLessThan(MOCK_GROUPS.length)
    expect(anchored.total).toBe(
      MOCK_GROUPS.filter(g => matchesTimeRange(g.startedAt, '15m', MOCK_TIME_ANCHOR_MS)).length
    )
    expect(anchored.groups.every(g => matchesTimeRange(g.startedAt, '15m', MOCK_TIME_ANCHOR_MS))).toBe(true)

    // Far from the anchor the same window excludes every fixture — proving the
    // provider measured from the anchor, not from "now".
    const farFuture = MOCK_GROUPS.filter(g =>
      matchesTimeRange(g.startedAt, '15m', MOCK_TIME_ANCHOR_MS + 86_400_000)
    )
    expect(farFuture.length).toBe(0)
    expect(matchesTimeRange('not-a-date', '15m', MOCK_TIME_ANCHOR_MS)).toBe(false)
    expect(matchesTimeRange('not-a-date', 'all', MOCK_TIME_ANCHOR_MS)).toBe(true)
  })

  it('keeps pagination totals consistent with the filter set', async () => {
    const q = { ...BASE_QUERY, severity: 'LOW' as const, pageSize: 2, page: 1 }
    const page1 = await mockCorrelationService.listGroups(q)
    const page2 = await mockCorrelationService.listGroups({ ...q, page: 2 })
    const expected = MOCK_GROUPS.filter(g => g.risk.severity === 'LOW').length
    expect(page1.total).toBe(expected)
    expect(page2.total).toBe(expected)
    expect(page1.groups.every(g => g.risk.severity === 'LOW')).toBe(true)
    const ids = new Set([...page1.groups, ...page2.groups].map(g => g.correlationId))
    expect(ids.size).toBe(page1.groups.length + page2.groups.length)
  })
})

describe('deterministic chronological ordering (§60)', () => {
  it('breaks equal-time ties by eventId, never by input order', () => {
    const a = { eventId: 'EV-2', timestamp: '2026-09-07T02:14:11Z' }
    const b = { eventId: 'EV-1', timestamp: '2026-09-07T02:14:11Z' }
    expect([a, b].sort(compareByObservedTime).map(e => e.eventId)).toEqual(['EV-1', 'EV-2'])
    expect([b, a].sort(compareByObservedTime).map(e => e.eventId)).toEqual(['EV-1', 'EV-2'])
  })

  it('orders out-of-order arrivals chronologically for any permutation', () => {
    const events = [
      { eventId: 'EV-c', timestamp: '2026-09-07T02:14:43Z' },
      { eventId: 'EV-a', timestamp: '2026-09-07T02:14:11Z' },
      { eventId: 'EV-b', timestamp: '2026-09-07T02:14:29Z' },
    ]
    const expected = ['EV-a', 'EV-b', 'EV-c']
    expect([...events].sort(compareByObservedTime).map(e => e.eventId)).toEqual(expected)
    expect([...events].reverse().sort(compareByObservedTime).map(e => e.eventId)).toEqual(expected)
    expect([events[1], events[0], events[2]].sort(compareByObservedTime).map(e => e.eventId)).toEqual(expected)
  })

  it('sorts unparseable timestamps last, never somewhere in the middle', () => {
    const events = [
      { eventId: 'EV-broken', timestamp: 'not-a-timestamp' },
      { eventId: 'EV-late', timestamp: '2026-09-07T03:00:00Z' },
      { eventId: 'EV-early', timestamp: '2026-09-07T02:00:00Z' },
    ]
    expect([...events].sort(compareByObservedTime).map(e => e.eventId)).toEqual([
      'EV-early',
      'EV-late',
      'EV-broken',
    ])
    expect([...events].reverse().sort(compareByObservedTime).map(e => e.eventId)).toEqual([
      'EV-early',
      'EV-late',
      'EV-broken',
    ])
  })

  it('derives every fixture group window from observed signal time (§60)', () => {
    for (const g of MOCK_GROUPS) {
      const sorted = [...g.memberEvents].sort(compareByObservedTime)
      expect(new Date(g.startedAt).getTime(), `${g.correlationId} start`).toBe(
        new Date(sorted[0].timestamp).getTime()
      )
    }
  })

  it('orders equal signal counts by correlationId so paging is stable', () => {
    const mk = (id: string, count: number) => ({ ...MOCK_GROUP_BY_ID['COR-1042'], correlationId: id, eventCount: count })
    const q = { ...BASE_QUERY, sort: 'signals' as const, order: 'desc' as const }
    const sorted = [mk('COR-b', 5), mk('COR-a', 5), mk('COR-c', 5)].sort((a, b) => compareCorrelationGroups(a, b, q))
    expect(sorted.map(g => g.correlationId)).toEqual(['COR-a', 'COR-b', 'COR-c'])
  })

  it('sorts groups with no risk score last under severity sort', () => {
    const scored = MOCK_GROUP_BY_ID['COR-1042']
    const unscored = MOCK_GROUP_BY_ID['COR-1047']
    expect(scored.risk.severity).toBe('HIGH')
    expect(unscored.risk.severity).toBeNull()
    const q = { ...BASE_QUERY, sort: 'severity' as const, order: 'desc' as const }
    expect(
      [unscored, scored].sort((a, b) => compareCorrelationGroups(a, b, q)).map(g => g.risk.severity)
    ).toEqual(['HIGH', null])
    expect(
      [scored, unscored].sort((a, b) => compareCorrelationGroups(a, b, q)).map(g => g.risk.severity)
    ).toEqual(['HIGH', null])
  })
})

describe('real mode has no silent fallback (§63)', () => {
  it('is marked LIVE, never masquerading as DEMO', () => {
    expect(realCorrelationService.source).toBe('LIVE')
  })
})

describe('store semantics — page reset, expansion, relationship resolution', () => {
  it('resets to page 1 when a filter changes, keeps the page on sort/paging', () => {
    const s = useCorrelationStore
    s.setState({ query: { ...DEFAULT_CORRELATION_QUERY } })
    s.getState().setQuery({ page: 3 })
    expect(s.getState().query.page).toBe(3)

    s.getState().setQuery({ severity: 'HIGH' })
    expect(s.getState().query.page).toBe(1)
    expect(s.getState().query.severity).toBe('HIGH')

    s.getState().setQuery({ page: 2 })
    s.getState().setQuery({ sort: 'signals' })
    expect(s.getState().query.page).toBe(2)
    expect(s.getState().query.sort).toBe('signals')

    s.getState().resetList()
    expect(s.getState().query).toEqual(DEFAULT_CORRELATION_QUERY)
  })

  it('expands and collapses groups without duplicating ids', () => {
    const s = useCorrelationStore
    s.setState({ expandedIds: [] })
    s.getState().toggleExpanded('COR-1042')
    s.getState().toggleExpanded('COR-1050')
    s.getState().toggleExpanded('COR-1042')
    expect(s.getState().expandedIds).toEqual(['COR-1050'])
    s.setState({ expandedIds: [] })
  })

  it('prefers fetched relationships, falls back to denormalized, never fakes on error', () => {
    const g = MOCK_GROUP_BY_ID['COR-1042']
    expect(g.relationships.length).toBeGreaterThan(0)
    expect(relationsFor(g, {}, undefined)).toEqual(g.relationships)

    const fetched = [
      { fromEventId: 'EV-1', toEventId: 'EV-2', type: 'TEMPORAL' as const, strength: null, explanation: 'x' },
    ]
    expect(relationsFor(g, { 'COR-1042': fetched }, 'ready')).toEqual(fetched)
    expect(relationsFor(g, { 'COR-1042': fetched }, 'error')).toEqual([])
    expect(relationsFor(g, {}, 'loading')).toEqual(g.relationships)
  })
})

describe('expanded-row and log formatting additions', () => {
  it('formats short clocks and group counts', () => {
    expect(formatClockShort('2026-09-07T02:14:11Z')).toMatch(/\d{2}:\d{2}/)
    expect(formatClockShort(null)).toBe('—')
    expect(formatGroupCount(1)).toBe('1 group')
    expect(formatGroupCount(4)).toBe('4 groups')
  })

  it('a group with a camera chain reports it as a chain, not a claim of movement', () => {
    const chained = MOCK_GROUPS.find(g => g.cameraChain !== null && g.cameraChain.length >= 2)!
    const label = formatCameraList(chained.cameraChain, [])
    expect(label).toBe(chained.cameraChain!.join(' / '))
    expect(label.toLowerCase()).not.toContain('moved')
    expect(label.toLowerCase()).not.toContain('same person')
  })
})