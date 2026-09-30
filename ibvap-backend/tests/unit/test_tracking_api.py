# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 6 — Tracking API Tests (spec §39)
#
# API-level coverage for app/api/routes/tracking/routes.py:
#   · GET  /api/v1/tracks                             (+ filter / search / sort / pagination / 422)
#   · GET  /api/v1/tracks/recent
#   · GET  /api/v1/tracks/{id}                        (+ trajectory, 404)
#   · GET  /api/v1/tracks/{id}/observations           (+ paging, 404)
#   · GET  /api/v1/tracks/{id}/history                (newest-first, paging)
#   · GET  /api/v1/tracks/{id}/candidates             (POSSIBLE_* vocabulary only)
#   · GET  /api/v1/cameras/{id}/tracks                (+ /feed, /summary)
#   · GET  /api/v1/tracking/health
#   · GET  /api/v1/tracking/config/{camera_id}
#   · POST /api/v1/internal/tracking/update           (403 / ingest / replay / 503)
#
# Notes on the test harness:
#   · ASGITransport does NOT run FastAPI startup events, so the tracking
#     provider global is registered explicitly per test with a fresh
#     DemoTrackingProvider and restored on teardown. Tests that need the
#     "no provider" state unset it inline.
#   · Timestamp assertions: TrackResponse.from_orm() re-attaches UTC to naive
#     SQLite datetimes → exact '+00:00' strings. Raw .isoformat() fields
#     (feed / summary / history / observation / candidate / config) round-trip
#     naive → asserted with .startswith().
#   · Only seeded, observable values are asserted — no fabricated metrics.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import pytest
from datetime import datetime, timezone

from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

import app.domain.tracking.provider as pmod
from app.domain.tracking.demo_provider import (
    DemoTrackingProvider,
    _CAMERA_DEMO_TRACKS,
)
from app.domain.tracking.provider import set_tracking_provider
from app.models.tracking import (
    TrackCandidate,
    TrackingConfig,
    TrackHistory,
    TrackObservation,
    TrackV2,
)

# ── Seeded scene constants ────────────────────────────────────────────────────

A1, A2, A3, A4 = "TRK-API-A1", "TRK-API-A2", "TRK-API-A3", "TRK-API-A4"
B1, B2, B3 = "TRK-API-B1", "TRK-API-B2", "TRK-API-B3"
CAM7, CAM19 = "CAM-07", "CAM-19"

ACTIVE_SET = {"TENTATIVE", "ACTIVE", "REACQUIRED"}


def _t(h: int, m: int, s: int = 0) -> datetime:
    """UTC timestamp on the seed date 2026-09-12."""
    return datetime(2026, 9, 12, h, m, s, tzinfo=timezone.utc)


# ── Seed row builders ─────────────────────────────────────────────────────────

def _track(
    track_id: str, camera_id: str, status: str, cls: str, *,
    first: datetime, last: datetime, obs_count: int = 1, source: str = "DEMO",
    confidence: float | None = None, continuity: str | None = None,
    detection_id: str | None = None, bbox: tuple | None = None,
    revision: int = 2, gap_count: int = 0,
) -> TrackV2:
    bx, by, bw, bh = bbox if bbox else (None, None, None, None)
    return TrackV2(
        track_id=track_id, camera_id=camera_id, status=status,
        object_class=cls, object_type=cls, source=source, provider="DEMO",
        revision=revision, schema_version="2.0", sync_state="LOCAL_ONLY",
        observation_count=obs_count, gap_count=gap_count, reacquisition_count=0,
        data_completeness="UNKNOWN",
        first_seen_at=first, last_seen_at=last, first_seen=first, last_seen=last,
        current_detection_id=detection_id,
        current_bbox_x=bx, current_bbox_y=by,
        current_bbox_width=bw, current_bbox_height=bh,
        confidence=confidence, continuity_quality=continuity,
    )


def _obs(
    obs_id: str, track_id: str, det_id: str, camera_id: str,
    ts: datetime, seq: int, bbox: tuple, *, conf: float = 0.88,
) -> TrackObservation:
    return TrackObservation(
        observation_id=obs_id, track_id=track_id, detection_id=det_id,
        camera_id=camera_id, observed_at=ts, received_at=ts, sequence=seq,
        bbox_x=bbox[0], bbox_y=bbox[1], bbox_width=bbox[2], bbox_height=bbox[3],
        confidence=conf, quality="GOOD", occlusion="LOW", object_class="PERSON",
        source="DEMO", provider="DEMO",
    )


