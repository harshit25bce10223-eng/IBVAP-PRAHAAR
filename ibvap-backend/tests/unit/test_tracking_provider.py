# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 6 — TrackingProvider / DemoTrackingProvider Unit Tests
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import pytest
from datetime import datetime, timezone

from app.domain.tracking.demo_provider import DemoTrackingProvider
from app.domain.tracking.provider import (
    CameraContext,
    DetectionInput,
    ProviderUpdateResult,
    get_tracking_provider,
    set_tracking_provider,
)
from app.domain.tracking.constants import (
    ASSOC_MATCHED, ASSOC_NEW_TRACK,
    PROVIDER_READY, PROVIDER_UNAVAILABLE,
)


def _det(det_id: str, camera_id: str = "CAM-07", cls: str = "PERSON") -> DetectionInput:
    return DetectionInput(
        detection_id=det_id,
        camera_id=camera_id,
        observed_at=datetime(2026, 9, 12, 10, 0, 0, tzinfo=timezone.utc),
        bbox_x=0.3, bbox_y=0.3, bbox_width=0.1, bbox_height=0.2,
        object_class=cls,
        confidence=0.87,
        quality="GOOD",
        occlusion="LOW",
        source="DEMO",
    )


def _ctx(camera_id: str = "CAM-07") -> CameraContext:
    return CameraContext(camera_id=camera_id)


class TestDemoTrackingProvider:

    async def test_not_ready_before_initialize(self):
        p = DemoTrackingProvider()
        assert p.ready() is False

    async def test_ready_after_initialize(self):
        p = DemoTrackingProvider()
        await p.initialize()
        assert p.ready() is True

    async def test_health_ready_state(self):
        p = DemoTrackingProvider()
        await p.initialize()
        h = p.health()
        assert h.state == PROVIDER_READY
        assert h.provider_name == "DEMO"

    async def test_health_unavailable_before_init(self):
        p = DemoTrackingProvider()
        h = p.health()
        assert h.state == PROVIDER_UNAVAILABLE

    async def test_metadata_no_real_tracker(self):
        """Provider metadata must NOT claim a real tracker name."""
        p = DemoTrackingProvider()
        await p.initialize()
        m = p.metadata()
        assert m.provider_name == "DEMO"
        assert m.tracker_name is None  # no real tracker
        assert m.tracker_version is None

    async def test_update_returns_assignments(self):
        p = DemoTrackingProvider()
        await p.initialize()
        dets = [_det("DET-A001"), _det("DET-A002")]
        result = await p.update(dets, _ctx())
        assert isinstance(result, ProviderUpdateResult)
        assert len(result.assignments) == 2
        assert result.camera_id == "CAM-07"

    async def test_update_idempotent_same_detection(self):
        """Same detection processed twice → same track assignment (idempotent)."""
        p = DemoTrackingProvider()
        await p.initialize()

        det = _det("DET-IDEM001")
        r1 = await p.update([det], _ctx())
        r2 = await p.update([det], _ctx())

        assert len(r1.assignments) == 1
        assert len(r2.assignments) == 1
        # Both must resolve to the same track_id
        assert r1.assignments[0].track_id == r2.assignments[0].track_id

    async def test_update_new_track_for_unknown_camera(self):
        """Detection on unknown camera creates a NEW_TRACK assignment."""
        p = DemoTrackingProvider()
        await p.initialize()
        det = _det("DET-NEW001", camera_id="CAM-UNKNOWN99")
        result = await p.update([det], _ctx("CAM-UNKNOWN99"))
        assert any(a.result == ASSOC_NEW_TRACK for a in result.assignments)

    async def test_multiple_classes_independent_tracks(self):
        """PERSON + VEHICLE + ANIMAL on same camera → independent track assignments."""
        p = DemoTrackingProvider()
        await p.initialize()
        dets = [
            _det("DET-P001", "CAM-07", "PERSON"),
            _det("DET-V001", "CAM-07", "VEHICLE"),
            _det("DET-A001", "CAM-12", "ANIMAL"),
        ]
        r07 = await p.update([dets[0], dets[1]], _ctx("CAM-07"))
        r12 = await p.update([dets[2]], _ctx("CAM-12"))

        # All detections got assignments
        assert len(r07.assignments) == 2
        assert len(r12.assignments) == 1

        # Track IDs must differ across classes
        t07 = {a.track_id for a in r07.assignments}
        t12 = {a.track_id for a in r12.assignments}
        assert t07.isdisjoint(t12) or all(t is not None for t in t07 | t12)

    async def test_flush_returns_empty(self):
        p = DemoTrackingProvider()
        await p.initialize()
        result = await p.flush("CAM-07")
        assert result.camera_id == "CAM-07"
        assert result.assignments == []

    async def test_shutdown_not_ready(self):
        p = DemoTrackingProvider()
        await p.initialize()
        assert p.ready()
        await p.shutdown()
        assert not p.ready()

    async def test_update_raises_if_not_initialized(self):
        p = DemoTrackingProvider()
        with pytest.raises(RuntimeError):
            await p.update([_det("DET-001")], _ctx())


class TestProviderRegistry:

    def test_get_returns_none_when_unset(self):
        from app.domain.tracking.provider import _tracking_provider
        import app.domain.tracking.provider as pmod
        # Save and restore
        original = pmod._tracking_provider
        pmod._tracking_provider = None
        assert get_tracking_provider() is None
        pmod._tracking_provider = original

    async def test_set_and_get_provider(self):
        p = DemoTrackingProvider()
        await p.initialize()
        set_tracking_provider(p)
        assert get_tracking_provider() is p
        # Restore to None for isolation
        import app.domain.tracking.provider as pmod
        pmod._tracking_provider = None
