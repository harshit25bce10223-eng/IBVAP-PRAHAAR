// PRHAAR Component 3 — contract + formatting tests (logic only, no DOM)
//
// Guards the seams Phase-2 must satisfy: fixtures carry only renderable
// states, every hash is a full 64-hex SHA-256 digest, verification verdicts
// arrive from the provider (never computed locally), and no string in the
// fixture corpus makes legal/admissibility claims.

import { describe, expect, it } from 'vitest'
import {
  ANCHOR_STATES,
  EVIDENCE_TYPES,
  INTEGRITY_STATES,
} from '@/types/evidence'
import type { EvidenceQuery } from '@/types/evidence'
import { MOCK_AUDIT, MOCK_EVIDENCE, MOCK_LEDGER } from '@/services/evidence/mockEvidenceData'
import { mockEvidenceService } from '@/services/evidence/mockEvidenceService'
import { realEvidenceService } from '@/services/evidence/realEvidenceService'
import { DEFAULT_EVIDENCE_QUERY } from '@/store/evidenceState'
import {
  toneForAnchor,
  toneForIntegrity,
  toneForLedger,
  toneForRecordStatus,
  toneForSync,
  TONE,
} from '../evidenceTone'
import { formatBytes, formatCount, formatDuration, humanize, truncateHash } from '../evidenceFormat'

const BASE_QUERY: EvidenceQuery = { ...DEFAULT_EVIDENCE_QUERY, pageSize: 20 }

const HEX64 = /^[0-9a-f]{64}$/
const BANNED_CLAIMS = [
  'court admissible',
  'legally certified',
  'forensically guaranteed',
  'unbreakable',
  '100% secure',
  'attacker-proof',
  'collision-proof',
  'blockchain-confirmed',
  'tampered by attacker',
  'evidence is fake',
]

describe('fixture contract (what Phase 2 must also satisfy)', () => {
  it('covers the four required scenarios EVD-10482…EVD-10485', () => {
    const byId = new Map(MOCK_EVIDENCE.map(r => [r.evidenceId, r]))
    const healthy = byId.get('EVD-10482')!
    expect(healthy.integrity).toBe('VERIFIED')
    expect(healthy.anchor.state).toBe('ANCHORED')
    expect(healthy.dataSource).toBe('EDGE')
    expect(healthy.syncState).toBe('SYNCED')

    const pending = byId.get('EVD-10483')!
    expect(pending.integrity).toBe('PENDING')
    expect(pending.anchor.state).toBe('PENDING')
    expect(pending.syncState).toBe('SYNC_PENDING')

    const mismatch = byId.get('EVD-10484')!
    expect(mismatch.integrity).toBe('MISMATCH')
    expect(mismatch.anchor.state).toBe('ANCHORED')
    expect(mismatch.dataSource).toBe('CENTRAL')
    expect(mismatch.status).toBe('UNDER_REVIEW')

    const noMedia = byId.get('EVD-10485')!
    expect(noMedia.mediaKind).toBe('none')
    expect(noMedia.integrity).toBe('VERIFIED')
  })

  it('every recorded digest is a full 64-hex SHA-256 value, unique per record', () => {
    const seen = new Set<string>()
    for (const r of MOCK_EVIDENCE) {
      expect(r.hashAlgorithm).toBe('SHA-256')
      expect(r.recordedHash).toMatch(HEX64)
      expect(seen.has(r.recordedHash)).toBe(false)
      seen.add(r.recordedHash)
    }
  })

  it('every status in fixtures is a canonical enum member', () => {
    for (const r of MOCK_EVIDENCE) {
      expect(EVIDENCE_TYPES).toContain(r.type)
      expect(INTEGRITY_STATES).toContain(r.integrity)
      expect(ANCHOR_STATES).toContain(r.anchor.state)
    }
  })

  it('no fixture, audit or ledger string makes legal/admissibility claims', () => {
    const corpus = JSON.stringify([MOCK_EVIDENCE, MOCK_AUDIT, MOCK_LEDGER]).toLowerCase()
    for (const claim of BANNED_CLAIMS) {
      expect(corpus).not.toContain(claim)
    }
  })

  it('all fixtures are labelled DEMO — never LIVE', () => {
    expect(MOCK_LEDGER.source).toBe('DEMO')
    expect(mockEvidenceService.source).toBe('DEMO')
  })
})

