# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — Repository Registry
# ─────────────────────────────────────────────────────────────────────────────
from app.repositories.event_repository import EventRepository
from app.repositories.incident_repository import IncidentRepository
from app.repositories.track_repository import TrackRepository
from app.repositories.zone_repository import ZoneRepository
from app.repositories.camera_health import (
    CameraHealthConfigRepository,
    CameraHealthObservationRepository,
    CameraHealthEventRepository,
    CameraHealthBaselineRepository,
    CameraHealthCurrentRepository,
)
from app.repositories.evidence import (
    EvidenceRecordRepository,
    EvidenceVerificationRepository,
    EvidenceLifecycleRepository,
    EvidenceLedgerRepository,
)
from app.repositories.event_correlation import (
    CorrelationGroupRepository,
    CorrelationGroupMemberRepository,
    CorrelationRelationshipRepository,
    CorrelationHistoryRepository,
    CorrelationConfigRepository,
)

__all__ = [
    "EventRepository",
    "IncidentRepository",
    "TrackRepository",
    "ZoneRepository",
    "CameraHealthConfigRepository",
    "CameraHealthObservationRepository",
    "CameraHealthEventRepository",
    "CameraHealthBaselineRepository",
    "CameraHealthCurrentRepository",
    "EvidenceRecordRepository",
    "EvidenceVerificationRepository",
    "EvidenceLifecycleRepository",
    "EvidenceLedgerRepository",
    "CorrelationGroupRepository",
    "CorrelationGroupMemberRepository",
    "CorrelationRelationshipRepository",
    "CorrelationHistoryRepository",
    "CorrelationConfigRepository",
]