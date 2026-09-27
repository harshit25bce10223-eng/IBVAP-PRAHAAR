// ─────────────────────────────────────────────────────────────────────────────
// PRHAAR Component 3 — Evidence + tamper-evident ledger domain types
// (canonical, render-only)
//
// The backend (Phase 2) is authoritative for every semantic field below:
// integrity verdicts, anchor states, ledger status, verification history.
// The frontend renders authoritative fields verbatim and MUST NOT compute
// hashes, decide match/mismatch, or claim legal admissibility.
// ─────────────────────────────────────────────────────────────────────────────

/** Backend evidence-kind enum. Rendered as-is; never hard-code one kind. */
export type EvidenceType =
  | 'SNAPSHOT'
  | 'VIDEO_CLIP'
  | 'FRAME'
  | 'METADATA'
  | 'EVENT_RECORD'
  | 'INCIDENT_PACKAGE'

/** Claimed origin of the record. UNKNOWN beats fabricated attribution. */
export type EvidenceSource =
  | 'CAMERA'
  | 'EDGE'
  | 'ANALYTICS'
  | 'INCIDENT'
  | 'SYSTEM'
  | 'UNKNOWN'

/** What the bytes are relative to the original capture. */
export type EvidenceRole =
  | 'ORIGINAL'
  | 'ORIGINAL_CAPTURE'
  | 'DERIVED'
  | 'ANNOTATED_COPY'
  | 'ANNOTATED'
  | 'EXPORT'
  | 'THUMBNAIL'

export type IntegrityState =
  | 'VERIFIED'
  | 'UNVERIFIED'
  | 'HASHED'
  | 'MISMATCH'
  | 'PENDING'
  | 'UNAVAILABLE'
  | 'UNKNOWN'

export type AnchorState =
  | 'ANCHORED'
  | 'PENDING'
  | 'FAILED'
  | 'UNAVAILABLE'
  | 'UNKNOWN'

/** Overall record standing. Distinct from per-check integrity. */
export type RecordStatus =
  | 'VALID'
  | 'UNDER_REVIEW'
  | 'QUARANTINED'
  | 'UNKNOWN'

export type LedgerStatus =
  | 'HEALTHY'
  | 'DEGRADED'
  | 'UNAVAILABLE'
  | 'VERIFYING'
  | 'UNKNOWN'

export type VerifyOutcome = 'MATCH' | 'MISMATCH' | 'ERROR'

export type ExportState =
  | 'NONE'
  | 'REQUESTED'
  | 'READY'
  | 'FAILED'

/** Where the bytes physically originated. Distinct from EvidenceSource
 *  (analytical origin). Backend-provided; never assumed. */
export type EvidenceDataSource = 'EDGE' | 'CENTRAL' | 'UNKNOWN'

/** Edge-to-central replication state for offline-capable capture. */
export type EvidenceSyncState =
  | 'LOCAL_ONLY'
  | 'SYNC_PENDING'
  | 'SYNCED'
  | 'SYNC_FAILED'
  | 'UNKNOWN'

export interface EvidenceProvenance {
  /** Ordered lineage, e.g. ['CAM-07','FRAME','EVENT','INCIDENT','EVIDENCE']. */
  chain: string[]
}

export interface EvidenceMilestone {
  key: string
  label: string
  /** ISO-8601. Null renders as NOT AVAILABLE — never invented. */
  at: string | null
}

export interface CustodyStep {
  stage: string
  detail: string | null
  at: string | null
}

export interface VerificationAttempt {
  attemptId: string
  at: string
  result: VerifyOutcome
  actor: string
  context: string | null
  /** Present only when the backend returns digests for display. */
  recordedHash: string | null
  computedHash: string | null
}

export interface LedgerAnchor {
  state: AnchorState
  ledgerId: string | null
  anchoredAt: string | null
  /** Hex root/anchor value when the backend supplies one. */
  rootValue: string | null
  /** Forward-compatible Merkle/append-only fields (Phase 2). */
  treeSize: number | null
  recordSequence: number | null
  previousRecordRef: string | null
  anchorVersion: string | null
}

/**
 * Canonical evidence record. Field-for-field compatible with the planned
 * Phase-2 responses (see IEvidenceService): list item + detail share one
 * shape so the table never needs a second fetch for display fields.
 */
export interface EvidenceRecord {
  evidenceId: string
  incidentId: string
  capturedAt: string
  cameraId: string
  zoneId: string | null
  regionProfile: string | null
  type: EvidenceType
  source: EvidenceSource
  /** Physical origin of the bytes (edge capture vs central ingest). */
  dataSource: EvidenceDataSource
  syncState: EvidenceSyncState
  /** ISO-8601 of the last sync transition. Null when never synced. */
  syncUpdatedAt: string | null
  role: EvidenceRole
  roleNote: string | null
  hashAlgorithm: string
  /** Canonical full digest (hex). Display truncates; copy uses this. */
  recordedHash: string
  integrity: IntegrityState
  anchor: LedgerAnchor
  status: RecordStatus
  fileSizeBytes: number | null
  mediaDurationSec: number | null
  codec: string | null
  /** 'image' | 'video' | 'none'. No preview URLs in Phase 1. */
  mediaKind: 'image' | 'video' | 'none'
  provenance: EvidenceProvenance
  milestones: EvidenceMilestone[]
  custody: CustodyStep[]
  verificationHistory: VerificationAttempt[]
  firstVerifiedAt: string | null
  lastVerifiedAt: string | null
  lastVerifiedBy: string | null
  exportState: ExportState
  exportHash: string | null
  exportRequestedAt: string | null
  createdAt: string
}

export interface AuditEntry {
  auditId: string
  at: string
  actor: string
  action: string
  target: string
  result: string
  reason: string | null
}

export interface LedgerSummary {
  recordCount: number
  status: LedgerStatus
  lastVerifiedAt: string | null
  lastVerifiedBy: string | null
  source: 'DEMO' | 'LIVE' | 'UNAVAILABLE'
}

/** API-ready list parameters (server pagination/sort/filter in Phase 2). */
export interface EvidenceQuery {
  search: string
  cameraId: string
  type: string
  integrity: string
  anchor: string
  source: string
  sort: 'captured_at' | 'camera' | 'integrity'
  order: 'asc' | 'desc'
  page: number
  pageSize: number
}

export interface EvidencePage {
  records: EvidenceRecord[]
  total: number
}

export interface VerifyResult {
  evidenceId: string
  outcome: VerifyOutcome
  recordedHash: string | null
  computedHash: string | null
  verifiedAt: string
  verifier: string
  explanation: string
  /** History entry the backend persisted for this attempt (if any). */
  historyEntry: VerificationAttempt | null
}

export const EVIDENCE_TYPES: EvidenceType[] = [
  'SNAPSHOT',
  'VIDEO_CLIP',
  'FRAME',
  'METADATA',
  'EVENT_RECORD',
  'INCIDENT_PACKAGE',
]

export const INTEGRITY_STATES: IntegrityState[] = [
  'VERIFIED',
  'UNVERIFIED',
  'HASHED',
  'MISMATCH',
  'PENDING',
  'UNAVAILABLE',
  'UNKNOWN',
]

export const ANCHOR_STATES: AnchorState[] = [
  'ANCHORED',
  'PENDING',
  'FAILED',
  'UNAVAILABLE',
  'UNKNOWN',
]
