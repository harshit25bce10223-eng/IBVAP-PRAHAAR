"""Component 4 — Correlated Situation Engine: new regression tests.

Covers the UPGRADE acceptance criteria from the PRHAAR C4 spec:
  - Task 2: out-of-order, late, duplicate-by-dedup-key, concurrent events
  - Task 3: timezone normalization + observed-time member ordering
  - Task 5: explanation summary, explanation facets, correlation strength
  - Task 6: history ordered by revision asc
  - C4/C6/C7 reference surfacing (detection / ANPR plate / track candidate)
"""

from __future__ import annotations

import asyncio
import json
import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from httpx import AsyncClient, ASGITransport

from app.main import app


def _evt(event_id: str, camera: str, **overrides) -> dict:
    base = {
        "event_id": event_id,
        "event_type": "DETECTION",
        "camera_id": camera,
        "zone_id": f"ZONE-{camera}",
        "sector_id": "SEC-1",
        "track_id": f"TRK-{camera}",
        "event_time": datetime.now(timezone.utc).isoformat(),
        "source": "TEST",
    }
    base.update(overrides)
    return base


@pytest.fixture
def client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


# ─── Task 2: out-of-order / late / duplicate / concurrent ─────────────────────

class TestOrderingSemantics:
    @pytest.mark.asyncio
    async def test_out_of_order_events_group_by_observed_time(self, client):
        """A(00) -> C(10) -> B(05) yields ONE group; B joins the existing group."""
        now = datetime.now(timezone.utc)
        a = _evt("EVT-AAA", "CAM-01", event_time=now.isoformat())
        c = _evt("EVT-CCC", "CAM-01", event_time=(now + timedelta(seconds=10)).isoformat())
        b = _evt("EVT-BBB", "CAM-01", event_time=(now + timedelta(seconds=5)).isoformat())

        r1 = await client.post("/api/v1/correlations/events/ingest", json=a)
        assert r1.json()["action"] == "CREATED"
        gid = r1.json()["correlation_id"]

        r2 = await client.post("/api/v1/correlations/events/ingest", json=c)
        assert r2.json()["action"] == "UPDATED"
        assert r2.json()["group_id"] == gid

        r3 = await client.post("/api/v1/correlations/events/ingest", json=b)
        assert r3.json()["action"] == "UPDATED", f"late/in-order event should join: {r3.json()}"
        assert r3.json()["group_id"] == gid

        detail = await client.get(f"/api/v1/correlations/{gid}")
        timestamps = [m["timestamp"] for m in detail.json()["members"]]
        parsed = [datetime.fromisoformat(t) for t in timestamps]
        assert parsed == sorted(parsed), "members must be ordered by observed time"

    @pytest.mark.asyncio
    async def test_late_event_joins_existing_window(self, client):
        """A late event inside the window of an active group joins it, not a new group."""
        now = datetime.now(timezone.utc)
        first = _evt("EVT-L1", "CAM-01", event_time=now.isoformat())
        r1 = await client.post("/api/v1/correlations/events/ingest", json=first)
        gid = r1.json()["correlation_id"]

        late = _evt(
            "EVT-L2", "CAM-01",
            event_time=(now - timedelta(seconds=4)).isoformat(),  # observed slightly earlier
        )
        r2 = await client.post("/api/v1/correlations/events/ingest", json=late)
        assert r2.json()["action"] == "UPDATED", f"late event should update existing group: {r2.json()}"
        assert r2.json()["group_id"] == gid

    @pytest.mark.asyncio
    async def test_duplicate_by_dedup_key_is_idempotent(self, client):
        """Same (camera, source_event_id, source_sequence) => DUPLICATE."""
        payload = {
            "event_id": f"EVT-D1-{uuid4().hex[:6]}",
            "event_type": "ANPR_READ",
            "camera_id": "CAM-07",
            "zone_id": "ZONE-CAM-07",
            "sector_id": "SEC-1",
            "track_id": "TRK-CAM-07",
            "source_event_id": "SRC-8877",
            "source_sequence": 3,
            "event_time": datetime.now(timezone.utc).isoformat(),
            "source": "ANPR",
            "payload": {"anpr_plate": "HR 26 DK 4401", "anpr_plate_confidence": 0.92},
        }
        r1 = await client.post("/api/v1/correlations/events/ingest", json=payload)
        assert r1.json()["action"] == "CREATED"
        gid = r1.json()["correlation_id"]

        payload2 = dict(payload)
        payload2["event_id"] = f"EVT-D2-{uuid4().hex[:6]}"  # different event_id, same dedup key
        r2 = await client.post("/api/v1/correlations/events/ingest", json=payload2)
        assert r2.json()["action"] == "DUPLICATE", f"same dedup key => duplicate: {r2.json()}"
        assert r2.json()["correlation_id"] == gid

    @pytest.mark.asyncio
    async def test_concurrent_identical_events_single_group(self, client):
        """Two simultaneous ingestions of the same event produce one group + one DUPLICATE."""
        evt = _evt(f"EVT-CN-{uuid4().hex[:6]}", "CAM-01")

        async def _ingest():
            async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
                return await c.post("/api/v1/correlations/events/ingest", json=evt)

        results = await asyncio.gather(_ingest(), _ingest())
        group_ids = []
        actions = []
        for r in results:
            assert r.status_code == 200, r.text
            data = r.json()
            actions.append(data["action"])
            group_ids.append(data.get("correlation_id") or data.get("group_id"))
        # one created, one duplicate; both reference the same correlation group
        assert "DUPLICATE" in actions
        created_gid = next(gid for action, gid in zip(actions, group_ids) if action == "CREATED")
        dup_gid = next(gid for action, gid in zip(actions, group_ids) if action == "DUPLICATE")
        assert created_gid == dup_gid, f"concurrent ingests must share a group: {actions} {group_ids}"


