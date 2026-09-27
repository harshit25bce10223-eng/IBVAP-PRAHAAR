# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 6 — Track Lifecycle Service
#
# Owns all track status transitions. No lifecycle rules are scattered in routes.
#
# State machine:
#
#   (new) ──► TENTATIVE ──► ACTIVE ──► LOST ──► REACQUIRED ──► ACTIVE
#                   └──────────────────────────────────────────────► ENDED
#                                         └──────────────────────► STALE
#   Any state ─────────────────────────────────────────────────► INVALID
#
# LOST ≠ ENDED (spec §18):
#   A LOST track may be reacquired.
#   An ENDED track must not spontaneously continue.
#
# Every status change:
#   1. Updates track.status + track.revision
#   2. Writes a TrackHistory record with reason, trigger, provider context
#   3. Flushes via session (caller commits)
#
# This service is stateless — it takes ORM objects and mutates them.
# Concurrency is handled by the caller (optimistic locking via revision).
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.domain.tracking.constants import (
    REASON_DETECTION_RECEIVED,
    REASON_NO_OBSERVATIONS,
    REASON_OPERATOR_OVERRIDE,
    REASON_PROVIDER_ENDED,
    REASON_PROVIDER_INVALID,
    REASON_PROVIDER_REACQUIRED,
    REASON_RECOVERY,
    REASON_STALE_AGE,
    REASON_TIMEOUT,
    TRACK_STATUS_ACTIVE,
    TRACK_STATUS_ENDED,
    TRACK_STATUS_INVALID,
    TRACK_STATUS_LOST,
    TRACK_STATUS_REACQUIRED,
    TRACK_STATUS_STALE,
    TRACK_STATUS_TENTATIVE,
    TRACK_STATUS_UNKNOWN,
    TRACK_STATUSES_TERMINAL_SET,
)
from app.models.tracking import TrackHistory, TrackV2

logger = get_logger("prhaar.tracking.lifecycle")