def _hist(
    hist_id: str, track_id: str, revision: int, old: str | None, new: str,
    ts: datetime, *, reason: str | None = None,
) -> TrackHistory:
    return TrackHistory(
        history_id=hist_id, track_id=track_id, revision=revision,
        old_status=old, new_status=new, reason=reason,
        provider="DEMO", provider_version="demo-1.0",
        configuration_version="demo-default-1.0", timestamp=ts,
    )


def _cand(
    cand_id: str, source_track: str, target_camera: str, target_track: str,
    relation: str, *, strength: float | None, reason: str,
    gap: float | None, created: datetime, expires: datetime | None,
) -> TrackCandidate:
    return TrackCandidate(
        candidate_id=cand_id, source_track_id=source_track,
        target_camera_id=target_camera, candidate_track_id=target_track,
        relation_type=relation, strength=strength, reason=reason, status="OPEN",
        source="DEMO", provider="DEMO", gap_duration_sec=gap,
        created_at=created, expires_at=expires,
    )


def _det_item(det_id: str, camera_id: str, ts: str,
              cls: str = "PERSON", conf: float = 0.8) -> dict:
    return {
        "detectionId": det_id, "cameraId": camera_id, "observedAt": ts,
        "bboxX": 0.4, "bboxY": 0.4, "bboxWidth": 0.1, "bboxHeight": 0.2,
        "objectClass": cls, "confidence": conf, "source": "DEMO",
    }


def _payload(camera_id: str, items: list[dict]) -> dict:
    return {"cameraId": camera_id, "source": "DEMO", "detections": items}


INTERNAL_HEADERS = {"X-Internal-Service": "test-suite"}


