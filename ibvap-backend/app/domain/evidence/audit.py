# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — Evidence Audit Service
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.evidence import EvidenceRecord


class EvidenceAuditService:
    """
    Service for logging evidence-related audit events.

    Logs privileged operations for accountability.
    """

    def __init__(self, session: Optional[AsyncSession] = None):
        self.session = session

    async def log(
        self,
        actor: str,
        action: str,
        target: str,
        result: str,
        reason: str | None = None,
        metadata: dict | None = None,
        session: Optional[Any] = None,
    ) -> None:
        """
        Log an audit event.

        Args:
            actor: Actor performing the action (USER, SYSTEM, SERVICE)
            action: Action type (VIEW, VERIFY, DOWNLOAD, EXPORT, ANNOTATE, LEDGER_VERIFY, MISMATCH)
            target: Target evidence ID
            result: Result (SUCCESS, FAILURE, DENIED)
            reason: Optional reason
            metadata: Optional additional metadata
            session: Database session (uses internal if not provided)
        """
        target_session = session or getattr(self, 'session', None)
        if not target_session:
            raise ValueError("No database session available")

        # Log to application log (structured)
        import logging
        logger = __import__("logging").getLogger("prhaar.audit.evidence")
        logger.info(
            "evidence_audit",
            extra={
                "actor": actor,
                "action": action,
                "target": target,
                "result": result,
                "reason": reason,
                "metadata": metadata,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
        )

    async def log_view(self, actor: str, evidence_id: str, session: Optional[Any] = None) -> None:
        await self.log(actor, "VIEW", evidence_id, "SUCCESS", session=session)

    async def log_verify(self, actor: str, evidence_id: str, outcome: str, session: Optional[Any] = None) -> None:
        await self.log(actor, "VERIFY", evidence_id, outcome, session=session)

    async def log_download(self, actor: str, evidence_id: str, session: Optional[Any] = None) -> None:
        await self.log(actor, "DOWNLOAD", evidence_id, "SUCCESS", session=session)

    async def log_export(self, actor: str, evidence_id: str, session: Optional[Any] = None) -> None:
        await self.log(actor, "EXPORT", evidence_id, "SUCCESS", session=session)

    async def log_annotate(self, actor: str, evidence_id: str, session: Optional[Any] = None) -> None:
        await self.log(actor, "ANNOTATE", evidence_id, "SUCCESS", session=session)

    async def log_ledger_verify(self, actor: str, evidence_id: str, outcome: str, session: Optional[Any] = None) -> None:
        await self.log(actor, "LEDGER_VERIFY", evidence_id, outcome, session=session)

    async def log_mismatch(self, actor: str, evidence_id: str, session: Optional[Any] = None) -> None:
        await self.log(actor, "MISMATCH", evidence_id, "MISMATCH", session=session)


# Global audit service instance
evidence_audit_service = EvidenceAuditService()