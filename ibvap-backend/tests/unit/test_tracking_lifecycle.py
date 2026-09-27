# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 6 — Track Lifecycle Service Unit Tests
#
# Tests the state machine independently of the database.
# Uses an in-memory async session via the shared conftest engine fixture.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import pytest
from datetime import datetime, timezone
from sqlalchemy import select

from app.domain.tracking.lifecycle import TrackLifecycleService
from app.domain.tracking.constants import (
    TRACK_STATUS_TENTATIVE, TRACK_STATUS_ACTIVE, TRACK_STATUS_LOST,
    TRACK_STATUS_REACQUIRED, TRACK_STATUS_ENDED, TRACK_STATUS_STALE,
    TRACK_STATUS_INVALID, TRACK_STATUS_UNKNOWN,
)
from app.models.tracking import TrackHistory, TrackV2


def _make_track(track_id: str = "TRK-TEST000001", camera_id: str = "CAM-07",
                status: str = TRACK_STATUS_UNKNOWN) -> TrackV2:
    now = datetime.now(timezone.utc)
    return TrackV2(
        track_id=track_id,
        camera_id=camera_id,
        object_class="PERSON",
        object_type="PERSON",
        status=status,
        source="DEMO",
        revision=1,
        schema_version="2.0",
        sync_state="LOCAL_ONLY",
        observation_count=0,
        gap_count=0,
        reacquisition_count=0,
        data_completeness="UNKNOWN",
        created_at=now,
        updated_at=now,
    )


