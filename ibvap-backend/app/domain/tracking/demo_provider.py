# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 6 — DemoTrackingProvider
#
# A deterministic, offline provider used during development and testing.
# Simulates the provider interface without any real tracker algorithm.
#
# SSB demo scenarios (spec §95):
#   CAM-07  — active person
#   CAM-12  — animal + degraded camera
#   CAM-19  — tentative long-range
#   CAM-03  — lost → reacquired → ended
#   Cross-camera candidate (CAM-07 → CAM-08)
#   Multiple tracks, large track set, incident-linked track
#
# Rules (spec §92–§94):
#   · DEMO mode is explicit; no automatic mock fallback in REAL mode
#   · No fake confidence, velocity, direction unless demo fixture supplies it
#   · Fixed timestamps — no new Date() fabrication for historical values
#   · No identity claims across cameras
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import asyncio
import time
from datetime import datetime, timezone

from app.core.logging import get_logger
from app.domain.tracking.constants import (
    ASSOC_MATCHED,
    ASSOC_NEW_TRACK,
    ASSOC_UNMATCHED,
    CONTINUITY_STRONG,
    CONTINUITY_MODERATE,
    CONTINUITY_WEAK,
    PROVIDER_READY,
    PROVIDER_UNAVAILABLE,
)
from app.domain.tracking.provider import (
    CameraContext,
    DetectionInput,
    ProviderHealthInfo,
    ProviderMetadata,
    ProviderUpdateResult,
    TrackAssignment,
    TrackingProvider,
)

logger = get_logger("prhaar.tracking.demo_provider")

# ─────────────────────────────────────────────────────────────────────────────
# Fixed demo track IDs — deterministic, never random in demo mode
# ─────────────────────────────────────────────────────────────────────────────
_DEMO_TRACKS: dict[str, dict] = {
    # CAM-07 — active person
    "TRK-DEMO0007A1": {"camera_id": "CAM-07", "object_class": "PERSON",  "status": "ACTIVE",    "continuity_quality": CONTINUITY_STRONG},
    "TRK-DEMO0007A2": {"camera_id": "CAM-07", "object_class": "VEHICLE", "status": "TENTATIVE", "continuity_quality": CONTINUITY_WEAK},
    # CAM-12 — animal + degraded camera
    "TRK-DEMO0012A1": {"camera_id": "CAM-12", "object_class": "ANIMAL",  "status": "ACTIVE",    "continuity_quality": CONTINUITY_MODERATE},
    "TRK-DEMO0012A2": {"camera_id": "CAM-12", "object_class": "PERSON",  "status": "LOST",      "continuity_quality": CONTINUITY_WEAK},
    # CAM-19 — tentative long-range
    "TRK-DEMO0019A1": {"camera_id": "CAM-19", "object_class": "UNKNOWN", "status": "TENTATIVE", "continuity_quality": CONTINUITY_WEAK},
    # CAM-03 — lost → reacquired → ended lifecycle
    "TRK-DEMO0003A1": {"camera_id": "CAM-03", "object_class": "PERSON",  "status": "REACQUIRED","continuity_quality": CONTINUITY_MODERATE},
    "TRK-DEMO0003A2": {"camera_id": "CAM-03", "object_class": "PERSON",  "status": "ENDED",     "continuity_quality": CONTINUITY_STRONG},
    # CAM-08 — continuation candidate from CAM-07
    "TRK-DEMO0008A1": {"camera_id": "CAM-08", "object_class": "PERSON",  "status": "ACTIVE",    "continuity_quality": CONTINUITY_MODERATE},
}

# Maps camera_id → list of demo track_ids active on that camera
_CAMERA_DEMO_TRACKS: dict[str, list[str]] = {}
for _tid, _tdata in _DEMO_TRACKS.items():
    _CAMERA_DEMO_TRACKS.setdefault(_tdata["camera_id"], []).append(_tid)


