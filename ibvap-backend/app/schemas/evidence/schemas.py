# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — Evidence Schemas (Pydantic v2)
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# ── Enums ─────────────────────────────────────────────────────────────────────

EvidenceType = Literal[
    "SNAPSHOT",
    "VIDEO_CLIP",
    "FRAME",
    "METADATA",
    "EVENT_RECORD",
    "INCIDENT_PACKAGE",
]

EvidenceSource = Literal[
    "CAMERA",
    "EDGE",
    "ANALYTICS",
    "INCIDENT",
    "SYSTEM",
    "UNKNOWN",
]

EvidenceRole = Literal[
    "ORIGINAL_CAPTURE",
    "DERIVED",
    "ANNOTATED",
    "EXPORT",
    "THUMBNAIL",
]

IntegrityState = Literal[
    "VERIFIED",
    "UNVERIFIED",
    "HASHED",
    "MISMATCH",
    "PENDING",
    "UNAVAILABLE",
    "UNKNOWN",
]

AnchorState = Literal[
    "ANCHORED",
    "PENDING",
    "FAILED",
    "UNAVAILABLE",
    "UNKNOWN",
]

RecordStatus = Literal[
    "VALID",
    "UNDER_REVIEW",
    "QUARANTINED",
    "UNKNOWN",
]

EvidenceSyncState = Literal[
    "LOCAL_ONLY",
    "SYNC_PENDING",
    "SYNCED",
    "SYNC_FAILED",
    "UNKNOWN",
]

VerifyOutcome = Literal["MATCH", "MISMATCH", "ERROR", "UNAVAILABLE"]
ExportState = Literal["NONE", "REQUESTED", "READY", "FAILED"]


# ── Nested Models ─────────────────────────────────────────────────────────────

class EvidenceProvenance(BaseModel):
    model_config = ConfigDict(extra="allow")
    chain: list[str] = []


class EvidenceMilestone(BaseModel):
    model_config = ConfigDict(extra="allow")
    key: str
    label: str
    at: str | None = None


class CustodyStep(BaseModel):
    model_config = ConfigDict(extra="allow")
    stage: str
    detail: str | None = None
    at: str | None = None


class VerificationAttempt(BaseModel):
    model_config = ConfigDict(extra="allow")
    attemptId: str
    at: str
    result: Literal["MATCH", "MISMATCH", "ERROR"]
    actor: str
    context: str | None = None
    recordedHash: str | None = None
    computedHash: str | None = None


class LedgerAnchor(BaseModel):
    model_config = ConfigDict(extra="allow")
    state: Literal["ANCHORED", "PENDING", "FAILED", "UNAVAILABLE", "UNKNOWN"]
    ledgerId: str | None = None
    anchoredAt: str | None = None
    rootValue: str | None = None
    treeSize: int | None = None
    recordSequence: int | None = None
    previousRecordRef: str | None = None
    anchorVersion: str | None = None


class AuditEntry(BaseModel):
    model_config = ConfigDict(extra="allow")
    auditId: str
    at: str
    actor: str
    action: str
    target: str
    result: str
    reason: str | None = None


class LedgerSummary(BaseModel):
    model_config = ConfigDict(extra="allow")
    recordCount: int
    status: Literal["HEALTHY", "DEGRADED", "UNAVAILABLE", "VERIFYING", "UNKNOWN"]
    lastVerifiedAt: str | None = None
    lastVerifiedBy: str | None = None
    source: Literal["DEMO", "LIVE", "UNAVAILABLE"]


# ── Main Evidence Record ──────────────────────────────────────────────────────