class TestTrackLifecycleTransitions:

    async def test_create_tentative(self, db_session):
        """New track enters TENTATIVE state."""
        track = _make_track()
        db_session.add(track)
        await db_session.flush()

        lc = TrackLifecycleService(db_session)
        await lc.create_tentative(track, detection_id="DET-001", provider="DEMO")

        assert track.status == TRACK_STATUS_TENTATIVE
        assert track.revision == 2

        # History record written
        rows = (await db_session.execute(
            select(TrackHistory).where(TrackHistory.track_id == track.track_id)
        )).scalars().all()
        assert len(rows) == 1
        assert rows[0].new_status == TRACK_STATUS_TENTATIVE
        assert rows[0].trigger_detection_id == "DET-001"

    async def test_activate(self, db_session):
        """TENTATIVE → ACTIVE on activation."""
        track = _make_track(status=TRACK_STATUS_TENTATIVE)
        track.revision = 2
        db_session.add(track)
        await db_session.flush()

        lc = TrackLifecycleService(db_session)
        await lc.activate(track, detection_id="DET-002")

        assert track.status == TRACK_STATUS_ACTIVE
        assert track.revision == 3

    async def test_lose(self, db_session):
        """ACTIVE → LOST increments gap_count."""
        track = _make_track(status=TRACK_STATUS_ACTIVE)
        track.revision = 3
        db_session.add(track)
        await db_session.flush()

        lc = TrackLifecycleService(db_session)
        await lc.lose(track)

        assert track.status == TRACK_STATUS_LOST
        assert track.gap_count == 1
        assert track.last_gap_started_at is not None

    async def test_reacquire(self, db_session):
        """LOST → REACQUIRED increments reacquisition_count."""
        track = _make_track(status=TRACK_STATUS_LOST)
        track.revision = 4
        track.gap_count = 1
        db_session.add(track)
        await db_session.flush()

        lc = TrackLifecycleService(db_session)
        await lc.reacquire(track, detection_id="DET-010")

        assert track.status == TRACK_STATUS_REACQUIRED
        assert track.reacquisition_count == 1
        assert track.last_reacquired_at is not None

    async def test_end(self, db_session):
        """ACTIVE → ENDED."""
        track = _make_track(status=TRACK_STATUS_ACTIVE)
        track.revision = 5
        db_session.add(track)
        await db_session.flush()

        lc = TrackLifecycleService(db_session)
        await lc.end(track)

        assert track.status == TRACK_STATUS_ENDED

    async def test_end_is_idempotent(self, db_session):
        """Calling end() on an already-ENDED track is a no-op."""
        track = _make_track(status=TRACK_STATUS_ENDED)
        track.revision = 6
        db_session.add(track)
        await db_session.flush()

        lc = TrackLifecycleService(db_session)
        await lc.end(track)  # should not raise

        assert track.status == TRACK_STATUS_ENDED
        # revision unchanged (no transition written)
        assert track.revision == 6

    async def test_stale(self, db_session):
        """ACTIVE → STALE."""
        track = _make_track(status=TRACK_STATUS_ACTIVE)
        track.revision = 3
        db_session.add(track)
        await db_session.flush()

        lc = TrackLifecycleService(db_session)
        await lc.stale(track)

        assert track.status == TRACK_STATUS_STALE

    async def test_stale_skipped_for_terminal(self, db_session):
        """Cannot stale an ENDED track."""
        track = _make_track(status=TRACK_STATUS_ENDED)
        track.revision = 7
        db_session.add(track)
        await db_session.flush()

        lc = TrackLifecycleService(db_session)
        await lc.stale(track)

        assert track.status == TRACK_STATUS_ENDED  # unchanged

    async def test_invalidate(self, db_session):
        """Any non-INVALID state → INVALID."""
        track = _make_track(status=TRACK_STATUS_LOST)
        track.revision = 4
        db_session.add(track)
        await db_session.flush()

        lc = TrackLifecycleService(db_session)
        await lc.invalidate(track, reason="OPERATOR_OVERRIDE")

        assert track.status == TRACK_STATUS_INVALID

    async def test_full_lifecycle(self, db_session):
        """UNKNOWN → TENTATIVE → ACTIVE → LOST → REACQUIRED → ACTIVE → ENDED."""
        track = _make_track()
        db_session.add(track)
        await db_session.flush()

        lc = TrackLifecycleService(db_session)
        await lc.create_tentative(track, detection_id="DET-100")
        assert track.status == TRACK_STATUS_TENTATIVE

        await lc.activate(track, detection_id="DET-101")
        assert track.status == TRACK_STATUS_ACTIVE

        await lc.lose(track)
        assert track.status == TRACK_STATUS_LOST
        assert track.gap_count == 1

        await lc.reacquire(track, detection_id="DET-105")
        assert track.status == TRACK_STATUS_REACQUIRED
        assert track.reacquisition_count == 1

        await lc.activate(track, detection_id="DET-106")
        assert track.status == TRACK_STATUS_ACTIVE

        await lc.end(track)
        assert track.status == TRACK_STATUS_ENDED

        # Check all history records were persisted
        rows = (await db_session.execute(
            select(TrackHistory).where(TrackHistory.track_id == track.track_id)
            .order_by(TrackHistory.timestamp)
        )).scalars().all()
        assert len(rows) == 6
        statuses = [r.new_status for r in rows]
        assert statuses == [
            TRACK_STATUS_TENTATIVE, TRACK_STATUS_ACTIVE,
            TRACK_STATUS_LOST, TRACK_STATUS_REACQUIRED,
            TRACK_STATUS_ACTIVE, TRACK_STATUS_ENDED,
        ]

    async def test_no_duplicate_noop_transition(self, db_session):
        """Same status → same status writes no history record."""
        track = _make_track(status=TRACK_STATUS_ACTIVE)
        track.revision = 3
        db_session.add(track)
        await db_session.flush()

        lc = TrackLifecycleService(db_session)
        await lc.activate(track)  # ACTIVE → ACTIVE = no-op

        rows = (await db_session.execute(
            select(TrackHistory).where(TrackHistory.track_id == track.track_id)
        )).scalars().all()
        assert len(rows) == 0
        assert track.revision == 3  # unchanged

    async def test_history_records_provider_version(self, db_session):
        """History records capture provider/version context."""
        track = _make_track()
        db_session.add(track)
        await db_session.flush()

        lc = TrackLifecycleService(db_session)
        await lc.create_tentative(
            track,
            provider="DEMO",
            provider_version="demo-1.0",
            configuration_version="demo-default-1.0",
        )

        row = (await db_session.execute(
            select(TrackHistory).where(TrackHistory.track_id == track.track_id)
        )).scalar_one()
        assert row.provider == "DEMO"
        assert row.provider_version == "demo-1.0"
        assert row.configuration_version == "demo-default-1.0"

    async def test_lose_cannot_lose_ended_track(self, db_session):
        """Cannot lose a terminal track — silently ignored."""
        track = _make_track(status=TRACK_STATUS_ENDED)
        track.revision = 8
        db_session.add(track)
        await db_session.flush()

        lc = TrackLifecycleService(db_session)
        await lc.lose(track)

        assert track.status == TRACK_STATUS_ENDED
        assert track.gap_count == 0  # no increment

    async def test_reacquire_only_from_lost(self, db_session):
        """reacquire() on a non-LOST track is a no-op."""
        track = _make_track(status=TRACK_STATUS_ACTIVE)
        track.revision = 3
        db_session.add(track)
        await db_session.flush()

        lc = TrackLifecycleService(db_session)
        await lc.reacquire(track)

        assert track.status == TRACK_STATUS_ACTIVE
        assert track.reacquisition_count == 0
