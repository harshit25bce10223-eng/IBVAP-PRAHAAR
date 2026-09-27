# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — Evidence Lifecycle Service
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evidence import EvidenceLifecycleEvent, EvidenceRecord


class EvidenceLifecycleService:
    """
    Service for managing evidence lifecycle events.

    Records state transitions and maintains audit trail.
    """

    def __init__(self, session: Optional[AsyncSession] = None):
        self.session = session

    async def log_event(
        self,
        evidence_id: str,
        event_type: str,
        actor: str,
        metadata: Optional[dict] = None,
        session: Optional[AsyncSession] = None,
    ) -> None:
        """
        Log a lifecycle event for evidence.

        Args:
            evidence_id: Evidence identifier
            event_type: Type of lifecycle event (e.g., CAPTURED, STORED, HASHED)
            actor: Actor/service that triggered the event
            metadata: Optional additional metadata
            session: Database session (uses internal if not provided)
        """
        target_session = session or self.session
        if not target_session:
            raise ValueError("No database session available")

        event = EvidenceLifecycleEvent(
            id=f"LCE-{uuid.uuid4().hex[:10].upper()}",
            evidence_id=evidence_id,
            event_type=event_type,
            timestamp=datetime.now(timezone.utc),
            actor=actor,
            metadata_json=__import__("json").dumps(metadata) if metadata else None,
            created_at=datetime.now(timezone.utc),
        )
        target_session.add(event)
        await target_session.flush()

    async def get_lifecycle(self, evidence_id: str, limit: int = 100) -> list[dict]:
        """Get lifecycle events for evidence."""
        from app.repositories.evidence import EvidenceLifecycleRepository
        from sqlalchemy.ext.asyncio import AsyncSession

        if not self.session:
            raise ValueError("No database session available")

        repo = EvidenceLifecycleRepository(self.session)
        events = await repo.list_by_evidence(evidence_id, limit=limit)

        return [
            {
                "id": e.id,
                "evidenceId": e.evidence_id,
                "eventType": e.event_type,
                "timestamp": e.timestamp.isoformat(),
                "actor": e.actor,
                "metadata": __import__("json").loads(e.metadata_json) if e.metadata_json else None,
                "createdAt": e.created_at.isoformat(),
            }
            for e in events
        ]

    async def log_captured(
        self, evidence_id: str, actor: str, session: Optional[AsyncSession] = None
    ) -> None:
        await self.log_event(evidence_id, "CAPTURED", actor, session=session)

    async def log_stored(
        self, evidence_id: str, actor: str, session: Optional[AsyncSession] = None
    ) -> None:
        await self.log_event(evidence_id, "STORED", actor, session=session)

    async def log_hashed(
        self, evidence_id: str, actor: str, session: Optional[AsyncSession] = None
    ) -> None:
        await self.log_event(evidence_id, "HASHED", actor, session=session)

    async def log_ledgered(
        self, evidence_id: str, actor: str, session: Optional[AsyncSession] = None
    ) -> None:
        await self.log_event(evidence_id, "LEDGERED", actor, session=session)

    async def log_anchored(
        self, evidence_id: str, actor: str, session: Optional[AsyncSession] = None
    ) -> None:
        await self.log_event(evidence_id, "ANCHORED", actor, session=session)

    async def log_verified(
        self,
        evidence_id: str,
        actor: str,
        verification_id: str,
        outcome: str,
        session: Optional[AsyncSession] = None,
    ) -> None:
        await self.log_event(
            evidence_id,
            "VERIFIED",
            actor,
            {"verification_id": verification_id, "outcome": outcome},
            session=session,
        )

    async def log_exported(
        self, evidence_id: str, actor: str, session: Optional[AsyncSession] = None
    ) -> None:
        await self.log_event(evidence_id, "EXPORTED", actor, session=session)

    async def log_archived(
        self, evidence_id: str, actor: str, session: Optional[AsyncSession] = None
    ) -> None:
        await self.log_event(evidence_id, "ARCHIVED", actor, session=session)

    async def log_export_requested(
        self, evidence_id: str, actor: str, session: Optional[AsyncSession] = None
    ) -> None:
        await self.log_event(evidence_id, "EXPORT_REQUESTED", actor, session=session)

    async def log_export_ready(
        self, evidence_id: str, actor: str, session: Optional[AsyncSession] = None
    ) -> None:
        await self.log_event(evidence_id, "EXPORT_READY", actor, session=session)

    async def log_export_failed(
        self, evidence_id: str, actor: str, reason: str, session: Optional[AsyncSession] = None
    ) -> None:
        await self.log_event(
            evidence_id, "EXPORT_FAILED", actor, {"reason": reason}, session=session
        )

    async def log_sync_started(
        self, evidence_id: str, actor: str, session: Optional[AsyncSession] = None
    ) -> None:
        await self.log_event(evidence_id, "SYNC_STARTED", actor, session=session)

    async def log_sync_completed(
        self, evidence_id: str, actor: str, session: Optional[AsyncSession] = None
    ) -> None:
        await self.log_event(evidence_id, "SYNC_COMPLETED", actor, session=session)

    async def log_sync_failed(
        self, evidence_id: str, actor: str, reason: str, session: Optional[AsyncSession] = None
    ) -> None:
        await self.log_event(
            evidence_id, "SYNC_FAILED", actor, {"reason": reason}, session=session
        )

    async def log_mismatch_detected(
        self,
        evidence_id: str,
        actor: str,
        verification_id: str,
        session: Optional[AsyncSession] = None,
    ) -> None:
        await self.log_event(
            evidence_id,
            "MISMATCH_DETECTED",
            actor,
            {"verification_id": verification_id},
            session=session,
        )

    async def log_ledger_appended(
        self,
        evidence_id: str,
        actor: str,
        ledger_record_id: str,
        session: Optional[AsyncSession] = None,
    ) -> None:
        await self.log_event(
            evidence_id,
            "LEDGER_APPENDED",
            actor,
            {"ledger_record_id": ledger_record_id},
            session=session,
        )

    async def log_anchor_created(
        self,
        evidence_id: str,
        actor: str,
        anchor_id: str,
        session: Optional[AsyncSession] = None,
    ) -> None:
        await self.log_event(
            evidence_id, "ANCHOR_CREATED", actor, {"anchor_id": anchor_id}, session=session
        )


# Global lifecycle service instance
evidence_lifecycle_service = EvidenceLifecycleService()