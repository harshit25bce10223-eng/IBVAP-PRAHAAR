# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — ORM Model Registry
# Importing these registers every table on Base.metadata (required by Alembic).
# ─────────────────────────────────────────────────────────────────────────────
import os

# In test mode, exclude TrackV2 to avoid table conflict with Component 1's Track
# Both map to the same "tracks" table; TrackV2 uses extend_existing=True in prod.
_is_test_env = os.environ.get("PYTEST_CURRENT_TEST") is not None or os.environ.get("ENV") == "test"

from app.models.event import Event
from app.models.incident import Incident
from app.models.track import Track
from app.models.zone import Zone
from app.models.camera_health import (
    CameraHealthConfig,
    CameraHealthObservation,
    CameraHealthEvent,
    CameraHealthBaseline,
    CameraHealthCurrent,
)
from app.models.evidence import (
    EvidenceRecord,
    EvidenceVerification,
    EvidenceLifecycleEvent,
    EvidenceLedgerRecord,
)
from app.models.event_correlation import (
    CorrelationGroup,
    CorrelationStatus,
    CorrelationGroupState,
    CorrelationCompleteness,
    CorrelationGroupMember,
    MembershipType,
    CorrelationRelationship,
    CorrelationRelationType,
    CorrelationHistory,
    CorrelationConfig,
    CorrelationConfigProfile,
)
from app.models.detection import (
    Detection,
    DetectionConfig,
    DetectionClass,
    DetectionQuality,
    DetectionOcclusion,
    DetectionState,
    DetectionSource,
    DetectionFeedState,
    InferenceState,
    DetectionSyncState,
)
from app.models.anpr import (
    VehicleSighting,
    PlateRead,
    PlateCandidate,
    ANPRConfig,
)

# Only import TrackV2 and related tracking models in non-test environments
if not _is_test_env:
    from app.models.tracking import (
        TrackV2,
        TrackObservation,
        TrackHistory,
        TrackCandidate,
        TrackingConfig,
    )

__all__ = [
    "Event",
    "Incident",
    "Track",
    "Zone",
    "CameraHealthConfig",
    "CameraHealthObservation",
    "CameraHealthEvent",
    "CameraHealthBaseline",
    "CameraHealthCurrent",
    "EvidenceRecord",
    "EvidenceVerification",
    "EvidenceLifecycleEvent",
    "EvidenceLedgerRecord",
    "CorrelationGroup",
    "CorrelationStatus",
    "CorrelationGroupState",
    "CorrelationCompleteness",
    "CorrelationGroupMember",
    "MembershipType",
    "CorrelationRelationship",
    "CorrelationRelationType",
    "CorrelationHistory",
    "CorrelationConfig",
    "CorrelationConfigProfile",
    "Detection",
    "DetectionConfig",
    "DetectionClass",
    "DetectionQuality",
    "DetectionOcclusion",
    "DetectionState",
    "DetectionSource",
    "DetectionFeedState",
    "InferenceState",
    "DetectionSyncState",
    # Component 7 — ANPR
    "VehicleSighting",
    "PlateRead",
    "PlateCandidate",
    "ANPRConfig",
]

# Add Component 6 tracking models only in non-test environments
if not _is_test_env:
    __all__.extend([
        "TrackV2",
        "TrackObservation",
        "TrackHistory",
        "TrackCandidate",
        "TrackingConfig",
    ])