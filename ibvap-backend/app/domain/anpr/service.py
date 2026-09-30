# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 7 — ANPR Service
#
# Main domain service coordinating:
#   · ANPRProvider (model-agnostic; actual OCR is external)
#   · VehicleSightingRepository / PlateReadRepository / ANPRConfigRepository
#   · CameraHealthProvider (Component 2 — read-only context)
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.domain.camera_health.provider import get_camera_health_provider
from app.domain.anpr.constants import normalize_vehicle_class
from app.domain.anpr.provider import (
    ANPRProvider,
    ANPRCameraContext,
    ANPRBatchResult,
    ANPRObservationResult,
    VehicleSightingInput,
    get_anpr_provider,
)
from app.models.anpr import VehicleSighting, PlateRead, PlateCandidate
from app.repositories.anpr import (
    VehicleSightingRepository,
    PlateReadRepository,
    ANPRConfigRepository,
)

logger = get_logger("prhaar.anpr.service")


def _iso_utc(dt: datetime | None) -> str | None:
    """ISO-8601 with explicit UTC offset (SQLite returns naive datetimes)."""
    if dt is None:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.isoformat()


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
        """Serialize the C2 health snapshot for storage on the sighting."""
        if ctx is None:
            return None
        try:
            return json.dumps(ctx, default=str)
        except (TypeError, ValueError):
            return None

    def _camera_context(
        self,
        camera_id: str,
        health: dict | None,
    ) -> ANPRCameraContext:
        # Component 2 health context exposes reliability / viewpoint shift —
        # there is no "health_state" key, so we do not invent one.
        return ANPRCameraContext(
            camera_id=camera_id,
            health_state=None,
            health_reliability=health.get("reliability") if health else None,
            viewpoint_shift=bool(health.get("viewpoint_shift_detected")) if health else False,
        )

    # ── Core ingestion pipeline ───────────────────────────────────────────────

    async def ingest_sightings(
        self,
        camera_id: str,
        sightings: list[VehicleSightingInput],
        *,
        source: str = "LIVE",
        sector_id: str | None = None,
        zone_id: str | None = None,
    ) -> ANPRBatchResult:
        """
        Process a vehicle sighting batch through the ANPR provider → persistence
        pipeline. Commits on success. Raises ANPRProviderUnavailableError if the
        provider is down or not ready.
        """
        provider = self._get_provider()
        health = await self._get_health_context(camera_id)
        health_json = self._health_context_json(health)
        ctx = self._camera_context(camera_id, health)

        # Enrich inputs with the camera-health snapshot. Caller-supplied values
        # win; the snapshot only fills gaps.
        for inp in sightings:
            if not inp.camera_id:
                inp.camera_id = camera_id
            if inp.camera_health_context_json is None and health_json is not None:
                inp.camera_health_context_json = health_json

        try:
            result = await provider.recognize(
                sightings=sightings,
                camera_context=ctx,
            )
        except Exception as exc:
            logger.exception("anpr_recognition_failed camera_id=%s error=%s", camera_id, exc)
            raise ANPRProviderUnavailableError(f"ANPR recognition failed: {exc}") from exc

        # Persist results (sightings, plate reads, candidates)
        await self._persist_results(camera_id, sightings, result, source, sector_id, zone_id)

        # Commit the batch atomically. A concurrent ingest may have committed
        # overlapping rows first (the unique sighting / detection+track / sync
        # keys are the arbitration point) — roll back and reclassify against
        # the committed data instead of surfacing a UNIQUE violation as a 500.
        for attempt in range(2):
            try:
                await self.session.commit()
                break
            except IntegrityError:
                await self.session.rollback()
                if attempt == 1:
                    raise
                logger.warning(
                    "anpr_ingest_concurrent_conflict camera_id=%s — reclassifying against committed rows",
                    camera_id,
                )
                await self._persist_results(
                    camera_id, sightings, result, source, sector_id, zone_id
                )
        return result

    async def _persist_results(
        self,
        camera_id: str,
        inputs: list[VehicleSightingInput],
        result: ANPRBatchResult,
        source: str,
        sector_id: str | None,
        zone_id: str | None,
    ) -> None:
        """Persist provider results (sightings, plate reads, candidates).

        Idempotency — re-ingesting the same observation must never duplicate a
        sighting and must never overwrite a stored raw plate read:
          · within this batch — sighting ID / detection+track / sync hash
          · against the database — same three keys

        The provider's per-sighting status is replaced with the real DB outcome
        (CREATED | DUPLICATE | ERROR) and batch counters are recomputed from
        those outcomes, so the response can never overstate what was written.
        """
        if len(result.results) != len(inputs):
            logger.warning(
                "anpr_result_count_mismatch camera_id=%s inputs=%d results=%d",
                camera_id, len(inputs), len(result.results),
            )

        created = duplicates = errors = 0
        seen_ids: set[str] = set()
        seen_det_track: set[tuple[str, str]] = set()
        seen_hashes: set[str] = set()

        for idx, inp in enumerate(inputs):
            obs: ANPRObservationResult | None = (
                result.results[idx] if idx < len(result.results) else None
            )
            if obs is None:
                # Provider returned fewer observations than inputs — count the
                # gap as an error instead of silently dropping the sighting.
                errors += 1
                continue
            if obs.status == "ERROR":
                errors += 1
                continue

            sighting_id = (obs.sighting_id or inp.sighting_id or "").strip()
            det_track_key = (
                (inp.detection_id, inp.track_id)
                if inp.detection_id and inp.track_id
                else None
            )

            # Idempotency — within this batch
            if sighting_id and sighting_id in seen_ids:
                obs.status = "DUPLICATE"
                duplicates += 1
                continue
            if det_track_key and det_track_key in seen_det_track:
                obs.status = "DUPLICATE"
                duplicates += 1
                continue
            if inp.sync_payload_hash and inp.sync_payload_hash in seen_hashes:
                obs.status = "DUPLICATE"
                duplicates += 1
                continue

            # Idempotency — already persisted. Autoflush is deferred while
            # these lookups run: a concurrent overlapping batch must surface
            # at commit (where the retry reconciles), not as a mid-loop
            # UNIQUE violation triggered by flushing this batch's own inserts.
            existing = None
            with self.session.no_autoflush:
                if sighting_id:
                    existing = await self.sighting_repo.get(sighting_id)
                if existing is None and det_track_key:
                    existing = await self.sighting_repo.get_by_detection_track_frame(*det_track_key)
                if existing is None and inp.sync_payload_hash:
                    existing = await self.sighting_repo.get_by_provider_observation_id(
                        inp.sync_payload_hash
                    )

            if existing is not None:
                obs.status = "DUPLICATE"
                obs.sighting_id = existing.sighting_id
                obs.vehicle_id = obs.vehicle_id or existing.vehicle_id
                duplicates += 1
                seen_ids.add(existing.sighting_id)
                if det_track_key:
                    seen_det_track.add(det_track_key)
                if inp.sync_payload_hash:
                    seen_hashes.add(inp.sync_payload_hash)
                continue

            final_sid = sighting_id or f"SGT-{uuid4().hex[:8].upper()}"
            self._create_sighting_records(final_sid, inp, obs, result, source, sector_id, zone_id)

            obs.status = "CREATED"
            obs.sighting_id = final_sid
            if obs.vehicle_id is None:
                obs.vehicle_id = inp.vehicle_id
            created += 1
            seen_ids.add(final_sid)
            if det_track_key:
                seen_det_track.add(det_track_key)
            if inp.sync_payload_hash:
                seen_hashes.add(inp.sync_payload_hash)

        result.created = created
        result.duplicates = duplicates
        result.errors = errors
        result.total_sightings = len(inputs)
        logger.info(
            "anpr_batch_persisted camera_id=%s created=%d duplicates=%d errors=%d",
            camera_id, created, duplicates, errors,
        )

    def _create_sighting_records(
        self,
        sighting_id: str,
        inp: VehicleSightingInput,
        obs: ANPRObservationResult,
        result: ANPRBatchResult,
        source: str,
        sector_id: str | None,
        zone_id: str | None,
    ) -> None:
        """Create the VehicleSighting (+ PlateRead + candidates) for one input."""
        sighting = VehicleSighting(
            sighting_id=sighting_id,
            camera_id=inp.camera_id,
            observed_at=inp.observed_at,
            received_at=inp.received_at or datetime.now(timezone.utc),
            # C7 §10 — only canonical classes are persisted; caller vocabulary
            # (e.g. "CAR") is normalized at this boundary, not stored raw.
            vehicle_class=normalize_vehicle_class(inp.vehicle_class),
            vehicle_color=inp.vehicle_color,
            vehicle_direction=inp.vehicle_direction or "UNKNOWN",
            track_id=inp.track_id,
            detection_id=inp.detection_id,
            vehicle_id=obs.vehicle_id or inp.vehicle_id,
            confidence=inp.confidence,
            detection_quality=inp.detection_quality,
            camera_health_state=inp.camera_health_state,
            camera_health_context_json=inp.camera_health_context_json,
            location_context=inp.location_context,
            sector_id=inp.sector_id or sector_id,
            zone_id=inp.zone_id or zone_id,
            watchlist_status=inp.watchlist_status or "NOT_CHECKED",
            evidence_id=inp.evidence_id,
            event_id=inp.event_id,
            correlation_id=inp.correlation_id,
            incident_id=inp.incident_id,
            thumbnail_url=inp.thumbnail_url,
            plate_crop_url=inp.plate_crop_url,
            provider=result.provider_name or inp.source_provider,
            provider_version=result.provider_version,
            source=source,
            sync_payload_hash=inp.sync_payload_hash,
            edge_device_id=inp.edge_device_id,
        )
        self.session.add(sighting)

        # Plate observation — the provider's final read wins over the caller's
        # input payload. Raw read is stored as-is and never rewritten later.
        payload = obs.plate_read or inp.plate_read
        if payload is None:
            return

        plate_read_id = f"PRD-{uuid4().hex[:8].upper()}"
        self.session.add(PlateRead(
            plate_read_id=plate_read_id,
            sighting_id=sighting_id,
            raw_read=payload.raw_read,
            normalized_read=payload.normalized_read,
            display_read=payload.display_read or payload.raw_read,
            confidence=payload.confidence,
            character_confidence=(
                json.dumps(payload.character_confidence)
                if payload.character_confidence else None
            ),
            format_status=payload.format_status or "UNKNOWN_FORMAT",
            quality=payload.quality or "UNKNOWN",
            crop_reference=payload.crop_reference,
            source_frame_ref=payload.source_frame_ref,
            observed_at=payload.observed_at or inp.observed_at,
            provider=result.provider_name,
            provider_version=result.provider_version,
        ))
        sighting.plate_read_id = plate_read_id
        sighting.plate_quality = payload.quality or "UNKNOWN"

        # Candidates — preserve every interpretation the provider produced.
        for position, cand in enumerate(payload.candidates or [], start=1):
            self.session.add(PlateCandidate(
                candidate_id=f"PCAND-{uuid4().hex[:8].upper()}",
                sighting_id=sighting_id,
                plate_read_id=plate_read_id,
                rank=cand.rank or position,
                raw_read=cand.raw_read,
                normalized_read=cand.normalized_read,
                confidence=cand.confidence,
                character_confidence=(
                    json.dumps(cand.character_confidence)
                    if cand.character_confidence else None
                ),
                format_status=cand.format_status or "UNKNOWN_FORMAT",
            ))

    # ── Single sighting reads ─────────────────────────────────────────────────

    async def get_sighting(self, sighting_id: str):
        sighting = await self.sighting_repo.get(sighting_id)
        if sighting is None:
            raise SightingNotFoundError(sighting_id)
        return sighting

    # ── Recent sightings (all cameras) ────────────────────────────────────────

    async def get_recent_sightings(self, *, limit: int = 100):
        return await self.sighting_repo.get_recent(limit=limit)

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
            "last_updated_at": _iso_utc(last_updated),
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
        confidence_min: float | None = None,
        confidence_max: float | None = None,
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
            confidence_min=confidence_min,
            confidence_max=confidence_max,
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
        confidence_min: float | None = None,
        confidence_max: float | None = None,
        search: str | None = None,
        sort: str = "observed_at",
        order: str = "desc",
        cursor: str | None = None,
        limit: int = 50,
    ) -> tuple[list, bool, str | None]:
        """Cursor pagination. Returns (rows, has_more, next_cursor).

        Raises ValueError for a malformed cursor or cursor + unsupported sort;
        the API layer maps that to INVALID_CURSOR.
        """
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
            confidence_min=confidence_min,
            confidence_max=confidence_max,
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
        """Global ANPR summary across all cameras (spec §26 plate-observation counts)."""
        return await self.sighting_repo.get_summary()

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
            "last_successful_update": _iso_utc(h.last_successful_update),
            "failure_count": h.failure_count,
            "queue_depth": h.queue_depth,
            "processing_latency_ms": h.processing_latency_ms,
            "cameras_active": h.cameras_active,
            "note": h.note,
        }