class TestTrackingAPI:
    """API-level tests for the Component 6 tracking routes."""

    @pytest.fixture
    def client(self, app):
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    @pytest.fixture(autouse=True)
    async def tracking_provider(self):
        """Fresh demo provider per test (startup events do not run under ASGITransport)."""
        original = pmod._tracking_provider
        provider = DemoTrackingProvider()
        await provider.initialize()
        set_tracking_provider(provider)
        yield provider
        pmod._tracking_provider = original

    async def _seed_scene(self, db_session) -> None:
        """
        Seed 7 tracks:
          CAM-07: A1 ACTIVE PERSON (3 obs, bbox 0.3/0.2), A2 TENTATIVE VEHICLE,
                  A3 LOST ANIMAL (3 history rows, revision 4, 1 candidate),
                  A4 ENDED PERSON
          CAM-19: B1 REACQUIRED VEHICLE (source EDGE, 1 candidate),
                  B2 ACTIVE PERSON, B3 STALE OBJECT
        """
        db_session.add_all([
            _track(A1, CAM7, "ACTIVE", "PERSON", first=_t(5, 50), last=_t(6, 0),
                   obs_count=3, detection_id="DET-API-A1-3",
                   bbox=(0.3, 0.2, 0.1, 0.1), confidence=0.91, continuity="STRONG"),
            _track(A2, CAM7, "TENTATIVE", "VEHICLE", first=_t(5, 51), last=_t(5, 59),
                   obs_count=2, continuity="WEAK"),
            _track(A3, CAM7, "LOST", "ANIMAL", first=_t(5, 52), last=_t(5, 58),
                   obs_count=3, continuity="MODERATE", gap_count=1, revision=4),
            _track(A4, CAM7, "ENDED", "PERSON", first=_t(5, 53), last=_t(5, 57),
                   obs_count=7, continuity="STRONG"),
            _track(B1, CAM19, "REACQUIRED", "VEHICLE", first=_t(5, 47), last=_t(5, 56),
                   obs_count=4, source="EDGE", continuity="MODERATE", revision=3),
            _track(B2, CAM19, "ACTIVE", "PERSON", first=_t(5, 48), last=_t(5, 55),
                   obs_count=2, continuity="STRONG"),
            _track(B3, CAM19, "STALE", "OBJECT", first=_t(5, 49), last=_t(5, 54),
                   obs_count=1, continuity="WEAK"),
        ])
        # A1 observations — inserted OUT OF ORDER to prove the API returns
        # them chronologically regardless of insert order.
        db_session.add_all([
            _obs("OBS-API-A1-3", A1, "DET-API-A1-3", CAM7, _t(6, 0, 30), 3, (0.30, 0.2, 0.1, 0.1)),
            _obs("OBS-API-A1-1", A1, "DET-API-A1-1", CAM7, _t(6, 0, 10), 1, (0.10, 0.2, 0.1, 0.1)),
            _obs("OBS-API-A1-2", A1, "DET-API-A1-2", CAM7, _t(6, 0, 20), 2, (0.20, 0.2, 0.1, 0.1)),
        ])
        # A3 lifecycle history (revisions 2→4); the API must return newest-first.
        db_session.add_all([
            _hist("THIST-API-1", A3, 2, None, "TENTATIVE", _t(5, 56, 30)),
            _hist("THIST-API-2", A3, 3, "TENTATIVE", "ACTIVE", _t(5, 57, 30)),
            _hist("THIST-API-3", A3, 4, "ACTIVE", "LOST", _t(5, 58, 0),
                  reason="NO_OBSERVATIONS"),
        ])
        db_session.add_all([
            _cand("CAND-API-1", A3, CAM19, B3, "POSSIBLE_CONTINUATION",
                  strength=0.42, reason="Temporal + direction compatibility (unverified hypothesis)",
                  gap=180.0, created=_t(6, 1, 0), expires=_t(6, 6, 0)),
            _cand("CAND-API-2", B1, CAM7, A1, "POSSIBLE_SAME_ENTITY",
                  strength=None, reason="No provider strength reported",
                  gap=None, created=_t(6, 2, 0), expires=None),
        ])
        db_session.add(TrackingConfig(
            config_id="TRCFG-API-1", camera_id=CAM7, provider="demo",
            tracker_name=None, tracker_version=None,
            sample_rate=1.0, min_frame_interval_ms=0, active=True,
            revision=1, configuration_version="1.0",
        ))
        await db_session.commit()

    # ── GET /api/v1/tracks ────────────────────────────────────────────────────

    async def test_list_tracks_default_order(self, client, db_session):
        """Default list: last_seen desc, paging meta present."""
        await self._seed_scene(db_session)
        resp = await client.get("/api/v1/tracks")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 7
        assert data["page"] == 1
        assert data["pageSize"] == 20
        assert [t["trackId"] for t in data["tracks"]] == [A1, A2, A3, A4, B1, B2, B3]

    async def test_list_tracks_filters(self, client, db_session):
        """Camera / class / status / source filters are exact and isolated."""
        await self._seed_scene(db_session)

        resp = await client.get("/api/v1/tracks", params={"camera_id": CAM7})
        data = resp.json()
        assert data["total"] == 4
        assert [t["trackId"] for t in data["tracks"]] == [A1, A2, A3, A4]

        resp = await client.get("/api/v1/tracks", params={"class": "PERSON"})
        data = resp.json()
        assert data["total"] == 3
        assert {t["trackId"] for t in data["tracks"]} == {A1, A4, B2}

        resp = await client.get(
            "/api/v1/tracks", params={"camera_id": CAM19, "status": "ACTIVE"}
        )
        data = resp.json()
        assert data["total"] == 1
        assert data["tracks"][0]["trackId"] == B2

        resp = await client.get("/api/v1/tracks", params={"source": "EDGE"})
        data = resp.json()
        assert data["total"] == 1
        assert data["tracks"][0]["trackId"] == B1

    async def test_list_tracks_sort_first_seen_asc(self, client, db_session):
        """sort=first_seen&order=asc orders B1(05:47) … A4(05:53)."""
        await self._seed_scene(db_session)
        resp = await client.get(
            "/api/v1/tracks", params={"sort": "first_seen", "order": "asc"}
        )
        data = resp.json()
        assert [t["trackId"] for t in data["tracks"]] == [B1, B2, B3, A1, A2, A3, A4]

    async def test_list_tracks_sort_longest_duration(self, client, db_session):
        """sort=longest orders by track duration (A1=600s … A4=240s)."""
        await self._seed_scene(db_session)
        resp = await client.get(
            "/api/v1/tracks", params={"sort": "longest", "order": "desc"}
        )
        data = resp.json()
        assert [t["trackId"] for t in data["tracks"]] == [A1, B1, A2, B2, A3, B3, A4]

    async def test_list_tracks_pagination(self, client, db_session):
        """pageSize=3&page=2 returns the 4th–6th rows and correct meta."""
        await self._seed_scene(db_session)
        resp = await client.get("/api/v1/tracks", params={"page": 2, "pageSize": 3})
        data = resp.json()
        assert data["total"] == 7
        assert data["page"] == 2
        assert data["pageSize"] == 3
        assert [t["trackId"] for t in data["tracks"]] == [A4, B1, B2]

    async def test_list_tracks_search(self, client, db_session):
        """search matches track_id and camera_id, case-insensitively."""
        await self._seed_scene(db_session)
        resp = await client.get("/api/v1/tracks", params={"search": "API-A"})
        data = resp.json()
        assert data["total"] == 4
        assert {t["trackId"] for t in data["tracks"]} == {A1, A2, A3, A4}

        resp = await client.get("/api/v1/tracks", params={"search": "api-b"})
        data = resp.json()
        assert data["total"] == 3
        assert {t["trackId"] for t in data["tracks"]} == {B1, B2, B3}

        resp = await client.get("/api/v1/tracks", params={"search": "CAM-19"})
        data = resp.json()
        assert data["total"] == 3
        assert {t["trackId"] for t in data["tracks"]} == {B1, B2, B3}

    async def test_list_tracks_invalid_from_time_422(self, client, db_session):
        """A non-ISO from_time returns 422 INVALID_QUERY with our error shape."""
        await self._seed_scene(db_session)
        resp = await client.get("/api/v1/tracks", params={"from_time": "yesterday"})
        assert resp.status_code == 422
        err = resp.json()["detail"]["error"]
        assert err["code"] == "INVALID_QUERY"
        assert "from_time" in err["message"]

    async def test_list_tracks_invalid_params_422(self, client, db_session):
        """sort pattern, page>=1 and pageSize<=200 are enforced."""
        await self._seed_scene(db_session)
        assert (await client.get("/api/v1/tracks", params={"sort": "banana"})).status_code == 422
        assert (await client.get("/api/v1/tracks", params={"page": 0})).status_code == 422
        assert (await client.get("/api/v1/tracks", params={"pageSize": 201})).status_code == 422

    async def test_recent_tracks_active_set_only(self, client, db_session):
        """GET /tracks/recent returns only active-set tracks, last_seen desc."""
        await self._seed_scene(db_session)
        resp = await client.get("/api/v1/tracks/recent")
        assert resp.status_code == 200
        tracks = resp.json()
        assert [t["trackId"] for t in tracks] == [A1, A2, B1, B2]
        assert all(t["status"] in ACTIVE_SET for t in tracks)

    # ── GET /api/v1/tracks/{track_id} ─────────────────────────────────────────

    async def test_track_detail_exact_fields(self, client, db_session):
        """Track detail exposes the locked camelCase contract with exact values."""
        await self._seed_scene(db_session)
        resp = await client.get(f"/api/v1/tracks/{A1}")
        assert resp.status_code == 200
        d = resp.json()
        assert d["trackId"] == A1
        assert d["cameraId"] == CAM7
        assert d["status"] == "ACTIVE"
        assert d["objectClass"] == "PERSON"
        assert d["firstSeenAt"] == "2026-09-12T05:50:00+00:00"
        assert d["lastSeenAt"] == "2026-09-12T06:00:00+00:00"
        assert d["observedAt"] == "2026-09-12T06:00:00+00:00"
        assert d["durationSec"] == 600.0
        assert d["detectionCount"] == 3
        assert d["currentDetectionId"] == "DET-API-A1-3"
        assert d["currentBoundingBox"] == {"x": 0.3, "y": 0.2, "width": 0.1, "height": 0.1}
        assert d["confidence"] == 0.91
        assert d["continuityQuality"] == "STRONG"
        assert d["source"] == "DEMO"
        assert d["dataSource"] == "DEMO"
        assert d["revision"] == 2
        assert d["schemaVersion"] == "2.0"
        assert d["trajectory"] is None  # not requested → absent, never fabricated
        assert isinstance(d["ageMs"], int)
        # Regression guard: computed snake_case values must not leak as extras
        assert "duration_sec" not in d and "age_ms" not in d

    async def test_track_detail_not_found_404(self, client, db_session):
        await self._seed_scene(db_session)
        resp = await client.get("/api/v1/tracks/TRK-NOPE")
        assert resp.status_code == 404
        assert resp.json()["detail"]["error"] == {
            "code": "TRACK_NOT_FOUND",
            "message": "Track 'TRK-NOPE' not found.",
        }

    async def test_track_trajectory_chronological_and_downsampled(self, client, db_session):
        """
        includeTrajectory returns real observation points in chronological order
        (insert order was 3,1,2); maxTrajectoryPoints=2 keeps first + latest only.
        """
        await self._seed_scene(db_session)
        resp = await client.get(
            f"/api/v1/tracks/{A1}", params={"includeTrajectory": "true"}
        )
        assert resp.status_code == 200
        pts = resp.json()["trajectory"]
        assert [p["observationId"] for p in pts] == [
            "OBS-API-A1-1", "OBS-API-A1-2", "OBS-API-A1-3",
        ]
        assert [p["sequence"] for p in pts] == [1, 2, 3]
        # centers = bbox_x + width/2 (0.10/0.20/0.30 + 0.05)
        assert [p["x"] for p in pts] == pytest.approx([0.15, 0.25, 0.35])
        assert all(p["y"] == pytest.approx(0.25) for p in pts)
        assert pts[0]["timestamp"].startswith("2026-09-12T06:00:10")

        resp = await client.get(
            f"/api/v1/tracks/{A1}",
            params={"includeTrajectory": "true", "maxTrajectoryPoints": 2},
        )
        pts2 = resp.json()["trajectory"]
        assert [p["observationId"] for p in pts2] == ["OBS-API-A1-1", "OBS-API-A1-3"]

    # ── Observations / history / candidates ───────────────────────────────────

    async def test_track_observations_paged(self, client, db_session):
        """Observations are chronological by observed_at, with correct total."""
        await self._seed_scene(db_session)
        resp = await client.get(f"/api/v1/tracks/{A1}/observations")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert data["page"] == 1
        assert data["pageSize"] == 50
        obs = data["observations"]
        assert [o["observationId"] for o in obs] == [
            "OBS-API-A1-1", "OBS-API-A1-2", "OBS-API-A1-3",
        ]
        assert [o["detectionId"] for o in obs] == [
            "DET-API-A1-1", "DET-API-A1-2", "DET-API-A1-3",
        ]
        assert obs[0]["observedAt"].startswith("2026-09-12T06:00:10")
        assert obs[2]["observedAt"].startswith("2026-09-12T06:00:30")
        assert obs[0]["bbox"] == {"x": 0.1, "y": 0.2, "width": 0.1, "height": 0.1}
        assert obs[0]["trackId"] == A1
        assert obs[0]["cameraId"] == CAM7
        assert obs[0]["source"] == "DEMO"

        resp = await client.get(
            f"/api/v1/tracks/{A1}/observations", params={"page": 2, "pageSize": 2}
        )
        data2 = resp.json()
        assert data2["total"] == 3
        assert [o["observationId"] for o in data2["observations"]] == ["OBS-API-A1-3"]

    async def test_track_observations_not_found_404(self, client, db_session):
        await self._seed_scene(db_session)
        resp = await client.get("/api/v1/tracks/TRK-NOPE/observations")
        assert resp.status_code == 404
        assert resp.json()["detail"]["error"]["code"] == "TRACK_NOT_FOUND"

    async def test_track_history_newest_first(self, client, db_session):
        """History is returned newest-first with full transition provenance."""
        await self._seed_scene(db_session)
        resp = await client.get(f"/api/v1/tracks/{A3}/history")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        hist = data["history"]
        assert [h["revision"] for h in hist] == [4, 3, 2]
        assert [h["newStatus"] for h in hist] == ["LOST", "ACTIVE", "TENTATIVE"]
        assert [h["oldStatus"] for h in hist] == ["ACTIVE", "TENTATIVE", None]
        assert hist[0]["historyId"] == "THIST-API-3"
        assert hist[0]["reason"] == "NO_OBSERVATIONS"
        assert hist[0]["provider"] == "DEMO"
        assert hist[0]["providerVersion"] == "demo-1.0"
        assert hist[0]["timestamp"].startswith("2026-09-12T05:58:00")
        assert hist[2]["timestamp"].startswith("2026-09-12T05:56:30")

    async def test_track_history_paged(self, client, db_session):
        await self._seed_scene(db_session)
        resp = await client.get(f"/api/v1/tracks/{A3}/history", params={"pageSize": 2})
        data = resp.json()
        assert data["total"] == 3
        assert data["pageSize"] == 2
        assert [h["revision"] for h in data["history"]] == [4, 3]

    async def test_track_candidates_vocabulary_guard(self, client, db_session):
        """
        Candidates are hypotheses only (POSSIBLE_*), with honest nullable
        strength — never an identity claim.
        """
        await self._seed_scene(db_session)
        resp = await client.get(f"/api/v1/tracks/{A3}/candidates")
        assert resp.status_code == 200
        cands = resp.json()
        assert len(cands) == 1
        c = cands[0]
        assert c["candidateId"] == "CAND-API-1"
        assert c["sourceTrackId"] == A3
        assert c["targetCameraId"] == CAM19
        assert c["candidateTrackId"] == B3
        assert c["relationType"] == "POSSIBLE_CONTINUATION"
        assert c["strength"] == 0.42
        assert c["status"] == "OPEN"
        assert c["gapDurationSec"] == 180.0
        assert c["createdAt"].startswith("2026-09-12T06:01:00")
        assert c["expiresAt"].startswith("2026-09-12T06:06:00")
        for banned in ("CONFIRMED", "IDENTIFIED", "SAME_PERSON", "SAME_VEHICLE"):
            assert banned not in c["relationType"]

        resp = await client.get(f"/api/v1/tracks/{B1}/candidates")
        decoy = resp.json()
        assert len(decoy) == 1
        assert decoy[0]["candidateId"] == "CAND-API-2"
        assert decoy[0]["relationType"] == "POSSIBLE_SAME_ENTITY"
        assert decoy[0]["strength"] is None  # not supplied → not fabricated

    async def test_track_candidates_not_found_404(self, client, db_session):
        await self._seed_scene(db_session)
        resp = await client.get("/api/v1/tracks/TRK-NOPE/candidates")
        assert resp.status_code == 404
        assert resp.json()["detail"]["error"]["code"] == "TRACK_NOT_FOUND"

    # ── Camera-scoped endpoints ───────────────────────────────────────────────

    async def test_camera_tracks_active_only(self, client, db_session):
        """Camera track list contains only active-set tracks for that camera."""
        await self._seed_scene(db_session)
        resp = await client.get(f"/api/v1/cameras/{CAM7}/tracks")
        assert resp.status_code == 200
        tracks = resp.json()
        assert [t["trackId"] for t in tracks] == [A1, A2]
        assert all(t["status"] in ACTIVE_SET for t in tracks)

        resp = await client.get("/api/v1/cameras/CAM-99/tracks")
        assert resp.json() == []

    async def test_camera_feed_ready(self, client, db_session):
        """Feed reports provider state and the active tracks for the camera."""
        await self._seed_scene(db_session)
        resp = await client.get(f"/api/v1/cameras/{CAM7}/tracks/feed")
        assert resp.status_code == 200
        data = resp.json()
        assert data["cameraId"] == CAM7
        assert data["state"] == "READY"
        assert data["providerHealth"] == "READY"
        assert [t["trackId"] for t in data["tracks"]] == [A1, A2]
        assert data["lastUpdatedAt"].startswith("2026-09-12T06:00:00")

    async def test_camera_feed_unavailable_without_provider(self, client, db_session):
        """Provider down → UNAVAILABLE, but last-known track data is still served."""
        await self._seed_scene(db_session)
        pmod._tracking_provider = None
        resp = await client.get(f"/api/v1/cameras/{CAM7}/tracks/feed")
        assert resp.status_code == 200
        data = resp.json()
        assert data["state"] == "UNAVAILABLE"
        assert data["providerHealth"] == "UNAVAILABLE"
        assert [t["trackId"] for t in data["tracks"]] == [A1, A2]

    async def test_camera_summary_counts(self, client, db_session):
        """Summary: totals, status counts and active-set-only class counts."""
        await self._seed_scene(db_session)
        resp = await client.get(f"/api/v1/cameras/{CAM7}/tracks/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["cameraId"] == CAM7
        assert data["totalTracks"] == 4
        assert data["totalActive"] == 2
        assert data["byStatus"] == {"ACTIVE": 1, "TENTATIVE": 1, "LOST": 1, "ENDED": 1}
        # A3 (ANIMAL, LOST) and A4 (PERSON, ENDED) are excluded — active set only
        assert data["byClass"] == {"PERSON": 1, "VEHICLE": 1}
        assert data["lastUpdatedAt"].startswith("2026-09-12T06:00:00")

    async def test_camera_summary_empty_camera(self, client, db_session):
        """Unknown camera → zero counts, empty dicts, null timestamp."""
        resp = await client.get("/api/v1/cameras/CAM-99/tracks/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["totalTracks"] == 0
        assert data["totalActive"] == 0
        assert data["byClass"] == {}
        assert data["byStatus"] == {}
        assert data["lastUpdatedAt"] is None

    async def test_timestamps_are_utc_offset_aware(self, client, db_session):
        """
        Every ISO timestamp served by the C6 GET endpoints must carry an
        explicit UTC offset.

        SQLite drops tzinfo on DateTime(timezone=True) round-trips, and a
        naive string like "2026-09-28T14:55:01" is parsed by browsers as
        LOCAL time — the displayed instant shifts by the local offset.
        Found live in §27 QA: Track Detail showed firstSeenAt converted to
        IST (20:25:01) next to raw-UTC 14:55:01 for updatedAt/observations/
        history (a 5.5h discrepancy). Serializers must pin UTC explicitly.
        """
        await self._seed_scene(db_session)

        d = (await client.get(f"/api/v1/tracks/{A1}")).json()
        assert d["updatedAt"].endswith("+00:00")
        assert d["firstSeenAt"].endswith("+00:00")
        assert d["lastSeenAt"].endswith("+00:00")
        assert d["observedAt"].endswith("+00:00")

        traj = (await client.get(
            f"/api/v1/tracks/{A1}", params={"includeTrajectory": "true"}
        )).json()["trajectory"]
        assert all(p["timestamp"].endswith("+00:00") for p in traj)

        obs = (await client.get(f"/api/v1/tracks/{A1}/observations")).json()["observations"]
        assert all(o["observedAt"].endswith("+00:00") for o in obs)
        assert all(o["receivedAt"].endswith("+00:00") for o in obs)

        hist = (await client.get(f"/api/v1/tracks/{A3}/history")).json()["history"]
        assert all(h["timestamp"].endswith("+00:00") for h in hist)

        cands = (await client.get(f"/api/v1/tracks/{A3}/candidates")).json()
        assert cands[0]["createdAt"].endswith("+00:00")
        assert cands[0]["expiresAt"].endswith("+00:00")

        feed = (await client.get(f"/api/v1/cameras/{CAM7}/tracks/feed")).json()
        assert feed["lastUpdatedAt"].endswith("+00:00")

        summary = (await client.get(f"/api/v1/cameras/{CAM7}/tracks/summary")).json()
        assert summary["lastUpdatedAt"].endswith("+00:00")

    # ── POST /api/v1/internal/tracking/update ─────────────────────────────────

    async def test_ingest_requires_internal_header_403(self, client, db_session):
        payload = _payload("CAM-API-ING0", [
            _det_item("DET-ING0-1", "CAM-API-ING0", "2026-09-12T06:10:00+00:00"),
        ])
        resp = await client.post("/api/v1/internal/tracking/update", json=payload)
        assert resp.status_code == 403
        err = resp.json()["detail"]["error"]
        assert err["code"] == "FORBIDDEN"
        assert "X-Internal-Service" in err["message"]

    async def test_ingest_invalid_timestamps_counted_without_provider(self, client):
        """
        A batch whose items all carry invalid timestamps is rejected and counted
        BEFORE any provider access — works even with no provider registered.
        """
        pmod._tracking_provider = None
        payload = _payload("CAM-API-ING0", [
            _det_item("DET-ING0-1", "CAM-API-ING0", "not-a-timestamp"),
            _det_item("DET-ING0-2", "CAM-API-ING0", "2026-99-99"),
        ])
        resp = await client.post(
            "/api/v1/internal/tracking/update", json=payload,
            headers=INTERNAL_HEADERS,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["totalDetections"] == 2
        assert data["rejected"] == 2
        assert data["matched"] == 0
        assert data["newTracks"] == 0
        assert data["duplicateRejected"] == 0
        assert data["errors"] == 0

    async def test_ingest_valid_batch_creates_tracks(self, client, db_session):
        """
        Valid detections on a camera with no demo fixture tracks create one
        TENTATIVE track each (first observation = hypothesis only).
        """
        payload = _payload("CAM-API-ING1", [
            _det_item("DET-ING1-1", "CAM-API-ING1", "2026-09-12T06:10:00+00:00", "PERSON"),
            _det_item("DET-ING1-2", "CAM-API-ING1", "2026-09-12T06:10:01+00:00", "PERSON"),
            _det_item("DET-ING1-3", "CAM-API-ING1", "2026-09-12T06:10:02+00:00", "VEHICLE"),
        ])
        resp = await client.post(
            "/api/v1/internal/tracking/update", json=payload, headers=INTERNAL_HEADERS
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["cameraId"] == "CAM-API-ING1"
        assert data["totalDetections"] == 3
        assert data["newTracks"] == 3
        assert data["matched"] == 0
        assert data["unmatched"] == 0
        assert data["duplicateRejected"] == 0
        assert data["errors"] == 0
        assert data["providerName"] == "DEMO"
        assert data["providerVersion"] == "demo-1.0"
        assert data["processingLatencyMs"] >= 0
        assert data["processedAt"]

        tracks = (await db_session.execute(
            select(TrackV2).where(TrackV2.camera_id == "CAM-API-ING1")
        )).scalars().all()
        assert len(tracks) == 3
        assert {t.status for t in tracks} == {"TENTATIVE"}
        assert {t.observation_count for t in tracks} == {1}
        # §36: the only sync state the tracking pipeline writes today is
        # LOCAL_ONLY (association.py:414) — assert the real write, invent nothing.
        assert {t.sync_state for t in tracks} == {"LOCAL_ONLY"}

    async def test_ingest_replay_duplicate_rejected(self, client, db_session):
        """Replaying an identical batch persists nothing new (spec §29)."""
        payload = _payload("CAM-API-ING3", [
            _det_item("DET-ING3-1", "CAM-API-ING3", "2026-09-12T06:10:00+00:00", "PERSON"),
            _det_item("DET-ING3-2", "CAM-API-ING3", "2026-09-12T06:10:01+00:00", "VEHICLE"),
        ])
        r1 = await client.post(
            "/api/v1/internal/tracking/update", json=payload, headers=INTERNAL_HEADERS
        )
        assert r1.json()["newTracks"] == 2

        r2 = await client.post(
            "/api/v1/internal/tracking/update", json=payload, headers=INTERNAL_HEADERS
        )
        d2 = r2.json()
        assert r2.status_code == 200
        assert d2["duplicateRejected"] == 2
        assert d2["newTracks"] == 0
        assert d2["matched"] == 0
        assert d2["errors"] == 0

        tracks = (await db_session.execute(
            select(TrackV2).where(TrackV2.camera_id == "CAM-API-ING3")
        )).scalars().all()
        assert len(tracks) == 2
        obs = (await db_session.execute(
            select(TrackObservation).where(TrackObservation.camera_id == "CAM-API-ING3")
        )).scalars().all()
        assert len(obs) == 2
        assert {o.detection_id for o in obs} == {"DET-ING3-1", "DET-ING3-2"}

    async def test_ingest_provider_unavailable_503(self, client, db_session):
        pmod._tracking_provider = None
        payload = _payload("CAM-API-ING4", [
            _det_item("DET-ING4-1", "CAM-API-ING4", "2026-09-12T06:10:00+00:00"),
        ])
        resp = await client.post(
            "/api/v1/internal/tracking/update", json=payload, headers=INTERNAL_HEADERS
        )
        assert resp.status_code == 503
        err = resp.json()["detail"]["error"]
        assert err["code"] == "TRACKING_UNAVAILABLE"
        assert err["message"] == "No TrackingProvider registered."

    # ── Provider health / config ──────────────────────────────────────────────

    async def test_tracking_health_ready(self, client, db_session):
        resp = await client.get("/api/v1/tracking/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["state"] == "READY"
        assert data["provider"] == "DEMO"
        assert data["providerVersion"] == "demo-1.0"
        assert data["trackerName"] is None       # no real tracker is active
        assert data["trackerVersion"] is None
        assert data["lastSuccessfulUpdate"] is None
        assert data["failureCount"] == 0
        assert data["queueDepth"] == 0
        assert data["camerasActive"] == len(_CAMERA_DEMO_TRACKS)
        assert "DEMO provider" in (data["note"] or "")

    async def test_tracking_health_unavailable(self, client, db_session):
        pmod._tracking_provider = None
        resp = await client.get("/api/v1/tracking/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["state"] == "UNAVAILABLE"
        assert data["provider"] == "NONE"
        assert data["providerVersion"] is None
        assert data["lastSuccessfulUpdate"] is None
        assert data["failureCount"] == 0
        assert data["queueDepth"] == 0
        assert data["camerasActive"] == 0
        assert data["note"] == "No TrackingProvider registered."

    async def test_tracking_config_present_and_absent(self, client, db_session):
        await self._seed_scene(db_session)
        resp = await client.get(f"/api/v1/tracking/config/{CAM7}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["configId"] == "TRCFG-API-1"
        assert data["cameraId"] == CAM7
        assert data["provider"] == "demo"
        assert data["trackerName"] is None
        assert data["active"] is True
        assert data["sampleRate"] == 1.0
        assert data["minFrameIntervalMs"] == 0
        assert data["configurationVersion"] == "1.0"
        assert data["createdAt"]

        resp = await client.get("/api/v1/tracking/config/CAM-08")
        assert resp.status_code == 200
        assert resp.json() is None  # no active config → explicit null, not a fake default
