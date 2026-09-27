# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 6 — Track Association Service
#
# Manages the detection → track pipeline:
#   1. Calls TrackingProvider.update() with normalized DetectionInput list
#   2. For each TrackAssignment returned by the provider:
#      a. Creates / fetches the TrackV2 record
#      b. Updates the track's current state (bbox, class, detection ref)
#      c. Creates a TrackObservation record (idempotent via DB unique constraint)
#      d. Triggers lifecycle transitions via TrackLifecycleService
#   3. Handles provider-reported ended/lost/reacquired track lists
#   4. Returns an AssociationBatchResult for observability
#
# Idempotency:
#   · Same detection_id → same observation (DB unique constraint on track+detection)
#   · Same detection batch replayed → same logical outcome
#   · Concurrency: optimistic revision check; stale updates raise RevisionConflict
#
# This service does NOT:
#   · implement the actual tracker algorithm
#   · duplicate Detection records
#   · create Events / Correlations / Incidents / Evidence
#   · compute risk scores
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.domain.tracking.constants import (
    ASSOC_MATCHED,
    ASSOC_NEW_TRACK,
    ASSOC_REJECTED,
    ASSOC_UNMATCHED,
    CONTINUITY_UNKNOWN,
    TRACK_STATUS_ACTIVE,
    TRACK_STATUS_TENTATIVE,
)
from app.domain.tracking.lifecycle import TrackLifecycleService
from app.domain.tracking.provider import (
    CameraContext,
    DetectionInput,
    TrackingProvider,
    ProviderUpdateResult,
    TrackAssignment,
)
from app.models.tracking import TrackObservation, TrackV2

logger = get_logger("prhaar.tracking.association")


# ─────────────────────────────────────────────────────────────────────────────
# Result types
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SingleAssociationResult:
    detection_id: str
    result: str  # MATCHED_TO_TRACK | NEW_TRACK | UNMATCHED | REJECTED
    track_id: str | None = None
    observation_id: str | None = None
    is_new_track: bool = False
    duplicate_rejected: bool = False
    error: str | None = None


@dataclass
class AssociationBatchResult:
    camera_id: str
    processed_at: datetime
    total_detections: int = 0
    matched: int = 0
    new_tracks: int = 0
    unmatched: int = 0
    rejected: int = 0
    duplicate_rejected: int = 0
    errors: int = 0
    results: list[SingleAssociationResult] = field(default_factory=list)
    provider_name: str | None = None
    provider_version: str | None = None
    processing_latency_ms: int | None = None


class RevisionConflict(Exception):
    """Raised when a stale revision update is detected."""
    def __init__(self, track_id: str, expected: int, found: int) -> None:
        super().__init__(
            f"Revision conflict on track {track_id}: "
            f"expected revision {expected}, found {found}"
        )
        self.track_id = track_id
        self.expected = expected
        self.found = found


# ─────────────────────────────────────────────────────────────────────────────
# Association service
# ─────────────────────────────────────────────────────────────────────────────

