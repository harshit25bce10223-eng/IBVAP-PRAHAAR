// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 3 — mock evidence provider (DEMO ONLY)
//
// Serves the isolated fixtures from `mockEvidenceData.ts`. A short fixed
// delay keeps async loading states exercisable; it does NOT simulate a
// backend. Verification verdicts come from the per-record MOCK_VERIFY table
// (mirroring what a backend would return) — nothing is computed locally.
// Unknown ids reject so the UI exercises error paths honestly.
// ─────────────────────────────────────────────────────────────────────────────

import type {
  AuditEntry,
  EvidencePage,
  EvidenceQuery,
  EvidenceRecord,
  LedgerSummary,
  VerifyResult,
} from '@/types/evidence'
import type { IEvidenceService, IExportReceipt } from './IEvidenceService'
import { MOCK_AUDIT, MOCK_EVIDENCE, MOCK_LEDGER, MOCK_VERIFY } from './mockEvidenceData'

const PROVIDER_DELAY_MS = 250

function delay(ms: number) {
  return new Promise<void>(resolve => setTimeout(resolve, ms))
}

const INTEGRITY_RANK: Record<string, number> = {
  VERIFIED: 0,
  UNVERIFIED: 1,
  PENDING: 2,
  UNAVAILABLE: 3,
  MISMATCH: 4,
  UNKNOWN: 5,
}

function applyQuery(records: EvidenceRecord[], q: EvidenceQuery): EvidenceRecord[] {
  const search = q.search.trim().toLowerCase()
  const out = records.filter(r => {
    if (q.cameraId !== 'ALL' && r.cameraId !== q.cameraId) return false
    if (q.type !== 'ALL' && r.type !== q.type) return false
    if (q.integrity !== 'ALL' && r.integrity !== q.integrity) return false
    if (q.anchor !== 'ALL' && r.anchor?.state !== q.anchor) return false
    if (q.source !== 'ALL' && r.source !== q.source) return false
    if (search) {
      const hay = `${r.evidenceId} ${r.incidentId} ${r.cameraId} ${r.recordedHash}`.toLowerCase()
      if (!hay.includes(search)) return false
    }
    return true
  })
  const dir = q.order === 'asc' ? 1 : -1
  return [...out].sort((a, b) => {
    if (q.sort === 'camera') return a.cameraId.localeCompare(b.cameraId) * dir
    if (q.sort === 'integrity') {
      return ((INTEGRITY_RANK[a.integrity] ?? 9) - (INTEGRITY_RANK[b.integrity] ?? 9)) * dir
    }
    return (new Date(a.capturedAt).getTime() - new Date(b.capturedAt).getTime()) * dir
  })
}

class MockEvidenceService implements IEvidenceService {
  readonly source = 'DEMO' as const

  async list(query: EvidenceQuery): Promise<EvidencePage> {
    await delay(PROVIDER_DELAY_MS)
    const filtered = applyQuery(MOCK_EVIDENCE, query)
    const start = (query.page - 1) * query.pageSize
    return {
      records: filtered.slice(start, start + query.pageSize),
      total: filtered.length,
    }
  }

  async get(evidenceId: string): Promise<EvidenceRecord> {
    await delay(PROVIDER_DELAY_MS)
    const record = MOCK_EVIDENCE.find(r => r.evidenceId === evidenceId)
    if (!record) throw new Error(`Evidence record ${evidenceId} not found.`)
    return record
  }

  async verify(evidenceId: string): Promise<VerifyResult> {
    await delay(PROVIDER_DELAY_MS + 350)
    const record = MOCK_EVIDENCE.find(r => r.evidenceId === evidenceId)
    const behavior = MOCK_VERIFY[evidenceId]
    if (!record || !behavior) throw new Error(`Verification service unavailable for ${evidenceId}.`)
    if (behavior.outcome === 'ERROR') {
      throw new Error('Verification service unavailable. The record is unchanged.')
    }
    const computed = behavior.computedHash ?? record.recordedHash
    const verifiedAt = new Date().toISOString()
    if (behavior.outcome === 'MATCH') {
      return {
        evidenceId,
        outcome: 'MATCH',
        recordedHash: record.recordedHash,
        computedHash: computed,
        verifiedAt,
        verifier: behavior.verifier,
        explanation: 'The computed SHA-256 digest matches the stored evidence digest.',
        historyEntry: {
          attemptId: `VRF-${Date.now().toString(36).toUpperCase()}`,
          at: verifiedAt,
          result: 'MATCH',
          actor: behavior.verifier,
          context: 'Officer-requested verification',
          recordedHash: record.recordedHash,
          computedHash: computed,
        },
      }
    }
    return {
      evidenceId,
      outcome: 'MISMATCH',
      recordedHash: record.recordedHash,
      computedHash: computed,
      verifiedAt,
      verifier: behavior.verifier,
      explanation:
        'The computed digest differs from the stored digest. Treat this record as requiring investigation.',
      historyEntry: {
        attemptId: `VRF-${Date.now().toString(36).toUpperCase()}`,
        at: verifiedAt,
        result: 'MISMATCH',
        actor: behavior.verifier,
        context: 'Officer-requested verification',
        recordedHash: record.recordedHash,
        computedHash: computed,
      },
    }
  }

  async requestExport(evidenceId: string): Promise<IExportReceipt> {
    await delay(PROVIDER_DELAY_MS)
    const record = MOCK_EVIDENCE.find(r => r.evidenceId === evidenceId)
    if (!record) throw new Error(`Evidence record ${evidenceId} not found.`)
    return {
      state: 'REQUESTED',
      reference: `EXP-${evidenceId}`,
      message: 'Export requested. The backend will prepare the file; this demo does not generate files.',
    }
  }

  async ledgerSummary(): Promise<LedgerSummary> {
    await delay(PROVIDER_DELAY_MS)
    return MOCK_LEDGER
  }

  async listAudit(limit = 50): Promise<AuditEntry[]> {
    await delay(PROVIDER_DELAY_MS)
    return MOCK_AUDIT.slice(0, limit)
  }
}

export const mockEvidenceService = new MockEvidenceService()
