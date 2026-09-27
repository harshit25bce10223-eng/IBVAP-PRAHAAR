# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — Evidence Sync Provider (Edge/Offline Support)
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Optional

from app.models.evidence import EvidenceRecord
from sqlalchemy.ext.asyncio import AsyncSession


class EvidenceSyncProvider(ABC):
    """
    Abstract interface for evidence synchronization.

    Handles edge-to-central evidence replication.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @abstractmethod
    async def queue_for_sync(self, evidence_id: str, priority: int = 0) -> dict[str, Any]:
        """Queue evidence for synchronization."""
        pass

    @abstractmethod
    async def sync(self, evidence_id: str) -> dict[str, Any]:
        """Synchronize specific evidence to central."""
        pass

    @abstractmethod
    async def get_sync_status(self, evidence_id: str) -> dict[str, Any]:
        """Get sync status for evidence."""
        pass

    @abstractmethod
    async def retry_failed(self, evidence_id: str) -> dict[str, Any]:
        """Retry failed sync."""
        pass


class CentralSyncProvider:
    """
    Central synchronization provider.

    Queues evidence for sync to central server.
    """

    name = "CENTRAL_SYNC"

    def __init__(self, session):
        self.session = session

    async def queue_for_sync(self, evidence_id: str, priority: int = 0) -> dict[str, Any]:
        from app.repositories.evidence import EvidenceRecordRepository
        record_repo = EvidenceRecordRepository(self.session)
        record = await record_repo.get(evidence_id)
        if not record:
            raise ValueError(f"Evidence '{evidence_id}' not found")

        # Update sync state
        await record_repo.update(evidence_id, sync_state="SYNC_PENDING")
        return {"status": "QUEUED", "evidence_id": evidence_id, "priority": priority}

    async def sync(self, evidence_id: str) -> dict[str, Any]:
        # In a real implementation, this would sync to central server
        return {"status": "SYNCED", "evidence_id": evidence_id}

    async def get_sync_status(self, evidence_id: str) -> dict[str, Any]:
        from app.repositories.evidence import EvidenceRecordRepository
        record_repo = EvidenceRecordRepository(self.session)
        record = await record_repo.get(evidence_id)
        if not record:
            return {"status": "UNKNOWN", "evidence_id": evidence_id}
        return {
            "evidence_id": evidence_id,
            "sync_state": record.sync_state,
            "last_synced_at": None,
        }

    async def retry_failed(self, evidence_id: str) -> dict[str, Any]:
        return await self.queue_for_sync(evidence_id)


class EdgeSyncProvider:
    """
    Edge synchronization provider.

    Handles local-only evidence with deferred sync.
    """

    name = "EDGE_SYNC"

    def __init__(self, session):
        self.session = session

    async def queue_for_sync(self, evidence_id: str, priority: int = 0) -> dict[str, Any]:
        from app.repositories.evidence import EvidenceRecordRepository
        record_repo = EvidenceRecordRepository(self.session)
        record = await record_repo.get(evidence_id)
        if not record:
            raise ValueError(f"Evidence '{evidence_id}' not found")

        await record_repo.update(evidence_id, sync_state="SYNC_PENDING")
        return {"status": "QUEUED", "evidence_id": evidence_id, "priority": priority}

    async def sync(self, evidence_id: str) -> dict[str, Any]:
        # Local edge sync - just mark as synced locally
        from app.repositories.evidence import EvidenceRecordRepository
        record_repo = EvidenceRecordRepository(self.session)
        await record_repo.update(evidence_id, sync_state="SYNCED")
        return {"status": "SYNCED", "evidence_id": evidence_id, "location": "edge"}

    async def get_sync_status(self, evidence_id: str) -> dict[str, Any]:
        from app.repositories.evidence import EvidenceRecordRepository
        record_repo = EvidenceRecordRepository(self.session)
        record = await record_repo.get(evidence_id)
        if not record:
            return {"status": "UNKNOWN", "evidence_id": evidence_id}
        return {
            "evidence_id": evidence_id,
            "sync_state": record.sync_state,
            "last_synced_at": None,
        }

    async def retry_failed(self, evidence_id: str) -> dict[str, Any]:
        return await self.queue_for_sync(evidence_id)


class SyncProviderFactory:
    """Factory for creating sync providers."""

    _providers = {
        "CENTRAL": "CentralSyncProvider",
        "EDGE": "EdgeSyncProvider",
    }

    @classmethod
    def register(cls, name: str, provider_class: type):
        pass

    @classmethod
    def create(cls, name: str, session, **kwargs):
        if name == "CENTRAL":
            from app.domain.evidence.sync import CentralSyncProvider
            return CentralSyncProvider(session)
        elif name == "EDGE":
            from app.domain.evidence.sync import EdgeSyncProvider
            return EdgeSyncProvider(session)
        raise ValueError(f"Unknown sync provider: {name}")

    @classmethod
    def get_default(cls, session):
        return cls.create("CENTRAL", session)