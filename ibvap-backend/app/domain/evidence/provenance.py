# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — Evidence Provenance Service
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from app.models.evidence import EvidenceRecord
from app.repositories.evidence import EvidenceRecordRepository
from sqlalchemy.ext.asyncio import AsyncSession


class ProvenanceService:
    """
    Service for building evidence provenance chains.

    Builds the complete lineage: Camera → Event → Incident → Evidence
    and Original → Derived → Export chains.
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.record_repo = EvidenceRecordRepository(session)

    async def get_provenance(self, evidence_id: str) -> dict[str, Any]:
        """
        Build complete provenance chain for evidence.

        Returns:
            Dict with chain, milestones, custody steps
        """
        record = await self.record_repo.get(evidence_id)
        if not record:
            return {
                "chain": [],
                "milestones": [],
                "custody": [],
            }

        chain = []
        milestones = []
        custody = []

        # Build the chain: Camera → Event → Incident → Evidence
        if record.camera_id:
            chain.append(record.camera_id)
        if record.event_id:
            chain.append(record.event_id)
        if record.incident_id:
            chain.append(record.incident_id)
        chain.append(record.evidence_id)

        # Milestones
        milestones.append({
            "key": "captured",
            "label": "Captured",
            "at": record.captured_at.isoformat() if record.captured_at else None,
        })
        if record.ingested_at:
            milestones.append({
                "key": "ingested",
                "label": "Ingested",
                "at": record.ingested_at.isoformat(),
            })
        milestones.append({
            "key": "created",
            "label": "Record Created",
            "at": record.created_at.isoformat() if record.created_at else None,
        })

        # Custody steps
        custody.append({
            "stage": "CAPTURE",
            "detail": f"Captured by {record.source}",
            "at": record.captured_at.isoformat() if record.captured_at else None,
        })
        custody.append({
            "stage": "INGEST",
            "detail": f"Ingested via {record.storage_backend}",
            "at": record.ingested_at.isoformat() if record.ingested_at else None,
        })
        custody.append({
            "stage": "HASH",
            "detail": f"Hashed with {record.content_hash_algorithm}",
            "at": record.created_at.isoformat() if record.created_at else None,
        })

        # Add derived chain if applicable
        if record.parent_evidence_id:
            parent = await self.record_repo.get(record.parent_evidence_id)
            if parent:
                chain.insert(-1, parent.evidence_id)

        return {
            "chain": chain,
            "milestones": milestones,
            "custody": custody,
        }

    async def get_derived_chain(self, evidence_id: str) -> list[dict[str, Any]]:
        """Get the full derived chain from original to current."""
        chain = []
        current_id = evidence_id

        while current_id:
            record = await self.record_repo.get(current_id)
            if not record:
                break

            chain.insert(0, {
                "evidenceId": record.evidence_id,
                "type": record.type,
                "role": record.role,
                "capturedAt": record.captured_at.isoformat() if record.captured_at else None,
                "hash": record.content_hash[:16] + "...",
            })

            current_id = record.parent_evidence_id

        return chain