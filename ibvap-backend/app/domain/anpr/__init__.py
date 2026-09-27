# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 7 — ANPR Domain
# ─────────────────────────────────────────────────────────────────────────────
from .constants import (
    PlateQuality,
    VehicleClass,
    VehicleColor,
    VehicleDirection,
    PlateFormatStatus,
    WatchlistStatus,
    ANPRSyncState,
    ANPRSource,
    SearchMatchType,
    ANPRProviderHealthState,
    CameraHealthState,
    CameraHealthReliability,
)
from .provider import (
    ANPRProvider,
    ANPRProviderHealthInfo,
    ANPRProviderMetadata,
    ANPRCameraContext,
    ANPRBatchResult,
    ANPRObservationResult,
    PlateCandidateInput,
    PlateReadInput,
    VehicleSightingInput,
    ANPRProviderUnavailableError,
    get_anpr_provider,
    set_anpr_provider,
)
from .demo_provider import DemoANPRProvider

__all__ = [
    # Constants
    "PlateQuality",
    "VehicleClass",
    "VehicleColor",
    "VehicleDirection",
    "PlateFormatStatus",
    "WatchlistStatus",
    "ANPRSyncState",
    "ANPRSource",
    "SearchMatchType",
    "ANPRProviderHealthState",
    "CameraHealthState",
    "CameraHealthReliability",
    # Provider
    "ANPRProvider",
    "ANPRProviderHealthInfo",
    "ANPRProviderMetadata",
    "ANPRCameraContext",
    "ANPRBatchResult",
    "ANPRObservationResult",
    "PlateCandidateInput",
    "PlateReadInput",
    "VehicleSightingInput",
    "ANPRProviderUnavailableError",
    "get_anpr_provider",
    "set_anpr_provider",
    # Demo provider
    "DemoANPRProvider",
]