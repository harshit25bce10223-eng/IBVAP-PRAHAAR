# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — Evidence Ledger Service (Append-Only)
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from app.domain.evidence.canonicalizer import canonicalizer
from app.domain.evidence.hasher import evidence_hasher
from app.models.evidence import EvidenceLedgerRecord, EvidenceRecord
from app.repositories.evidence import EvidenceLedgerRepository, EvidenceRecordRepository
from app.domain.evidence.lifecycle import evidence_lifecycle_service
from sqlalchemy.ext.asyncio import AsyncSession


class LedgerError(Exception):
    """Ledger-specific error."""
    pass


class EvidenceLedgerService:
    """
    Append-only ledger service for evidence records.

    Each evidence record gets a ledger entry with:
    - Monotonically increasing sequence number
    - Previous record hash (chaining)
    - Content hash of evidence
    - Canonicalized record payload
    - Record hash (hash of canonical payload)

    The ledger is append-only - records cannot be modified or deleted.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.ledger_repo = EvidenceLedgerRepository(session)
        self.record_repo = EvidenceRecordRepository(session)

    async def append(self, evidence_id: str, actor: str = "system") -> str:
        """
        Append a new ledger record for evidence.

        Args:
            evidence_id: Evidence to ledger
            actor: Actor performing the operation

        Returns:
            Ledger record ID

        Raises:
            ValueError: If evidence not found
        """
        record = await self.record_repo.get(evidence_id)
        if not record:
            raise ValueError(f"Evidence '{evidence_id}' not found")

        # Get the last ledger record for chaining
        last_record = await self.ledger_repo.get_last()
        sequence_number = (last_record.sequence_number + 1) if last_record else 1
        previous_record_hash = last_record.record_hash if last_record else None

        # Build canonical payload
        payload = {
            "evidence_id": record.evidence_id,
            "content_hash": record.content_hash,
            "type": record.type,
            "source": record.source,
            "role": record.role,
            "captured_at": record.captured_at.isoformat() if record.captured_at else None,
            "created_at": record.created_at.isoformat() if record.created_at else None,
            "sequence_number": sequence_number,
            "previous_record_hash": previous_record_hash,
            "algorithm_version": record.algorithm_version,
        }

        # Canonicalize and hash
        canonical_payload = canonicalizer.canonicalize_for_ledger(payload)
        record_hash = evidence_hasher.hash_bytes(canonical_payload.encode("utf-8"))

        # Create ledger record
        ledger_record_id = f"LGR-{uuid.uuid4().hex[:10].upper()}"

        ledger_record = EvidenceLedgerRecord(
            ledger_record_id=ledger_record_id,
            evidence_id=evidence_id,
            sequence_number=sequence_number,
            previous_record_hash=previous_record_hash,
            content_hash=record.content_hash,
            record_hash=record_hash,
            canonical_payload_json=canonical_payload,
            algorithm_version=record.algorithm_version,
            status="ACTIVE",
            anchor_status="UNAVAILABLE",
        )

        # Atomically append (handles race conditions via unique constraint)
        from sqlalchemy.exc import IntegrityError
        max_retries = 3
        for attempt in range(max_retries):
            try:
                self.session.add(ledger_record)
                await self.session.flush()
                break
            except Exception as e:
                await self.session.rollback()
                # Retry with updated sequence number
                last_record = await self.ledger_repo.get_last()
                sequence_number = (last_record.sequence_number + 1) if last_record else 1
                previous_record_hash = last_record.record_hash if last_record else None

                payload["sequence_number"] = sequence_number
                payload["previous_record_hash"] = previous_record_hash
                canonical_payload = canonicalizer.canonicalize_for_ledger(payload)
                record_hash = evidence_hasher.hash_bytes(canonical_payload.encode("utf-8"))

                ledger_record = EvidenceLedgerRecord(
                    ledger_record_id=f"LGR-{uuid.uuid4().hex[:10].upper()}",
                    evidence_id=evidence_id,
                    sequence_number=sequence_number,
                    previous_record_hash=previous_record_hash,
                    content_hash=record.content_hash,
                    record_hash=record_hash,
                    canonical_payload_json=canonicalizer.canonicalize_for_ledger(payload),
                    algorithm_version=record.algorithm_version,
                    status="ACTIVE",
                    anchor_status="UNAVAILABLE",
                )
        else:
            raise LedgerError("Failed to append ledger record after retries")

        # Update evidence record with ledger hash
        from app.repositories.evidence import EvidenceRecordRepository
        record_repo = EvidenceRecordRepository(self.session)
        await record_repo.update(evidence_id, ledger_record_hash=record_hash)

        # Log lifecycle
        from app.domain.evidence.lifecycle import evidence_lifecycle_service
        await evidence_lifecycle_service.log_ledger_appended(
            evidence_id, "system", ledger_record_id, session=self.session
        )

        return ledger_record_id

    async def verify_ledger(self) -> dict[str, Any]:
        """
        Verify the entire ledger chain integrity.

        Returns:
            Dict with status and details
        """
        records = await self.ledger_repo.get_all_ordered()

        if not records:
            return {"status": "VALID", "checked_records": 0}

        previous_hash = None
        for i, record in enumerate(records):
            # Check sequence continuity
            if record.sequence_number != i + 1:
                return {
                    "status": "BROKEN",
                    "first_broken_location": {
                        "sequence_number": record.sequence_number,
                        "expected": i + 1,
                        "reason": "Sequence gap",
                    },
                    "checked_records": i,
                }

            # Check previous hash linkage
            if i > 0 and record.previous_record_hash != previous_hash:
                return {
                    "status": "BROKEN",
                    "first_broken_location": {
                        "sequence_number": record.sequence_number,
                        "reason": "Previous hash mismatch",
                    },
                    "checked_records": i,
                }

            # Verify record hash
            payload = json.loads(record.canonical_payload_json)
            payload["sequence_number"] = record.sequence_number
            payload["previous_record_hash"] = record.previous_record_hash
            canonical_payload = canonicalizer.canonicalize_for_ledger(payload)
            computed_hash = evidence_hasher.hash_bytes(canonical_payload.encode("utf-8"))

            if record.record_hash != computed_hash:
                return {
                    "status": "BROKEN",
                    "first_broken_location": {
                        "sequence_number": record.sequence_number,
                        "reason": "Record hash mismatch",
                    },
                    "checked_records": i,
                }

            # Verify content hash relationship
            if record.content_hash != payload["content_hash"]:
                return {
                    "status": "BROKEN",
                    "first_broken_location": {
                        "sequence_number": record.sequence_number,
                        "reason": "Content hash mismatch in payload",
                    },
                    "checked_records": i,
                }

            previous_hash = record.record_hash

        return {"status": "VALID", "checked_records": len(records)}

    async def get_ledger_summary(self) -> dict[str, Any]:
        """Get ledger health summary."""
        total = await self.ledger_repo.count()
        last_record = await self.ledger_repo.get_last()

        # Quick verification of last N records
        verification = await self.verify_ledger()

        return {
            "recordCount": total,
            "status": "HEALTHY" if verification["status"] == "VALID" else "DEGRADED",
            "lastVerifiedAt": datetime.now(timezone.utc).isoformat(),
            "lastVerifiedBy": "system",
            "source": "LIVE",
            "lastRecord": {
                "sequenceNumber": last_record.sequence_number if last_record else 0,
                "recordHash": last_record.record_hash if last_record else None,
                "createdAt": last_record.created_at.isoformat() if last_record else None,
            } if last_record else None,
        }

    async def get_evidence_ledger_record(self, evidence_id: str):
        """Get the ledger record for a specific evidence."""
        return await self.ledger_repo.get_by_evidence(evidence_id)