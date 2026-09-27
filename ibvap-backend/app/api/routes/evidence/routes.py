# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# PRHAAR â€” Evidence API Routes
# â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
from __future__ import annotations

import io
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import IBVAPError
from app.db.database import get_db_session
from app.domain.evidence.service import EvidenceService
from app.domain.evidence.provenance import ProvenanceService
from app.domain.evidence.lifecycle import EvidenceLifecycleService
from app.domain.evidence.ledger import EvidenceLedgerService
from app.domain.evidence.verification import EvidenceVerificationService
from app.domain.evidence.sync import CentralSyncProvider
from app.repositories.evidence import EvidenceRecordRepository, EvidenceVerificationRepository
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
    EvidenceDetailResponse,
)

router = APIRouter(prefix="/evidence", tags=["evidence"])


def get_evidence_service(session: AsyncSession = Depends(get_db_session)) -> EvidenceService:
    return EvidenceService(session)


def get_provenance_service(session: AsyncSession = Depends(get_db_session)) -> ProvenanceService:
    return ProvenanceService(session)


def get_lifecycle_service(session: AsyncSession = Depends(get_db_session)) -> EvidenceLifecycleService:
    return EvidenceLifecycleService(session)


def get_ledger_service(session: AsyncSession = Depends(get_db_session)) -> EvidenceLedgerService:
    return EvidenceLedgerService(session)


def get_verification_service(session: AsyncSession = Depends(get_db_session)) -> EvidenceVerificationService:
    return EvidenceVerificationService(session)


# â”€â”€ Ledger Summary (MUST be before /{evidence_id} to prevent capture) â”€â”€â”€â”€â”€â”€â”€â”€

@router.get("/ledger/summary", response_model=LedgerSummary)
async def get_ledger_summary(
    service: EvidenceService = Depends(get_evidence_service),
):
    """Get ledger health summary."""
    summary = await service.get_ledger_summary()
    return LedgerSummary(**summary)


@router.post("/ledger/verify")
async def verify_ledger(
    service: EvidenceService = Depends(get_evidence_service),
):
    """Verify ledger chain integrity."""
    return await service.verify_ledger()


# â”€â”€ Evidence CRUD (dynamic /{evidence_id} routes AFTER static routes) â”€â”€â”€â”€â”€â”€â”€â”€

@router.get("/", response_model=EvidencePage)
async def list_evidence(
    query: EvidenceQuery = Depends(),
    service: EvidenceService = Depends(get_evidence_service),
):
    """List evidence with pagination, filtering, and sorting."""
    records, total = await service.list_evidence(query)
    return EvidencePage(records=records, total=total)


@router.get("/{evidence_id}", response_model=EvidenceDetailResponse)
async def get_evidence(
    evidence_id: str,
    service: EvidenceService = Depends(get_evidence_service),
):
    """Get full evidence detail."""
    return await service.get_evidence(evidence_id)


@router.get("/{evidence_id}/content")
async def get_evidence_content(
    evidence_id: str,
    service: EvidenceService = Depends(get_evidence_service),
):
    """Stream evidence content."""
    try:
        stream, mime_type, content_hash = await service.get_content(evidence_id)
        return StreamingResponse(
            stream,
            media_type=mime_type,
            headers={
                "Content-Disposition": f'inline; filename="evidence_{evidence_id}"',
                "X-Content-Hash": content_hash,
            },
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))


# â”€â”€ Verification â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.post("/{evidence_id}/verify", response_model=VerifyResult)
async def verify_evidence(
    evidence_id: str,
    actor_id: str | None = Query(None, description="Actor performing verification"),
    service: EvidenceService = Depends(get_evidence_service),
):
    """Verify evidence integrity."""
    return await service.verify(evidence_id, actor_id)


@router.get("/{evidence_id}/verification-history")
async def get_verification_history(
    evidence_id: str,
    limit: int = Query(50, ge=1, le=100),
    service: EvidenceService = Depends(get_evidence_service),
):
    """Get verification history for evidence."""
    history = await service.get_verification_history(evidence_id)
    return {"evidence_id": evidence_id, "history": history}


# â”€â”€ Provenance â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.get("/{evidence_id}/provenance")
async def get_provenance(
    evidence_id: str,
    service: EvidenceService = Depends(get_evidence_service),
):
    """Get evidence provenance chain."""
    provenance = await service.get_provenance(evidence_id)
    return provenance


# â”€â”€ Lifecycle â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.get("/{evidence_id}/lifecycle")
async def get_lifecycle(
    evidence_id: str,
    limit: int = Query(100, ge=1, le=500),
    service: EvidenceService = Depends(get_evidence_service),
):
    """Get evidence lifecycle events."""
    lifecycle = await service.get_lifecycle(evidence_id)
    return {"evidence_id": evidence_id, "events": lifecycle}


# â”€â”€ Ledger â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.get("/{evidence_id}/ledger")
async def get_ledger_record(
    evidence_id: str,
    service: EvidenceService = Depends(get_evidence_service),
):
    """Get ledger record for evidence."""
    ledger = await service.get_ledger_record(evidence_id)
    if not ledger:
        raise HTTPException(status_code=404, detail="Ledger record not found")
    return ledger

