# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 7 — ANPR Service
#
# Main domain service coordinating:
#   · ANPRProvider (model-agnostic; actual OCR is external)
#   · VehicleSightingRepository (persistence)
#   · PlateReadRepository
#   · CameraHealthProvider (Component 2 — read-only context)
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.domain.camera_health.provider import get_camera_health_provider
from app.domain.anpr.constants import (
    ANPRSource,
    ANPRSyncState,
)
from app.domain.anpr.provider import (
    ANPRProvider,
    ANPRProviderUnavailableError,
    ANPRCameraContext,
    ANPRBatchResult,
    PlateReadInput,
    VehicleSightingInput,
    get_anpr_provider,
)
from app.repositories.anpr import (
    VehicleSightingRepository,
    PlateReadRepository,
    ANPRConfigRepository,
)

logger = get_logger("prhaar.anpr.service")


class ANPRServiceError(Exception):
    """Base error for ANPRService failures."""


class SightingNotFoundError(ANPRServiceError):
    def __init__(self, sighting_id: str) -> None:
        super().__init__(f"Sighting '{sighting_id}' not found.")
        self.sighting_id = sighting_id


class ANPRProviderUnavailableError(ANPRServiceError):
    def __init__(self, reason: str = "ANPR Provider is not ready.") -> None:
        super().__init__(reason)


