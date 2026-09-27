# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 6 — TrackingService
#
# Main domain service that coordinates:
#   · TrackingProvider (model-agnostic; actual algorithm is external)
#   · TrackLifecycleService (state machine)
#   · TrackAssociationService (detection → track pipeline)
#   · TrackRepositoryV2 (queries)
#   · TrackObservationRepository (observation queries)
#   · CameraHealthProvider (Component 2 — read-only context)
#
# This service is instantiated per-request (not a singleton) so it inherits
# the request-scoped DB session from FastAPI's Depends() mechanism.
#
# What this service does NOT do:
#   · Run the actual tracker algorithm (that is the provider's job)
#   · Create Events / Correlations / Incidents / Evidence
#   · Compute risk scores
#   · Make identity claims
#   · Query Component 2/3/4/5 tables directly
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.domain.camera_health.provider import get_camera_health_provider
from app.domain.tracking.association import AssociationBatchResult, TrackAssociationService
from app.domain.tracking.constants import (
    CANDIDATE_POSSIBLE_CONTINUATION,
    CANDIDATE_POSSIBLE_SAME_ENTITY,
    TRACK_STATUS_ACTIVE,
    TRACK_STATUS_ENDED,
    TRACK_STATUS_INVALID,
    TRACK_STATUS_LOST,
    TRACK_STATUS_STALE,
    TRACK_STATUSES_ACTIVE_SET,
)
from app.domain.tracking.lifecycle import TrackLifecycleService
from app.domain.tracking.provider import (
    CameraContext,
    DetectionInput,
    ProviderHealthInfo,
    ProviderMetadata,
    TrackingProvider,
    get_tracking_provider,
)
from app.models.tracking import TrackCandidate, TrackingConfig, TrackV2
from app.repositories.tracking import TrackObservationRepository, TrackRepositoryV2

logger = get_logger("prhaar.tracking.service")


class TrackingServiceError(Exception):
    """Base error for TrackingService failures."""


class TrackNotFoundError(TrackingServiceError):
    def __init__(self, track_id: str) -> None:
        super().__init__(f"Track '{track_id}' not found.")
        self.track_id = track_id


class ProviderUnavailableError(TrackingServiceError):
    def __init__(self, reason: str = "Provider is not ready.") -> None:
        super().__init__(reason)