class DemoTrackingProvider(TrackingProvider):
    """
    Deterministic demo provider — no real tracking algorithm.
    Associates detections to fixed demo tracks by class match + sequence.
    Used for integration testing and frontend development only.
    """

    _PROVIDER_NAME = "DEMO"
    _PROVIDER_VERSION = "demo-1.0"
    _ALGO_VERSION = "demo-noop-1.0"
    _CONFIG_VERSION = "demo-default-1.0"

    def __init__(self) -> None:
        self._ready = False
        self._started_at: datetime | None = None
        self._last_update: datetime | None = None
        self._failure_count = 0
        self._total_updates = 0
        # Per-camera internal sequence counter
        self._sequences: dict[str, dict[str, int]] = {}  # camera_id → track_id → seq
        # Per-camera detection→track mapping (one detection → at most one track)
        self._assignments: dict[str, str] = {}  # detection_id → track_id
        # Instance-local snapshot of the demo fixture. Runtime additions go to
        # these dictionaries only — module-level state is never mutated, so two
        # provider instances (e.g. tests, or DEMO restarts) stay isolated.
        self._tracks: dict[str, dict] = {
            tid: dict(data) for tid, data in _DEMO_TRACKS.items()
        }
        self._camera_tracks: dict[str, list[str]] = {
            cam: list(tids) for cam, tids in _CAMERA_DEMO_TRACKS.items()
        }

    async def initialize(self) -> None:
        await asyncio.sleep(0)  # yield to event loop
        self._ready = True
        self._started_at = datetime.now(timezone.utc)
        logger.info("DemoTrackingProvider initialized")

    def ready(self) -> bool:
        return self._ready

    async def update(
        self,
        detections: list[DetectionInput],
        context: CameraContext,
    ) -> ProviderUpdateResult:
        if not self._ready:
            raise RuntimeError("DemoTrackingProvider.update() called before initialize()")

        start = time.monotonic()
        camera_id = context.camera_id
        assignments: list[TrackAssignment] = []

        # Get demo tracks for this camera
        demo_track_ids = self._camera_tracks.get(camera_id, [])

        if not self._sequences.get(camera_id):
            self._sequences[camera_id] = {tid: 0 for tid in demo_track_ids}

        # Match each detection to a demo track by object_class, round-robin
        class_queues: dict[str, list[str]] = {}
        for tid in demo_track_ids:
            cls = self._tracks[tid]["object_class"]
            class_queues.setdefault(cls, []).append(tid)

        # Track which demo tracks we've used this batch to avoid double-assignment
        used_demo_tracks: set[str] = set()

        for det in detections:
            # Idempotent: same detection → same result
            if det.detection_id in self._assignments:
                existing_tid = self._assignments[det.detection_id]
                seq = self._sequences[camera_id].get(existing_tid, 0)
                assignments.append(TrackAssignment(
                    detection_id=det.detection_id,
                    result=ASSOC_MATCHED,
                    track_id=existing_tid,
                    is_new_track=False,
                    sequence=seq,
                    continuity_quality=self._tracks.get(existing_tid, {}).get(
                        "continuity_quality", None
                    ),
                    confidence=det.confidence,
                ))
                continue

            # Try to match to a demo track of the same class
            candidates = [
                tid for tid in class_queues.get(det.object_class, [])
                if tid not in used_demo_tracks
            ]
            # Also try UNKNOWN class tracks as fallback
            if not candidates:
                candidates = [
                    tid for tid in class_queues.get("UNKNOWN", [])
                    if tid not in used_demo_tracks
                ]

            if candidates:
                chosen_tid = candidates[0]
                used_demo_tracks.add(chosen_tid)
                self._sequences[camera_id][chosen_tid] = (
                    self._sequences[camera_id].get(chosen_tid, 0) + 1
                )
                seq = self._sequences[camera_id][chosen_tid]
                self._assignments[det.detection_id] = chosen_tid
                assignments.append(TrackAssignment(
                    detection_id=det.detection_id,
                    result=ASSOC_MATCHED,
                    track_id=chosen_tid,
                    is_new_track=False,
                    sequence=seq,
                    continuity_quality=self._tracks[chosen_tid]["continuity_quality"],
                    confidence=det.confidence,
                ))
            else:
                # No demo track available for this camera/class — new track
                from app.models.tracking import _trk_id
                new_tid = _trk_id()
                self._assignments[det.detection_id] = new_tid
                self._tracks[new_tid] = {
                    "camera_id": camera_id,
                    "object_class": det.object_class,
                    "status": "TENTATIVE",
                    "continuity_quality": CONTINUITY_WEAK,
                }
                self._camera_tracks.setdefault(camera_id, []).append(new_tid)
                self._sequences[camera_id][new_tid] = 1
                assignments.append(TrackAssignment(
                    detection_id=det.detection_id,
                    result=ASSOC_NEW_TRACK,
                    track_id=new_tid,
                    is_new_track=True,
                    sequence=1,
                    continuity_quality=CONTINUITY_WEAK,
                    confidence=det.confidence,
                ))

        elapsed_ms = int((time.monotonic() - start) * 1000)
        self._last_update = datetime.now(timezone.utc)
        self._total_updates += 1

        return ProviderUpdateResult(
            camera_id=camera_id,
            processed_at=self._last_update,
            assignments=assignments,
            tracks_ended=[],
            tracks_lost=[],
            tracks_reacquired=[],
            provider_name=self._PROVIDER_NAME,
            provider_version=self._PROVIDER_VERSION,
            configuration_version=self._CONFIG_VERSION,
            processing_latency_ms=elapsed_ms,
        )

    async def flush(self, camera_id: str) -> ProviderUpdateResult:
        return ProviderUpdateResult(
            camera_id=camera_id,
            processed_at=datetime.now(timezone.utc),
            assignments=[],
            provider_name=self._PROVIDER_NAME,
            provider_version=self._PROVIDER_VERSION,
        )

    def health(self) -> ProviderHealthInfo:
        return ProviderHealthInfo(
            state=PROVIDER_READY if self._ready else PROVIDER_UNAVAILABLE,
            provider_name=self._PROVIDER_NAME,
            provider_version=self._PROVIDER_VERSION,
            last_successful_update=self._last_update,
            failure_count=self._failure_count,
            queue_depth=0,
            processing_latency_ms=None,
            cameras_active=len(self._camera_tracks),
            note="DEMO provider — no real tracking algorithm active",
        )

    def metadata(self) -> ProviderMetadata:
        return ProviderMetadata(
            provider_name=self._PROVIDER_NAME,
            tracker_name=None,       # no real tracker
            tracker_version=None,
            algorithm_version=self._ALGO_VERSION,
            configuration_version=self._CONFIG_VERSION,
            description="Deterministic demo provider for development and testing. "
                        "No production tracking algorithm is active.",
        )

    async def shutdown(self) -> None:
        self._ready = False
        logger.info("DemoTrackingProvider shut down")
