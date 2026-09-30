# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 7 — ANPR API Tests (spec §52)
#
# API-level coverage for app/api/routes/anpr/routes.py:
#   · GET  /api/v1/anpr/sightings                     (+ filters / search / sort / cursor / 422)
#   · GET  /api/v1/anpr/sightings/recent
#   · GET  /api/v1/anpr/sightings/{id}                (+ 404)
#   · GET  /api/v1/anpr/sightings/{id}/candidates     (ranked, preserved; [] when unreadable)
#   · GET  /api/v1/anpr/vehicles/{id}                 (+ 404) and /history
#   · GET  /api/v1/anpr/cameras/{id}/vehicles         (+ /feed, /summary)
#   · GET  /api/v1/anpr/search                        (§24 five labels, precedence)
#   · GET  /api/v1/anpr/summary                       (§26 plate-observation counts)
#   · GET  /api/v1/anpr/health                        (+ no-provider state)
#   · GET  /api/v1/anpr/config/{camera_id}            (null when unset)
#   · POST /api/v1/anpr/internal/observe              (403 / ingest / idempotency /
#                                                      concurrency / 503 / timeout seam)
#
# §52 areas covered: models · schemas · provider · ingestion · idempotency ·
# concurrency · search · history · candidate preservation · quality · camera
# relationship · track relationship · event handoff · incident handoff ·
# evidence reference · provider failure · timeout.
#
# Test harness notes:
#   · ASGITransport does NOT run FastAPI startup events, so the ANPR provider
#     global is registered explicitly per test with a fresh DemoANPRProvider
#     and restored on teardown. Tests needing "no provider" / "not ready" /
#     "provider timeout" override it inline.
#   · INGEST REQUEST CONTRACT: the inbound schemas accept snake_case keys
#     (aliases) and reject unknown keys (extra="forbid"); the plate read is
#     keyed "plateRead" (plain field name, no alias). Tests pin this contract.
#   · READ RESPONSE WIRE FORMAT: every route uses response_model_by_alias=False
#     → serialized by FIELD NAME → camelCase (sightingId, vehicleTrackId,
#     plateRead, evidenceRef, sourceProvider, ...).
#   · Timestamps: VehicleSightingResponse.from_orm re-attaches UTC to naive
#     SQLite datetimes → exact '+00:00' strings. Aggregates computed from
#     raw isoformat values are asserted leniently (startswith).
#   · Only seeded, observable values are asserted — no fabricated metrics,
#     no OCR accuracy claims.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import asyncio
import pytest
from datetime import datetime, timezone

from httpx import AsyncClient, ASGITransport
from sqlalchemy import func, select

import app.domain.anpr.provider as pmod
from app.domain.anpr.demo_provider import DemoANPRProvider
from app.domain.anpr.provider import (
    ANPRProvider,
    ANPRProviderHealthInfo,
    ANPRProviderMetadata,
    set_anpr_provider,
)
from app.models.anpr import ANPRConfig, PlateCandidate, PlateRead, VehicleSighting

# ── Seeded scene constants ────────────────────────────────────────────────────

CAM7, CAM8, CAM13 = "CAM-07", "CAM-08", "CAM-13"

S1, S2, S3, S4, S5 = (
    "SGT-API-0001", "SGT-API-0002", "SGT-API-0003", "SGT-API-0004", "SGT-API-0005",
)

INTERNAL_HEADERS = {"X-Internal-Service": "test-suite"}


def _t(h: int, m: int, s: int = 0) -> datetime:
    """UTC timestamp on the seed date 2026-09-12."""
    return datetime(2026, 9, 12, h, m, s, tzinfo=timezone.utc)


def _iso(h: int, m: int, s: int = 0) -> str:
    return _t(h, m, s).isoformat()


# ── ORM seed builders (read-API tests) ────────────────────────────────────────

def _sighting(
    sighting_id: str, camera_id: str, observed: datetime, *,
    vehicle_id: str | None = None, track_id: str | None = None,
    detection_id: str | None = None, vehicle_class: str = "PERSONAL_CAR",
    direction: str = "NORTH", confidence: float | None = None,
    watchlist: str = "NOT_CHECKED", plate_quality: str | None = None,
    evidence: str | None = None, event: str | None = None,
    correlation: str | None = None, incident: str | None = None,
    location: str | None = None, provider: str | None = "ANPR-DEMO",
) -> VehicleSighting:
    return VehicleSighting(
        sighting_id=sighting_id, camera_id=camera_id, observed_at=observed,
        received_at=observed, vehicle_id=vehicle_id, track_id=track_id,
        detection_id=detection_id, vehicle_class=vehicle_class,
        vehicle_direction=direction, confidence=confidence,
        watchlist_status=watchlist, plate_quality=plate_quality,
        evidence_id=evidence, event_id=event, correlation_id=correlation,
        incident_id=incident, location_context=location, provider=provider,
    )


def _read(
    plate_read_id: str, sighting_id: str, observed: datetime,
    raw: str, normalized: str | None, *, confidence: float = 0.9,
    quality: str = "GOOD", format_status: str = "VALID_FORMAT",
    display: str | None = None,
) -> PlateRead:
    return PlateRead(
        plate_read_id=plate_read_id, sighting_id=sighting_id,
        raw_read=raw, normalized_read=normalized,
        display_read=display or normalized or raw,
        confidence=confidence, quality=quality, format_status=format_status,
        observed_at=observed, provider="ANPR-DEMO", provider_version="demo-1.0",
    )


