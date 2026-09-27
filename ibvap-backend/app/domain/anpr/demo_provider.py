# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 7 — DemoANPRProvider
#
# Deterministic demo provider — no real OCR, fixed fixtures for testing.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone
from typing import Any

from app.core.logging import get_logger
from app.domain.anpr.constants import (
    ANPRProviderHealthState,
    PlateQuality,
    VehicleClass,
    VehicleDirection,
)
from app.domain.anpr.provider import (
    ANPRBatchResult,
    ANPRObservationResult,
    ANPRCameraContext,
    ANPRProvider,
    ANPRProviderHealthInfo,
    ANPRProviderMetadata,
    PlateReadInput,
    VehicleSightingInput,
)

logger = get_logger("prhaar.anpr.demo_provider")

# ─────────────────────────────────────────────────────────────────────────────
# Fixed demo plate fixtures — deterministic, never random
# ─────────────────────────────────────────────────────────────────────────────

_DEMO_PLATES: dict[str, dict] = {
    # Camera -> list of plate fixtures
    "CAM-07": [
        {
            "raw_read": "HR26AK4521",
            "normalized_read": "HR26AK4521",
            "display_read": "HR26AK4521",
            "confidence": 0.92,
            "quality": "GOOD",
            "format_status": "VALID_FORMAT",
            "vehicle_class": "PERSONAL_CAR",
            "vehicle_color": "WHITE",
            "vehicle_direction": "NORTH",
        },
        {
            "raw_read": "HR26AK452I",
            "normalized_read": "HR26AK452I",
            "display_read": "HR26AK452I",
            "confidence": 0.61,
            "quality": "FAIR",
            "format_status": "POSSIBLE_FORMAT",
            "vehicle_class": "PERSONAL_CAR",
            "vehicle_color": "WHITE",
            "vehicle_direction": "NORTH",
        },
        {
            "raw_read": "GJ01BV2209",
            "normalized_read": "GJ01BV2209",
            "display_read": "GJ01BV2209",
            "confidence": 0.87,
            "quality": "GOOD",
            "format_status": "VALID_FORMAT",
            "vehicle_class": "SUV",
            "vehicle_color": "BLACK",
            "vehicle_direction": "INBOUND",
        },
    ],
    "CAM-08": [
        {
            "raw_read": "MP09CD7731",
            "normalized_read": "MP09CD7731",
            "display_read": "MP09CD7731",
            "confidence": 0.48,
            "quality": "FAIR",
            "format_status": "POSSIBLE_FORMAT",
            "vehicle_class": "SUV",
            "vehicle_color": "GREY",
            "vehicle_direction": "SOUTH",
        },
        {
            "raw_read": "HR26AK4521",
            "normalized_read": "HR26AK4521",
            "display_read": "HR26AK4521",
            "confidence": 0.89,
            "quality": "GOOD",
            "format_status": "VALID_FORMAT",
            "vehicle_class": "PERSONAL_CAR",
            "vehicle_color": "WHITE",
            "vehicle_direction": "NORTH",
        },
    ],
    "CAM-09": [
        {
            "raw_read": "RJ14AB1O52",
            "normalized_read": "RJ14AB1052",
            "display_read": "RJ14AB1052",
            "confidence": 0.91,
            "quality": "FAIR",
            "format_status": "POSSIBLE_FORMAT",
            "vehicle_class": "PERSONAL_CAR",
            "vehicle_color": "SILVER",
            "vehicle_direction": "EAST",
        },
        {
            "raw_read": "MH43AA8801",
            "normalized_read": "MH43AA8801",
            "display_read": "MH43AA8801",
            "confidence": 0.78,
            "quality": "GOOD",
            "format_status": "VALID_FORMAT",
            "vehicle_class": "BUS",
            "vehicle_color": "YELLOW",
            "vehicle_direction": "OUTBOUND",
        },
    ],
    "CAM-11": [
        {
            "raw_read": "DL1LT7821",
            "normalized_read": "DL1LT7821",
            "display_read": "DL1LT7821",
            "confidence": 0.61,
            "quality": "MOTION_BLUR",
            "format_status": "VALID_FORMAT",
            "vehicle_class": "TRUCK",
            "vehicle_color": "RED",
            "vehicle_direction": "INBOUND",
        },
        {
            "raw_read": "HR26AK4521",
            "normalized_read": "HR26AK4521",
            "display_read": "HR26AK4521",
            "confidence": 0.91,
            "quality": "GOOD",
            "format_status": "VALID_FORMAT",
            "vehicle_class": "PERSONAL_CAR",
            "vehicle_color": "WHITE",
            "vehicle_direction": "NORTH",
        },
    ],
    "CAM-12": [
        {
            "raw_read": "UP32GH0034",
            "normalized_read": "UP32GH0034",
            "display_read": "UP32GH0034",
            "confidence": 0.53,
            "quality": "LOW_LIGHT",
            "format_status": "VALID_FORMAT",
            "vehicle_class": "SUV",
            "vehicle_color": "BLACK",
            "vehicle_direction": "OUTBOUND",
        },
    ],
    "CAM-13": [
        {
            "raw_read": "DL8C__123",
            "normalized_read": None,
            "display_read": "DL8C__123",
            "confidence": 0.34,
            "quality": "PARTIAL",
            "format_status": "NOT_ENOUGH_DATA",
            "vehicle_class": "VAN",
            "vehicle_color": "BLUE",
            "vehicle_direction": "WEST",
        },
    ],
}

