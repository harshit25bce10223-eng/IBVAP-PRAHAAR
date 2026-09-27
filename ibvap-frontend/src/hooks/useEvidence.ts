// ─────────────────────────────────────────────────────────────────────────────
// useEvidence — Service → Store → Component boundary (Component 3)
//
// Pages consume the ledger exclusively through this hook: query state,
// list lifecycle, ledger summary and audit trail. No axios in JSX, one
// request per query key, no fetch on every render.
// ─────────────────────────────────────────────────────────────────────────────

import { useCallback, useEffect } from 'react'
import { useEvidenceStore } from '@/store/evidenceState'

export function useEvidenceLedger() {
  const query = useEvidenceStore(s => s.query)
  const page = useEvidenceStore(s => s.page)
  const listState = useEvidenceStore(s => s.listState)
  const listError = useEvidenceStore(s => s.listError)
  const ledger = useEvidenceStore(s => s.ledger)
  const ledgerState = useEvidenceStore(s => s.ledgerState)
  const audit = useEvidenceStore(s => s.audit)
  const auditState = useEvidenceStore(s => s.auditState)
  const auditError = useEvidenceStore(s => s.auditError)
  const setQuery = useEvidenceStore(s => s.setQuery)
  const fetchList = useEvidenceStore(s => s.fetchList)
  const fetchLedger = useEvidenceStore(s => s.fetchLedger)
  const fetchAudit = useEvidenceStore(s => s.fetchAudit)

  useEffect(() => {
    let cancelled = false
    fetchList().catch(() => {
      if (!cancelled) return
    })
    return () => {
      cancelled = true
    }
  }, [fetchList, query])

  useEffect(() => {
    fetchLedger().catch(() => {})
    fetchAudit().catch(() => {})
  }, [fetchLedger, fetchAudit])

  const retryList = useCallback(() => fetchList(), [fetchList])
  const retryAudit = useCallback(() => fetchAudit(), [fetchAudit])

  return {
    query,
    page,
    listState,
    listError,
    ledger,
    ledgerState,
    audit,
    auditState,
    auditError,
    setQuery,
    retryList,
    retryAudit,
  }
}
