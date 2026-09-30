"""Component 4 — Correlated Situation Engine: grouping gates, list filters, risk by reference.

Covers the remaining C4 acceptance criteria not exercised by the existing suites:
  - temporal window semantics across a day boundary (22:41 vs 03:20 never correlate)
  - camera adjacency comes from the CONFIGURED topology, never from id proximity
  - min_support_events holds a correlation provisional (UNCERTAIN) until support exists
  - max_group_duration splits a situation instead of chaining one group forever
  - list filters: severity (band of the highest-scoring referenced incident),
    time_range, status, source, search — combined filters keep earlier conditions (§58)
  - risk is surfaced BY REFERENCE from C1 incidents; C4 never computes a score,
    and an unscored group never presents as LOW
  - history records every transition (no truncation)
  - config rejection: unknown keys, and merged PATCH validation
"""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone
from uuid import uuid4

from httpx import AsyncClient, ASGITransport


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


def _uid(prefix: str) -> str:
    return f"{prefix}-{uuid4().hex[:8]}"


async def _ingest(client: AsyncClient, payload: dict) -> dict:
    resp = await client.post("/api/v1/correlations/events/ingest", json=payload)
    assert resp.status_code == 200, resp.text
    return resp.json()


def _group_of(result: dict) -> str:
    return result.get("group_id") or result.get("correlation_id")


@pytest.fixture
def client(app):
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _link_incident(db_session, event_id: str, risk_score: int, severity: str, camera: str) -> str:
    """Persist a C1-owned incident row referencing an ingested event.

    Correlation reads incidents by reference only; this writes the C1 side so
    the by-reference surfacing can be asserted.
    """
    from app.models.incident import Incident

    incident = Incident(
        risk_score=risk_score,
        severity=severity,
        factors_json="[]",
        event_id=event_id,
        camera_id=camera,
        track_id=f"TRK-{camera}",
        zone_id=f"ZONE-{camera}",
    )
    db_session.add(incident)
    await db_session.commit()
    return incident.incident_id


# ─── Temporal window semantics across a day boundary ──────────────────────────

class TestTemporalWindowSemantics:
    @pytest.mark.asyncio
    async def test_day_boundary_events_never_correlate(self, client):
        """22:41 and 03:20 (next day) are ~4h39m apart: separate situations.

        Guards against wrap-around arithmetic that would treat a late-evening
        and an early-morning timestamp as 'close'.
        """
        late = datetime(2026, 1, 1, 22, 41, 0, tzinfo=timezone.utc)
        early = datetime(2026, 1, 2, 3, 20, 0, tzinfo=timezone.utc)

        r1 = await _ingest(client, _evt(_uid("EVT-N1"), "CAM-01", event_time=late.isoformat()))
        r2 = await _ingest(client, _evt(_uid("EVT-N2"), "CAM-01", event_time=early.isoformat()))

        assert r1["action"] == "CREATED"
        assert r2["action"] == "CREATED"
        assert _group_of(r1) != _group_of(r2)

    @pytest.mark.asyncio
    async def test_events_within_window_across_midnight_correlate(self, client):
        """23:59:50 and 00:00:10 are 20s apart: one situation."""
        before = datetime(2026, 1, 1, 23, 59, 50, tzinfo=timezone.utc)
        after = datetime(2026, 1, 2, 0, 0, 10, tzinfo=timezone.utc)

        r1 = await _ingest(client, _evt(_uid("EVT-N3"), "CAM-01", event_time=before.isoformat()))
        r2 = await _ingest(client, _evt(_uid("EVT-N4"), "CAM-01", event_time=after.isoformat()))

        assert r2["action"] == "UPDATED", r2
        assert _group_of(r2) == _group_of(r1)


# ─── Adjacency is topology from config, never id proximity ────────────────────