# Sequence counters per camera
_DEMO_SEQUENCES: dict[str, int] = {}


class DemoANPRProvider(ANPRProvider):
    """
    Deterministic demo ANPR provider — no real OCR model.

    Cycles through fixed plate fixtures per camera.
    Used for development, testing, and frontend development only.
    """

    _PROVIDER_NAME = "ANPR-DEMO"
    _PROVIDER_VERSION = "demo-1.0"

    def __init__(self) -> None:
        self._ready = False
        self._started_at: datetime | None = None
        self._last_update: datetime | None = None
        self._failure_count = 0
        self._total_recognitions = 0
        # Per-camera sequence index
        self._sequences: dict[str, int] = {}

    async def initialize(self) -> None:
        await asyncio.sleep(0)  # yield to event loop
        self._ready = True
        self._started_at = datetime.now(timezone.utc)
        logger.info("DemoANPRProvider initialized")

    def ready(self) -> bool:
        return self._ready

    async def recognize(
        self,
        sightings: list[VehicleSightingInput],
        camera_context: ANPRCameraContext,
    ) -> ANPRBatchResult:
        if not self._ready:
            raise RuntimeError("DemoANPRProvider.recognize() called before initialize()")

        start = time.monotonic()
        camera_id = camera_context.camera_id
        results: list[ANPRObservationResult] = []

        # Get plate fixtures for this camera
        fixtures = _DEMO_PLATES.get(camera_id, _DEMO_PLATES.get("CAM-07", []))
        if not self._sequences.get(camera_id):
            self._sequences[camera_id] = 0

        seq = self._sequences[camera_id]

        for sighting in sightings:
            # Use provided plate read if available, else cycle through fixtures
            if sighting.plate_read:
                plate_fixture = {
                    "raw_read": sighting.plate_read.raw_read,
                    "normalized_read": sighting.plate_read.normalized_read,
                    "display_read": sighting.plate_read.display_read,
                    "confidence": sighting.plate_read.confidence,
                    "quality": sighting.plate_read.quality,
                    "format_status": sighting.plate_read.format_status,
                    "vehicle_class": sighting.vehicle_class,
                    "vehicle_color": sighting.vehicle_color,
                    "vehicle_direction": sighting.vehicle_direction,
                }
            else:
                # Cycle through fixtures
                fixture = fixtures[seq % len(fixtures)]
                seq += 1
                plate_fixture = fixture

            # Create plate read input from fixture
            plate_read = PlateReadInput(
                raw_read=plate_fixture["raw_read"],
                normalized_read=plate_fixture.get("normalized_read"),
                display_read=plate_fixture["display_read"],
                confidence=plate_fixture["confidence"],
                quality=plate_fixture["quality"],
                format_status=plate_fixture["format_status"],
                observed_at=sighting.observed_at,
            )

            # TODO: In real implementation, this would create sighting + plate read + candidates
            # For demo, just return a result
            results.append(ANPRObservationResult(
                sighting_id=f"SGT-DEMO{self._sequences[camera_id]:04d}",
                vehicle_id=sighting.vehicle_id or f"VEH-DEMO{self._sequences[camera_id]:04d}",
                status="CREATED",
            ))

        elapsed_ms = int((time.monotonic() - start) * 1000)
        self._sequences[camera_id] = seq
        self._last_update = datetime.now(timezone.utc)
        self._total_recognitions += 1

        return ANPRBatchResult(
            camera_id=camera_id,
            processed_at=self._last_update,
            total_sightings=len(sightings),
            created=len(results),
            duplicates=0,
            errors=0,
            results=results,
            provider_name=self._PROVIDER_NAME,
            provider_version=self._PROVIDER_VERSION,
            processing_latency_ms=elapsed_ms,
        )

    async def flush(self, camera_id: str) -> ANPRBatchResult:
        return ANPRBatchResult(
            camera_id=camera_id,
            processed_at=datetime.now(timezone.utc),
            total_sightings=0,
            created=0,
            duplicates=0,
            errors=0,
            results=[],
            provider_name=self._PROVIDER_NAME,
            provider_version=self._PROVIDER_VERSION,
        )

    def health(self) -> ANPRProviderHealthInfo:
        return ANPRProviderHealthInfo(
            state="READY" if self._ready else "UNAVAILABLE",
            provider_name=self._PROVIDER_NAME,
            provider_version=self._PROVIDER_VERSION,
            last_successful_update=self._last_update,
            failure_count=self._failure_count,
            queue_depth=0,
            processing_latency_ms=None,
            cameras_active=len(_DEMO_SEQUENCES),
            note="DEMO provider — no real ANPR model active",
        )

    def metadata(self) -> ANPRProviderMetadata:
        return ANPRProviderMetadata(
            provider_name=self._PROVIDER_NAME,
            tracker_name=None,
            tracker_version=None,
            algorithm_version="demo-fixed-1.0",
            configuration_version="demo-default-1.0",
            description="Deterministic demo ANPR provider for development and testing. No production OCR model is active.",
            supported_vehicle_classes=list(VehicleClass.__args__),  # type: ignore
            supported_plate_formats=["VALID_FORMAT", "POSSIBLE_FORMAT", "INVALID_FORMAT", "UNKNOWN_FORMAT", "NOT_ENOUGH_DATA"],
            max_batch_size=50,
            supports_multi_frame=False,
            supports_character_confidence=False,
            supports_quality_assessment=True,
        )

    async def shutdown(self) -> None:
        self._ready = False
        logger.info("DemoANPRProvider shut down")