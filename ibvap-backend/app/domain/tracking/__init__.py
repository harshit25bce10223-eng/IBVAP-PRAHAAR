# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 6 — Tracking Engine domain package
# ─────────────────────────────────────────────────────────────────────────────
from app.domain.tracking.constants import (
    TRACK_STATUS_ACTIVE,
    TRACK_STATUS_TENTATIVE,
    TRACK_STATUS_LOST,
    TRACK_STATUS_REACQUIRED,
    TRACK_STATUS_ENDED,
    TRACK_STATUS_STALE,
    TRACK_STATUS_INVALID,
    TRACK_STATUS_UNKNOWN,
    TRACK_STATUSES_ACTIVE_SET,
    TRACK_STATUSES_TERMINAL_SET,
)
from app.domain.tracking.provider import (
    TrackingProvider,
    DetectionInput,
    TrackAssignment,
    ProviderUpdateResult,
    ProviderHealthInfo,
    ProviderMetadata,
    CameraContext,
    get_tracking_provider,
    set_tracking_provider,
    require_tracking_provider,
)
from app.domain.tracking.lifecycle import TrackLifecycleService
from app.domain.tracking.association import TrackAssociationService, AssociationBatchResult
from app.domain.tracking.service import TrackingService, TrackNotFoundError, ProviderUnavailableError

__all__ = [
    "TRACK_STATUS_ACTIVE", "TRACK_STATUS_TENTATIVE", "TRACK_STATUS_LOST",
    "TRACK_STATUS_REACQUIRED", "TRACK_STATUS_ENDED", "TRACK_STATUS_STALE",
    "TRACK_STATUS_INVALID", "TRACK_STATUS_UNKNOWN",
    "TRACK_STATUSES_ACTIVE_SET", "TRACK_STATUSES_TERMINAL_SET",
    "TrackingProvider", "DetectionInput", "TrackAssignment",
    "ProviderUpdateResult", "ProviderHealthInfo", "ProviderMetadata", "CameraContext",
    "get_tracking_provider", "set_tracking_provider", "require_tracking_provider",
    "TrackLifecycleService", "TrackAssociationService", "AssociationBatchResult",
    "TrackingService", "TrackNotFoundError", "ProviderUnavailableError",
]