describe('mock provider (identical interface to the future backend)', () => {
  it('lists with filtering, sorting and pagination', async () => {
    const all = await mockEvidenceService.list(BASE_QUERY)
    expect(all.total).toBe(MOCK_EVIDENCE.length)

    const cam = await mockEvidenceService.list({ ...BASE_QUERY, cameraId: 'CAM-12' })
    expect(cam.total).toBeGreaterThan(0)
    expect(cam.records.every(r => r.cameraId === 'CAM-12')).toBe(true)

    const mismatch = await mockEvidenceService.list({ ...BASE_QUERY, integrity: 'MISMATCH' })
    expect(mismatch.records.map(r => r.evidenceId)).toContain('EVD-10484')

    const search = await mockEvidenceService.list({ ...BASE_QUERY, search: 'a3f8c79d' })
    expect(search.records.map(r => r.evidenceId)).toContain('EVD-10482')

    const page1 = await mockEvidenceService.list({ ...BASE_QUERY, page: 1, pageSize: 4 })
    const page2 = await mockEvidenceService.list({ ...BASE_QUERY, page: 2, pageSize: 4 })
    expect(page1.records.length).toBe(4)
    expect(page2.records[0].evidenceId).not.toBe(page1.records[0].evidenceId)
  })

  it('returns MATCH with identical digests for a healthy record', async () => {
    const res = await mockEvidenceService.verify('EVD-10482')
    expect(res.outcome).toBe('MATCH')
    expect(res.computedHash).toBe(res.recordedHash)
    expect(res.historyEntry).not.toBeNull()
  })

  it('returns MISMATCH with differing digests for the investigation case', async () => {
    const res = await mockEvidenceService.verify('EVD-10484')
    expect(res.outcome).toBe('MISMATCH')
    expect(res.computedHash).not.toBe(res.recordedHash)
    expect(res.computedHash).toMatch(HEX64)
  })

  it('rejects unknown ids and unavailable verifiers without fabricating', async () => {
    await expect(mockEvidenceService.get('EVD-00000')).rejects.toThrow()
    await expect(mockEvidenceService.verify('EVD-00000')).rejects.toThrow()
    await expect(mockEvidenceService.verify('EVD-10463')).rejects.toThrow()
  })

  it('serves ledger summary and audit trail', async () => {
    const summary = await mockEvidenceService.ledgerSummary()
    expect(summary.recordCount).toBeGreaterThan(0)
    const audit = await mockEvidenceService.listAudit(3)
    expect(audit.length).toBe(3)
  })

  it('RealEvidenceService has source LIVE and defines required API endpoints', () => {
    expect(realEvidenceService.source).toBe('LIVE')
    expect(typeof realEvidenceService.list).toBe('function')
    expect(typeof realEvidenceService.get).toBe('function')
    expect(typeof realEvidenceService.verify).toBe('function')
    expect(typeof realEvidenceService.requestExport).toBe('function')
    expect(typeof realEvidenceService.ledgerSummary).toBe('function')
    expect(typeof realEvidenceService.listAudit).toBe('function')
  })
})

describe('tone map (single source for every surface)', () => {
  it('maps every integrity, anchor, record, ledger and sync state', () => {
    for (const s of INTEGRITY_STATES) expect(TONE[toneForIntegrity(s)]).toBeDefined()
    for (const s of ANCHOR_STATES) expect(TONE[toneForAnchor(s)]).toBeDefined()
    for (const s of ['VALID', 'UNDER_REVIEW', 'QUARANTINED', 'UNKNOWN'] as const) {
      expect(TONE[toneForRecordStatus(s)]).toBeDefined()
    }
    for (const s of ['HEALTHY', 'DEGRADED', 'UNAVAILABLE', 'VERIFYING', 'UNKNOWN'] as const) {
      expect(TONE[toneForLedger(s)]).toBeDefined()
    }
    for (const s of ['LOCAL_ONLY', 'SYNC_PENDING', 'SYNCED', 'SYNC_FAILED', 'UNKNOWN'] as const) {
      expect(TONE[toneForSync(s)]).toBeDefined()
    }
    expect(toneForIntegrity('VERIFIED')).toBe('good')
    expect(toneForIntegrity('MISMATCH')).toBe('failed')
    expect(toneForIntegrity('PENDING')).toBe('degraded')
    expect(toneForIntegrity('HASHED')).toBe('degraded')
  })
})

describe('formatting honesty', () => {
  it('truncates hashes for rows but keeps the full digest intact', () => {
    const full = MOCK_EVIDENCE[0].recordedHash
    const short = truncateHash(full)
    expect(short).toContain('…')
    expect(short.length).toBeLessThan(full.length)
    expect(short.startsWith(full.slice(0, 8))).toBe(true)
    expect(truncateHash('')).toBe('HASH NOT AVAILABLE')
  })

  it('renders N/A for missing sizes and durations, never zero', () => {
    expect(formatBytes(null)).toBe('N/A')
    expect(formatDuration(null)).toBe('N/A')
    expect(formatBytes(0)).toBe('0 B')
    expect(formatBytes(412608)).toContain('KB')
  })

  it('humanizes enums and formats counts', () => {
    expect(humanize('VIDEO_CLIP')).toBe('Video Clip')
    expect(humanize('SYNC_PENDING')).toBe('Sync Pending')
    expect(formatCount(1248)).toBe('1,248')
  })

  it('default query is newest-first, page one', () => {
    expect(DEFAULT_EVIDENCE_QUERY.sort).toBe('captured_at')
    expect(DEFAULT_EVIDENCE_QUERY.order).toBe('desc')
    expect(DEFAULT_EVIDENCE_QUERY.page).toBe(1)
  })
})