class EvidenceRecord(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True)

    evidenceId: str
    incidentId: str | None = None
    capturedAt: str
    cameraId: str
    zoneId: str | None = None
    regionProfile: str | None = None
    type: Literal[
        "SNAPSHOT", "VIDEO_CLIP", "FRAME", "METADATA", "EVENT_RECORD", "INCIDENT_PACKAGE"
    ]
    source: Literal["CAMERA", "EDGE", "ANALYTICS", "INCIDENT", "SYSTEM", "UNKNOWN"]
    dataSource: Literal["EDGE", "CENTRAL", "UNKNOWN"]
    syncState: Literal[
        "LOCAL_ONLY", "SYNC_PENDING", "SYNCED", "SYNC_FAILED", "UNKNOWN"
    ]
    role: Literal["ORIGINAL_CAPTURE", "DERIVED", "ANNOTATED", "EXPORT", "THUMBNAIL"]
    roleNote: str | None = None
    hashAlgorithm: str
    recordedHash: str
    integrity: Literal[
        "VERIFIED", "UNVERIFIED", "HASHED", "MISMATCH", "PENDING", "UNAVAILABLE", "UNKNOWN"
    ]
    anchor: dict | None = None
    status: Literal["VALID", "UNDER_REVIEW", "QUARANTINED", "UNKNOWN"]
    fileSizeBytes: int | None = None
    mediaDurationSec: int | None = None
    codec: str | None = None
    mediaKind: Literal["image", "video", "none"]
    provenance: dict | None = None
    milestones: list[dict] = []
    custody: list[dict] = []
    verificationHistory: list[dict] = []
    firstVerifiedAt: str | None = None
    lastVerifiedAt: str | None = None
    lastVerifiedBy: str | None = None
    exportState: Literal["NONE", "REQUESTED", "READY", "FAILED"]
    exportHash: str | None = None
    exportRequestedAt: str | None = None
    createdAt: str


# ── List/Summary ──────────────────────────────────────────────────────────────

class EvidenceSummary(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True)

    evidenceId: str
    incidentId: str | None = None
    capturedAt: str
    cameraId: str
    zoneId: str | None = None
    type: Literal[
        "SNAPSHOT", "VIDEO_CLIP", "FRAME", "METADATA", "EVENT_RECORD", "INCIDENT_PACKAGE"
    ]
    source: Literal["CAMERA", "EDGE", "ANALYTICS", "INCIDENT", "SYSTEM", "UNKNOWN"]
    role: Literal["ORIGINAL_CAPTURE", "DERIVED", "ANNOTATED", "EXPORT", "THUMBNAIL"]
    hashAlgorithm: str
    recordedHash: str
    integrity: Literal[
        "VERIFIED", "UNVERIFIED", "HASHED", "MISMATCH", "PENDING", "UNAVAILABLE", "UNKNOWN"
    ]
    anchor: dict | None = None
    status: Literal["VALID", "UNDER_REVIEW", "QUARANTINED", "UNKNOWN"]
    fileSizeBytes: int | None = None
    mediaKind: Literal["image", "video", "none"]
    createdAt: str


# ── Query/List ────────────────────────────────────────────────────────────────

class EvidenceQuery(BaseModel):
    model_config = ConfigDict(extra="forbid")
    search: str = ""
    cameraId: str = ""
    incidentId: str = ""
    eventId: str = ""
    type: str = ""
    integrity: str = ""
    anchor: str = ""
    source: str = ""
    sort: Literal["captured_at", "camera", "integrity"] = "captured_at"
    order: Literal["asc", "desc"] = "desc"
    page: int = Field(default=1, ge=1)
    pageSize: int = Field(default=20, ge=1, le=100)


class EvidencePage(BaseModel):
    model_config = ConfigDict(extra="allow")
    records: list[EvidenceSummary]
    total: int


# ── Detail/Response ──────────────────────────────────────────────────────────

class EvidenceDetailResponse(BaseModel):
    model_config = ConfigDict(extra="allow")

    evidenceId: str
    incidentId: str | None = None
    eventId: str | None = None
    cameraId: str
    zoneId: str | None = None
    regionProfile: str | None = None
    type: Literal[
        "SNAPSHOT", "VIDEO_CLIP", "FRAME", "METADATA", "EVENT_RECORD", "INCIDENT_PACKAGE"
    ]
    source: Literal["CAMERA", "EDGE", "ANALYTICS", "INCIDENT", "SYSTEM", "UNKNOWN"]
    role: Literal["ORIGINAL_CAPTURE", "DERIVED", "ANNOTATED", "EXPORT", "THUMBNAIL"]
    roleNote: str | None = None
    capturedAt: str
    ingestedAt: str
    createdAt: str
    mimeType: str | None = None
    fileSizeBytes: int | None = None
    mediaDurationSec: int | None = None
    width: int | None = None
    height: int | None = None
    storageBackend: str
    storageKey: str
    hashAlgorithm: str
    recordedHash: str
    ledgerRecordHash: str | None = None
    sector: str | None = None
    schemaVersion: int
    canonicalizationVersion: str
    algorithmVersion: str
    syncState: Literal[
        "LOCAL_ONLY", "SYNC_PENDING", "SYNCED", "SYNC_FAILED", "UNKNOWN"
    ]
    status: str
    integrity: Literal[
        "VERIFIED", "UNVERIFIED", "HASHED", "MISMATCH", "PENDING", "UNAVAILABLE", "UNKNOWN"
    ]
    anchor: dict | None = None
    createdByService: str | None = None
    metadata: dict | None = None
    provenance: dict | None = None
    milestones: list[dict] = []
    custody: list[dict] = []
    verificationHistory: list[dict] = []