# â”€â”€ Export â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.post("/{evidence_id}/export", response_model=ExportReceipt)
async def request_export(
    evidence_id: str,
    service: EvidenceService = Depends(get_evidence_service),
):
    """Request evidence export."""
    return await service.request_export(evidence_id)


# â”€â”€ Sync â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.post("/{evidence_id}/sync")
async def queue_for_sync(
    evidence_id: str,
    priority: int = Query(0, ge=0, le=10),
    service: EvidenceService = Depends(get_evidence_service),
):
    """Queue evidence for synchronization."""
    return await service.queue_for_sync(evidence_id, priority)


@router.get("/{evidence_id}/sync")
async def get_sync_status(
    evidence_id: str,
    service: EvidenceService = Depends(get_evidence_service),
):
    """Get sync status for evidence."""
    return await service.get_sync_status(evidence_id)


# â”€â”€ Audit â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.get("/{evidence_id}/audit")
async def get_audit(
    evidence_id: str,
    limit: int = Query(100, ge=1, le=500),
    service: EvidenceService = Depends(get_evidence_service),
):
    """Get audit trail for evidence."""
    return await service.list_audit(limit)


# â”€â”€ Internal Ingestion (for Edge/Ingestion component) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.post("/internal/cameras/{camera_id}/evidence/observations", response_model=EvidenceIngestResponse)
async def ingest_evidence(
    camera_id: str,
    observation: dict[str, Any],
    session: AsyncSession = Depends(get_db_session),
):
    """
    Internal endpoint for edge/video adapters to ingest evidence.

    This is NOT a user-facing endpoint.
    """
    from app.domain.evidence.service import EvidenceService
    from app.repositories.evidence import EvidenceRecordRepository

    record_repo = EvidenceRecordRepository(session)
    service = EvidenceService(session)

    # Parse observation
    incident_id = observation.get("incident_id")
    event_id = observation.get("event_id")
    zone_id = observation.get("zone_id")
    type_ = observation.get("type", "SNAPSHOT")
    source = observation.get("source", "CAMERA")
    role = observation.get("role", "ORIGINAL_CAPTURE")
    captured_at = datetime.fromisoformat(observation.get("captured_at", datetime.now(timezone.utc).isoformat()))
    mime_type = observation.get("mime_type")
    file_size_bytes = observation.get("file_size_bytes")
    media_duration_ms = observation.get("media_duration_ms")
    width = observation.get("width")
    height = observation.get("height")
    parent_evidence_id = observation.get("parent_evidence_id")
    region_profile = observation.get("region_profile")
    sector = observation.get("sector")
    algorithm_version = observation.get("algorithm_version")

    # For internal ingestion, we expect base64 encoded content
    import base64
    content_b64 = observation.get("content")
    if not content_b64:
        raise HTTPException(status_code=400, detail="Missing content")

    content = base64.b64decode(content_b64)
    stream = io.BytesIO(content)

    service = __import__("app.domain.evidence.service", fromlist=["EvidenceService"]).EvidenceService(session)
    record = await __import__("app.domain.evidence.service", fromlist=["EvidenceService"]).EvidenceService(session).create_evidence(
        incident_id=incident_id,
        event_id=event_id,
        camera_id=camera_id,
        zone_id=zone_id,
        type_=type_,
        source=source,
        role=role,
        captured_at=captured_at,
        stream=io.BytesIO(content),
        mime_type=mime_type,
        file_size_bytes=len(content),
    )

    return EvidenceIngestResponse(
        accepted=True,
        evidenceId=record.evidence_id,
        currentStatus=record.status,
    )


# â”€â”€ Config (placeholder) â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@router.post("/{camera_id}/health/config")
async def create_camera_health_config(
    camera_id: str,
    config: dict[str, Any],
    session: AsyncSession = Depends(get_db_session),
):
    """Create health config for a camera."""
    from app.repositories.camera_health import CameraHealthConfigRepository
    config_repo = CameraHealthConfigRepository(session)
    config_obj = await config_repo.create(camera_id, **config)
    await session.commit()
    return {"camera_id": config_obj.camera_id, "created": True}


@router.get("/{camera_id}/health/config")
async def get_camera_health_config(
    camera_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Get health config for a camera."""
    from app.repositories.camera_health import CameraHealthConfigRepository
    config_repo = CameraHealthConfigRepository(session)
    config = await config_repo.get(camera_id)
    if not config:
        raise HTTPException(status_code=404, detail="Config not found")
    return config


@router.patch("/{camera_id}/health/config")
async def update_camera_health_config(
    camera_id: str,
    config: dict[str, Any],
    session: AsyncSession = Depends(get_db_session),
):
    """Update health config for a camera."""
    from app.repositories.camera_health import CameraHealthConfigRepository
    config_repo = CameraHealthConfigRepository(session)
    config_obj = await config_repo.update(camera_id, **config)
    if not config_obj:
        raise HTTPException(status_code=404, detail="Config not found")
    await session.commit()
    return config_obj


@router.delete("/{camera_id}/health/config")
async def delete_camera_health_config(
    camera_id: str,
    session: AsyncSession = Depends(get_db_session),
):
    """Delete health config for a camera."""
    from app.repositories.camera_health import CameraHealthConfigRepository
    config_repo = CameraHealthConfigRepository(session)
    deleted = await config_repo.delete(camera_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Config not found")
    await session.commit()
    return {"deleted": True}