class ANPRService:
    """
    Per-request ANPR domain service.

    Instantiate via FastAPI Depends():
        async def route(session: AsyncSession = Depends(get_db_session)):
            svc = ANPRService(session)
            ...
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.sighting_repo = VehicleSightingRepository(session)
        self.plate_read_repo = PlateReadRepository(session)
        self.config_repo = ANPRConfigRepository(session)

    # ── Provider access ───────────────────────────────────────────────────────

    def _get_provider(self) -> ANPRProvider:
        p = get_anpr_provider()
        if p is None:
            raise ANPRProviderUnavailableError("No ANPR Provider registered.")
        if not p.ready():
            raise ANPRProviderUnavailableError("ANPR Provider is not ready.")
        return p

    # ── Camera Health context (Component 2 — read-only) ───────────────────────

    async def _get_health_context(self, camera_id: str) -> dict[str, Any] | None:
        hp = get_camera_health_provider()
        if hp is None:
            return None
        try:
            return await hp.get_latest_health_context(camera_id)
        except Exception as exc:
            logger.warning("health_context_unavailable camera_id=%s error=%s", camera_id, exc)
            return None

    def _health_context_json(self, ctx: dict | None) -> str | None:
        if ctx is None:
            return None
        return str(ctx)  # Simplified; production would use JSON

    def _camera_context(
        self,
        camera_id: str,
        health: dict | None,
    ) -> ANPRCameraContext:
        return ANPRCameraContext(
            camera_id=camera_id,
            health_state=health.get("reliability") if health else None,
            health_reliability=health.get("reliability") if health else None,
            viewpoint_shift=bool(health.get("viewpoint_shift_detected")) if health else False,
        )

    # ── Core ingestion pipeline ───────────────────────────────────────────────

    async def ingest_sightings(
        self,
        camera_id: str,
        sightings: list,
        *,
        source: str = "LIVE",
        sector_id: str | None = None,
        zone_id: str | None = None,
    ) -> ANPRBatchResult:
        """
        Process a vehicle sighting batch through the ANPR provider → persistence pipeline.
        Commits on success. Raises ANPRProviderUnavailableError if provider is down.
        """
        provider = self._get_provider()
        health = await self._get_health_context(camera_id)
        health_json = self._health_context_json(health)
        ctx = self._camera_context(camera_id, health)

        # Convert to provider input format
        provider_inputs = []
        for s in sightings:
            # Build plate read input
            plate_read = None
            if s.plate_read:
                plate_read = PlateReadInput(
                    raw_read=s.plate_read.raw_read,
                    normalized_read=s.plate_read.normalized_read,
                    display_read=s.plate_read.display_read,
                    confidence=s.plate_read.confidence,
                    character_confidence=s.plate_read.character_confidence,
                    format_status=s.plate_read.format_status,
                    quality=s.plate_read.quality,
                    crop_reference=s.plate_read.crop_reference,
                    source_frame_ref=s.plate_read.source_frame_ref,
                    observed_at=s.plate_read.observed_at,
                    candidates=[
                        c for c in s.plate_read.candidates
                    ] if s.plate_read.candidates else [],
                )

            provider_inputs.append(VehicleSightingInput(
                camera_id=camera_id,
                observed_at=s.observed_at,
                received_at=s.received_at,
                vehicle_class=s.vehicle_class,
                vehicle_color=s.vehicle_color,
                vehicle_direction=s.vehicle_direction,
                track_id=s.track_id,
                detection_id=s.detection_id,
                vehicle_id=s.vehicle_id,
                plate_read=plate_read,
                confidence=s.confidence,
                detection_quality=s.detection_quality,
                camera_health_state=s.camera_health_state,
                camera_health_context_json=health_json,
                location_context=s.location_context,
                sector_id=s.sector_id,
                zone_id=s.zone_id,
                watchlist_status=s.watchlist_status,
                evidence_id=s.evidence_id,
                event_id=s.event_id,
                correlation_id=s.correlation_id,
                incident_id=s.incident_id,
                thumbnail_url=s.thumbnail_url,
                plate_crop_url=s.plate_crop_url,
                source_provider=s.source_provider,
                sync_payload_hash=s.sync_payload_hash,
                edge_device_id=s.edge_device_id,
            ))

        # Process through provider
        try:
            result = await provider.recognize(
                detections=provider_inputs,
                context=ctx,
            )
        except Exception as exc:
            logger.exception("anpr_recognition_failed camera_id=%s error=%s", camera_id, exc)
            raise ANPRProviderUnavailableError(f"ANPR recognition failed: {exc}") from exc

        # Persist results (sightings, plate reads, candidates)
        await self._persist_results(camera_id, result, source, sector_id, zone_id, health_json)

        # Commit the batch atomically
        await self.session.commit()
        return result

    async def _persist_results(
        self,
        camera_id: str,
        result: ANPRBatchResult,
        source: str,
        sector_id: str | None,
        zone_id: str | None,
        health_context_json: str | None,
    ) -> None:
        """Persist batch results to database."""
        # This would create VehicleSighting, PlateRead, PlateCandidate records
        # Implementation depends on the exact ANPRBatchResult structure
        # For now, placeholder
        logger.info(
            "anpr_batch_persisted camera_id=%s created=%d duplicates=%d errors=%d",
            camera_id, result.created, result.duplicates, result.errors
        )

    # ── Single sighting reads ──────────────────────────────────────────────────

    async def get_sighting(self, sighting_id: str):
        sighting = await self.sighting_repo.get(sighting_id)
        if sighting is None:
            raise SightingNotFoundError(sighting_id)
        return sighting

    # ── Camera sightings ──────────────────────────────────────────────────────

    async def get_camera_sightings(
        self,
        camera_id: str,
        *,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        status: str | None = None,
        quality: str | None = None,
        vehicle_class: str | None = None,
        direction: str | None = None,
        watchlist_status: str | None = None,
        limit: int = 100,
    ):
        return await self.sighting_repo.get_for_camera(
            camera_id,
            from_time=from_time,
            to_time=to_time,
            status=status,
            quality=quality,
            vehicle_class=vehicle_class,
            direction=direction,
            watchlist_status=watchlist_status,
            limit=limit,
        )

    async def get_camera_feed(
        self,
        camera_id: str,
        *,
        limit: int = 50,
    ):
        """Get camera feed with active sightings + provider state."""
        provider = get_anpr_provider()
        if provider is None:
            provider_health = "UNAVAILABLE"
            feed_state = "UNAVAILABLE"
        else:
            try:
                h = provider.health()
                provider_health = h.state
                feed_state = "READY" if h.state == "READY" else "DEGRADED"
            except Exception:
                provider_health = "UNKNOWN"
                feed_state = "UNKNOWN"

        sightings = await self.sighting_repo.get_for_camera(camera_id, limit=limit)

        last_updated = None
        if sightings:
            last_updated = max(
                (s.observed_at for s in sightings if s.observed_at), default=None
            )

        return {
            "camera_id": camera_id,
            "state": feed_state,
            "last_updated_at": last_updated.isoformat() if last_updated else None,
            "sightings": sightings,
            "provider_health": provider_health,
        }

    # ── Vehicle history (cross-camera) ────────────────────────────────────────

    async def get_vehicle_history(
        self,
        vehicle_id: str,
        *,
        limit: int = 200,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
    ):
        return await self.sighting_repo.get_vehicle_history(
            vehicle_id,
            limit=limit,
            from_time=from_time,
            to_time=to_time,
        )

    # ── Paginated list ────────────────────────────────────────────────────────

    async def list_sightings(
        self,
        *,
        camera_id: str | None = None,
        vehicle_id: str | None = None,
        track_id: str | None = None,
        detection_id: str | None = None,
        status: str | None = None,
        quality: str | None = None,
        vehicle_class: str | None = None,
        direction: str | None = None,
        watchlist_status: str | None = None,
        source: str | None = None,
        sector_id: str | None = None,
        zone_id: str | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        search: str | None = None,
        sort: str = "observed_at",
        order: str = "desc",
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list, int]:
        return await self.sighting_repo.list_sightings(
            camera_id=camera_id,
            vehicle_id=vehicle_id,
            track_id=track_id,
            detection_id=detection_id,
            status=status,
            quality=quality,
            vehicle_class=vehicle_class,
            direction=direction,
            watchlist_status=watchlist_status,
            source=source,
            sector_id=sector_id,
            zone_id=zone_id,
            from_time=from_time,
            to_time=to_time,
            search=search,
            sort=sort,
            order=order,
            page=page,
            page_size=page_size,
        )

    async def list_sightings_cursor(
        self,
        *,
        camera_id: str | None = None,
        vehicle_id: str | None = None,
        track_id: str | None = None,
        detection_id: str | None = None,
        status: str | None = None,
        quality: str | None = None,
        vehicle_class: str | None = None,
        direction: str | None = None,
        watchlist_status: str | None = None,
        source: str | None = None,
        sector_id: str | None = None,
        zone_id: str | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        search: str | None = None,
        sort: str = "observed_at",
        order: str = "desc",
        cursor: str | None = None,
        limit: int = 50,
    ):
        return await self.sighting_repo.list_sightings_cursor(
            camera_id=camera_id,
            vehicle_id=vehicle_id,
            track_id=track_id,
            detection_id=detection_id,
            status=status,
            quality=quality,
            vehicle_class=vehicle_class,
            direction=direction,
            watchlist_status=watchlist_status,
            source=source,
            sector_id=sector_id,
            zone_id=zone_id,
            from_time=from_time,
            to_time=to_time,
            search=search,
            sort=sort,
            order=order,
            cursor=cursor,
            limit=limit,
        )

    # ── Search ────────────────────────────────────────────────────────────────

    async def search_plates(
        self,
        query: str,
        *,
        camera_id: str | None = None,
        match_type: str | None = None,
        limit: int = 50,
    ):
        return await self.sighting_repo.search_plates(
            query,
            camera_id=camera_id,
            match_type=match_type,
            limit=limit,
        )

    # ── Camera summary ────────────────────────────────────────────────────────

    async def get_camera_summary(self, camera_id: str):
        return await self.sighting_repo.get_camera_summary(camera_id)

    # ── ANPR Summary (all cameras) ────────────────────────────────────────────

    async def get_summary(self):
        """Global ANPR summary across all cameras."""
        # This would aggregate across all cameras
        # For now, return empty structure
        return {
            "total_reads": 0,
            "readable_plates": 0,
            "partial_reads": 0,
            "unreadable_plates": 0,
            "unique_tracked_sightings": 0,
            "cameras_reporting": 0,
            "last_updated": None,
        }

    # ── ANPR Config ───────────────────────────────────────────────────────────

    async def get_config(self, camera_id: str):
        return await self.config_repo.get_by_camera(camera_id)

    # ── Provider health ───────────────────────────────────────────────────────

    def get_provider_health(self):
        provider = get_anpr_provider()
        if provider is None:
            return {
                "state": "UNAVAILABLE",
                "provider": "NONE",
                "provider_version": None,
                "tracker_name": None,
                "tracker_version": None,
                "last_successful_update": None,
                "failure_count": 0,
                "queue_depth": 0,
                "processing_latency_ms": None,
                "cameras_active": 0,
                "note": "No ANPR provider registered.",
            }
        h = provider.health()
        return {
            "state": h.state,
            "provider": h.provider_name,
            "provider_version": h.provider_version,
            "tracker_name": h.tracker_name,
            "tracker_version": h.tracker_version,
            "last_successful_update": h.last_successful_update.isoformat() if h.last_successful_update else None,
            "failure_count": h.failure_count,
            "queue_depth": h.queue_depth,
            "processing_latency_ms": h.processing_latency_ms,
            "cameras_active": h.cameras_active,
            "note": h.note,
        }