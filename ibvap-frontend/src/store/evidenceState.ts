// ─────────────────────────────────────────────────────────────────────────────
// evidenceState — normalized evidence cache (Component 3)
//
// One normalized record per evidence id; the table page and detail drawer
// read the same entries. List queries re-fetch on filter/sort/page change
// (API-ready params); verification is an explicit per-record action with
// single-flight, and results merge back into the cached record.
// Verification never runs on drawer open — only on officer action.
// ─────────────────────────────────────────────────────────────────────────────

import { create } from 'zustand'
import { evidenceService } from '@/services/evidence'
import type {
  AuditEntry,
  EvidencePage,
  EvidenceQuery,
  EvidenceRecord,
  ExportState,
  LedgerSummary,
  VerifyResult,
} from '@/types/evidence'

export type EvidenceListState = 'idle' | 'loading' | 'ready' | 'error'
export type VerifyState = 'idle' | 'verifying' | 'done' | 'error'

export const DEFAULT_EVIDENCE_QUERY: EvidenceQuery = {
  search: '',
  cameraId: 'ALL',
  type: 'ALL',
  integrity: 'ALL',
  anchor: 'ALL',
  source: 'ALL',
  sort: 'captured_at',
  order: 'desc',
  page: 1,
  pageSize: 8,
}

interface EvidenceStore {
  query: EvidenceQuery
  page: EvidencePage | null
  listState: EvidenceListState
  listError: string | null

  records: Record<string, EvidenceRecord>
  ledger: LedgerSummary | null
  ledgerState: EvidenceListState
  audit: AuditEntry[]
  auditState: EvidenceListState
  auditError: string | null

  verifyStates: Record<string, VerifyState>
  verifyResults: Record<string, VerifyResult>
  verifyErrors: Record<string, string>

  setQuery: (patch: Partial<EvidenceQuery>) => void
  fetchList: () => Promise<void>
  fetchRecord: (evidenceId: string) => Promise<void>
  verifyRecord: (evidenceId: string) => Promise<void>
  requestExport: (evidenceId: string) => Promise<string>
  fetchLedger: () => Promise<void>
  fetchAudit: () => Promise<void>
}

const listFlight = new Map<string, Promise<void>>()
const verifyFlight = new Map<string, Promise<void>>()

function queryKey(q: EvidenceQuery): string {
  return JSON.stringify(q)
}

export const useEvidenceStore = create<EvidenceStore>((set, get) => ({
  query: { ...DEFAULT_EVIDENCE_QUERY },
  page: null,
  listState: 'idle',
  listError: null,

  records: {},
  ledger: null,
  ledgerState: 'idle',
  audit: [],
  auditState: 'idle',
  auditError: null,

  verifyStates: {},
  verifyResults: {},
  verifyErrors: {},

  setQuery: patch =>
    set(s => ({
      query: { ...s.query, ...patch, page: patch.page ?? (patch.search !== undefined || patch.cameraId !== undefined || patch.type !== undefined || patch.integrity !== undefined || patch.anchor !== undefined || patch.source !== undefined ? 1 : s.query.page) },
    })),

  fetchList: () => {
    const key = queryKey(get().query)
    const existing = listFlight.get(key)
    if (existing) return existing
    set({ listState: 'loading', listError: null })
    const task = (async () => {
      try {
        const page = await evidenceService.list(get().query)
        const merged: Record<string, EvidenceRecord> = { ...get().records }
        for (const r of page.records) merged[r.evidenceId] = r
        set({ page, records: merged, listState: 'ready' })
      } catch (err) {
        set({
          listState: 'error',
          listError: err instanceof Error ? err.message : 'Evidence records could not be loaded.',
        })
      } finally {
        listFlight.delete(key)
      }
    })()
    listFlight.set(key, task)
    return task
  },

  fetchRecord: async evidenceId => {
    if (get().records[evidenceId]) return
    try {
      const record = await evidenceService.get(evidenceId)
      set(s => ({ records: { ...s.records, [evidenceId]: record } }))
    } catch {
      // Table already carries display fields; detail shows its own error.
    }
  },

  verifyRecord: evidenceId => {
    const existing = verifyFlight.get(evidenceId)
    if (existing) return existing
    set(s => ({
      verifyStates: { ...s.verifyStates, [evidenceId]: 'verifying' },
      verifyErrors: { ...s.verifyErrors, [evidenceId]: '' },
    }))
    const task = (async () => {
      try {
        const result = await evidenceService.verify(evidenceId)
        set(s => {
          const prev = s.records[evidenceId]
          const updated: EvidenceRecord | undefined = prev
            ? {
                ...prev,
                integrity: result.outcome === 'MATCH' ? 'VERIFIED' : 'MISMATCH',
                // A fresh MISMATCH escalates to review. A MATCH never clears
                // review standing on its own — only backend review does that.
                status: result.outcome === 'MATCH' ? prev.status : 'UNDER_REVIEW',
                lastVerifiedAt: result.verifiedAt,
                lastVerifiedBy: result.verifier,
                firstVerifiedAt: prev.firstVerifiedAt ?? result.verifiedAt,
                verificationHistory: result.historyEntry
                  ? [result.historyEntry, ...prev.verificationHistory]
                  : prev.verificationHistory,
              }
            : undefined
          const records = updated ? { ...s.records, [evidenceId]: updated } : s.records
          const page = s.page
            ? { ...s.page, records: s.page.records.map(r => (r.evidenceId === evidenceId && updated ? updated : r)) }
            : s.page
          return {
            records,
            page,
            verifyStates: { ...s.verifyStates, [evidenceId]: 'done' },
            verifyResults: { ...s.verifyResults, [evidenceId]: result },
          }
        })
      } catch (err) {
        set(s => ({
          verifyStates: { ...s.verifyStates, [evidenceId]: 'error' },
          verifyErrors: {
            ...s.verifyErrors,
            [evidenceId]: err instanceof Error ? err.message : 'Verification service unavailable.',
          },
        }))
      } finally {
        verifyFlight.delete(evidenceId)
      }
    })()
    verifyFlight.set(evidenceId, task)
    return task
  },

  requestExport: async evidenceId => {
    const receipt = await evidenceService.requestExport(evidenceId)
    set(s => {
      const prev = s.records[evidenceId]
      if (!prev) return s
      const updated: EvidenceRecord = {
        ...prev,
        exportState: receipt.state as ExportState,
        exportRequestedAt: new Date().toISOString(),
      }
      return {
        records: { ...s.records, [evidenceId]: updated },
        page: s.page
          ? { ...s.page, records: s.page.records.map(r => (r.evidenceId === evidenceId ? updated : r)) }
          : s.page,
      }
    })
    return receipt.message
  },

  fetchLedger: async () => {
    if (get().ledgerState === 'loading' || get().ledgerState === 'ready') return
    set({ ledgerState: 'loading' })
    try {
      const ledger = await evidenceService.ledgerSummary()
      set({ ledger, ledgerState: 'ready' })
    } catch {
      set({ ledgerState: 'error' })
    }
  },

  fetchAudit: async () => {
    if (get().auditState === 'loading' || get().auditState === 'ready') return
    set({ auditState: 'loading', auditError: null })
    try {
      const audit = await evidenceService.listAudit(50)
      set({ audit, auditState: 'ready' })
    } catch (err) {
      set({
        auditState: 'error',
        auditError: err instanceof Error ? err.message : 'Audit log could not be loaded.',
      })
    }
  },
}))