class TrackLifecycleService:
    """
    Computes and persists track lifecycle transitions.

    Usage:
        lc = TrackLifecycleService(session)
        await lc.activate(track, detection_id="DET-...", provider="DEMO")
        # session.commit() is the caller's responsibility
    """

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    # ── Public transition methods ─────────────────────────────────────────────

    async def create_tentative(
        self,
        track: TrackV2,
        *,
        detection_id: str | None = None,
        provider: str | None = None,
        provider_version: str | None = None,
        configuration_version: str | None = None,
        reason: str = REASON_DETECTION_RECEIVED,
    ) -> None:
        """Set a new track to TENTATIVE (initial hypothesis)."""
        await self._transition(
            track,
            new_status=TRACK_STATUS_TENTATIVE,
            detection_id=detection_id,
            provider=provider,
            provider_version=provider_version,
            configuration_version=configuration_version,
            reason=reason,
        )

    async def activate(
        self,
        track: TrackV2,
        *,
        detection_id: str | None = None,
        provider: str | None = None,
        provider_version: str | None = None,
        configuration_version: str | None = None,
        reason: str = REASON_DETECTION_RECEIVED,
    ) -> None:
        """Move track to ACTIVE (continuity established / observation received)."""
        await self._transition(
            track,
            new_status=TRACK_STATUS_ACTIVE,
            detection_id=detection_id,
            provider=provider,
            provider_version=provider_version,
            configuration_version=configuration_version,
            reason=reason,
        )

    async def lose(
        self,
        track: TrackV2,
        *,
        detection_id: str | None = None,
        provider: str | None = None,
        provider_version: str | None = None,
        configuration_version: str | None = None,
        reason: str = REASON_NO_OBSERVATIONS,
    ) -> None:
        """Move track to LOST (temporary gap — may be reacquired)."""
        if track.status in TRACK_STATUSES_TERMINAL_SET:
            logger.warning(
                "Cannot lose a terminal track track_id=%s status=%s",
                track.track_id, track.status
            )
            return

        # Record gap start time
        track.last_gap_started_at = datetime.now(timezone.utc)
        track.gap_count = (track.gap_count or 0) + 1

        await self._transition(
            track,
            new_status=TRACK_STATUS_LOST,
            detection_id=detection_id,
            provider=provider,
            provider_version=provider_version,
            configuration_version=configuration_version,
            reason=reason,
        )

    async def reacquire(
        self,
        track: TrackV2,
        *,
        detection_id: str | None = None,
        provider: str | None = None,
        provider_version: str | None = None,
        configuration_version: str | None = None,
        reason: str = REASON_PROVIDER_REACQUIRED,
    ) -> None:
        """Move a LOST track to REACQUIRED."""
        if track.status not in {TRACK_STATUS_LOST, TRACK_STATUS_STALE}:
            logger.debug(
                "reacquire() called on non-LOST track track_id=%s status=%s — ignoring",
                track.track_id, track.status
            )
            return

        track.last_reacquired_at = datetime.now(timezone.utc)
        track.reacquisition_count = (track.reacquisition_count or 0) + 1

        await self._transition(
            track,
            new_status=TRACK_STATUS_REACQUIRED,
            detection_id=detection_id,
            provider=provider,
            provider_version=provider_version,
            configuration_version=configuration_version,
            reason=reason,
        )

    async def end(
        self,
        track: TrackV2,
        *,
        detection_id: str | None = None,
        provider: str | None = None,
        provider_version: str | None = None,
        configuration_version: str | None = None,
        reason: str = REASON_PROVIDER_ENDED,
    ) -> None:
        """Move track to ENDED (lifecycle complete — object left scene)."""
        if track.status == TRACK_STATUS_ENDED:
            return  # idempotent
        await self._transition(
            track,
            new_status=TRACK_STATUS_ENDED,
            detection_id=detection_id,
            provider=provider,
            provider_version=provider_version,
            configuration_version=configuration_version,
            reason=reason,
        )

    async def stale(
        self,
        track: TrackV2,
        *,
        provider: str | None = None,
        provider_version: str | None = None,
        configuration_version: str | None = None,
        reason: str = REASON_STALE_AGE,
    ) -> None:
        """Mark track as STALE (data age exceeded freshness window)."""
        if track.status in TRACK_STATUSES_TERMINAL_SET:
            return
        if track.status == TRACK_STATUS_STALE:
            return  # idempotent
        await self._transition(
            track,
            new_status=TRACK_STATUS_STALE,
            provider=provider,
            provider_version=provider_version,
            configuration_version=configuration_version,
            reason=reason,
        )

    async def invalidate(
        self,
        track: TrackV2,
        *,
        reason: str = REASON_PROVIDER_INVALID,
        provider: str | None = None,
        provider_version: str | None = None,
        configuration_version: str | None = None,
    ) -> None:
        """Mark track as INVALID (provider or operator rejected it)."""
        if track.status == TRACK_STATUS_INVALID:
            return  # idempotent
        await self._transition(
            track,
            new_status=TRACK_STATUS_INVALID,
            provider=provider,
            provider_version=provider_version,
            configuration_version=configuration_version,
            reason=reason,
        )

    async def recover(
        self,
        track: TrackV2,
        *,
        detection_id: str | None = None,
        provider: str | None = None,
        provider_version: str | None = None,
        configuration_version: str | None = None,
    ) -> None:
        """
        After provider restart: recover a persisted track back to ACTIVE
        if it was in a non-terminal state.  Caller must have validated that
        the provider confirms continuity.
        """
        if track.status in TRACK_STATUSES_TERMINAL_SET:
            logger.info(
                "recover() skipped — terminal track track_id=%s status=%s",
                track.track_id, track.status
            )
            return
        await self._transition(
            track,
            new_status=TRACK_STATUS_ACTIVE,
            detection_id=detection_id,
            provider=provider,
            provider_version=provider_version,
            configuration_version=configuration_version,
            reason=REASON_RECOVERY,
        )

    # ── Internal implementation ───────────────────────────────────────────────

    async def _transition(
        self,
        track: TrackV2,
        *,
        new_status: str,
        detection_id: str | None = None,
        provider: str | None = None,
        provider_version: str | None = None,
        configuration_version: str | None = None,
        reason: str | None = None,
    ) -> None:
        """
        Apply a status transition, increment revision, write history record.
        Does NOT commit — caller is responsible for session.commit().
        """
        old_status = track.status
        if old_status == new_status:
            return  # no-op — idempotent

        # Increment revision (optimistic locking token)
        track.revision = (track.revision or 1) + 1
        track.status = new_status
        track.updated_at = datetime.now(timezone.utc)

        # Write history record
        record = TrackHistory(
            track_id=track.track_id,
            revision=track.revision,
            old_status=old_status,
            new_status=new_status,
            reason=reason,
            trigger_detection_id=detection_id,
            provider=provider,
            provider_version=provider_version,
            configuration_version=configuration_version,
            timestamp=datetime.now(timezone.utc),
        )
        self.session.add(record)
        await self.session.flush()

        logger.info(
            "track_lifecycle track_id=%s %s→%s revision=%d reason=%s",
            track.track_id, old_status, new_status, track.revision, reason
        )
