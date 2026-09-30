"""Component 4 — Event Correlation Engine Regression Tests.

These tests exercise the correlation semantics required by the ULTIMATE
PRHAAR build (Correlated Situation Engine):
  - time-ordered grouping by OBSERVED time, not arrival order
  - late / out-of-order events join the correct existing group
  - idempotency (event_id and dedup key), deterministic dedup
  - temporal / spatial / adjacency / same-track / ANPR-style correlation
  - blind-spot safety: simultaneity alone is NOT a correlation
  - timezone normalization and aware-UTC persistence
  - config validation, camera adjacency wiring, config-scoped rules
  - history written on every transition; relationship explanations present
  - integrity verification (VERIFIED / INCONSISTENT)
  - correct aggregated counts and full get payload
  - batched read paths (ingest/list hot path) return per-group-identical
    rows and group dicts (parity lock for the performance batching)
  - ingest temporal prefilter parity across the window+2*clock_skew boundary
    (identical decisions with and without the prefilter; MAX(Event.ts) equals
    the group dict ended_at the engine classifies against)
"""

from __future__ import annotations

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


class TestCorrelationAPI:
    @pytest.fixture
    def client(self, app):
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    @pytest.mark.asyncio
    async def test_same_camera_recent_event_correlates(self, client):
        """Two events on the same camera within the window are RELATED/CORRELATED."""
        r1 = await client.post("/api/v1/correlations/events/ingest", json=_evt("EVT-A1", "CAM-01"))
        assert r1.status_code == 200
        assert r1.json()["action"] == "CREATED"
        group_id = r1.json()["correlation_id"]

        r2 = await client.post("/api/v1/correlations/events/ingest", json=_evt("EVT-A2", "CAM-01"))
        assert r2.status_code == 200
        data = r2.json()
        assert data["action"] == "UPDATED"
        assert data["group_id"] == group_id

    @pytest.mark.asyncio
    async def test_distant_events_form_separate_groups(self, client):
        """Events outside the temporal window never share a group."""
        now = datetime.now(timezone.utc)
        r1 = await client.post(
            "/api/v1/correlations/events/ingest",
            json=_evt("EVT-B1", "CAM-01", event_time=now.isoformat()),
        )
        r2 = await client.post(
            "/api/v1/correlations/events/ingest",
            json=_evt("EVT-B2", "CAM-01", event_time=(now + timedelta(minutes=10)).isoformat()),
        )
        assert r1.json()["action"] == "CREATED"
        assert r2.json()["action"] == "CREATED"
        assert r1.json()["correlation_id"] != r2.json()["correlation_id"]

    @pytest.mark.asyncio
    async def test_different_sectors_same_time_not_correlated(self, client):
        """Simultaneity across unrelated sectors is NOT a correlation (blind-spot)."""
        now = datetime.now(timezone.utc).isoformat()
        r1 = await client.post(
            "/api/v1/correlations/events/ingest",
            json=_evt("EVT-C1", "CAM-01", sector_id="SEC-1", zone_id="ZONE-CAM-01", event_time=now),
        )
        r2 = await client.post(
            "/api/v1/correlations/events/ingest",
            json=_evt("EVT-C2", "CAM-02", sector_id="SEC-2", zone_id="ZONE-CAM-02", event_time=now),
        )
        assert r1.json()["action"] == "CREATED"
        assert r2.json()["action"] == "CREATED"
        assert r1.json()["correlation_id"] != r2.json()["correlation_id"]

    @pytest.mark.asyncio
    async def test_same_track_across_cameras_correlates(self, client):
        """Same track on adjacent/other cameras in the same sector is CORRELATED."""
        now = datetime.now(timezone.utc)
        r1 = await client.post(
            "/api/v1/correlations/events/ingest",
            json=_evt("EVT-D1", "CAM-01", track_id="TRK-99", event_time=now.isoformat()),
        )
        group_id = r1.json()["correlation_id"]
        r2 = await client.post(
            "/api/v1/correlations/events/ingest",
            json=_evt("EVT-D2", "CAM-02", track_id="TRK-99",
                      event_time=(now + timedelta(seconds=10)).isoformat(),
                      zone_id="ZONE-CAM-02"),
        )
        assert r2.status_code == 200
        data = r2.json()
        assert data["action"] == "UPDATED"
        assert data["group_id"] == group_id
        assert data["score"] >= 70

        detail = await client.get(f"/api/v1/correlations/{group_id}")
        rels = detail.json()["relationships"]
        assert any(r["type"] == "ENTITY" and r.get("explanation") for r in rels)

    @pytest.mark.asyncio
    async def test_duplicate_event_id_is_idempotent(self, client):
        """Re-ingesting the same event_id returns DUPLICATE."""
        payload = _evt(f"EVT-E1-{uuid4().hex[:6]}", "CAM-01")
        r1 = await client.post("/api/v1/correlations/events/ingest", json=payload)
        r2 = await client.post("/api/v1/correlations/events/ingest", json=payload)
        assert r1.json()["action"] == "CREATED"
        assert r2.json()["action"] == "DUPLICATE"

    @pytest.mark.asyncio
    async def test_duplicate_by_dedup_key(self, client):
        """Same source_event_id+sequence with a NEW event_id is still DUPLICATE."""
        base = _evt(f"EVT-F1-{uuid4().hex[:6]}", "CAM-01")
        base["source_event_id"] = "upstream-123"
        base["source_sequence"] = 7
        r1 = await client.post("/api/v1/correlations/events/ingest", json=base)

        renamed = dict(base)
        renamed["event_id"] = f"EVT-F2-{uuid4().hex[:6]}"
        r2 = await client.post("/api/v1/correlations/events/ingest", json=renamed)
        assert r1.json()["action"] == "CREATED"
        assert r2.json()["action"] == "DUPLICATE"

    @pytest.mark.asyncio
    async def test_out_of_order_event_joins_existing_group(self, client):
        """Grouping is by OBSERVED time: a late event joins the correct group."""
        base = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        r1 = await client.post(
            "/api/v1/correlations/events/ingest",
            json=_evt("EVT-G1", "CAM-01", event_time=base.isoformat()),
        )
        group_id = r1.json()["correlation_id"]

        r2 = await client.post(
            "/api/v1/correlations/events/ingest",
            json=_evt("EVT-G2", "CAM-01", event_time=(base + timedelta(seconds=30)).isoformat()),
        )
        assert r2.json()["action"] == "UPDATED"
        assert r2.json()["group_id"] == group_id

        # Out-of-order: time between the existing members arrives last.
        r3 = await client.post(
            "/api/v1/correlations/events/ingest",
            json=_evt("EVT-G3", "CAM-01", event_time=(base + timedelta(seconds=10)).isoformat()),
        )
        assert r3.status_code == 200
        assert r3.json()["action"] == "UPDATED"
        assert r3.json()["group_id"] == group_id

    @pytest.mark.asyncio
    async def test_timezone_normalization(self, client):
        """Naive and offset timestamps that match in UTC correlate without error."""
        r1 = await client.post(
            "/api/v1/correlations/events/ingest",
            json=_evt("EVT-H1", "CAM-01", event_time="2026-01-01T12:00:00"),
        )
        group_id = r1.json()["correlation_id"]
        r2 = await client.post(
            "/api/v1/correlations/events/ingest",
            json=_evt("EVT-H2", "CAM-01", event_time="2026-01-01T17:30:00+05:30"),
        )
        assert r2.status_code == 200
        assert r2.json()["action"] == "UPDATED"
        assert r2.json()["group_id"] == group_id

    @pytest.mark.asyncio
    async def test_invalid_config_rejected(self, client):
        """Negative temporal window is rejected with 422."""
        resp = await client.post(
            "/api/v1/correlations/config",
            json={"profile": "MIXED_BORDER_SECTOR", "temporal_window_seconds": -5},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_config_adjacency_drives_relation(self, client):
        """Adjacent cameras co-relate and produce a SPATIAL relation + explanation."""
        cfg_resp = await client.post(
            "/api/v1/correlations/config",
            json={
                "profile": "MIXED_BORDER_SECTOR",
                "temporal_window_seconds": 600,
                "max_group_duration_seconds": 3600,
                "min_relationship_strength": 50,
                "camera_adjacency": {"CAM-01": ["CAM-02"]},
                "active": True,
            },
        )
        assert cfg_resp.status_code == 200
        config_id = cfg_resp.json()["config_id"]
        assert config_id.startswith("CFC-")

        now = datetime.now(timezone.utc)
        r1 = await client.post(
            "/api/v1/correlations/events/ingest",
            json=_evt("EVT-J1", "CAM-01", event_time=now.isoformat()),
        )
        group_id = r1.json()["correlation_id"]
        # Different sector: only camera adjacency can explain the correlation.
        r2 = await client.post(
            "/api/v1/correlations/events/ingest",
            json=_evt("EVT-J2", "CAM-02", zone_id="ZONE-CAM-02", track_id="TRK-CAM-02",
                      sector_id="SEC-2",
                      event_time=(now + timedelta(seconds=5)).isoformat()),
        )
        assert r2.json()["action"] == "UPDATED"
        assert r2.json()["group_id"] == group_id

        detail = await client.get(f"/api/v1/correlations/{group_id}")
        rels = detail.json()["relationships"]
        adjacent = [r for r in rels if r["type"] == "SPATIAL" and "ADJACENT" in (r.get("evidence_json") or {}).get("subtype", "")]
        assert adjacent, "expected an ADJACENT_CAMERA spatial relation"
        assert adjacent[0]["explanation"]

    @pytest.mark.asyncio
    async def test_get_correlation_full_payload(self, client):
        """GET /correlations/{id} returns group summary + members + relations + history."""
        r1 = await client.post(
            "/api/v1/correlations/events/ingest",
            json=_evt(f"EVT-K1-{uuid4().hex[:6]}", "CAM-01"),
        )
        group_id = r1.json()["correlation_id"]
        await client.post(
            "/api/v1/correlations/events/ingest",
            json=_evt(f"EVT-K2-{uuid4().hex[:6]}", "CAM-01",
                      event_time=(datetime.now(timezone.utc) + timedelta(seconds=5)).isoformat()),
        )
        resp = await client.get(f"/api/v1/correlations/{group_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["correlation_id"] == group_id
        assert len(data["members"]) == 2
        assert len(data["relationships"]) >= 2
        assert len(data["history"]) >= 2
        assert data["event_count"] == 2

    @pytest.mark.asyncio
    async def test_list_filter_by_camera(self, client):
        """Camera filter narrows the list; totals are accurate (distinct groups)."""
        await client.post("/api/v1/correlations/events/ingest",
                          json=_evt("EVT-L1", "CAM-01", sector_id="SEC-1", zone_id="Z1"))
        await client.post("/api/v1/correlations/events/ingest",
                          json=_evt("EVT-L2", "CAM-02", sector_id="SEC-2", zone_id="Z2"))

        all_resp = await client.get("/api/v1/correlations/", params={"page": 1, "page_size": 10})
        cam_resp = await client.get("/api/v1/correlations/", params={"camera_id": "CAM-01"})
        assert all_resp.json()["total"] == 2
        assert cam_resp.json()["total"] == 1

    @pytest.mark.asyncio
    async def test_list_sort_invariant(self, client):
        """Unknown sort columns fall back without error."""
        resp = await client.get("/api/v1/correlations/", params={"sort": "not_a_column", "order": "asc"})
        assert resp.status_code == 200

    @pytest.mark.asyncio
    async def test_verify_verified_for_sound_group(self, client):
        """A correlated 2-member group verifies as VERIFIED."""
        now = datetime.now(timezone.utc)
        r1 = await client.post(
            "/api/v1/correlations/events/ingest",
            json=_evt("EVT-M1", "CAM-01", event_time=now.isoformat()),
        )
        group_id = r1.json()["correlation_id"]
        await client.post(
            "/api/v1/correlations/events/ingest",
            json=_evt("EVT-M2", "CAM-01", event_time=(now + timedelta(seconds=5)).isoformat()),
        )
        resp = await client.post(f"/api/v1/correlations/{group_id}/verify")
        assert resp.status_code == 200
        assert resp.json()["status"] == "VERIFIED"

    @pytest.mark.asyncio
    async def test_correlated_group_counts(self, client):
        """Aggregated counts reflect distinct cameras/zones/sources."""
        now = datetime.now(timezone.utc)
        r1 = await client.post(
            "/api/v1/correlations/events/ingest",
            json=_evt("EVT-N1", "CAM-01", source="DETECTION", event_time=now.isoformat()),
        )
        group_id = r1.json()["correlation_id"]
        await client.post(
            "/api/v1/correlations/events/ingest",
            json=_evt("EVT-N2", "CAM-01", zone_id="ZONE-OTHER",
                      source="TRACKING", track_id="TRK-CAM-01",
                      event_time=(now + timedelta(seconds=5)).isoformat()),
        )
        detail = await client.get(f"/api/v1/correlations/{group_id}")
        data = detail.json()
        assert data["event_count"] == 2
        assert data["camera_count"] == 1
        assert data["source_count"] == 2

    @pytest.mark.asyncio
    async def test_concurrent_duplicates_deterministic(self, client):
        """Re-raising an identical event (rapid re-sends) yields one membership."""
        payload = _evt(f"EVT-P1-{uuid4().hex[:6]}", "CAM-01")
        await client.post("/api/v1/correlations/events/ingest", json=payload)
        await client.post("/api/v1/correlations/events/ingest", json=payload)
        await client.post("/api/v1/correlations/events/ingest", json=payload)

        listing = await client.get("/api/v1/correlations/", params={"page": 1, "page_size": 50})
        group_summaries = [g for g in listing.json()["groups"]]
        total_memberships = sum(g["event_count"] for g in group_summaries if g["event_count"] == 1)
        assert total_memberships == 1, "identical event must produce exactly one membership"

    @pytest.mark.asyncio
    async def test_list_groups_include_member_events(self, client):
        """List groups carry event-derived member_events for the frontend adapter."""
        await client.post(
            "/api/v1/correlations/events/ingest",
            json=_evt("EVT-S1", "CAM-01",
                      event_time=(datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()),
        )
        listing = await client.get("/api/v1/correlations/", params={"page": 1, "page_size": 10})
        groups = listing.json()["groups"]
        assert groups, "expected seeded group"
        g = groups[0]
        assert "member_events" in g
        assert len(g["member_events"]) == 1
        member = g["member_events"][0]
        assert member["event_id"] == "EVT-S1"
        assert member["kind"] == "DETECTION"
        assert member["camera_id"] == "CAM-01"
        assert member["source"] in ("VIRTUAL_FENCE", "UNKNOWN")
        assert "timestamp" in member
        assert "severity" in member

    @pytest.mark.asyncio
    async def test_get_event_member_endpoint(self, client):
        """GET /correlations/events/{event_id} returns the member + owning group."""
        await client.post(
            "/api/v1/correlations/events/ingest",
            json=_evt("EVT-S2", "CAM-01",
                      event_time=(datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()),
        )
        resp = await client.get("/api/v1/correlations/events/EVT-S2")
        assert resp.status_code == 200
        data = resp.json()
        assert data["event_id"] == "EVT-S2"
        assert data["member"]["kind"] == "DETECTION"
        assert data["group"]["correlation_id"] == data["correlation_id"]

    @pytest.mark.asyncio
    async def test_get_event_member_missing_404(self, client):
        resp = await client.get("/api/v1/correlations/events/EVT-DOES-NOT-EXIST")
        assert resp.status_code == 404

    @pytest.mark.asyncio
    async def test_get_config_list_route_not_shadowed(self, client):
        """GET /correlations/config must not be captured by /{correlation_id}."""
        resp = await client.get("/api/v1/correlations/config")
        assert resp.status_code == 200
        assert "configs" in resp.json()

    @pytest.mark.asyncio
    async def test_get_correlation_full_payload_members_enriched(self, client):
        """Detail members carry event-derived attributes (kind/source/camera/ts)."""
        r1 = await client.post(
            "/api/v1/correlations/events/ingest",
            json=_evt(f"EVT-T1-{uuid4().hex[:6]}", "CAM-01"),
        )
        group_id = r1.json()["correlation_id"]
        detail = await client.get(f"/api/v1/correlations/{group_id}")
        data = detail.json()
        assert data["members"][0]["kind"] == "DETECTION"
        assert data["members"][0]["camera_id"] == "CAM-01"
        assert data["members"][0]["source"] in ("VIRTUAL_FENCE", "UNKNOWN")


class TestCorrelationRepoLevel:
    @pytest.mark.asyncio
    async def test_verify_inconsistent_when_rel_removed(self, db_session):
        """A supporting member disconnected from every relation => INCONSISTENT."""
        from app.domain.event_correlation.group_service import CorrelationService
        from app.repositories.event_correlation import CorrelationRelationshipRepository

        now = datetime.now(timezone.utc)
        service = CorrelationService(db_session)
        first = await service.ingest_event(
            {"event_id": f"EVT-Q1-{uuid4().hex[:6]}", "camera_id": "CAM-01",
             "zone_id": "Z", "sector_id": "SEC-1", "event_time": now, "source": "TEST"},
        )
        group_id = first["correlation_id"]
        await service.ingest_event(
            {"event_id": f"EVT-Q2-{uuid4().hex[:6]}", "camera_id": "CAM-01",
             "zone_id": "Z", "sector_id": "SEC-1",
             "event_time": now + timedelta(seconds=5), "source": "TEST"},
        )

        rel_repo = CorrelationRelationshipRepository(db_session)
        for rel in await rel_repo.list_by_group(group_id):
            await rel_repo.delete(rel.id)
        await db_session.commit()

        result = await service.verify_correlation(group_id)
        assert result["status"] == "INCONSISTENT"
        assert len(result["orphaned_members"]) == 1

    @pytest.mark.asyncio
    async def test_verify_verified_for_single_member(self, db_session):
        """A standalone single-member group is VERIFIED (primary is exempt)."""
        from app.domain.event_correlation.group_service import CorrelationService

        service = CorrelationService(db_session)
        first = await service.ingest_event(
            {"event_id": f"EVT-R1-{uuid4().hex[:6]}", "camera_id": "CAM-01",
             "zone_id": "Z", "sector_id": "SEC-1", "event_time": datetime.now(timezone.utc), "source": "TEST"},
        )
        result = await service.verify_correlation(first["correlation_id"])
        assert result["status"] == "VERIFIED"


class TestBatchedReadParity:
    """Lock the batched read paths to per-group semantics.

    ``list_by_groups`` and ``_group_dicts_batched`` removed an O(groups x
    members) read pattern from the ingest/list hot paths; these tests pin them
    to the pre-existing per-group behavior: identical rows, identical
    ordering, identical group dicts, duplicate-id tolerance, empty input.
    """

    @staticmethod
    async def _seed_groups(db_session):
        from app.domain.event_correlation.group_service import CorrelationService

        service = CorrelationService(db_session)
        base = datetime(2026, 2, 1, 10, 0, 0, tzinfo=timezone.utc)
        # Two multi-member groups on distinct cameras plus one singleton. Each
        # seed group stays within one camera/sector/track, so cross-group
        # temporal+spatial+entity scores stay zero (hard gate keeps the
        # grouping deterministic and independent of ingest order).
        for camera_idx, member_count in ((1, 2), (2, 3), (3, 1)):
            for j in range(member_count):
                result = await service.ingest_event(
                    {
                        "event_id": f"EVT-PAR-{camera_idx}-{j}",
                        "camera_id": f"CAM-PAR-{camera_idx}",
                        "zone_id": f"ZONE-PAR-{camera_idx}",
                        "sector_id": f"SEC-PAR-{camera_idx}",
                        "track_id": f"TRK-PAR-{camera_idx}",
                        "event_time": base + timedelta(seconds=5 * j),
                        "source": "TEST",
                    }
                )
                if j == 0:
                    assert result["action"] == "CREATED"
                else:
                    assert result["action"] == "UPDATED"
        return service

    @pytest.mark.asyncio
    async def test_member_and_relationship_batch_parity(self, db_session):
        from app.repositories.event_correlation import (
            CorrelationGroupMemberRepository,
            CorrelationGroupRepository,
            CorrelationRelationshipRepository,
        )

        await self._seed_groups(db_session)
        groups = await CorrelationGroupRepository(db_session).list_active()
        assert len(groups) == 3
        ids = [g.correlation_id for g in groups]

        member_repo = CorrelationGroupMemberRepository(db_session)
        per_group_members = {gid: await member_repo.list_by_group(gid) for gid in ids}
        batched_members = await member_repo.list_by_groups(ids)
        assert set(batched_members) == set(ids)
        for gid in ids:
            assert [(m.id, m.event_id) for m in batched_members[gid]] == [
                (m.id, m.event_id) for m in per_group_members[gid]
            ]

        # Observed-time ordering inside a group is preserved (Event.ts asc).
        multi_id = next(gid for gid in ids if len(per_group_members[gid]) == 3)
        assert [m.event_id for m in batched_members[multi_id]] == [
            "EVT-PAR-2-0",
            "EVT-PAR-2-1",
            "EVT-PAR-2-2",
        ]

        # Duplicate ids in one request never duplicate rows.
        repeated = await member_repo.list_by_groups([multi_id, multi_id])
        assert [m.id for m in repeated[multi_id]] == [
            m.id for m in batched_members[multi_id]
        ]

        rel_repo = CorrelationRelationshipRepository(db_session)
        per_group_rels = {gid: await rel_repo.list_by_group(gid) for gid in ids}
        batched_rels = await rel_repo.list_by_groups(ids)
        assert set(batched_rels) == {gid for gid in ids if per_group_rels[gid]}
        for gid in ids:
            assert [(r.id, r.type) for r in batched_rels.get(gid, [])] == [
                (r.id, r.type) for r in per_group_rels[gid]
            ]

        # Empty input short-circuits without touching the database.
        assert await member_repo.list_by_groups([]) == {}
        assert await rel_repo.list_by_groups([]) == {}

    @pytest.mark.asyncio
    async def test_group_dicts_batched_matches_per_group_build(self, db_session):
        """The ingest hot path builds byte-identical candidate group dicts."""
        from app.repositories.event_correlation import CorrelationGroupRepository

        service = await self._seed_groups(db_session)
        groups = await CorrelationGroupRepository(db_session).list_active()
        assert len(groups) == 3

        per_group = [await service._group_to_dict(g) for g in groups]
        batched = await service._group_dicts_batched(groups)
        assert batched == [d for d in per_group if d is not None]
        assert sorted(len(d["member_events"]) for d in batched) == [1, 2, 3]
        assert await service._group_dicts_batched([]) == []


class TestTemporalPrefilterParity:
    """Lock the ingest temporal prefilter to the rule engine's temporal gate.

    ``_temporal_candidate_prefilter`` drops active groups whose observed span
    lies farther than ``window + 2 * clock_skew`` (default 60s + 10s = 70s)
    from the incoming event on BOTH bounds: the group's ``started_at`` and its
    latest member timestamp. The engine skips those groups at its first gate
    anyway, so ingest decisions must be identical with and without the
    prefilter -- including exactly on the decision boundary.
    """

    # Twin group span [t0, t0 + 5s]; probe offset in seconds -> expected
    # (action, score, status, membership_type). Non-temporal contribution is a
    # fixed 55 (same camera 30 + same track 15 + source compatibility 10), so
    # score = int(0.45 * temporal_confidence + 55). A point-vs-point temporal
    # relation EXISTS whenever the offset is within +/- 70s of either bound
    # (confidence floors at 0, but the relation still counts).
    _OFFSET_EXPECTATIONS = {
        -120: ("CREATED", 0, "STANDALONE", "PRIMARY"),
        -71: ("CREATED", 0, "STANDALONE", "PRIMARY"),
        -70: ("UPDATED", 55, "RELATED", "CONTEXT"),  # boundary: conf 0 via started_at
        -65: ("UPDATED", 55, "RELATED", "CONTEXT"),  # conf 0 via started_at
        -40: ("UPDATED", 70, "CORRELATED", "SUPPORTING"),
        -5: ("UPDATED", 96, "CORRELATED", "SUPPORTING"),
        0: ("UPDATED", 100, "CORRELATED", "SUPPORTING"),
        5: ("UPDATED", 100, "CORRELATED", "SUPPORTING"),  # conf 100 via ended_at
        65: ("UPDATED", 55, "RELATED", "CONTEXT"),
        70: ("UPDATED", 55, "RELATED", "CONTEXT"),  # boundary: conf 0 via started_at
        75: ("UPDATED", 55, "RELATED", "CONTEXT"),  # boundary: kept ONLY via latest-member bound
        76: ("CREATED", 0, "STANDALONE", "PRIMARY"),
        120: ("CREATED", 0, "STANDALONE", "PRIMARY"),
    }

    @pytest.mark.asyncio
    async def test_ingest_decisions_identical_with_and_without_prefilter(self, db_session):
        from app.domain.event_correlation.group_service import CorrelationService

        service_a = CorrelationService(db_session)
        service_b = CorrelationService(db_session)

        async def _no_prefilter(groups, rule, event_ts):
            return groups

        service_b._temporal_candidate_prefilter = _no_prefilter

        base = datetime(2026, 3, 1, 6, 0, 0, tzinfo=timezone.utc)

        def _payload(event_id, copy, index, ts):
            camera = f"CAM-PAIR-{index}-{copy}"
            return {
                "event_id": event_id,
                "camera_id": camera,
                "zone_id": f"ZONE-{camera}",
                "sector_id": f"SEC-{camera}",
                "track_id": f"TRK-{camera}",
                "event_time": ts,
                "source": "VIRTUAL_FENCE",
            }

        for index, (offset, expected) in enumerate(sorted(self._OFFSET_EXPECTATIONS.items())):
            # 2h stagger between offset pairs keeps every twin's neighbourhood
            # clear of all other twins; per-copy unique camera/zone/sector/track
            # makes cross-copy matches impossible (spatial gate blocks them).
            t0 = base + timedelta(hours=2 * index)
            twin_ids: dict[str, str] = {}
            for copy in ("A", "B"):
                service = service_a if copy == "A" else service_b
                first = await service.ingest_event(
                    _payload(f"EVT-PRF-{index}-{copy}-0", copy, index, t0)
                )
                assert first["action"] == "CREATED"
                twin_id = first["correlation_id"]
                second = await service.ingest_event(
                    _payload(
                        f"EVT-PRF-{index}-{copy}-1", copy, index,
                        t0 + timedelta(seconds=5),
                    )
                )
                assert second["action"] == "UPDATED"
                assert second["group_id"] == twin_id
                assert second["score"] == 96
                assert second["status"] == "CORRELATED"
                twin_ids[copy] = twin_id

            probe_time = t0 + timedelta(seconds=offset)
            decisions = {}
            responses = {}
            for copy in ("A", "B"):
                service = service_a if copy == "A" else service_b
                resp = await service.ingest_event(
                    _payload(f"EVT-PRF-{index}-{copy}-PROBE", copy, index, probe_time)
                )
                responses[copy] = resp
                decisions[copy] = (
                    resp["action"], resp["score"], resp["status"], resp["membership_type"],
                )

            detail = f"offset {offset} (index {index})"
            assert decisions["A"] == decisions["B"], f"prefilter changed the decision at {detail}"
            assert decisions["A"] == expected, f"unexpected decision at {detail}: {decisions['A']}"

            for copy, resp in responses.items():
                if resp["action"] == "UPDATED":
                    assert resp["group_id"] == twin_ids[copy]
                    assert resp["correlation_id"] == twin_ids[copy]
                else:
                    assert resp["group_id"] != twin_ids[copy]
                    assert resp["correlation_id"] != twin_ids[copy]

        # 13 twins x 2 copies + 4 CREATED probes x 2 copies; nothing closes (B-06).
        active = await service_a.group_repo.list_active()
        assert len(active) == 34

    @pytest.mark.asyncio
    async def test_prefilter_keeps_exactly_the_engine_temporal_gate(self, db_session):
        from app.domain.event_correlation.group_service import CorrelationService, _to_aware

        service = CorrelationService(db_session)
        base = datetime(2026, 4, 1, 6, 0, 0, tzinfo=timezone.utc)

        async def _seed(camera, times):
            for i, ts in enumerate(times):
                resp = await service.ingest_event({
                    "event_id": f"EVT-BND-{camera}-{i}",
                    "camera_id": camera,
                    "zone_id": f"ZONE-{camera}",
                    "sector_id": f"SEC-{camera}",
                    "track_id": f"TRK-{camera}",
                    "event_time": ts,
                    "source": "VIRTUAL_FENCE",
                })
                assert resp["action"] == ("CREATED" if i == 0 else "UPDATED")

        # Layout: G1 span [base, base+5s], G2 span [base+2h, base+2h+10s],
        # G3 singleton at base+4h. Layout groups are 2h+ apart, so seeds cannot
        # attach to another group.
        await _seed("CAM-BND-1", [base, base + timedelta(seconds=5)])
        await _seed(
            "CAM-BND-2",
            [base + timedelta(hours=2), base + timedelta(hours=2, seconds=10)],
        )
        await _seed("CAM-BND-3", [base + timedelta(hours=4)])

        rule = await service._build_rule_engine({})
        groups = await service.group_repo.list_active()
        assert len(groups) == 3
        group_dicts = await service._group_dicts_batched(groups)
        assert len(group_dicts) == 3
        by_id = {d["correlation_id"]: d for d in group_dicts}
        g1, g2, g3 = (by_id[g.correlation_id] for g in sorted(groups, key=lambda g: g.started_at))

        # The prefilter's second bound must be the same MAX(Event.ts) the group
        # dict reports as ended_at (the value the engine classifies against).
        latest = await service.member_repo.latest_event_ts_by_groups(
            [g.correlation_id for g in groups]
        )
        assert set(latest) == set(by_id)
        for gid, ts in latest.items():
            assert _to_aware(ts) == _to_aware(by_id[gid]["ended_at"])

        probes = [
            (base - timedelta(seconds=71), set()),
            (base - timedelta(seconds=70), {g1["correlation_id"]}),
            (base - timedelta(seconds=65), {g1["correlation_id"]}),
            (base + timedelta(seconds=2), {g1["correlation_id"]}),
            (base + timedelta(seconds=75), {g1["correlation_id"]}),  # latest-member boundary
            (base + timedelta(seconds=76), set()),
            (base + timedelta(hours=1), set()),
            (base + timedelta(hours=2, seconds=80), {g2["correlation_id"]}),  # latest-member boundary
            (base + timedelta(hours=2, seconds=81), set()),
            (base + timedelta(hours=4, seconds=70), {g3["correlation_id"]}),
            (base + timedelta(hours=4, seconds=71), set()),
        ]
        for probe_time, expected_ids in probes:
            kept = await service._temporal_candidate_prefilter(groups, rule, probe_time)
            kept_ids = {g.correlation_id for g in kept}
            engine_event = {"event_id": "EVT-BND-PROBE", "event_time": probe_time}
            engine_ids = {
                d["correlation_id"]
                for d in group_dicts
                if rule._temporal_vs_group(engine_event, d)
            }
            assert kept_ids == engine_ids, f"prefilter diverged from engine at {probe_time}"
            assert kept_ids == expected_ids, f"unexpected keep set at {probe_time}"

        # Defensive branches: no groups, and no comparable event time anchor.
        assert await service._temporal_candidate_prefilter([], rule, base) == []
        kept_all = await service._temporal_candidate_prefilter(groups, rule, None)
        assert {g.correlation_id for g in kept_all} == set(by_id)

    @pytest.mark.asyncio
    async def test_latest_event_ts_matches_group_dict_ended_at(self, db_session):
        from app.domain.event_correlation.group_service import CorrelationService, _to_aware

        service = CorrelationService(db_session)
        base = datetime(2026, 5, 1, 6, 0, 0, tzinfo=timezone.utc)

        def _payload(event_id, camera, ts):
            return {
                "event_id": event_id,
                "camera_id": camera,
                "zone_id": f"ZONE-{camera}",
                "sector_id": f"SEC-{camera}",
                "track_id": f"TRK-{camera}",
                "event_time": ts,
                "source": "VIRTUAL_FENCE",
            }

        # Out-of-order arrival: the later event lands first, the earlier one
        # joins late. MAX(Event.ts) must still reflect observed time.
        first = await service.ingest_event(
            _payload("EVT-LAT-1-0", "CAM-LAT-1", base + timedelta(seconds=30))
        )
        assert first["action"] == "CREATED"
        late = await service.ingest_event(_payload("EVT-LAT-1-1", "CAM-LAT-1", base))
        assert late["action"] == "UPDATED"
        assert late["score"] == 77
        assert late["status"] == "CORRELATED"
        assert late["group_id"] == first["correlation_id"]

        first2 = await service.ingest_event(_payload("EVT-LAT-2-0", "CAM-LAT-2", base))
        assert first2["action"] == "CREATED"
        second2 = await service.ingest_event(
            _payload("EVT-LAT-2-1", "CAM-LAT-2", base + timedelta(seconds=15))
        )
        assert second2["action"] == "UPDATED"
        assert second2["score"] == 88

        groups = await service.group_repo.list_active()
        assert len(groups) == 2
        group_dicts = await service._group_dicts_batched(groups)
        latest = await service.member_repo.latest_event_ts_by_groups(
            [g.correlation_id for g in groups]
        )
        assert set(latest) == {d["correlation_id"] for d in group_dicts}
        for d in group_dicts:
            assert _to_aware(latest[d["correlation_id"]]) == _to_aware(d["ended_at"])

        # The group whose earliest observed event arrived last still reports
        # its later bound as ended_at.
        assert _to_aware(latest[first["correlation_id"]]) == base + timedelta(seconds=30)

        assert await service.member_repo.latest_event_ts_by_groups([]) == {}