# ── Verification ─────────────────────────────────────────────────────────────

class VerifyResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    evidenceId: str
    outcome: Literal["MATCH", "MISMATCH", "ERROR", "UNAVAILABLE"]
    recordedHash: str | None = None
    computedHash: str | None = None
    verifiedAt: str
    verifier: str
    explanation: str
    historyEntry: dict | None = None


class VerificationHistoryEntry(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True)
    verificationId: str
    evidenceId: str
    algorithm: str
    recordedHash: str
    computedHash: str | None = None
    outcome: Literal["MATCH", "MISMATCH", "ERROR", "UNAVAILABLE"]
    verifiedAt: str
    verifierService: str
    actorId: str | None = None
    reason: str | None = None
    context: dict | None = None
    createdAt: str


# ── Lifecycle ────────────────────────────────────────────────────────────────

class LifecycleEvent(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True)
    id: str
    evidenceId: str
    eventType: str
    timestamp: str
    actor: str
    metadata: dict | None = None
    createdAt: str


# ── Ledger ───────────────────────────────────────────────────────────────────

class LedgerRecord(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True)
    ledgerRecordId: str
    evidenceId: str
    sequenceNumber: int
    previousRecordHash: str | None = None
    contentHash: str
    recordHash: str
    canonicalPayload: dict
    createdAt: str
    anchorStatus: str
    anchorId: str | None = None
    anchorTimestamp: str | None = None
    rootReference: str | None = None
    treeSize: int | None = None
    algorithmVersion: str
    status: str


class LedgerVerificationResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    status: Literal["VALID", "BROKEN"]
    firstBrokenLocation: dict | None = None
    checkedRecords: int


# ── Export ───────────────────────────────────────────────────────────────────

class ExportReceipt(BaseModel):
    model_config = ConfigDict(extra="allow")
    state: Literal["NONE", "REQUESTED", "READY", "FAILED"]
    reference: str | None = None
    message: str


# ── Audit ────────────────────────────────────────────────────────────────────

class AuditEntry(BaseModel):
    model_config = ConfigDict(extra="allow", from_attributes=True)
    auditId: str
    at: str
    actor: str
    action: str
    target: str
    result: str
    reason: str | None = None



# ── Ingestion ────────────────────────────────────────────────────────────────

class EvidenceIngestRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    incidentId: str | None = None
    eventId: str | None = None
    cameraId: str | None = None
    zoneId: str | None = None
    type: Literal[
        "SNAPSHOT", "VIDEO_CLIP", "FRAME", "METADATA", "EVENT_RECORD", "INCIDENT_PACKAGE"
    ]
    source: Literal["CAMERA", "EDGE", "ANALYTICS", "INCIDENT", "SYSTEM", "UNKNOWN"]
    role: Literal["ORIGINAL_CAPTURE", "DERIVED", "ANNOTATED", "EXPORT", "THUMBNAIL"]
    capturedAt: str
    mimeType: str | None = None
    fileSizeBytes: int | None = None
    mediaDurationMs: int | None = None
    width: int | None = None
    height: int | None = None
    parentEvidenceId: str | None = None
    regionProfile: str | None = None
    sector: str | None = None
    algorithmVersion: str | None = None


class EvidenceIngestResponse(BaseModel):
    model_config = ConfigDict(extra="allow")
    evidenceId: str
    status: str
    hash: str