class TestAdjacencyTopology:
    @pytest.mark.asyncio
    async def test_adjacency_follows_configured_topology_not_id_order(self, client):
        """Only the configured pair correlates; a numerically-close camera does not."""
        cfg = await client.post(
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
        assert cfg.status_code == 200, cfg.text

        now = datetime.now(timezone.utc)
        r1 = await _ingest(client, _evt(_uid("EVT-AD1"), "CAM-01", event_time=now.isoformat()))
        gid_a = _group_of(r1)

        # CAM-03 is id-adjacent to CAM-01 but absent from the topology, and shares
        # neither sector, zone nor track: simultaneity alone must not correlate it.
        r3 = await _ingest(
            client,
            _evt(_uid("EVT-AD3"), "CAM-03",
                 sector_id="SEC-3", zone_id="ZONE-CAM-03",
                 event_time=(now + timedelta(seconds=5)).isoformat()),
        )
        assert r3["action"] == "CREATED", r3
        assert _group_of(r3) != gid_a

        # The configured neighbour correlates even though the sector differs.
        r2 = await _ingest(
            client,
            _evt(_uid("EVT-AD2"), "CAM-02",
                 sector_id="SEC-2", zone_id="ZONE-CAM-02",
                 event_time=(now + timedelta(seconds=5)).isoformat()),
        )
        assert r2["action"] == "UPDATED", r2
        assert _group_of(r2) == gid_a

        detail = await client.get(f"/api/v1/correlations/{gid_a}")
        rels = detail.json()["relationships"]
        adjacent = [
            r for r in rels
            if r["type"] == "SPATIAL" and (r.get("evidence_json") or {}).get("subtype") == "ADJACENT_CAMERA"
        ]
        assert adjacent, f"expected ADJACENT_CAMERA relation: {rels}"
        assert adjacent[0]["explanation"]


# ─── Grouping gates: min_support_events / max_group_duration ─────────────────

class TestGroupingGates:
    @pytest.mark.asyncio
    async def test_min_support_events_holds_group_provisional(self, client):
        """With min_support_events=3, a 2-event group is UNCERTAIN until support exists."""
        cfg = await client.post(
            "/api/v1/correlations/config",
            json={
                "profile": "MIXED_BORDER_SECTOR",
                "temporal_window_seconds": 600,
                "max_group_duration_seconds": 3600,
                "min_relationship_strength": 50,
                "min_support_events": 3,
                "active": True,
            },
        )
        assert cfg.status_code == 200, cfg.text

        now = datetime.now(timezone.utc)
        r1 = await _ingest(client, _evt(_uid("EVT-MS1"), "CAM-01", event_time=now.isoformat()))
        gid = _group_of(r1)

        r2 = await _ingest(
            client, _evt(_uid("EVT-MS2"), "CAM-01", event_time=(now + timedelta(seconds=5)).isoformat())
        )
        assert r2["action"] == "UPDATED"
        assert r2["group_id"] == gid
        assert r2["status"] == "UNCERTAIN", f"support 2 < minimum 3 must stay provisional: {r2}"

        r3 = await _ingest(
            client, _evt(_uid("EVT-MS3"), "CAM-01", event_time=(now + timedelta(seconds=10)).isoformat())
        )
        assert r3["action"] == "UPDATED"
        assert r3["group_id"] == gid
        assert r3["status"] == "CORRELATED", f"support 3 meets the minimum: {r3}"

    @pytest.mark.asyncio
    async def test_max_group_duration_splits_situation(self, client):
        """An event that would extend the span past the maximum starts a new group."""
        cfg = await client.post(
            "/api/v1/correlations/config",
            json={
                "profile": "MIXED_BORDER_SECTOR",
                "temporal_window_seconds": 200,
                "max_group_duration_seconds": 250,
                "min_relationship_strength": 50,
                "active": True,
            },
        )
        assert cfg.status_code == 200, cfg.text

        base = datetime.now(timezone.utc)
        r1 = await _ingest(client, _evt(_uid("EVT-MD1"), "CAM-01", event_time=base.isoformat()))
        gid = _group_of(r1)

        r2 = await _ingest(
            client, _evt(_uid("EVT-MD2"), "CAM-01", event_time=(base + timedelta(seconds=150)).isoformat())
        )
        assert r2["action"] == "UPDATED", r2
        assert r2["group_id"] == gid

        # +300s is inside the 200s temporal window of the group's latest bound, so
        # only the 250s maximum duration can exclude it.
        r3 = await _ingest(
            client, _evt(_uid("EVT-MD3"), "CAM-01", event_time=(base + timedelta(seconds=300)).isoformat())
        )
        assert r3["action"] == "CREATED", f"span 300s > maximum 250s must start a new situation: {r3}"
        assert r3["correlation_id"] != gid


# ─── List filters + risk by reference ────────────────────────────────────────

class TestListFiltersAndRiskReference:
    async def _seed_two_groups(self, client):
        """Group A (2 same-camera events) and group B (isolated camera/sector)."""
        now = datetime.now(timezone.utc)
        a1 = _uid("EVT-FA1")
        r1 = await _ingest(client, _evt(a1, "CAM-71", event_time=now.isoformat()))
        gid_a = _group_of(r1)
        a2 = _uid("EVT-FA2")
        r2 = await _ingest(
            client, _evt(a2, "CAM-71", event_time=(now + timedelta(seconds=5)).isoformat())
        )
        assert r2["action"] == "UPDATED" and r2["group_id"] == gid_a
        b1 = _uid("EVT-FB1")
        r3 = await _ingest(
            client,
            _evt(b1, "CAM-72", sector_id="SEC-72", zone_id="ZONE-CAM-72", event_time=now.isoformat()),
        )
        gid_b = _group_of(r3)
        assert r3["action"] == "CREATED" and gid_b != gid_a
        return gid_a, a1, a2, gid_b, b1

    @pytest.mark.asyncio
    async def test_severity_filter_uses_referenced_incident_band(self, client, db_session):
        """severity=HIGH selects the group whose referenced incident is in the HIGH band."""
        gid_a, a1, a2, gid_b, b1 = await self._seed_two_groups(client)
        incident_id = await _link_incident(db_session, a1, 82, "HIGH", "CAM-71")

        resp = await client.get("/api/v1/correlations/", params={"severity": "HIGH"})
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["total"] == 1, data
        group = data["groups"][0]
        assert group["correlation_id"] == gid_a
        assert group["risk_score"] == 82
        assert group["risk_severity"] == "HIGH"
        assert group["risk_incident_ids"] == [incident_id]

        assert (await client.get("/api/v1/correlations/", params={"severity": "CRITICAL"})).json()["total"] == 0

    @pytest.mark.asyncio
    async def test_unscored_group_never_matches_a_severity_band(self, client, db_session):
        """No incident => no score: the group is absent from every severity filter."""
        gid_a, a1, a2, gid_b, b1 = await self._seed_two_groups(client)
        await _link_incident(db_session, a1, 82, "HIGH", "CAM-71")

        for band in ("LOW", "MEDIUM", "HIGH", "CRITICAL"):
            data = (await client.get("/api/v1/correlations/", params={"severity": band})).json()
            ids = [g["correlation_id"] for g in data["groups"]]
            assert gid_b not in ids, f"unscored group must not present as {band}: {data}"

        detail = (await client.get(f"/api/v1/correlations/{gid_b}")).json()
        assert detail["risk_score"] is None
        assert detail["risk_severity"] is None
        assert detail["risk_incident_ids"] == []

    @pytest.mark.asyncio
    async def test_group_severity_is_the_highest_scoring_referenced_incident(self, client, db_session):
        gid_a, a1, a2, gid_b, b1 = await self._seed_two_groups(client)
        high_id = await _link_incident(db_session, a1, 82, "HIGH", "CAM-71")
        top_id = await _link_incident(db_session, a2, 92, "CRITICAL", "CAM-71")

        critical = (await client.get("/api/v1/correlations/", params={"severity": "CRITICAL"})).json()
        assert critical["total"] == 1
        group = critical["groups"][0]
        assert group["correlation_id"] == gid_a
        assert group["risk_score"] == 92
        assert group["risk_severity"] == "CRITICAL"
        assert group["risk_incident_ids"] == sorted([high_id, top_id])
        assert (await client.get("/api/v1/correlations/", params={"severity": "HIGH"})).json()["total"] == 0

    @pytest.mark.asyncio
    async def test_time_range_filter_windows_started_at(self, client):
        old = datetime.now(timezone.utc) - timedelta(days=2)
        r_old = await _ingest(client, _evt(_uid("EVT-TR-OLD"), "CAM-81", event_time=old.isoformat()))
        gid_old = _group_of(r_old)
        r_new = await _ingest(
            client,
            _evt(_uid("EVT-TR-NEW"), "CAM-82", sector_id="SEC-82", zone_id="ZONE-CAM-82"),
        )
        gid_new = _group_of(r_new)

        recent = (await client.get("/api/v1/correlations/", params={"time_range": "15m"})).json()
        assert [g["correlation_id"] for g in recent["groups"]] == [gid_new]
        assert recent["total"] == 1

        today = (await client.get("/api/v1/correlations/", params={"time_range": "today"})).json()
        assert [g["correlation_id"] for g in today["groups"]] == [gid_new]

        unfiltered = (await client.get("/api/v1/correlations/", params={"page_size": 50})).json()
        all_ids = [g["correlation_id"] for g in unfiltered["groups"]]
        assert gid_old in all_ids and gid_new in all_ids

    @pytest.mark.asyncio
    async def test_search_matches_group_and_member_event_ids(self, client):
        gid_a, a1, a2, gid_b, b1 = await self._seed_two_groups(client)

        by_member = (await client.get("/api/v1/correlations/", params={"search": a1})).json()
        assert by_member["total"] == 1, by_member
        assert by_member["groups"][0]["correlation_id"] == gid_a

        by_group = (await client.get("/api/v1/correlations/", params={"search": gid_b})).json()
        assert by_group["total"] == 1
        assert by_group["groups"][0]["correlation_id"] == gid_b

        missing = (await client.get("/api/v1/correlations/", params={"search": "NO-SUCH-SIGNAL"})).json()
        assert missing["total"] == 0

    @pytest.mark.asyncio
    async def test_search_matches_member_camera_track_and_incident(self, client, db_session):
        """The Event Log search box promises CAM/TRK/INC; each must resolve."""
        gid_a, a1, a2, gid_b, b1 = await self._seed_two_groups(client)
        incident_id = await _link_incident(db_session, a1, 72, "MEDIUM", "CAM-71")

        by_camera = (await client.get("/api/v1/correlations/", params={"search": "CAM-71"})).json()
        assert by_camera["total"] == 1, by_camera
        assert by_camera["groups"][0]["correlation_id"] == gid_a

        by_track = (await client.get("/api/v1/correlations/", params={"search": "TRK-CAM-72"})).json()
        assert by_track["total"] == 1, by_track
        assert by_track["groups"][0]["correlation_id"] == gid_b

        by_incident = (await client.get("/api/v1/correlations/", params={"search": incident_id})).json()
        assert by_incident["total"] == 1, by_incident
        assert by_incident["groups"][0]["correlation_id"] == gid_a

    @pytest.mark.asyncio
    async def test_combined_filters_keep_every_condition(self, client, db_session):
        """§58: adding a filter never overwrites the previous WHERE clause."""
        gid_a, a1, a2, gid_b, b1 = await self._seed_two_groups(client)
        await _link_incident(db_session, a1, 82, "HIGH", "CAM-71")

        combined = await client.get(
            "/api/v1/correlations/",
            params={
                "severity": "HIGH",
                "camera_id": "CAM-71",
                "status": "CORRELATED",
                "source": "TEST",
                "time_range": "1h",
                "search": a1,
            },
        )
        assert combined.status_code == 200, combined.text
        data = combined.json()
        assert data["total"] == 1, data
        assert data["groups"][0]["correlation_id"] == gid_a

        # Flipping one condition must narrow to nothing rather than widen the result.
        for key, value in (
            ("severity", "CRITICAL"),
            ("camera_id", "CAM-72"),
            ("status", "DISSOLVED"),
            ("source", "NO_SUCH_SOURCE"),
            ("search", "NO-SUCH-SIGNAL"),
        ):
            params = {
                "severity": "HIGH", "camera_id": "CAM-71", "status": "CORRELATED",
                "source": "TEST", "time_range": "1h", "search": a1,
            }
            params[key] = value
            resp = (await client.get("/api/v1/correlations/", params=params)).json()
            assert resp["total"] == 0, f"{key}={value} must narrow the combined filter: {resp}"


# ─── History is never truncated ──────────────────────────────────────────────

class TestHistoryCompleteness:
    @pytest.mark.asyncio
    async def test_every_transition_is_recorded(self, client):
        """N ingests into one group produce N ordered history revisions."""
        now = datetime.now(timezone.utc)
        r1 = await _ingest(client, _evt(_uid("EVT-HS1"), "CAM-61", event_time=now.isoformat()))
        gid = _group_of(r1)
        ingest_count = 1
        for offset in range(1, 7):
            r = await _ingest(
                client,
                _evt(_uid(f"EVT-HS{offset + 1}"), "CAM-61",
                     event_time=(now + timedelta(seconds=offset * 3)).isoformat()),
            )
            assert r["action"] == "UPDATED", r
            ingest_count += 1

        hist = (await client.get(f"/api/v1/correlations/{gid}/history")).json()["history"]
        revisions = [h["revision"] for h in hist]
        assert len(hist) == ingest_count, f"{ingest_count} ingests must leave {ingest_count} transitions: {revisions}"
        assert revisions == sorted(revisions)
        assert len(set(revisions)) == len(revisions)


# ─── Config rejection (unknown keys + merged PATCH validation) ───────────────

class TestConfigRejection:
    @pytest.mark.asyncio
    async def test_unknown_config_key_rejected(self, client):
        resp = await client.post(
            "/api/v1/correlations/config",
            json={"profile": "MIXED_BORDER_SECTOR", "temporal_window": 120},
        )
        assert resp.status_code == 422
        assert "temporal_window" in resp.text

    @pytest.mark.asyncio
    async def test_unknown_key_rejected_on_patch(self, client):
        created = await client.post(
            "/api/v1/correlations/config",
            json={"profile": "MIXED_BORDER_SECTOR", "temporal_window_seconds": 60},
        )
        assert created.status_code == 200
        config_id = created.json()["config_id"]

        resp = await client.patch(
            f"/api/v1/correlations/config/{config_id}",
            json={"risk_weight": 0.5},
        )
        assert resp.status_code == 422

    @pytest.mark.asyncio
    async def test_patch_validates_the_merged_result(self, client):
        """A partial PATCH cannot leave duration <= temporal window in storage."""
        created = await client.post(
            "/api/v1/correlations/config",
            json={
                "profile": "MIXED_BORDER_SECTOR",
                "temporal_window_seconds": 60,
                "max_group_duration_seconds": 300,
            },
        )
        assert created.status_code == 200
        config_id = created.json()["config_id"]

        rejected = await client.patch(
            f"/api/v1/correlations/config/{config_id}",
            json={"temporal_window_seconds": 400},
        )
        assert rejected.status_code == 422

        stored = (await client.get(f"/api/v1/correlations/config/{config_id}")).json()
        assert stored["temporal_window_seconds"] == 60
        assert stored["max_group_duration_seconds"] == 300

        accepted = await client.patch(
            f"/api/v1/correlations/config/{config_id}",
            json={"max_group_duration_seconds": 900},
        )
        assert accepted.status_code == 200
        assert accepted.json()["max_group_duration_seconds"] == 900
