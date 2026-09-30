# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 7 — DemoANPRProvider
#
# Deterministic demo provider — no real OCR, fixed fixtures for testing.
#
# Scenarios covered (spec §29): clear plate · low confidence · multiple
# candidates · partial read · unreadable plate · night (LOW_LIGHT) · glare.
#
# The provider produces the final plate observation payload
# (PlateReadInput + candidates) that the service persists. It never writes
# to the database directly.
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
    PlateCandidateInput,
    PlateReadInput,
    VehicleSightingInput,
)

logger = get_logger("prhaar.anpr.demo_provider")

# ─────────────────────────────────────────────────────────────────────────────
# Fixed demo plate fixtures — deterministic, never random
#
# A fixture with "raw_read": None represents an UNREADABLE observation
# (no plate read produced). "candidates" carries the deterministic OCR
# candidate list; rank is derived from list order (1-based).
# ─────────────────────────────────────────────────────────────────────────────

_DEMO_PLATES: dict[str, list[dict[str, Any]]] = {
    # Camera -> list of plate fixtures
    "CAM-07": [
        # Clear plate, high confidence — multiple candidates (ambiguous digit)
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
            "candidates": [
                {"raw_read": "HR26AK4521", "normalized_read": "HR26AK4521", "confidence": 0.92, "format_status": "VALID_FORMAT"},
                {"raw_read": "HR26AK452I", "normalized_read": "HR26AK452I", "confidence": 0.61, "format_status": "POSSIBLE_FORMAT"},
            ],
        },
        # Ambiguous trailing character — low confidence with alternative candidate
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
            "candidates": [
                {"raw_read": "HR26AK452I", "normalized_read": "HR26AK452I", "confidence": 0.61, "format_status": "POSSIBLE_FORMAT"},
                {"raw_read": "HR26AK4521", "normalized_read": "HR26AK4521", "confidence": 0.44, "format_status": "POSSIBLE_FORMAT"},
            ],
        },
        # Clear plate, SUV
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
            "candidates": [
                {"raw_read": "GJ01BV2209", "normalized_read": "GJ01BV2209", "confidence": 0.87, "format_status": "VALID_FORMAT"},
            ],
        },
        # Unreadable — no plate read produced (night motorcycle)
        {
            "raw_read": None,
            "vehicle_class": "MOTORCYCLE",
            "vehicle_color": "BLACK",
            "vehicle_direction": "NORTH",
        },
    ],
    "CAM-08": [
        # Low-confidence OCR, possible character confusion
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
            "candidates": [
                {"raw_read": "MP09CD7731", "normalized_read": "MP09CD7731", "confidence": 0.48, "format_status": "POSSIBLE_FORMAT"},
                {"raw_read": "MP09C07731", "normalized_read": None, "confidence": 0.31, "format_status": "INVALID_FORMAT"},
            ],
        },
        # Same plate seen on second camera (multi-camera demo)
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
            "candidates": [
                {"raw_read": "HR26AK4521", "normalized_read": "HR26AK4521", "confidence": 0.89, "format_status": "VALID_FORMAT"},
            ],
        },
        # Glare scenario — plate partially compromised by glare
        {
            "raw_read": "PB10GR7788",
            "normalized_read": "PB10GR7788",
            "display_read": "PB10GR7788",
            "confidence": 0.42,
            "quality": "GLARE",
            "format_status": "POSSIBLE_FORMAT",
            "vehicle_class": "TRUCK",
            "vehicle_color": "WHITE",
            "vehicle_direction": "SOUTH",
            "candidates": [
                {"raw_read": "PB10GR7788", "normalized_read": "PB10GR7788", "confidence": 0.42, "format_status": "POSSIBLE_FORMAT"},
            ],
        },
    ],
    "CAM-09": [
        # O/0 ambiguity — multiple candidates (spec §5 example)
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
            "candidates": [
                {"raw_read": "RJ14AB1O52", "normalized_read": "RJ14AB1052", "confidence": 0.91, "format_status": "POSSIBLE_FORMAT"},
                {"raw_read": "RJ14AB1062", "normalized_read": "RJ14AB1062", "confidence": 0.66, "format_status": "POSSIBLE_FORMAT"},
                {"raw_read": "RJ14AB105Z", "normalized_read": None, "confidence": 0.43, "format_status": "INVALID_FORMAT"},
            ],
        },
        # Clear bus plate
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
            "candidates": [
                {"raw_read": "MH43AA8801", "normalized_read": "MH43AA8801", "confidence": 0.78, "format_status": "VALID_FORMAT"},
                {"raw_read": "MH43AA8B01", "normalized_read": None, "confidence": 0.52, "format_status": "INVALID_FORMAT"},
            ],
        },
    ],
    "CAM-11": [
        # Motion blur — low confidence truck
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
            "candidates": [
                {"raw_read": "DL1LT7821", "normalized_read": "DL1LT7821", "confidence": 0.61, "format_status": "VALID_FORMAT"},
                {"raw_read": "DL1LT782I", "normalized_read": None, "confidence": 0.39, "format_status": "INVALID_FORMAT"},
            ],
        },
        # Same plate on third camera (multi-camera demo)
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
            "candidates": [
                {"raw_read": "HR26AK4521", "normalized_read": "HR26AK4521", "confidence": 0.91, "format_status": "VALID_FORMAT"},
            ],
        },
    ],
    "CAM-12": [
        # Night scene — LOW_LIGHT quality
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
            "candidates": [
                {"raw_read": "UP32GH0034", "normalized_read": "UP32GH0034", "confidence": 0.53, "format_status": "VALID_FORMAT"},
            ],
        },
    ],
    "CAM-13": [
        # Partial plate — not enough data to normalize
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
            "candidates": [
                {"raw_read": "DL8C__123", "normalized_read": None, "confidence": 0.34, "format_status": "NOT_ENOUGH_DATA"},
            ],
        },
    ],
}