# ─── Task 3: timezone normalization + ordering ────────────────────────────────

class TestTimezoneAndOrdering:
    @pytest.mark.asyncio
    async def test_timezone_offsets_normalize_for_temporal_correlation(self, client):
        """An event expressed with a +05:30 offset, within the window, joins the group."""
        now = datetime.now(timezone.utc)
        r1 = await client.post(
            "/api/v1/correlations/events/ingest",
            json=_evt("EVT-TZ1", "CAM-01", event_time=now.isoformat()),
        )
        assert r1.json()["action"] == "CREATED"
        gid = r1.json()["correlation_id"]

        # Event 4 seconds after `now`, but its timestamp is expressed with a
        # +05:30 offset string. The engine must normalize to aware UTC and see it
        # as ~4s apart -> joins the existing group.
        instant_utc = now + timedelta(seconds=4)
        offset_str = instant_utc.astimezone(timezone(timedelta(hours=5, minutes=30)))
        event_offs = _evt(
            "EVT-TZ2", "CAM-01",
            event_time=offset_str.strftime("%Y-%m-%dT%H:%M:%S%z"),
        )
        r2 = await client.post("/api/v1/correlations/events/ingest", json=event_offs)
        assert r2.json()["action"] == "UPDATED", f"offset event within window => join: {r2.json()}"
        assert r2.json()["group_id"] == gid

    @pytest.mark.asyncio
    async def test_members_serialized_by_observed_time(self, client):
        """list_correlation_groups returns members ordered by event ts, not added_at."""
        now = datetime.now(timezone.utc)
        r1 = await client.post(
            "/api/v1/correlations/events/ingest",
            json=_evt("EVT-ORD1", "CAM-01", event_time=(now + timedelta(seconds=10)).isoformat()),
        )
        gid = r1.json()["correlation_id"]
        # add an earlier event afterwards
        await client.post(
            "/api/v1/correlations/events/ingest",
            json=_evt("EVT-ORD2", "CAM-01", event_time=now.isoformat()),
        )
        detail = await client.get(f"/api/v1/correlations/{gid}")
        ts = [m["timestamp"] for m in detail.json()["members"]]
        parsed = [datetime.fromisoformat(t) for t in ts]
        assert parsed == sorted(parsed), "members must sort by observed time asc"


# ─── Task 5: explanation summary / strength / C5-C7 refs ──────────────────────

class TestExplanationAndReferences:
    async def _seed_correlated(self, client):
        now = datetime.now(timezone.utc)
        r1 = await client.post(
            "/api/v1/correlations/events/ingest",
            json=_evt("EVT-X1", "CAM-07", event_time=now.isoformat()),
        )
        gid = r1.json()["correlation_id"]
        r2 = await client.post(
            "/api/v1/correlations/events/ingest",
            json=_evt("EVT-X2", "CAM-07", event_time=(now + timedelta(seconds=6)).isoformat()),
        )
        return gid, r2

    @pytest.mark.asyncio
    async def test_explanation_summary_present(self, client):
        gid, r2 = await self._seed_correlated(client)
        detail = await client.get(f"/api/v1/correlations/{gid}")
        g = detail.json()  # route flattens group fields + members/relationships/history
        assert g.get("explanation_summary"), "explanation_summary must be present"
        assert "2 signals" in g["explanation_summary"], g["explanation_summary"]
        # correlation strength is NOT a risk label
        assert g.get("correlation_strength") in ("LOW", "MEDIUM", "HIGH", "NONE")

    @pytest.mark.asyncio
    async def test_anpr_plate_and_detection_refs_surfaced(self, client):
        payload = {
            "event_id": f"EVT-AR-{uuid4().hex[:6]}",
            "event_type": "ANPR_READ",
            "camera_id": "CAM-09",
            "zone_id": "ZONE-CAM-09",
            "sector_id": "SEC-1",
            "track_id": "TRK-CAM-09",
            "event_time": datetime.now(timezone.utc).isoformat(),
            "source": "ANPR",
            "payload": {
                "anpr_plate": "HR 26 DK 4401",
                "anpr_plate_confidence": 0.91,
                "anpr_quality": "HIGH",
                "anpr_sighting_id": "SIG-667",
                "detection_id": "DET-009",
            },
        }
        r = await client.post("/api/v1/correlations/events/ingest", json=payload)
        gid = r.json()["correlation_id"]
        detail = await client.get(f"/api/v1/correlations/{gid}")
        member = detail.json()["members"][0]
        assert member["anpr_plate"] == "HR 26 DK 4401"
        assert member["detection_id"] == "DET-009"
        assert member["anpr_sighting_id"] == "SIG-667"
        assert member["anpr_quality"] == "HIGH"

    @pytest.mark.asyncio
    async def test_track_candidate_ref_surfaced(self, client):
        payload = _evt(f"EVT-TC-{uuid4().hex[:6]}", "CAM-05")
        payload["payload"] = {"track_candidate": {"track_id": "TRK-POSS-88", "confidence": 0.83, "label": "possible continuation"}}
        r = await client.post("/api/v1/correlations/events/ingest", json=payload)
        gid = r.json()["correlation_id"]
        detail = await client.get(f"/api/v1/correlations/{gid}")
        member = detail.json()["members"][0]
        assert member["track_candidate"]["track_id"] == "TRK-POSS-88"


