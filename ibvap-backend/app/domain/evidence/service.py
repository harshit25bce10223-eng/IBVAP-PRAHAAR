# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — Evidence Service (Main Orchestrator)
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional, BinaryIO

from app.core.errors import IBVAPError, IBVAPErrorCode
from app.domain.evidence.hasher import evidence_hasher
from app.domain.evidence.canonicalizer import canonicalizer
from app.domain.evidence.storage import default_storage, EvidenceStorage, StorageMetadata
from app.domain.evidence.verification import EvidenceVerificationService
from app.domain.evidence.provenance import ProvenanceService
from app.domain.evidence.lifecycle import EvidenceLifecycleService
from app.domain.evidence.ledger import EvidenceLedgerService
from app.domain.evidence.anchor import AnchorProviderFactory
from app.domain.evidence.sync import CentralSyncProvider
from app.domain.evidence.audit import EvidenceAuditService
from app.models.evidence import (
    EvidenceRecord,
    EvidenceVerification,
    VERIFY_OUTCOME_MATCH,
    VERIFY_OUTCOME_MISMATCH,
    VERIFY_OUTCOME_ERROR,
    VERIFY_OUTCOME_UNAVAILABLE,
)
from app.repositories.evidence import (
    EvidenceRecordRepository,
    EvidenceVerificationRepository,
)
from app.schemas.evidence import (
    EvidenceRecord as EvidenceRecordSchema,
    EvidenceSummary,
    EvidencePage,
    EvidenceQuery,
    EvidenceDetailResponse,
    VerifyResult,
    VerificationHistoryEntry,
    LifecycleEvent,
    LedgerRecord,
    LedgerVerificationResult,
    ExportReceipt,
    AuditEntry,
    LedgerSummary,
    EvidenceIngestRequest,
    EvidenceIngestResponse,
)
from sqlalchemy.ext.asyncio import AsyncSession


class EvidenceNotFoundError(IBVAPError):
    def __init__(self, evidence_id: str) -> None:
        super().__init__(
            IBVAPErrorCode.INTERNAL_ERROR,
            f"Evidence '{evidence_id}' not found.",
            field="evidence_id",
            status_code=404,
        )