class TrackAssociationService:
    """
    Orchestrates the detection → track association pipeline.

    Requires:
      · provider   — a ready TrackingProvider instance
      · session    — SQLAlchemy AsyncSession
      · lifecycle  — TrackLifecycleService (shared, same session)
    """

    def __init__(
        self,
        provider: TrackingProvider,
        session: AsyncSession,
        lifecycle: TrackLifecycleService,
    ) -> None:
        self.provider = provider
        self.session = session
        self.lifecycle = lifecycle

    # ── Main entry point ──────────────────────────────────────────────────────

    async def process_detections(
        self,
        detections: list[DetectionInput],
        context: CameraContext,
        *,
        source: str = "UNKNOWN",
        sector_id: str | None = None,
        region_profile: str | None = None,
        health_context_json: str | None = None,
    ) -> AssociationBatchResult:
        """
        Process a batch of detections for one camera through the provider.
        Persists track + observation records, triggers lifecycle transitions.
        Transactionally coherent where practical (one flush per batch).

        Partial-success: one invalid detection does not invalidate valid ones.
        """
        camera_id = context.camera_id

        logger.info(
            "detection_received camera_id=%s count=%d",
            camera_id, len(detections)
        )

        batch_result = AssociationBatchResult(
            camera_id=camera_id,
            processed_at=datetime.now(timezone.utc),
            total_detections=len(detections),
        )

        if not detections:
            return batch_result

        # ── 1. Call provider ──────────────────────────────────────────────────
        try:
            provider_result: ProviderUpdateResult = await asyncio.wait_for(
                self.provider.update(detections, context),
                timeout=30.0,  # hard cap — configurable in a future settings key
            )
        except asyncio.TimeoutError:
            logger.error("provider_timeout camera_id=%s", camera_id)
            batch_result.errors = len(detections)
            return batch_result
        except Exception as exc:
            logger.exception("provider_error camera_id=%s error=%s", camera_id, exc)
            batch_result.errors = len(detections)
            return batch_result

        batch_result.provider_name = provider_result.provider_name
        batch_result.provider_version = provider_result.provider_version
        batch_result.processing_latency_ms = provider_result.processing_latency_ms

        # Build a detection_id → DetectionInput map for quick lookup
        det_map: dict[str, DetectionInput] = {d.detection_id: d for d in detections}

        # ── 2. Process each assignment ────────────────────────────────────────
        for assignment in provider_result.assignments:
            single = await self._process_assignment(
                assignment=assignment,
                det_map=det_map,
                context=context,
                source=source,
                sector_id=sector_id,
                region_profile=region_profile,
                health_context_json=health_context_json,
                provider_result=provider_result,
            )
            batch_result.results.append(single)
            # Tally
            if single.error:
                batch_result.errors += 1
            elif single.duplicate_rejected:
                batch_result.duplicate_rejected += 1
            elif single.result == ASSOC_MATCHED:
                batch_result.matched += 1
            elif single.result == ASSOC_NEW_TRACK:
                batch_result.new_tracks += 1
            elif single.result == ASSOC_UNMATCHED:
                batch_result.unmatched += 1
            elif single.result == ASSOC_REJECTED:
                batch_result.rejected += 1

        # ── 3. Handle provider-reported lifecycle events ───────────────────────
        await self._handle_provider_lifecycle(provider_result, source)

        return batch_result

    # ── Assignment processing ─────────────────────────────────────────────────

    async def _process_assignment(
        self,
        *,
        assignment: TrackAssignment,
        det_map: dict[str, DetectionInput],
        context: CameraContext,
        source: str,
        sector_id: str | None,
        region_profile: str | None,
        health_context_json: str | None,
        provider_result: ProviderUpdateResult,
    ) -> SingleAssociationResult:
        det = det_map.get(assignment.detection_id)
        if det is None:
            logger.warning("duplicate_rejected detection_id=%s (not in det_map)", assignment.detection_id)
            return SingleAssociationResult(
                detection_id=assignment.detection_id,
                result=ASSOC_REJECTED,
                error="detection_id not found in input batch",
            )

        track_id = assignment.track_id
        if not track_id:
            return SingleAssociationResult(
                detection_id=assignment.detection_id,
                result=ASSOC_UNMATCHED,
            )

        # ── Get or create track ───────────────────────────────────────────────
        try:
            track, created = await self._get_or_create_track(
                track_id=track_id,
                det=det,
                assignment=assignment,
                context=context,
                source=source,
                sector_id=sector_id,
                region_profile=region_profile,
                health_context_json=health_context_json,
                provider_result=provider_result,
            )
        except Exception as exc:
            logger.exception(
                "tracking_update_failed camera_id=%s detection_id=%s track_id=%s error=%s",
                context.camera_id, det.detection_id, track_id, exc
            )
            return SingleAssociationResult(
                detection_id=det.detection_id,
                result=ASSOC_REJECTED,
                error=str(exc),
            )

        # ── Update track current state ────────────────────────────────────────
        self._update_track_fields(
            track=track,
            det=det,
            assignment=assignment,
            provider_result=provider_result,
            health_context_json=health_context_json,
            sector_id=sector_id,
            region_profile=region_profile,
        )

        # ── Lifecycle transition ──────────────────────────────────────────────
        if created or track.status == TRACK_STATUS_TENTATIVE:
            if not created:
                # Already tentative — promote to active on new observation
                await self.lifecycle.activate(
                    track,
                    detection_id=det.detection_id,
                    provider=provider_result.provider_name,
                    provider_version=provider_result.provider_version,
                    configuration_version=provider_result.configuration_version,
                )
        else:
            # If track was LOST/REACQUIRED/STALE, mark ACTIVE again
            if track.status in {"LOST", "REACQUIRED", "STALE"}:
                await self.lifecycle.reacquire(
                    track,
                    detection_id=det.detection_id,
                    provider=provider_result.provider_name,
                    provider_version=provider_result.provider_version,
                    configuration_version=provider_result.configuration_version,
                ) if track.status == "LOST" else None
                await self.lifecycle.activate(
                    track,
                    detection_id=det.detection_id,
                    provider=provider_result.provider_name,
                    provider_version=provider_result.provider_version,
                )

        # ── Create observation (idempotent via DB uniqueness) ─────────────────
        obs, is_duplicate = await self._create_observation(
            track=track,
            det=det,
            assignment=assignment,
            provider_result=provider_result,
        )

        if is_duplicate:
            logger.debug(
                "duplicate_observations_total track_id=%s detection_id=%s",
                track_id, det.detection_id
            )
            return SingleAssociationResult(
                detection_id=det.detection_id,
                result=ASSOC_MATCHED,
                track_id=track_id,
                observation_id=None,
                is_new_track=False,
                duplicate_rejected=True,
            )

        result_type = ASSOC_NEW_TRACK if created else ASSOC_MATCHED
        logger.info(
            "detection_associated detection_id=%s track_id=%s result=%s revision=%d",
            det.detection_id, track_id, result_type, track.revision
        )

        return SingleAssociationResult(
            detection_id=det.detection_id,
            result=result_type,
            track_id=track_id,
            observation_id=obs.observation_id if obs else None,
            is_new_track=created,
        )

    # ── Get or create TrackV2 ─────────────────────────────────────────────────

    async def _get_or_create_track(
        self,
        *,
        track_id: str,
        det: DetectionInput,
        assignment: TrackAssignment,
        context: CameraContext,
        source: str,
        sector_id: str | None,
        region_profile: str | None,
        health_context_json: str | None,
        provider_result: ProviderUpdateResult,
    ) -> tuple[TrackV2, bool]:
        """
        Returns (track, created=True|False).
        Uses INSERT-on-conflict via IntegrityError → re-fetch pattern for concurrency.
        """
        from sqlalchemy import select
        result = await self.session.execute(
            select(TrackV2).where(TrackV2.track_id == track_id)
        )
        existing = result.scalar_one_or_none()
        if existing is not None:
            return existing, False

        now = datetime.now(timezone.utc)
        track = TrackV2(
            track_id=track_id,
            camera_id=context.camera_id,
            object_class=det.object_class,
            object_type=det.object_class,  # legacy column compat
            status=TRACK_STATUS_TENTATIVE,
            source=source,
            provider=provider_result.provider_name,
            tracker_name=provider_result.provider_name,  # refined later
            tracker_version=provider_result.provider_version,
            configuration_version=provider_result.configuration_version,
            first_seen_at=det.observed_at,
            last_seen_at=det.observed_at,
            first_seen=det.observed_at,
            last_seen=det.observed_at,
            observation_count=0,
            continuity_quality=assignment.continuity_quality or CONTINUITY_UNKNOWN,
            sector_id=sector_id or det.sector_id,
            region_profile=region_profile or det.region_profile,
            health_context_json=health_context_json,
            revision=1,
            schema_version="2.0",
            sync_state="LOCAL_ONLY",
            data_completeness="UNKNOWN",
            gap_count=0,
            reacquisition_count=0,
            created_at=now,
            updated_at=now,
        )
        self.session.add(track)
        try:
            await self.session.flush()
            logger.info(
                "track_created track_id=%s camera_id=%s class=%s",
                track_id, context.camera_id, det.object_class
            )
            # Record initial TENTATIVE lifecycle entry
            await self.lifecycle.create_tentative(
                track,
                detection_id=det.detection_id,
                provider=provider_result.provider_name,
                provider_version=provider_result.provider_version,
                configuration_version=provider_result.configuration_version,
            )
            return track, True
        except IntegrityError:
            await self.session.rollback()
            # Concurrent worker created the same track_id first — fetch it
            from sqlalchemy import select
            result2 = await self.session.execute(
                select(TrackV2).where(TrackV2.track_id == track_id)
            )
            existing2 = result2.scalar_one_or_none()
            if existing2:
                return existing2, False
            raise

    # ── Update track current state ────────────────────────────────────────────

    def _update_track_fields(
        self,
        *,
        track: TrackV2,
        det: DetectionInput,
        assignment: TrackAssignment,
        provider_result: ProviderUpdateResult,
        health_context_json: str | None,
        sector_id: str | None,
        region_profile: str | None,
    ) -> None:
        """Update mutable track fields with latest observation data."""
        now = datetime.now(timezone.utc)

        track.current_detection_id = det.detection_id
        track.current_bbox_x = det.bbox_x
        track.current_bbox_y = det.bbox_y
        track.current_bbox_width = det.bbox_width
        track.current_bbox_height = det.bbox_height

        # Legacy JSON bbox (Component 1 compatibility)
        track.current_bbox_json = json.dumps({
            "x": det.bbox_x, "y": det.bbox_y,
            "width": det.bbox_width, "height": det.bbox_height,
        })

        # Update last seen
        # Ensure both datetimes are timezone-aware for comparison
        track_last_seen = track.last_seen_at
        if track_last_seen is not None and track_last_seen.tzinfo is None:
            track_last_seen = track_last_seen.replace(tzinfo=timezone.utc)
        if track_last_seen is None or det.observed_at > track_last_seen:
            track.last_seen_at = det.observed_at
            track.last_seen = det.observed_at

        track.observation_count = (track.observation_count or 0) + 1
        track.updated_at = now

        # Class — detect reclassification
        if track.object_class and track.object_class != det.object_class and det.object_class != "UNKNOWN":
            track.previous_class = track.object_class
            track.class_revision_reason = "Provider reclassification"
            track.class_revised_at = now
            track.object_class = det.object_class
            track.object_type = det.object_class  # legacy compat

        # Provider provenance
        if provider_result.provider_name:
            track.provider = provider_result.provider_name
        if provider_result.provider_version:
            track.tracker_version = provider_result.provider_version
        if provider_result.configuration_version:
            track.configuration_version = provider_result.configuration_version

        # Continuity quality (from assignment)
        if assignment.continuity_quality:
            track.continuity_quality = assignment.continuity_quality

        # Confidence (nullable — preserve if provider gives it)
        if assignment.confidence is not None:
            track.confidence = assignment.confidence

        # Health context snapshot
        if health_context_json:
            track.health_context_json = health_context_json

        # Context
        if sector_id:
            track.sector_id = sector_id
        if region_profile:
            track.region_profile = region_profile

    # ── Create observation ────────────────────────────────────────────────────

    async def _create_observation(
        self,
        *,
        track: TrackV2,
        det: DetectionInput,
        assignment: TrackAssignment,
        provider_result: ProviderUpdateResult,
    ) -> tuple[TrackObservation | None, bool]:
        """
        Create a TrackObservation record.
        Returns (observation, is_duplicate=True/False).
        is_duplicate=True means the observation already exists — not an error.
        Checks for existing observation first to avoid IntegrityError.
        """
        from sqlalchemy import select
        
        # Check if observation already exists (idempotent)
        existing = await self.session.execute(
            select(TrackObservation).where(
                TrackObservation.track_id == track.track_id,
                TrackObservation.detection_id == det.detection_id,
            )
        )
        if existing.scalar_one_or_none() is not None:
            return None, True
        
        obs = TrackObservation(
            track_id=track.track_id,
            detection_id=det.detection_id,
            camera_id=det.camera_id,
            observed_at=det.observed_at,
            received_at=datetime.now(timezone.utc),
            sequence=assignment.sequence,
            bbox_x=det.bbox_x,
            bbox_y=det.bbox_y,
            bbox_width=det.bbox_width,
            bbox_height=det.bbox_height,
            confidence=det.confidence,
            quality=det.quality,
            occlusion=det.occlusion,
            velocity=assignment.velocity,
            speed=assignment.speed,
            direction=assignment.direction,
            object_class=det.object_class,
            source=det.source,
            provider=provider_result.provider_name,
            frame_id=det.frame_id,
            frame_number=det.frame_number,
        )
        self.session.add(obs)
        await self.session.flush()
        return obs, False

    # ── Provider lifecycle events (ended / lost / reacquired) ─────────────────

    async def _handle_provider_lifecycle(
        self,
        provider_result: ProviderUpdateResult,
        source: str,
    ) -> None:
        from sqlalchemy import select

        provider_name = provider_result.provider_name
        provider_version = provider_result.provider_version
        cfg_version = provider_result.configuration_version

        for track_id in provider_result.tracks_ended:
            result = await self.session.execute(
                select(TrackV2).where(TrackV2.track_id == track_id)
            )
            track = result.scalar_one_or_none()
            if track:
                await self.lifecycle.end(
                    track, provider=provider_name,
                    provider_version=provider_version,
                    configuration_version=cfg_version,
                )
                logger.info("track_ended track_id=%s provider=%s", track_id, provider_name)

        for track_id in provider_result.tracks_lost:
            result = await self.session.execute(
                select(TrackV2).where(TrackV2.track_id == track_id)
            )
            track = result.scalar_one_or_none()
            if track:
                await self.lifecycle.lose(
                    track, provider=provider_name,
                    provider_version=provider_version,
                    configuration_version=cfg_version,
                )
                logger.info("track_lost track_id=%s provider=%s", track_id, provider_name)

        for track_id in provider_result.tracks_reacquired:
            result = await self.session.execute(
                select(TrackV2).where(TrackV2.track_id == track_id)
            )
            track = result.scalar_one_or_none()
            if track:
                await self.lifecycle.reacquire(
                    track, provider=provider_name,
                    provider_version=provider_version,
                    configuration_version=cfg_version,
                )
                logger.info("track_reacquired track_id=%s provider=%s", track_id, provider_name)
