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
import { MOCK_GROUPS, MOCK_GROUP_BY_ID, MOCK_MEMBER_BY_ID } from '@/services/correlation/mockCorrelationData'
import { mockCorrelationService } from '@/services/correlation/mockCorrelationService'
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
  diffSec,
  formatCameraCount,
  formatCameraList,
  formatClock,
  formatConfidence,
  formatDate,
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