class EvidenceService:
    """
    Main evidence service orchestrating all evidence operations.

    Coordinates storage, hashing, verification, provenance, lifecycle,
    ledger, anchoring, and sync.
    """

    def __init__(self, session: AsyncSession, storage: Optional[Any] = None):
        self.session = session
        self.storage = storage or __import__("app.domain.evidence.storage", fromlist=["default_storage"]).default_storage
        self.record_repo = __import__("app.repositories.evidence", fromlist=["EvidenceRecordRepository"]).EvidenceRecordRepository(session)
        self.verification_repo = __import__("app.repositories.evidence", fromlist=["EvidenceVerificationRepository"]).EvidenceVerificationRepository(session)

        # Sub-services
        self.verification_service = __import__("app.domain.evidence.verification", fromlist=["EvidenceVerificationService"]).EvidenceVerificationService(session)
        self.provenance_service = __import__("app.domain.evidence.provenance", fromlist=["ProvenanceService"]).ProvenanceService(session)
        self.lifecycle_service = __import__("app.domain.evidence.lifecycle", fromlist=["EvidenceLifecycleService"]).EvidenceLifecycleService(session)
        self.ledger_service = __import__("app.domain.evidence.ledger", fromlist=["EvidenceLedgerService"]).EvidenceLedgerService(session)
        self.audit_service = __import__("app.domain.evidence.audit", fromlist=["EvidenceAuditService"]).EvidenceAuditService(session)

    # ── Creation / Ingestion ────────────────────────────────────────────────

    async def create_evidence(
        self,
        incident_id: str | None,
        event_id: str | None,
        camera_id: str,
        zone_id: str | None,
        type_: str,
        source: str,
        role: str,
        captured_at: datetime,
        stream: BinaryIO,
        mime_type: str | None = None,
        file_size_bytes: int | None = None,
        media_duration_ms: int | None = None,
        width: int | None = None,
        height: int | None = None,
        parent_evidence_id: str | None = None,
        region_profile: str | None = None,
        sector: str | None = None,
        algorithm_version: str | None = None,
    ) -> EvidenceRecord:
        """
        Create a new evidence record from a content stream.

        This is the main entry point for evidence creation.
        """
        # Generate evidence ID
        evidence_id = f"EVD-{uuid.uuid4().hex[:10].upper()}"

        # Store content
        try:
            storage_meta: Any = self.storage.put(evidence_id, stream, mime_type)
        except Exception as e:
            raise IBVAPError(
                IBVAPErrorCode.INTERNAL_ERROR,
                f"Failed to store evidence: {str(e)}",
                status_code=500,
            )

        # Compute hash
        stream.seek(0)
        content_hash = evidence_hasher.hash_stream(stream)

        # Create evidence record
        record = await self.record_repo.create(
            evidence_id=evidence_id,
            incident_id=incident_id,
            event_id=event_id,
            camera_id=camera_id,
            zone_id=zone_id,
            parent_evidence_id=parent_evidence_id,
            type=type_,
            source=source,
            role=role,
            captured_at=captured_at,
            mime_type=mime_type,
            file_size_bytes=file_size_bytes or storage_meta.file_size_bytes,
            media_duration_ms=media_duration_ms,
            width=width,
            height=height,
            storage_backend=storage_meta.storage_backend,
            storage_key=storage_meta.storage_key,
            content_hash_algorithm="SHA-256",
            content_hash=content_hash,
            region_profile=region_profile,
            sector=sector,
            algorithm_version=algorithm_version or "SHA-256",
        )

        # Log lifecycle
        await __import__("app.domain.evidence.lifecycle", fromlist=["evidence_lifecycle_service"]).evidence_lifecycle_service.log_event(
            evidence_id=evidence_id,
            event_type="CAPTURED",
            actor="ingestion_service",
            metadata={"storage_key": storage_meta.storage_key},
            session=self.session,
        )
        await __import__("app.domain.evidence.lifecycle", fromlist=["evidence_lifecycle_service"]).evidence_lifecycle_service.log_stored(
            evidence_id, "ingestion_service", session=self.session
        )

        # Hash lifecycle event (compute already done above)
        await __import__("app.domain.evidence.lifecycle", fromlist=["evidence_lifecycle_service"]).evidence_lifecycle_service.log_hashed(
            evidence_id, "hashing_service", session=self.session
        )
        
        # Update integrity status to HASHED after hashing
        record.integrity_status = "HASHED"
        record.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        
        # Append to ledger
        ledger_record_id = await __import__("app.domain.evidence.ledger", fromlist=["EvidenceLedgerService"]).EvidenceLedgerService(self.session).append(evidence_id)
        await __import__("app.domain.evidence.lifecycle", fromlist=["evidence_lifecycle_service"]).evidence_lifecycle_service.log_ledger_appended(
            evidence_id, "ledger_service", ledger_record_id, session=self.session
        )

        # Log audit
        await __import__("app.domain.evidence.audit", fromlist=["EvidenceAuditService"]).EvidenceAuditService(self.session).log(
            actor="ingestion_service",
            action="EVIDENCE_CREATED",
            target=evidence_id,
            result="SUCCESS",
            reason="Evidence created and stored",
        )

        return record

    async def create_incident_package(
        self,
        incident_id: str,
        camera_id: str,
        zone_id: str | None,
        snapshot_data: dict,
    ) -> str:
        """
        Create an INCIDENT_PACKAGE evidence record from incident snapshot.
        """
        import json
        # Create JSON snapshot
        snapshot_json = json.dumps(snapshot_data, separators=(",", ":"), sort_keys=True, default=str).encode("utf-8")

        # Create in-memory stream
        import io
        stream = io.BytesIO(snapshot_json)

        return await self.create_evidence(
            incident_id=incident_id,
            event_id=None,
            camera_id=camera_id,
            zone_id=None,
            type_="INCIDENT_PACKAGE",
            source="INCIDENT",
            role="ORIGINAL_CAPTURE",
            captured_at=datetime.now(timezone.utc),
            stream=io.BytesIO(snapshot_json),
            mime_type="application/json",
            file_size_bytes=len(snapshot_json),
        )

    # ── Retrieval ──────────────────────────────────────────────────────────

    async def get_evidence(self, evidence_id: str) -> EvidenceDetailResponse:
        """Get full evidence detail."""
        record = await self.record_repo.get(evidence_id)
        if not record:
            raise EvidenceNotFoundError(evidence_id)

        # Build provenance
        provenance = await __import__("app.domain.evidence.provenance", fromlist=["ProvenanceService"]).ProvenanceService(self.session).get_provenance(evidence_id)

        # Get lifecycle
        lifecycle = await __import__("app.domain.evidence.lifecycle", fromlist=["evidence_lifecycle_service"]).evidence_lifecycle_service.get_lifecycle(evidence_id)

        # Get verification history
        verification_history = await self.verification_repo.list_by_evidence(evidence_id)

        # Get ledger record
        ledger_record = await __import__("app.domain.evidence.ledger", fromlist=["EvidenceLedgerService"]).EvidenceLedgerService(self.session).get_evidence_ledger_record(evidence_id)

        anchor_data = None
        if ledger_record:
            anchor_data = {
                "state": ledger_record.anchor_status or "PENDING",
                "ledgerId": ledger_record.anchor_id,
                "anchoredAt": ledger_record.anchor_timestamp.isoformat() if ledger_record.anchor_timestamp else None,
                "rootValue": ledger_record.root_reference,
                "treeSize": ledger_record.tree_size,
                "recordSequence": ledger_record.sequence_number,
                "previousRecordRef": ledger_record.previous_record_hash,
                "anchorVersion": ledger_record.algorithm_version,
            }

        return EvidenceDetailResponse(
            evidenceId=record.evidence_id,
            incidentId=record.incident_id,
            eventId=record.event_id,
            cameraId=record.camera_id,
            zoneId=record.zone_id,
            regionProfile=record.region_profile,
            type=record.type,
            source=record.source,
            role=record.role,
            roleNote=None,
            capturedAt=record.captured_at.isoformat() if record.captured_at else None,
            ingestedAt=record.ingested_at.isoformat() if record.ingested_at else None,
            createdAt=record.created_at.isoformat() if record.created_at else None,
            mimeType=record.mime_type,
            fileSizeBytes=record.file_size_bytes,
            mediaDurationSec=record.media_duration_ms // 1000 if record.media_duration_ms else None,
            width=record.width,
            height=record.height,
            storageBackend=record.storage_backend,
            storageKey=record.storage_key,
            hashAlgorithm=record.content_hash_algorithm,
            recordedHash=record.content_hash,
            ledgerRecordHash=record.ledger_record_hash,
            sector=record.sector,
            schemaVersion=record.schema_version,
            canonicalizationVersion=record.canonicalization_version,
            algorithmVersion=record.algorithm_version,
            syncState=record.sync_state,
            status=record.status,
            integrity=record.integrity_status,
            anchor=anchor_data,
            createdByService=record.created_by_service,
            metadata=__import__("json").loads(record.metadata_json) if record.metadata_json else None,
            provenance=provenance,
            milestones=provenance.get("milestones", []),
            custody=provenance.get("custody", []),
            verificationHistory=[
                {
                    "attemptId": v.verification_id,
                    "at": v.verified_at.isoformat() if v.verified_at else None,
                    "result": v.outcome,
                    "actor": v.verifier_service or "system",
                    "context": v.reason,
                    "recordedHash": v.recorded_hash,
                    "computedHash": v.computed_hash,
                }
                for v in verification_history
            ],
        )

    async def list_evidence(self, query: EvidenceQuery) -> tuple[list[EvidenceSummary], int]:
        """List evidence with pagination and filters."""
        # Note: anchor is set to None on list items for performance (avoiding N+1 ledger joins)
        records, total = await self.record_repo.list_paginated(
            page=query.page,
            page_size=query.pageSize,
            camera_id=query.cameraId or None,
            incident_id=query.incidentId or None,
            event_id=query.eventId or None,
            search=query.search or None,
            type_=query.type or None,
            integrity=query.integrity or None,
            anchor=query.anchor or None,
            source=query.source or None,
            sort=query.sort,
            order=query.order,
        )

        summaries = [
            EvidenceSummary(
                evidenceId=r.evidence_id,
                incidentId=r.incident_id,
                capturedAt=r.captured_at.isoformat() if r.captured_at else None,
                cameraId=r.camera_id,
                zoneId=r.zone_id,
                type=r.type,
                source=r.source,
                role=r.role,
                hashAlgorithm=r.content_hash_algorithm,
                recordedHash=r.content_hash,
                integrity=r.integrity_status,
                anchor=None,
                status=r.status,
                fileSizeBytes=r.file_size_bytes,
                mediaKind="image" if r.mime_type and r.mime_type.startswith("image/") else "video" if r.mime_type and r.mime_type.startswith("video/") else "none",
                createdAt=r.created_at.isoformat() if r.created_at else None,
            )
            for r in records
        ]

        return summaries, total

    async def get_provenance(self, evidence_id: str):
        return await __import__("app.domain.evidence.provenance", fromlist=["ProvenanceService"]).ProvenanceService(self.session).get_provenance(evidence_id)

    async def get_lifecycle(self, evidence_id: str):
        return await __import__("app.domain.evidence.lifecycle", fromlist=["evidence_lifecycle_service"]).evidence_lifecycle_service.get_lifecycle(evidence_id)


    # ── Verification ────────────────────────────────────────────────────────

    async def verify(self, evidence_id: str, actor_id: str | None = None) -> VerifyResult:
        """Verify evidence integrity."""
        verification = await __import__("app.domain.evidence.verification", fromlist=["EvidenceVerificationService"]).EvidenceVerificationService(self.session).verify(evidence_id, actor_id)

        return VerifyResult(
            evidenceId=verification.evidence_id,
            outcome=verification.outcome,
            recordedHash=verification.recorded_hash,
            computedHash=verification.computed_hash,
            verifiedAt=verification.verified_at.isoformat(),
            verifier=verification.verifier_service,
            explanation="Content integrity verified" if verification.outcome == "MATCH" else "Hash mismatch detected",
        )

    async def get_verification_history(self, evidence_id: str):
        verifications = await self.verification_repo.list_by_evidence(evidence_id)
        return [
            VerificationHistoryEntry(
                verificationId=v.verification_id,
                evidenceId=v.evidence_id,
                algorithm=v.algorithm,
                recordedHash=v.recorded_hash,
                computedHash=v.computed_hash,
                outcome=v.outcome,
                verifiedAt=v.verified_at.isoformat(),
                verifierService=v.verifier_service,
                actorId=v.actor_id,
                reason=v.reason,
                context=__import__("json").loads(v.context_json) if v.context_json else None,
                createdAt=v.created_at.isoformat(),
            )
            for v in verifications
        ]

    # ── Ledger ─────────────────────────────────────────────────────────────

    async def get_ledger_record(self, evidence_id: str):
        return await __import__("app.domain.evidence.ledger", fromlist=["EvidenceLedgerService"]).EvidenceLedgerService(self.session).get_evidence_ledger_record(evidence_id)

    async def verify_ledger(self):
        return await __import__("app.domain.evidence.ledger", fromlist=["EvidenceLedgerService"]).EvidenceLedgerService(self.session).verify_ledger()

    async def get_ledger_summary(self):
        return await __import__("app.domain.evidence.ledger", fromlist=["EvidenceLedgerService"]).EvidenceLedgerService(self.session).get_ledger_summary()

    # ── Content Retrieval ──────────────────────────────────────────────────

    async def get_content(self, evidence_id: str) -> tuple[BinaryIO, str, str]:
        """Get evidence content stream."""
        record = await self.record_repo.get(evidence_id)
        if not record:
            raise EvidenceNotFoundError(evidence_id)

        if not record.storage_key:
            raise ValueError("Evidence has no storage key")

        stream = __import__("app.domain.evidence.storage", fromlist=["default_storage"]).default_storage.get(record.storage_key)
        return stream, record.mime_type or "application/octet-stream", record.content_hash

    # ── Export ──────────────────────────────────────────────────────────────

    async def request_export(self, evidence_id: str) -> dict[str, Any]:
        """Request an export of evidence."""
        record = await self.record_repo.get(evidence_id)
        if not record:
            raise EvidenceNotFoundError(evidence_id)

        # Log lifecycle
        await __import__("app.domain.evidence.lifecycle", fromlist=["evidence_lifecycle_service"]).evidence_lifecycle_service.log_export_requested(
            evidence_id, "system", session=self.session
        )

        return ExportReceipt(
            state="REQUESTED",
            reference=f"EXP-{uuid.uuid4().hex[:8].upper()}",
            message="Export request received, processing",
        )

    # ── Sync ────────────────────────────────────────────────────────────────

    async def queue_for_sync(self, evidence_id: str, priority: int = 0):
        sync_provider = __import__("app.domain.evidence.sync", fromlist=["CentralSyncProvider"]).CentralSyncProvider(self.session)
        return await sync_provider.queue_for_sync(evidence_id, priority)

    async def get_sync_status(self, evidence_id: str):
        sync_provider = __import__("app.domain.evidence.sync", fromlist=["CentralSyncProvider"]).CentralSyncProvider(self.session)
        return await sync_provider.get_sync_status(evidence_id)

    # ── Audit ──────────────────────────────────────────────────────────────

    async def list_audit(self, limit: int = 100) -> list[AuditEntry]:
        """List audit entries derived from persistent evidence lifecycle events."""
        import json
        from app.repositories.evidence.lifecycle_repository import EvidenceLifecycleRepository

        lifecycle_repo = EvidenceLifecycleRepository(self.session)
        events = await lifecycle_repo.list_all(limit=limit)

        audit_entries = []
        for event in events:
            reason = None
            if event.metadata_json:
                try:
                    meta = json.loads(event.metadata_json)
                    reason = meta.get("outcome") or meta.get("reason") or str(meta)
                except Exception:
                    reason = event.metadata_json

            audit_entries.append(
                AuditEntry(
                    auditId=event.id,
                    at=event.timestamp.isoformat() if event.timestamp else event.created_at.isoformat(),
                    actor=event.actor or "system",
                    action=event.event_type,
                    target=event.evidence_id,
                    result="RECORDED",
                    reason=reason,
                )
            )
        return audit_entries