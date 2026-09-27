# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — Evidence Verification Service
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from app.core.errors import IBVAPError, IBVAPErrorCode
from app.domain.evidence.hasher import evidence_hasher
from app.domain.evidence.storage import default_storage
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
from app.domain.evidence.lifecycle import evidence_lifecycle_service
from app.domain.evidence.audit import evidence_audit_service
from sqlalchemy.ext.asyncio import AsyncSession


class EvidenceVerificationError(IBVAPError):
    def __init__(self, message: str, evidence_id: str | None = None) -> None:
        super().__init__(
            IBVAPErrorCode.INTERNAL_ERROR,
            message,
            field="evidence_id",
            status_code=400,
        )
        self.evidence_id = evidence_id


class EvidenceVerificationService:
    """
    Service for verifying evidence integrity.

    Computes SHA-256 of stored content and compares with recorded hash.
    Persists verification history. Never modifies original hash on mismatch.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.record_repo = EvidenceRecordRepository(session)
        self.verification_repo = EvidenceVerificationRepository(session)

    async def verify(self, evidence_id: str, actor_id: str | None = None) -> EvidenceVerification:
        """
        Verify evidence integrity by recomputing content hash.

        Args:
            evidence_id: Evidence to verify
            actor_id: Optional actor performing verification

        Returns:
            Verification record with outcome

        Raises:
            EvidenceVerificationError: If evidence not found or storage unavailable
        """
        # Get evidence record
        record = await self.record_repo.get(evidence_id)
        if not record:
            raise EvidenceVerificationError(
                f"Evidence '{evidence_id}' not found",
                evidence_id=evidence_id,
            )

        # Check if content is available
        if not record.storage_key:
            verification = await self._create_verification_record(
                evidence_id=record.evidence_id,
                algorithm=record.content_hash_algorithm,
                recorded_hash=record.content_hash,
                computed_hash=None,
                outcome=VERIFY_OUTCOME_UNAVAILABLE,
                verifier_service="evidence_verification_service",
                actor_id=actor_id,
                reason="No storage key available",
            )
            await self.session.commit()
            return verification

        # Retrieve content from storage
        try:
            stream = default_storage.get(record.storage_key)
        except FileNotFoundError:
            verification = await self._create_verification_record(
                evidence_id=record.evidence_id,
                algorithm=record.content_hash_algorithm,
                recorded_hash=record.content_hash,
                computed_hash=None,
                outcome=VERIFY_OUTCOME_UNAVAILABLE,
                verifier_service="evidence_verification_service",
                actor_id=actor_id,
                reason="Storage file not found",
            )
            await self.session.commit()
            return verification
        except Exception as e:
            verification = await self._create_verification_record(
                evidence_id=record.evidence_id,
                algorithm=record.content_hash_algorithm,
                recorded_hash=record.content_hash,
                computed_hash=None,
                outcome=VERIFY_OUTCOME_ERROR,
                verifier_service="evidence_verification_service",
                actor_id=actor_id,
                reason=f"Storage error: {str(e)}",
            )
            await self.session.commit()
            return verification

        # Compute hash
        try:
            computed_hash = evidence_hasher.hash_stream(stream)
        except Exception as e:
            stream.close()
            verification = await self._create_verification_record(
                evidence_id=record.evidence_id,
                algorithm=record.content_hash_algorithm,
                recorded_hash=record.content_hash,
                computed_hash=None,
                outcome=VERIFY_OUTCOME_ERROR,
                verifier_service="evidence_verification_service",
                actor_id=actor_id,
                reason=f"Hash computation failed: {str(e)}",
            )
            await self.session.commit()
            return verification

        stream.close()

        # Compare hashes
        outcome = VERIFY_OUTCOME_MATCH if computed_hash == record.content_hash else VERIFY_OUTCOME_MISMATCH

        # Create verification record
        verification = await self._create_verification_record(
            evidence_id=record.evidence_id,
            algorithm=record.content_hash_algorithm,
            recorded_hash=record.content_hash,
            computed_hash=computed_hash,
            outcome=outcome,
            verifier_service="evidence_verification_service",
            actor_id=actor_id,
            reason="Content integrity check" if outcome == VERIFY_OUTCOME_MATCH else "Hash mismatch detected",
        )

        # Update evidence integrity status
        record.integrity_status = "VERIFIED" if outcome == VERIFY_OUTCOME_MATCH else "MISMATCH"
        record.updated_at = datetime.now(timezone.utc)

        # Log lifecycle event
        await evidence_lifecycle_service.log_event(
            evidence_id=record.evidence_id,
            event_type="VERIFIED",
            actor=actor_id or "system",
            metadata={
                "verification_id": verification.verification_id,
                "outcome": outcome,
            },
            session=self.session,
        )

        # Audit log
        await evidence_audit_service.log(
            actor=actor_id or "system",
            action="VERIFY",
            target=record.evidence_id,
            result=outcome,
            reason="Integrity verification",
            session=self.session,
        )

        await self.session.commit()
        return verification

    async def _create_verification_record(
        self,
        evidence_id: str,
        algorithm: str,
        recorded_hash: str,
        computed_hash: str | None,
        outcome: str,
        verifier_service: str,
        actor_id: str | None,
        reason: str | None,
    ) -> EvidenceVerification:
        """Create and persist a verification record."""
        verification_id = f"VER-{uuid.uuid4().hex[:10].upper()}"

        verification = EvidenceVerification(
            verification_id=verification_id,
            evidence_id=evidence_id,
            algorithm=algorithm,
            recorded_hash=recorded_hash,
            computed_hash=computed_hash,
            outcome=outcome,
            verified_at=datetime.now(timezone.utc),
            verifier_service=verifier_service,
            actor_id=actor_id,
            reason=reason,
        )

        self.session.add(verification)
        await self.session.flush()
        return verification

    async def get_verification_history(
        self, evidence_id: str, limit: int = 50
    ) -> list[Any]:
        """Get verification history for evidence."""
        from app.repositories.evidence import EvidenceVerificationRepository
        verification_repo = EvidenceVerificationRepository(self.session)
        return await verification_repo.list_by_evidence(evidence_id, limit=limit)