def _cand(
    candidate_id: str, sighting_id: str, plate_read_id: str, rank: int,
    raw: str, normalized: str | None, confidence: float,
    format_status: str = "POSSIBLE_FORMAT",
) -> PlateCandidate:
    return PlateCandidate(
        candidate_id=candidate_id, sighting_id=sighting_id,
        plate_read_id=plate_read_id, rank=rank, raw_read=raw,
        normalized_read=normalized, confidence=confidence,
        format_status=format_status,
    )


# ── Ingest payload builders (snake_case contract + plateRead key) ─────────────

def _plate_payload(
    raw: str, *, normalized: str | None = None, display: str | None = None,
    confidence: float = 0.9, quality: str = "GOOD",
    format_status: str = "VALID_FORMAT", observed_at: str | None = None,
    sighting_id: str | None = None, candidates: list[dict] | None = None,
) -> dict:
    payload: dict = {
        "raw_read": raw,
        "display_read": display or normalized or raw,
        "confidence": confidence,
        "quality": quality,
        "format_status": format_status,
        "observed_at": observed_at or _iso(6, 0),
    }
    if normalized is not None:
        payload["normalized_read"] = normalized
    if sighting_id is not None:
        payload["sighting_id"] = sighting_id
    if candidates:
        payload["candidates"] = candidates
    return payload


def _sighting_payload(
    camera_id: str, observed_at: str, *, sighting_id: str | None = None,
    track_id: str | None = None, detection_id: str | None = None,
    vehicle_id: str | None = None, vehicle_class: str = "PERSONAL_CAR",
    direction: str = "NORTH", plate: dict | None = None, **extra,
) -> dict:
    item: dict = {"camera_id": camera_id, "observed_at": observed_at}
    if sighting_id is not None:
        item["sighting_id"] = sighting_id
    if track_id is not None:
        item["track_id"] = track_id
    if detection_id is not None:
        item["detection_id"] = detection_id
    if vehicle_id is not None:
        item["vehicle_id"] = vehicle_id
    item["vehicle_class"] = vehicle_class
    item["vehicle_direction"] = direction
    if plate is not None:
        item["plateRead"] = plate
    item.update(extra)
    return item


def _body(camera_id: str, sightings: list[dict], *, source: str = "LIVE") -> dict:
    return {"camera_id": camera_id, "source": source, "sightings": sightings}


class _TimeoutProvider(ANPRProvider):
    """Provider whose recognize() raises TimeoutError — pins §52 'timeout' seam."""

    _PROVIDER_NAME = "ANPR-TIMEOUT-STUB"

    def ready(self) -> bool:
        return True

    async def recognize(self, sightings, camera_context):  # noqa: ANN001
        raise asyncio.TimeoutError("ANPR inference timed out after 5000 ms")

    async def flush(self, camera_id: str):  # noqa: ANN201
        raise NotImplementedError

    def health(self) -> ANPRProviderHealthInfo:
        return ANPRProviderHealthInfo(state="READY", provider_name=self._PROVIDER_NAME)

    def metadata(self) -> ANPRProviderMetadata:
        return ANPRProviderMetadata(provider_name=self._PROVIDER_NAME)

    async def shutdown(self) -> None:
        return None