class TrackingService:
    """
    Per-request tracking domain service.

    Instantiate via FastAPI Depends():
        async def route(session: AsyncSession = Depends(get_db_session)):
            svc = TrackingService(session)
            ...
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.track_repo = TrackRepositoryV2(session)
        self.obs_repo = TrackObservationRepository(session)
        self.lifecycle = TrackLifecycleService(session)

    # ── Provider access ───────────────────────────────────────────────────────

    def _get_provider(self) -> TrackingProvider:
        p = get_tracking_provider()
        if p is None:
            raise ProviderUnavailableError("No TrackingProvider registered.")
        if not p.ready():
            raise ProviderUnavailableError("TrackingProvider is not ready.")
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
        snapshot = {
            "state":          ctx.get("reliability"),        # state proxy
            "reliability":    ctx.get("reliability"),
            "viewpoint_shift": ctx.get("viewpoint_shift_detected", False),
            "captured_at":    ctx.get("last_updated"),
        }
        return json.dumps(snapshot)

    def _camera_context(
        self,
        camera_id: str,
        health: dict | None,
    ) -> CameraContext:
        return CameraContext(
            camera_id=camera_id,
            health_state=health.get("reliability") if health else None,
            health_reliability=health.get("reliability") if health else None,
            viewpoint_shift=bool(health.get("viewpoint_shift_detected")) if health else False,
        )

    # ── Core ingestion pipeline ───────────────────────────────────────────────

    async def ingest_detections(
        self,
        camera_id: str,
        detections: list[DetectionInput],
        *,
        source: str = "LIVE",
        sector_id: str | None = None,
        region_profile: str | None = None,
    ) -> AssociationBatchResult:
        """
        Process a detection batch through the provider → track pipeline.
        Commits on success. Raises ProviderUnavailableError if provider is down.
        """
        provider = self._get_provider()
        health = await self._get_health_context(camera_id)
        health_json = self._health_context_json(health)
        ctx = self._camera_context(camera_id, health)

        assoc = TrackAssociationService(
            provider=provider,
            session=self.session,
            lifecycle=self.lifecycle,
        )

        result = await assoc.process_detections(
            detections=detections,
            context=ctx,
            source=source,
            sector_id=sector_id,
            region_profile=region_profile,
            health_context_json=health_json,
        )

        # Commit the batch atomically
        await self.session.commit()
        return result

    # ── Single track reads ────────────────────────────────────────────────────

    async def get_track(self, track_id: str) -> TrackV2:
        track = await self.track_repo.get(track_id)
        if track is None:
            raise TrackNotFoundError(track_id)
        return track

    # ── Camera track queries ──────────────────────────────────────────────────

    async def get_active_tracks(self, camera_id: str) -> list[TrackV2]:
        return await self.track_repo.get_active_for_camera(camera_id)

    async def get_recent_tracks(
        self, camera_id: str, *, since: datetime | None = None, limit: int = 50
    ) -> list[TrackV2]:
        return await self.track_repo.get_recent_for_camera(
            camera_id, since=since, limit=limit
        )

    async def get_all_active_tracks(self) -> list[TrackV2]:
        return await self.track_repo.get_all_active()

    # ── Paginated list ────────────────────────────────────────────────────────

    async def list_tracks(
        self,
        *,
        camera_id: str | None = None,
        status: str | None = None,
        object_class: str | None = None,
        source: str | None = None,
        sector_id: str | None = None,
        region_profile: str | None = None,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        search: str | None = None,
        sort: str = "last_seen",
        order: str = "desc",
        page: int = 1,
        page_size: int = 20,
    ) -> tuple[list[TrackV2], int]:
        return await self.track_repo.list_tracks(
            camera_id=camera_id,
            status=status,
            object_class=object_class,
            source=source,
            sector_id=sector_id,
            region_profile=region_profile,
            from_time=from_time,
            to_time=to_time,
            search=search,
            sort=sort,
            order=order,
            page=page,
            page_size=page_size,
        )

    # ── Camera summary ────────────────────────────────────────────────────────

    async def get_camera_summary(self, camera_id: str) -> dict[str, Any]:
        return await self.track_repo.get_camera_summary(camera_id)

    # ── Track feed (for frontend) ─────────────────────────────────────────────

    async def get_track_feed(self, camera_id: str) -> dict[str, Any]:
        """Returns TrackingFeed shape matching the locked frontend contract."""
        provider = get_tracking_provider()
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

        tracks = await self.track_repo.get_active_for_camera(camera_id)

        last_updated = None
        if tracks:
            last_updated = max(
                (t.last_seen_at for t in tracks if t.last_seen_at), default=None
            )

        return {
            "camera_id": camera_id,
            "state": feed_state,
            "last_updated_at": last_updated.isoformat() if last_updated else None,
            "tracks": tracks,
            "provider_health": provider_health,
        }

    # ── Observations ──────────────────────────────────────────────────────────

    async def get_track_observations(
        self,
        track_id: str,
        *,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        page: int = 1,
        page_size: int = 50,
    ):
        # Verify track exists
        await self.get_track(track_id)
        return await self.obs_repo.list_for_track(
            track_id,
            from_time=from_time,
            to_time=to_time,
            page=page,
            page_size=page_size,
        )

    async def get_trajectory(
        self,
        track_id: str,
        *,
        from_time: datetime | None = None,
        to_time: datetime | None = None,
        max_points: int = 200,
    ):
        await self.get_track(track_id)
        return await self.obs_repo.get_trajectory_points(
            track_id, from_time=from_time, to_time=to_time, max_points=max_points
        )

    # ── Track history ─────────────────────────────────────────────────────────

    async def get_track_history(
        self,
        track_id: str,
        *,
        page: int = 1,
        page_size: int = 50,
    ):
        await self.get_track(track_id)
        limit = min(page_size, 200)
        offset = (max(page, 1) - 1) * limit
        return await self.track_repo.get_track_history(track_id, limit=limit, offset=offset)

    # ── Cross-camera candidates ───────────────────────────────────────────────

    async def get_track_candidates(self, track_id: str) -> list[TrackCandidate]:
        await self.get_track(track_id)
        return await self.track_repo.get_candidates(track_id)

    async def create_candidate(
        self,
        *,
        source_track_id: str,
        target_camera_id: str,
        candidate_track_id: str | None = None,
        relation_type: str = CANDIDATE_POSSIBLE_CONTINUATION,
        strength: float | None = None,
        reason: str | None = None,
        provider: str | None = None,
        gap_duration_sec: float | None = None,
        expires_at: datetime | None = None,
    ) -> TrackCandidate:
        """
        Record a cross-camera continuation hypothesis.
        Never implies identity — only POSSIBLE_CONTINUATION or POSSIBLE_SAME_ENTITY.
        """
        if relation_type not in {
            CANDIDATE_POSSIBLE_CONTINUATION, CANDIDATE_POSSIBLE_SAME_ENTITY
        }:
            raise ValueError(f"Invalid relation_type: {relation_type}")

        cand = TrackCandidate(
            source_track_id=source_track_id,
            target_camera_id=target_camera_id,
            candidate_track_id=candidate_track_id,
            relation_type=relation_type,
            strength=strength,
            reason=reason,
            status="OPEN",
            source="SYSTEM",
            provider=provider,
            gap_duration_sec=gap_duration_sec,
            expires_at=expires_at,
        )
        self.session.add(cand)
        await self.session.commit()
        return cand

    # ── Provider health ───────────────────────────────────────────────────────

    def get_provider_health(self) -> dict[str, Any]:
        provider = get_tracking_provider()
        if provider is None:
            return {
                "state": "UNAVAILABLE",
                "provider": "NONE",
                "provider_version": None,
                "last_successful_update": None,
                "failure_count": 0,
                "queue_depth": 0,
                "processing_latency_ms": None,
                "cameras_active": 0,
                "note": "No TrackingProvider registered.",
            }
        try:
            h: ProviderHealthInfo = provider.health()
            m: ProviderMetadata = provider.metadata()
            return {
                "state": h.state,
                "provider": h.provider_name,
                "provider_version": h.provider_version,
                "tracker_name": m.tracker_name,
                "tracker_version": m.tracker_version,
                "last_successful_update": (
                    h.last_successful_update.isoformat()
                    if h.last_successful_update else None
                ),
                "failure_count": h.failure_count,
                "queue_depth": h.queue_depth,
                "processing_latency_ms": h.processing_latency_ms,
                "cameras_active": h.cameras_active,
                "note": h.note,
            }
        except Exception as exc:
            logger.exception("provider_health_error: %s", exc)
            return {"state": "UNKNOWN", "provider": "ERROR", "note": str(exc)}

    # ── Stale track management ────────────────────────────────────────────────

    async def mark_stale_tracks(
        self,
        *,
        camera_id: str | None = None,
        stale_after_seconds: int = 300,
    ) -> int:
        """
        Mark non-terminal tracks whose last_seen_at is older than stale_after_seconds
        as STALE. Returns count of tracks marked.
        Called by background maintenance or admin endpoint — not called per detection.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=stale_after_seconds)
        candidates = await self.track_repo.get_tracks_older_than(
            camera_id=camera_id,
            older_than=cutoff,
            statuses=["ACTIVE", "TENTATIVE", "LOST", "REACQUIRED"],
        )
        count = 0
        for track in candidates:
            await self.lifecycle.stale(track)
            count += 1

        if count:
            await self.session.commit()
            logger.info("stale_tracks_marked count=%d camera_id=%s", count, camera_id)
        return count