# Fallback fixture set for unknown cameras (keeps demo usable with arbitrary IDs)
_DEFAULT_FIXTURES = _DEMO_PLATES["CAM-07"]


def _camera_token(camera_id: str) -> str:
    """Short camera token for demo ID generation (CAM-07 → 07)."""
    return camera_id.replace("CAM-", "").strip("-") or "00"


def _plate_token(plate: str | None) -> str | None:
    """Alphanumeric plate token for demo vehicle grouping (demo use only)."""
    if not plate:
        return None
    token = "".join(ch for ch in plate.upper() if ch.isalnum())
    return token or None


class DemoANPRProvider(ANPRProvider):
    """
    Deterministic demo ANPR provider — no real OCR model.

    Cycles through fixed plate fixtures per camera and produces the final
    plate observation payload (read + candidates) for each sighting.
    Used for development, testing, and frontend development only.

    NOTE: No production OCR model is active. Vehicle grouping below is a
    demo-only plate-linked convenience; real vehicle identity resolution
    is a separate AI/ML phase.
    """

    _PROVIDER_NAME = "ANPR-DEMO"
    _PROVIDER_VERSION = "demo-1.0"

    def __init__(self) -> None:
        self._ready = False
        self._started_at: datetime | None = None
        self._last_update: datetime | None = None
        self._failure_count = 0
        self._total_recognitions = 0
        # Per-camera observation sequence (increments for every sighting)
        self._sequences: dict[str, int] = {}
        # Cameras that have actually produced observations (real health signal)
        self._cameras_seen: set[str] = set()

    async def initialize(self) -> None:
        await asyncio.sleep(0)  # yield to event loop
        self._ready = True
        self._started_at = datetime.now(timezone.utc)
        logger.info("DemoANPRProvider initialized")

    def ready(self) -> bool:
        return self._ready

    # ── Fixture → payload ─────────────────────────────────────────────────────

    def _plate_read_from_fixture(
        self,
        fixture: dict[str, Any],
        sighting: VehicleSightingInput,
    ) -> PlateReadInput | None:
        """
        Build the plate observation payload for a fixture.
        Returns None for the UNREADABLE scenario (no plate read produced).
        """
        raw = fixture.get("raw_read")
        if raw is None:
            return None  # UNREADABLE — no plate read

        candidates_raw = fixture.get("candidates") or [
            {
                "raw_read": raw,
                "normalized_read": fixture.get("normalized_read"),
                "confidence": fixture["confidence"],
                "format_status": fixture.get("format_status", "UNKNOWN_FORMAT"),
            }
        ]
        candidates = [
            PlateCandidateInput(
                rank=i,
                raw_read=c["raw_read"],
                normalized_read=c.get("normalized_read"),
                confidence=c["confidence"],
                character_confidence=c.get("character_confidence"),
                format_status=c.get("format_status", "UNKNOWN_FORMAT"),
            )
            for i, c in enumerate(candidates_raw, start=1)
        ]

        return PlateReadInput(
            raw_read=raw,
            normalized_read=fixture.get("normalized_read"),
            display_read=fixture.get("display_read") or raw,
            confidence=fixture["confidence"],
            quality=fixture.get("quality", "UNKNOWN"),
            format_status=fixture.get("format_status", "UNKNOWN_FORMAT"),
            observed_at=sighting.observed_at,
            candidates=candidates,
        )

    # ── Recognition ───────────────────────────────────────────────────────────

    async def recognize(
        self,
        sightings: list[VehicleSightingInput],
        camera_context: ANPRCameraContext,
    ) -> ANPRBatchResult:
        if not self._ready:
            raise RuntimeError("DemoANPRProvider.recognize() called before initialize()")

        start = time.monotonic()
        camera_id = camera_context.camera_id
        fixtures = _DEMO_PLATES.get(camera_id, _DEFAULT_FIXTURES)
        seq = self._sequences.get(camera_id, 0)
        self._cameras_seen.add(camera_id)

        results: list[ANPRObservationResult] = []
        cam_token = _camera_token(camera_id)

        for sighting in sightings:
            seq += 1  # per-observation sequence — unique within and across batches

            if sighting.plate_read:
                # Caller supplied a plate read — pass through unchanged
                # (raw_read preserved; candidates carried over if present)
                plate_read: PlateReadInput | None = PlateReadInput(
                    raw_read=sighting.plate_read.raw_read,
                    normalized_read=sighting.plate_read.normalized_read,
                    display_read=sighting.plate_read.display_read,
                    confidence=sighting.plate_read.confidence,
                    character_confidence=sighting.plate_read.character_confidence,
                    format_status=sighting.plate_read.format_status,
                    quality=sighting.plate_read.quality,
                    crop_reference=sighting.plate_read.crop_reference,
                    source_frame_ref=sighting.plate_read.source_frame_ref,
                    observed_at=sighting.plate_read.observed_at,
                    candidates=list(sighting.plate_read.candidates or []),
                )
            else:
                fixture = fixtures[(seq - 1) % len(fixtures)] if fixtures else None
                plate_read = self._plate_read_from_fixture(fixture, sighting) if fixture else None

            sighting_id = sighting.sighting_id or f"SGT-DEMO-{cam_token}-{seq:04d}"

            # Demo-only plate-linked vehicle grouping: sightings that share a
            # readable plate token resolve to the same demo vehicle entity.
            vehicle_id = sighting.vehicle_id
            if vehicle_id is None and plate_read is not None:
                token = _plate_token(plate_read.normalized_read or plate_read.raw_read)
                vehicle_id = f"VEH-DEMO-{token}" if token else None

            results.append(ANPRObservationResult(
                sighting_id=sighting_id,
                vehicle_id=vehicle_id,
                status="CREATED",
                plate_read=plate_read,
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
            cameras_active=len(self._cameras_seen),
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