# ─── Task 6: history ordered by revision ──────────────────────────────────────

class TestHistoryOrdering:
    @pytest.mark.asyncio
    async def test_history_ordered_by_revision_asc(self, client):
        now = datetime.now(timezone.utc)
        r1 = await client.post(
            "/api/v1/correlations/events/ingest",
            json=_evt("EVT-H1", "CAM-02", event_time=now.isoformat()),
        )
        gid = r1.json()["correlation_id"]
        await client.post(
            "/api/v1/correlations/events/ingest",
            json=_evt("EVT-H2", "CAM-02", event_time=(now + timedelta(seconds=3)).isoformat()),
        )
        resp = await client.get(f"/api/v1/correlations/{gid}/history")
        hist = resp.json()["history"]
        revs = [h["revision"] for h in hist]
        assert revs == sorted(revs), f"history must be ordered by revision asc: {revs}"


# ─── Task 4: config validation (backend rejects 422) ─────────────────────────

class TestConfigValidation:
    @pytest.mark.asyncio
    async def test_negative_temporal_window_rejected(self, client):
        r = await client.post("/api/v1/correlations/config", json={"temporal_window_seconds": -5})
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_min_relationship_strength_out_of_range_rejected(self, client):
        r = await client.post("/api/v1/correlations/config", json={"min_relationship_strength": 150})
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_camera_adjacency_not_object_rejected(self, client):
        r = await client.post("/api/v1/correlations/config", json={"camera_adjacency": ["CAM-01"]})
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_camera_adjacency_bad_value_rejected(self, client):
        r = await client.post(
            "/api/v1/correlations/config",
            json={"camera_adjacency": {"CAM-01": [123, "CAM-02"]}},
        )
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_duration_not_greater_than_window_rejected(self, client):
        r = await client.post(
            "/api/v1/correlations/config",
            json={"temporal_window_seconds": 300, "max_group_duration_seconds": 120},
        )
        assert r.status_code == 422

    @pytest.mark.asyncio
    async def test_zero_spatial_window_rejected(self, client):
        r = await client.post("/api/v1/correlations/config", json={"spatial_window_meters": 0})
        assert r.status_code == 422


# ─── Task 6: human review records a mapped status transition + history ────────

class TestReview:
    @pytest.mark.asyncio
    async def test_review_dismissed_maps_dissolved_with_history(self, client):
        now = datetime.now(timezone.utc)
        r1 = await client.post(
            "/api/v1/correlations/events/ingest",
            json=_evt("EVT-R1", "CAM-03", event_time=now.isoformat()),
        )
        gid = r1.json()["correlation_id"]

        resp = await client.post(
            f"/api/v1/correlations/{gid}/review",
            params={"decision": "DISMISSED", "reason": "operator review"},
        )
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["status"] == "DISSOLVED"
        assert data["review_decision"] == "DISMISSED"

        hist = await client.get(f"/api/v1/correlations/{gid}/history")
        reasons = [h["reason"] for h in hist.json()["history"]]
        assert any("Review: DISMISSED" in (r or "") for r in reasons), reasons

    @pytest.mark.asyncio
    async def test_review_invalid_decision_rejected(self, client):
        now = datetime.now(timezone.utc)
        r1 = await client.post(
            "/api/v1/correlations/events/ingest",
            json=_evt("EVT-R2", "CAM-04", event_time=now.isoformat()),
        )
        gid = r1.json()["correlation_id"]
        resp = await client.post(
            f"/api/v1/correlations/{gid}/review",
            params={"decision": "NOT_A_DECISION"},
        )
        assert resp.status_code == 422