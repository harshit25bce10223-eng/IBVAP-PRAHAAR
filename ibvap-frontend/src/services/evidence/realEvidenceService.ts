// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 3 — Real Evidence Service (Backend API Integration)
// ─────────────────────────────────────────────────────────────────────────────

import { api, qs, asApiError } from '@/services/api'
import type {
  AuditEntry,
  EvidencePage,
  EvidenceQuery,
  EvidenceRecord,
  LedgerSummary,
  VerifyResult,
} from '@/types/evidence'
import type { IEvidenceService, IExportReceipt } from './IEvidenceService'

export class RealEvidenceService implements IEvidenceService {
  readonly source = 'LIVE' as const

  async list(query: EvidenceQuery): Promise<EvidencePage> {
    try {
      const params = qs({
        search: query.search || undefined,
        cameraId: query.cameraId !== 'ALL' ? query.cameraId : undefined,
        type: query.type !== 'ALL' ? query.type : undefined,
        integrity: query.integrity !== 'ALL' ? query.integrity : undefined,
        anchor: query.anchor !== 'ALL' ? query.anchor : undefined,
        source: query.source !== 'ALL' ? query.source : undefined,
        sort: query.sort,
        order: query.order,
        page: query.page,
        pageSize: query.pageSize,
      })
      const response = await api.get<EvidencePage>(`/evidence/${params}`)
      return response.data
    } catch (err) {
      const apiErr = asApiError(err)
      throw new Error(`[RealEvidenceService] Failed to list evidence: ${apiErr.message}`)
    }
  }

  async get(evidenceId: string): Promise<EvidenceRecord> {
    try {
      const response = await api.get<EvidenceRecord>(`/evidence/${encodeURIComponent(evidenceId)}`)
      return response.data
    } catch (err) {
      const apiErr = asApiError(err)
      throw new Error(`[RealEvidenceService] Failed to load evidence ${evidenceId}: ${apiErr.message}`)
    }
  }

  async verify(evidenceId: string): Promise<VerifyResult> {
    try {
      const response = await api.post<VerifyResult>(`/evidence/${encodeURIComponent(evidenceId)}/verify`)
      return response.data
    } catch (err) {
      const apiErr = asApiError(err)
      throw new Error(`[RealEvidenceService] Verification failed for ${evidenceId}: ${apiErr.message}`)
    }
  }

  async requestExport(evidenceId: string): Promise<IExportReceipt> {
    try {
      const response = await api.post<IExportReceipt>(`/evidence/${encodeURIComponent(evidenceId)}/export`)
      return response.data
    } catch (err) {
      const apiErr = asApiError(err)
      throw new Error(`[RealEvidenceService] Export request failed for ${evidenceId}: ${apiErr.message}`)
    }
  }

  async ledgerSummary(): Promise<LedgerSummary> {
    try {
      const response = await api.get<LedgerSummary>('/evidence/ledger/summary')
      return response.data
    } catch (err) {
      const apiErr = asApiError(err)
      throw new Error(`[RealEvidenceService] Failed to load ledger summary: ${apiErr.message}`)
    }
  }

  async listAudit(limit = 100): Promise<AuditEntry[]> {
    try {
      const params = qs({ limit })
      const response = await api.get<AuditEntry[]>(`/evidence/audit${params}`)
      return response.data
    } catch (err) {
      const apiErr = asApiError(err)
      throw new Error(`[RealEvidenceService] Failed to load audit trail: ${apiErr.message}`)
    }
  }
}

export const realEvidenceService = new RealEvidenceService()
