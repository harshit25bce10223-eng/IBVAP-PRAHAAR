// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 3 — Evidence service boundary
//
// Phase 1 (current): the exported provider is a mock serving isolated
// development fixtures. No axios, no fake endpoint, no synthetic latency
// pretending to be a backend.
//
// Phase 2 (planned): implement this interface against the real backend and
// swap the singleton in `services/evidence/index.ts`. Pages, hooks, stores
// and components consume ONLY this interface — no UI redesign required.
//
// Planned contract (follows existing `/api/v1` conventions):
//   GET  /api/v1/evidence?...filters&sort=&page=      → EvidencePage
//   GET  /api/v1/evidence/{evidence_id}               → EvidenceRecord
//   POST /api/v1/evidence/{evidence_id}/verify        → VerifyResult
//   POST /api/v1/evidence/{evidence_id}/export        → { state, reference }
//   GET  /api/v1/evidence/ledger/summary              → LedgerSummary
//   GET  /api/v1/evidence/audit?...                   → AuditEntry[]
// ─────────────────────────────────────────────────────────────────────────────

import type {
  AuditEntry,
  EvidencePage,
  EvidenceQuery,
  EvidenceRecord,
  ExportState,
  LedgerSummary,
  VerifyResult,
} from '@/types/evidence'

export interface IExportReceipt {
  state: ExportState
  reference: string | null
  message: string
}

export interface IEvidenceService {
  /** Paginated, filtered evidence list (server-side in Phase 2). */
  list(query: EvidenceQuery): Promise<EvidencePage>
  /** Full record for the detail panel. */
  get(evidenceId: string): Promise<EvidenceRecord>
  /** Backend-performed integrity verification. Never computed locally. */
  verify(evidenceId: string): Promise<VerifyResult>
  /** Export request — tracks REQUESTED/READY/FAILED, never builds files. */
  requestExport(evidenceId: string): Promise<IExportReceipt>
  /** Ledger health summary for the page header. */
  ledgerSummary(): Promise<LedgerSummary>
  /** Audit trail entries (never contains secrets). */
  listAudit(limit?: number): Promise<AuditEntry[]>
  /** Data provenance of this provider: 'DEMO' (fixtures) or 'LIVE'. */
  readonly source: 'DEMO' | 'LIVE'
}