class TestANPRAPI:
    """API-level tests for the Component 7 ANPR routes."""

    @pytest.fixture
    def client(self, app):
        return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")

    @pytest.fixture(autouse=True)
    async def anpr_provider(self):
        """Fresh demo provider per test (startup events do not run under ASGITransport)."""
        original = pmod._anpr_provider
        provider = DemoANPRProvider()
        await provider.initialize()
        set_anpr_provider(provider)
        yield provider
        pmod._anpr_provider = original

    async def _seed_scene(self, db_session) -> None:
        """
        Seed 5 sightings:
          S1 CAM-07 VEH-API-A (plate HR26AK4521, 3 candidates, evidence/event/
             correlation/incident refs, CLEAR)
          S2 CAM-07 VEH-API-A (no plate read — same vehicle as S1)
          S3 CAM-08 VEH-API-B (raw PB1OGR7788 → normalized PB10GR7788, GLARE,
             1 candidate)
          S4 CAM-07 VEH-API-C (no plate read, MOTORCYCLE, no track)
          S5 CAM-13 VEH-API-D (PARTIAL DL8C__123, NOT_ENOUGH_DATA)
        """
        db_session.add_all([
            _sighting(S1, CAM7, _t(5, 50), vehicle_id="VEH-API-A",
                      track_id="TRK-API-A", detection_id="DET-API-A",
                      confidence=0.93, watchlist="CLEAR", plate_quality="GOOD",
                      evidence="EV-API-1", event="EVT-API-1",
                      correlation="CORR-API-1", incident="INC-API-1",
                      location="NH-44 Checkpoint Alpha"),
            _sighting(S2, CAM7, _t(5, 52), vehicle_id="VEH-API-A",
                      track_id="TRK-API-A2", confidence=0.85),
            _sighting(S3, CAM8, _t(5, 51), vehicle_id="VEH-API-B",
                      track_id="TRK-API-B", vehicle_class="TRUCK",
                      direction="SOUTH", confidence=0.42, plate_quality="GLARE"),
            _sighting(S4, CAM7, _t(5, 54), vehicle_id="VEH-API-C",
                      vehicle_class="MOTORCYCLE", direction="UNKNOWN"),
            _sighting(S5, CAM13, _t(5, 56), vehicle_id="VEH-API-D",
                      track_id="TRK-API-D", vehicle_class="VAN",
                      direction="WEST", confidence=0.34, plate_quality="PARTIAL"),
        ])
        db_session.add_all([
            _read("PRD-API-1", S1, _t(5, 50), "HR26AK4521", "HR26AK4521",
                  confidence=0.92),
            _read("PRD-API-3", S3, _t(5, 51), "PB1OGR7788", "PB10GR7788",
                  confidence=0.42, quality="GLARE", format_status="POSSIBLE_FORMAT"),
            _read("PRD-API-5", S5, _t(5, 56), "DL8C__123", None,
                  confidence=0.34, quality="PARTIAL",
                  format_status="NOT_ENOUGH_DATA", display="DL8C__123"),
        ])
        db_session.add_all([
            _cand("PCAND-API-1", S1, "PRD-API-1", 1, "HR26AK4521", "HR26AK4521",
                  0.92, "VALID_FORMAT"),
            _cand("PCAND-API-2", S1, "PRD-API-1", 2, "HR26AK452I", "HR26AK452I", 0.61),
            _cand("PCAND-API-3", S1, "PRD-API-1", 3, "HR26AK45ZI", None, 0.44,
                  "INVALID_FORMAT"),
            _cand("PCAND-API-4", S3, "PRD-API-3", 1, "PB1OGR7788", "PB10GR7788", 0.42),
            _cand("PCAND-API-5", S5, "PRD-API-5", 1, "DL8C__123", None, 0.34,
                  "NOT_ENOUGH_DATA"),
        ])
        # Link plate_read_id on the sightings (service does this at ingest).
        for sid, prd in ((S1, "PRD-API-1"), (S3, "PRD-API-3"), (S5, "PRD-API-5")):
            row = await db_session.get(VehicleSighting, sid)
            row.plate_read_id = prd
        await db_session.commit()

    # ── models / schemas ──────────────────────────────────────────────────────

    async def test_model_defaults_and_roundtrip(self, client, db_session):
        """ORM defaults + camelCase wire round-trip of core fields."""
        await self._seed_scene(db_session)

        row = await db_session.get(VehicleSighting, S1)
        assert row.watchlist_status == "CLEAR"
        assert row.sync_state == "LOCAL_ONLY"
        assert row.schema_version == "1.0"
        assert row.revision == 1

        r = await client.get("/api/v1/anpr/sightings/SGT-API-0001")
        assert r.status_code == 200
        body = r.json()
        # Wire field names (response_model_by_alias=False → camelCase).
        assert body["sightingId"] == S1
        assert body["vehicleId"] == "VEH-API-A"
        assert body["vehicleTrackId"] == "TRK-API-A"
        assert body["cameraId"] == CAM7
        assert body["observedAt"] == "2026-09-12T05:50:00+00:00"
        assert body["vehicleClass"] == "PERSONAL_CAR"
        assert body["vehicleDirection"] == "NORTH"
        assert body["watchlistStatus"] == "CLEAR"
        assert body["sourceProvider"] == "ANPR-DEMO"
        assert body["locationContext"] == "NH-44 Checkpoint Alpha"
        # No snake_case leakage on the wire.
        assert "sighting_id" not in body
        assert "vehicle_track_id" not in body
        assert "source_provider" not in body

    async def test_sighting_detail_handoff_refs(self, client, db_session):
        """Event / incident / evidence / correlation references map to refs."""
        await self._seed_scene(db_session)

        r = await client.get(f"/api/v1/anpr/sightings/{S1}")
        assert r.status_code == 200
        body = r.json()
        assert body["evidenceRef"] == "EV-API-1"
        assert body["eventRef"] == "EVT-API-1"
        assert body["correlationRef"] == "CORR-API-1"
        assert body["incidentRef"] == "INC-API-1"
        assert body["plateRead"]["rawRead"] == "HR26AK4521"
        assert body["plateRead"]["displayRead"] == "HR26AK4521"
        assert body["plateRead"]["quality"] == "GOOD"
        assert body["plateRead"]["formatStatus"] == "VALID_FORMAT"

    async def test_sighting_detail_404(self, client):
        r = await client.get("/api/v1/anpr/sightings/SGT-NOPE")
        assert r.status_code == 404
        assert r.json()["detail"]["error"]["code"] == "SIGHTING_NOT_FOUND"

    # ── candidate preservation ────────────────────────────────────────────────

    async def test_candidates_ranked_and_preserved(self, client, db_session):
        """All candidates preserved in rank order; unreadable → []."""
        await self._seed_scene(db_session)

        r = await client.get(f"/api/v1/anpr/sightings/{S1}/candidates")
        assert r.status_code == 200
        cands = r.json()
        assert [c["rank"] for c in cands] == [1, 2, 3]
        assert [c["rawRead"] for c in cands] == [
            "HR26AK4521", "HR26AK452I", "HR26AK45ZI",
        ]
        assert cands[0]["confidence"] == 0.92
        assert cands[2]["normalizedRead"] is None
        assert cands[2]["formatStatus"] == "INVALID_FORMAT"

        # S2 has no plate read → empty candidate list (not an error).
        r = await client.get(f"/api/v1/anpr/sightings/{S2}/candidates")
        assert r.status_code == 200
        assert r.json() == []

        # 404 propagates for unknown sightings.
        r = await client.get("/api/v1/anpr/sightings/SGT-NOPE/candidates")
        assert r.status_code == 404
        assert r.json()["detail"]["error"]["code"] == "SIGHTING_NOT_FOUND"

    # ── filters / quality / track relationship ────────────────────────────────

    async def test_list_filters(self, client, db_session):
        await self._seed_scene(db_session)

        async def ids(**params) -> list[str]:
            r = await client.get("/api/v1/anpr/sightings", params=params)
            assert r.status_code == 200
            return [s["sightingId"] for s in r.json()["sightings"]]

        assert await ids(camera_id=CAM7) == [S4, S2, S1]  # observed_at desc
        assert await ids(vehicle_id="VEH-API-A") == [S2, S1]
        assert await ids(track_id="TRK-API-A") == [S1]
        assert await ids(quality="GLARE") == [S3]
        assert await ids(vehicle_class="MOTORCYCLE") == [S4]
        assert await ids(direction="SOUTH") == [S3]
        assert await ids(watchlist_status="CLEAR") == [S1]
        assert await ids(confidence_min=0.5) == [S2, S1]  # 0.85, 0.93 — desc
        assert await ids(confidence_max=0.5) == [S5, S3]  # 0.34, 0.42 — desc

    async def test_list_time_filter_and_search_text(self, client, db_session):
        await self._seed_scene(db_session)

        r = await client.get("/api/v1/anpr/sightings", params={
            "from": _iso(5, 51), "to": _iso(5, 53),
        })
        assert r.status_code == 200
        assert [s["sightingId"] for s in r.json()["sightings"]] == [S2, S3]

        r = await client.get("/api/v1/anpr/sightings", params={"search": "HR26AK4521"})
        assert r.status_code == 200
        assert [s["sightingId"] for s in r.json()["sightings"]] == [S1]

    async def test_pagination_cursor_roundtrip(self, client, db_session):
        """Keyset pagination: page 2 continues exactly after page 1."""
        await self._seed_scene(db_session)

        r1 = await client.get("/api/v1/anpr/sightings",
                              params={"camera_id": CAM7, "limit": 2})
        assert r1.status_code == 200
        p1 = r1.json()
        assert [s["sightingId"] for s in p1["sightings"]] == [S4, S2]
        assert p1["hasMore"] is True
        assert p1["nextCursor"]

        r2 = await client.get("/api/v1/anpr/sightings",
                              params={"camera_id": CAM7, "limit": 2,
                                      "cursor": p1["nextCursor"]})
        assert r2.status_code == 200
        p2 = r2.json()
        assert [s["sightingId"] for s in p2["sightings"]] == [S1]
        assert p2["hasMore"] is False
        assert p2["nextCursor"] is None

    async def test_invalid_cursor_422(self, client, db_session):
        await self._seed_scene(db_session)
        r = await client.get("/api/v1/anpr/sightings", params={"cursor": "garbage"})
        assert r.status_code == 422
        assert r.json()["detail"]["error"]["code"] == "INVALID_CURSOR"

    async def test_recent_sightings(self, client, db_session):
        await self._seed_scene(db_session)
        r = await client.get("/api/v1/anpr/sightings/recent", params={"limit": 3})
        assert r.status_code == 200
        assert [s["sightingId"] for s in r.json()] == [S5, S4, S2]

    # ── search (§24 five labels) ──────────────────────────────────────────────

    async def test_search_five_labels_and_precedence(self, client, db_session):
        await self._seed_scene(db_session)

        async def search(q, **params) -> list[tuple[str, str]]:
            r = await client.get("/api/v1/anpr/search", params={"q": q, **params})
            assert r.status_code == 200
            return [(x["sighting"]["sightingId"], x["matchType"]) for x in r.json()]

        # Exact normalized + related (same vehicle, no plate read of its own).
        assert await search("HR26AK4521") == [
            (S1, "EXACT_NORMALIZED_MATCH"),
            (S2, "RELATED_SIGHTING"),
        ]
        # Raw read text differs from normalized (letter O vs zero).
        assert await search("PB1OGR7788") == [(S3, "RAW_READ_MATCH")]
        # Partial normalized hit — never reported as exact.
        res = await search("0GR77")
        assert res == [(S3, "PARTIAL_MATCH")]
        assert all(label != "EXACT_NORMALIZED_MATCH" for _, label in res)
        # Non-top candidate text.
        assert await search("HR26AK45ZI") == [
            (S1, "CANDIDATE_MATCH"),
            (S2, "RELATED_SIGHTING"),
        ]
        # No match.
        assert await search("ZZ99ZZ9999") == []

    async def test_search_filters_and_limits(self, client, db_session):
        await self._seed_scene(db_session)

        r = await client.get("/api/v1/anpr/search", params={"q": "PB10GR7788"})
        assert r.status_code == 200
        assert [(x["sighting"]["sightingId"], x["matchType"])
                for x in r.json()] == [(S3, "EXACT_NORMALIZED_MATCH")]

        # Camera filter excludes CAM-07 rows for a query matching only CAM-08.
        r = await client.get("/api/v1/anpr/search",
                             params={"q": "HR26AK4521", "camera_id": CAM8})
        assert r.status_code == 200
        assert r.json() == []

        # match_type restricts to a single §24 label (short alias accepted).
        r = await client.get("/api/v1/anpr/search",
                             params={"q": "HR26AK4521", "match_type": "exact"})
        assert r.status_code == 200
        assert [x["matchType"] for x in r.json()] == ["EXACT_NORMALIZED_MATCH"]

        r = await client.get("/api/v1/anpr/search",
                             params={"q": "PB1OGR7788", "match_type": "raw"})
        assert r.status_code == 200
        assert [(x["sighting"]["sightingId"], x["matchType"])
                for x in r.json()] == [(S3, "RAW_READ_MATCH")]

        # Limit caps results (related row dropped when limit reached at exact).
        r = await client.get("/api/v1/anpr/search",
                             params={"q": "HR26AK4521", "limit": 1})
        assert r.status_code == 200
        assert len(r.json()) == 1

    # ── history / vehicle / camera relationships ──────────────────────────────

    async def test_vehicle_detail_and_history(self, client, db_session):
        await self._seed_scene(db_session)

        # Newest sighting of the vehicle.
        r = await client.get("/api/v1/anpr/vehicles/VEH-API-A")
        assert r.status_code == 200
        assert r.json()["sightingId"] == S2

        r = await client.get("/api/v1/anpr/vehicles/VEH-API-A/history")
        assert r.status_code == 200
        h = r.json()
        assert h["vehicleId"] == "VEH-API-A"
        # History is chronological by observed_at (repo contract); the vehicle
        # detail route above is the "newest sighting" surface.
        assert [s["sightingId"] for s in h["sightings"]] == [S1, S2]
        assert h["totalSightings"] == 2
        assert h["firstSeen"].startswith("2026-09-12T05:50:00")
        assert h["lastSeen"].startswith("2026-09-12T05:52:00")

        # 404 only for the detail route.
        r = await client.get("/api/v1/anpr/vehicles/VEH-NOPE")
        assert r.status_code == 404
        assert r.json()["detail"]["error"]["code"] == "VEHICLE_NOT_FOUND"

        # Unknown vehicle history → 200 with empty history (no fabrication).
        r = await client.get("/api/v1/anpr/vehicles/VEH-NOPE/history")
        assert r.status_code == 200
        h = r.json()
        assert h["sightings"] == [] and h["totalSightings"] == 0
        assert h["firstSeen"] is None and h["lastSeen"] is None

    async def test_vehicle_history_time_window(self, client, db_session):
        await self._seed_scene(db_session)
        r = await client.get("/api/v1/anpr/vehicles/VEH-API-A/history",
                             params={"from_time": _iso(5, 51)})
        assert r.status_code == 200
        h = r.json()
        assert [s["sightingId"] for s in h["sightings"]] == [S2]
        assert h["totalSightings"] == 1

    async def test_camera_vehicles_feed_summary(self, client, db_session):
        await self._seed_scene(db_session)

        r = await client.get(f"/api/v1/anpr/cameras/{CAM7}/vehicles")
        assert r.status_code == 200
        assert [s["sightingId"] for s in r.json()] == [S4, S2, S1]

        # Camera-scoped filters.
        r = await client.get(f"/api/v1/anpr/cameras/{CAM7}/vehicles",
                             params={"quality": "GOOD"})
        assert r.status_code == 200
        assert [s["sightingId"] for s in r.json()] == [S1]

        # Feed: readiness comes from the registered provider; lastUpdatedAt
        # from the newest observation.
        r = await client.get(f"/api/v1/anpr/cameras/{CAM7}/vehicles/feed")
        assert r.status_code == 200
        feed = r.json()
        assert feed["cameraId"] == CAM7
        assert feed["state"] == "READY"
        assert feed["providerHealth"] == "READY"
        assert feed["lastUpdatedAt"].startswith("2026-09-12T05:54:00")
        assert [s["sightingId"] for s in feed["sightings"]] == [S4, S2, S1]

        # Summary: exact counts from the seeded scene.
        r = await client.get(f"/api/v1/anpr/cameras/{CAM7}/vehicles/summary")
        assert r.status_code == 200
        sm = r.json()
        assert sm["cameraId"] == CAM7
        assert sm["totalSightings"] == 3
        assert sm["byStatus"] == {"CLEAR": 1, "NOT_CHECKED": 2}
        assert sm["byQuality"] == {"GOOD": 1}
        assert sm["byClass"] == {"PERSONAL_CAR": 2, "MOTORCYCLE": 1}
        assert sm["lastUpdatedAt"].startswith("2026-09-12T05:54:00")

    async def test_global_summary_counts(self, client, db_session):
        """§26 plate-observation counts across the seeded scene."""
        await self._seed_scene(db_session)
        r = await client.get("/api/v1/anpr/summary")
        assert r.status_code == 200
        s = r.json()
        assert s["totalReads"] == 5
        assert s["readablePlates"] == 2      # S1 VALID + S3 POSSIBLE
        assert s["partialReads"] == 1        # S5 PARTIAL/NOT_ENOUGH_DATA
        assert s["unreadablePlates"] == 2    # S2, S4 (no plate read)
        assert s["uniqueTrackedSightings"] == 4  # A, A2, B, D
        assert s["camerasReporting"] == 3
        assert s["lastUpdated"].startswith("2026-09-12T05:56:00")

    # ── provider health ───────────────────────────────────────────────────────

    async def test_health_with_provider(self, client):
        r = await client.get("/api/v1/anpr/health")
        assert r.status_code == 200
        h = r.json()
        assert h["state"] == "READY"
        assert h["provider"] == "ANPR-DEMO"
        assert h["providerVersion"] == "demo-1.0"
        assert h["queueDepth"] == 0
        assert "DEMO" in (h["note"] or "")

    async def test_health_no_provider(self, client):
        pmod._anpr_provider = None
        r = await client.get("/api/v1/anpr/health")
        assert r.status_code == 200
        h = r.json()
        assert h["state"] == "UNAVAILABLE"
        assert h["provider"] == "NONE"
        assert h["camerasActive"] == 0
        assert h["note"] == "No ANPR provider registered."

    # ── config ────────────────────────────────────────────────────────────────

    async def test_config_null_when_unset_then_seeded(self, client, db_session):
        r = await client.get(f"/api/v1/anpr/config/{CAM7}")
        assert r.status_code == 200
        assert r.json() is None

        db_session.add(ANPRConfig(
            config_id="ANCFG-API-1", camera_id=CAM7, provider="demo",
            sample_rate=1.0, min_frame_interval_ms=0, active=True,
            revision=1, configuration_version="1.0",
        ))
        await db_session.commit()

        r = await client.get(f"/api/v1/anpr/config/{CAM7}")
        assert r.status_code == 200
        cfg = r.json()
        assert cfg["configId"] == "ANCFG-API-1"
        assert cfg["cameraId"] == CAM7
        assert cfg["provider"] == "demo"
        assert cfg["active"] is True
        assert cfg["configurationVersion"] == "1.0"

    # ── ingestion (provider path) ─────────────────────────────────────────────

    async def test_ingest_creates_and_persists(self, client, db_session):
        """Happy path: explicit IDs (sighting-level + plate-level) persist."""
        body = _body(CAM7, [
            _sighting_payload(CAM7, _iso(6, 0), sighting_id="SGT-ING-0001",
                              track_id="TRK-ING-1", detection_id="DET-ING-1",
                              vehicle_class="SUV", direction="INBOUND",
                              plate=_plate_payload("RJ14AB1052",
                                                   normalized="RJ14AB1052",
                                                   confidence=0.91)),
            _sighting_payload(CAM7, _iso(6, 1),
                              plate=_plate_payload("GJ01BV2209",
                                                   normalized="GJ01BV2209",
                                                   confidence=0.87,
                                                   sighting_id="SGT-ING-0002")),
        ])
        r = await client.post("/api/v1/anpr/internal/observe",
                              json=body, headers=INTERNAL_HEADERS)
        assert r.status_code == 200, r.text
        ack = r.json()
        assert ack["cameraId"] == CAM7
        assert ack["totalSightings"] == 2
        assert ack["created"] == 2
        assert ack["duplicates"] == 0
        assert ack["errors"] == 0
        assert ack["providerName"] == "ANPR-DEMO"
        assert ack["providerVersion"] == "demo-1.0"
        assert isinstance(ack["processingLatencyMs"], int)
        assert "total_sightings" not in ack  # camelCase wire

        # Both IDs persisted exactly as supplied (sighting-level precedence,
        # then plateRead-level).
        r = await client.get("/api/v1/anpr/sightings/SGT-ING-0001")
        assert r.status_code == 200
        b = r.json()
        assert b["sightingId"] == "SGT-ING-0001"
        assert b["vehicleTrackId"] == "TRK-ING-1"
        assert b["plateRead"]["rawRead"] == "RJ14AB1052"
        assert b["sourceProvider"] == "ANPR-DEMO"

        r = await client.get("/api/v1/anpr/sightings/SGT-ING-0002")
        assert r.status_code == 200
        assert r.json()["plateRead"]["normalizedRead"] == "GJ01BV2209"

        count = (await db_session.execute(
            select(func.count()).select_from(VehicleSighting)
        )).scalar_one()
        assert count == 2

    async def test_ingest_demo_fixtures_and_candidates(self, client, db_session):
        """Demo provider fixtures cycle deterministically per camera."""
        body = _body(CAM7, [
            _sighting_payload(CAM7, _iso(6, 0)),
            _sighting_payload(CAM7, _iso(6, 1)),
            _sighting_payload(CAM7, _iso(6, 2)),
        ])
        r = await client.post("/api/v1/anpr/internal/observe",
                              json=body, headers=INTERNAL_HEADERS)
        assert r.status_code == 200, r.text
        assert r.json()["created"] == 3

        # Fixture plates + demo vehicle grouping (deterministic).
        expected = [
            ("SGT-DEMO-07-0001", "HR26AK4521", "VEH-DEMO-HR26AK4521"),
            ("SGT-DEMO-07-0002", "HR26AK452I", "VEH-DEMO-HR26AK452I"),
            ("SGT-DEMO-07-0003", "GJ01BV2209", "VEH-DEMO-GJ01BV2209"),
        ]
        for sid, plate, vid in expected:
            r = await client.get(f"/api/v1/anpr/sightings/{sid}")
            assert r.status_code == 200
            b = r.json()
            assert b["plateRead"]["rawRead"] == plate
            assert b["vehicleId"] == vid

        # Candidate sets preserved for the ambiguous fixtures.
        r = await client.get("/api/v1/anpr/sightings/SGT-DEMO-07-0001/candidates")
        assert [(c["rank"], c["rawRead"]) for c in r.json()] == [
            (1, "HR26AK4521"), (2, "HR26AK452I"),
        ]
        r = await client.get("/api/v1/anpr/sightings/SGT-DEMO-07-0003/candidates")
        assert [(c["rank"], c["rawRead"]) for c in r.json()] == [(1, "GJ01BV2209")]

    async def test_ingest_unreadable_fixture(self, client, db_session):
        """4th CAM-07 fixture is unreadable → no plate read, empty candidates."""
        body = _body(CAM7, [_sighting_payload(CAM7, _iso(6, i)) for i in range(4)])
        r = await client.post("/api/v1/anpr/internal/observe",
                              json=body, headers=INTERNAL_HEADERS)
        assert r.status_code == 200, r.text
        assert r.json()["created"] == 4

        r = await client.get("/api/v1/anpr/sightings/SGT-DEMO-07-0004")
        assert r.status_code == 200
        b = r.json()
        assert b["plateRead"] is None
        assert b["plateCandidates"] == []
        # Caller/edge metadata wins for vehicle class — the provider supplies
        # the plate observation only (ANPRObservationResult has no class field),
        # so the payload's default PERSONAL_CAR persists here.
        assert b["vehicleClass"] == "PERSONAL_CAR"

        r = await client.get("/api/v1/anpr/sightings/SGT-DEMO-07-0004/candidates")
        assert r.json() == []

    async def test_ingest_normalizes_vehicle_class_to_canonical_taxonomy(
        self, client, db_session,
    ):
        """C7 §10 — caller vocabulary is folded onto the canonical taxonomy at
        the persistence boundary; unmapped values become UNKNOWN, never raw."""
        cases = [
            ("CAR", "PERSONAL_CAR"),
            ("suv", "SUV"),
            ("MOTORBIKE", "MOTORCYCLE"),
            ("TRUCK", "TRUCK"),
            ("Banana", "UNKNOWN"),
        ]
        body = _body(CAM7, [
            _sighting_payload(CAM7, _iso(6, i), vehicle_class=raw)
            for i, (raw, _) in enumerate(cases)
        ])
        r = await client.post("/api/v1/anpr/internal/observe",
                              json=body, headers=INTERNAL_HEADERS)
        assert r.status_code == 200, r.text
        assert r.json()["created"] == len(cases)

        for i, (raw, expected) in enumerate(cases):
            sid = f"SGT-DEMO-07-{i + 1:04d}"
            r = await client.get(f"/api/v1/anpr/sightings/{sid}")
            assert r.status_code == 200
            assert r.json()["vehicleClass"] == expected, (raw, sid)

    async def test_ingest_missing_header_403(self, client):
        body = _body(CAM7, [_sighting_payload(CAM7, _iso(6, 0))])
        r = await client.post("/api/v1/anpr/internal/observe", json=body)
        assert r.status_code == 403
        assert r.json()["detail"]["error"]["code"] == "FORBIDDEN"

    async def test_ingest_bad_timestamp_422(self, client):
        body = _body(CAM7, [_sighting_payload(CAM7, "not-a-time")])
        r = await client.post("/api/v1/anpr/internal/observe",
                              json=body, headers=INTERNAL_HEADERS)
        assert r.status_code == 422
        assert r.json()["detail"]["error"]["code"] == "INVALID_SIGHTING"

    async def test_ingest_contract_rejects_camelcase_keys(self, client):
        """Inbound contract is snake_case (aliases); camelCase is rejected."""
        body = {
            "camera_id": CAM7,
            "sightings": [{"cameraId": CAM7, "observedAt": _iso(6, 0)}],
        }
        r = await client.post("/api/v1/anpr/internal/observe",
                              json=body, headers=INTERNAL_HEADERS)
        assert r.status_code == 422  # extra="forbid" — extra key rejected

    # ── idempotency ───────────────────────────────────────────────────────────

    async def test_idempotent_same_sighting_id_raw_read_unchanged(
        self, client, db_session,
    ):
        """Re-ingest of the same sighting ID is a duplicate; nothing rewritten."""
        first = _body(CAM7, [
            _sighting_payload(CAM7, _iso(6, 0), sighting_id="SGT-IDEM-1",
                              plate=_plate_payload("AB12CD3456",
                                                   normalized="AB12CD3456",
                                                   candidates=[{
                                                       "rank": 1,
                                                       "raw_read": "AB12CD3456",
                                                       "normalized_read": "AB12CD3456",
                                                       "confidence": 0.9,
                                                       "format_status": "VALID_FORMAT",
                                                   }])),
        ])
        r = await client.post("/api/v1/anpr/internal/observe",
                              json=first, headers=INTERNAL_HEADERS)
        assert r.status_code == 200
        assert r.json()["created"] == 1

        # Replay with a DIFFERENT plate — must be ignored entirely.
        second = _body(CAM7, [
            _sighting_payload(CAM7, _iso(6, 5), sighting_id="SGT-IDEM-1",
                              plate=_plate_payload("ZZ99ZZ9999",
                                                   normalized="ZZ99ZZ9999")),
        ])
        r = await client.post("/api/v1/anpr/internal/observe",
                              json=second, headers=INTERNAL_HEADERS)
        assert r.status_code == 200
        ack = r.json()
        assert ack["created"] == 0
        assert ack["duplicates"] == 1

        rows = (await db_session.execute(
            select(func.count()).select_from(VehicleSighting)
        )).scalar_one()
        assert rows == 1

        r = await client.get("/api/v1/anpr/sightings/SGT-IDEM-1")
        assert r.json()["plateRead"]["rawRead"] == "AB12CD3456"  # never rewritten
        cands = (await db_session.execute(
            select(func.count()).select_from(PlateCandidate)
        )).scalar_one()
        assert cands == 1  # no candidate duplication from the replay

    async def test_idempotent_detection_track_pair(self, client, db_session):
        """Same (detection_id, track_id) without a caller ID → duplicate row folded."""
        def _payload(observed: str) -> dict:
            return _body(CAM7, [
                _sighting_payload(CAM7, observed, track_id="TRK-IDEM-2",
                                  detection_id="DET-IDEM-2"),
            ])

        r = await client.post("/api/v1/anpr/internal/observe",
                              json=_payload(_iso(6, 0)), headers=INTERNAL_HEADERS)
        assert r.status_code == 200
        assert r.json()["created"] == 1
        first_id = "SGT-DEMO-07-0001"

        r = await client.post("/api/v1/anpr/internal/observe",
                              json=_payload(_iso(6, 1)), headers=INTERNAL_HEADERS)
        assert r.status_code == 200
        ack = r.json()
        assert ack["created"] == 0
        assert ack["duplicates"] == 1

        rows = (await db_session.execute(
            select(func.count()).select_from(VehicleSighting)
        )).scalar_one()
        assert rows == 1
        existing = await db_session.get(VehicleSighting, first_id)
        assert existing is not None  # duplicate resolves to the existing row

    async def test_idempotent_sync_payload_hash(self, client, db_session):
        """Same provider observation hash without a caller ID → folded."""
        def _payload(observed: str) -> dict:
            return _body(CAM8, [
                _sighting_payload(CAM8, observed,
                                  sync_payload_hash="HASH-IDEM-3"),
            ])

        r = await client.post("/api/v1/anpr/internal/observe",
                              json=_payload(_iso(6, 0)), headers=INTERNAL_HEADERS)
        assert r.status_code == 200
        assert r.json()["created"] == 1

        r = await client.post("/api/v1/anpr/internal/observe",
                              json=_payload(_iso(6, 1)), headers=INTERNAL_HEADERS)
        assert r.status_code == 200
        ack = r.json()
        assert ack["created"] == 0
        assert ack["duplicates"] == 1

        rows = (await db_session.execute(
            select(func.count()).select_from(VehicleSighting)
        )).scalar_one()
        assert rows == 1

    async def test_concurrent_duplicate_ingest(self, client, db_session):
        """Two overlapping identical batches → exactly one row per sighting."""
        def _payload() -> dict:
            return _body(CAM7, [
                _sighting_payload(CAM7, _iso(6, 0), sighting_id="SGT-CONC-1"),
                _sighting_payload(CAM7, _iso(6, 1), sighting_id="SGT-CONC-2"),
            ])

        r1, r2 = await asyncio.gather(
            client.post("/api/v1/anpr/internal/observe",
                        json=_payload(), headers=INTERNAL_HEADERS),
            client.post("/api/v1/anpr/internal/observe",
                        json=_payload(), headers=INTERNAL_HEADERS),
        )
        assert r1.status_code == 200, r1.text
        assert r2.status_code == 200, r2.text
        a1, a2 = r1.json(), r2.json()
        assert a1["created"] + a2["created"] == 2
        assert a1["duplicates"] + a2["duplicates"] == 2
        assert a1["errors"] == 0 and a2["errors"] == 0

        rows = (await db_session.execute(
            select(func.count()).select_from(VehicleSighting)
        )).scalar_one()
        assert rows == 2

    # ── provider failure / timeout ────────────────────────────────────────────

    async def test_ingest_no_provider_503(self, client):
        pmod._anpr_provider = None
        body = _body(CAM7, [_sighting_payload(CAM7, _iso(6, 0))])
        r = await client.post("/api/v1/anpr/internal/observe",
                              json=body, headers=INTERNAL_HEADERS)
        assert r.status_code == 503
        detail = r.json()["detail"]["error"]
        assert detail["code"] == "ANPR_UNAVAILABLE"
        assert "No ANPR Provider registered" in detail["message"]

    async def test_ingest_not_ready_provider_503(self, client):
        set_anpr_provider(DemoANPRProvider())  # not initialized → not ready
        body = _body(CAM7, [_sighting_payload(CAM7, _iso(6, 0))])
        r = await client.post("/api/v1/anpr/internal/observe",
                              json=body, headers=INTERNAL_HEADERS)
        assert r.status_code == 503
        detail = r.json()["detail"]["error"]
        assert detail["code"] == "ANPR_UNAVAILABLE"
        assert "not ready" in detail["message"]

    async def test_ingest_provider_timeout_503_no_partial_persist(
        self, client, db_session,
    ):
        """Provider timeout surfaces as ANPR_UNAVAILABLE; nothing is persisted."""
        set_anpr_provider(_TimeoutProvider())
        body = _body(CAM7, [_sighting_payload(CAM7, _iso(6, 0))])
        r = await client.post("/api/v1/anpr/internal/observe",
                              json=body, headers=INTERNAL_HEADERS)
        assert r.status_code == 503
        detail = r.json()["detail"]["error"]
        assert detail["code"] == "ANPR_UNAVAILABLE"
        assert "recognition failed" in detail["message"]

        rows = (await db_session.execute(
            select(func.count()).select_from(VehicleSighting)
        )).scalar_one()
        assert rows == 0
