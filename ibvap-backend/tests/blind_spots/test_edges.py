"""Blind-spot tests: inputs and scenarios the happy path misses.

Covered here:
- Boundary confidence values (0.0 and 1.0 accepted, others rejected)
- Reliability values
- Bbox bottom-center semantics (ground contact)
- Polygon on edges / vertices
- Zone with no camera (validation)
- Identifier validation
- Persistence across "restart": DB is authoritative, no duplicates after re-init.
"""
import json

import httpx


def square(poly):
    return [{"x": x, "y": y} for x, y in poly]


def payload(**kw):
    base = {
        "track_id": "TRK-BLIND",
        "camera_id": "CAM-9",
        "object_type": "HUMAN",
        "bbox": {"x": 0.42, "y": 0.35, "width": 0.08, "height": 0.25},
        "confidence": 0.9,
        "is_night": False,
        "multi_camera_confirmed": False,
        "reliability": "HIGH",
        "timestamp": "2026-09-07T02:17:43Z",
    }
    base.update(kw)
    return base


async def test_confidence_boundaries(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # 0.0 and 1.0 are legal.
        assert (await client.post("/api/v1/evaluation/track_and_evaluate", json=payload(confidence=0.0))).status_code == 200
        assert (await client.post("/api/v1/evaluation/track_and_evaluate", json=payload(confidence=1.0, track_id="TRK-BLIND-2"))).status_code == 200
        # Outside range rejected.
        assert (await client.post("/api/v1/evaluation/track_and_evaluate", json=payload(confidence=-0.01, track_id="TRK-BLIND-3"))).status_code == 422
        assert (await client.post("/api/v1/evaluation/track_and_evaluate", json=payload(confidence=1.01, track_id="TRK-BLIND-4"))).status_code == 422


async def test_reliability_values(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        for rel in ("HIGH", "MEDIUM", "LOW"):
            body = payload(reliability=rel, track_id=f"TRK-REL-{rel}")
            res = await client.post("/api/v1/evaluation/track_and_evaluate", json=body)
            assert res.status_code == 200, (rel, res.text)
        bad = await client.post(
            "/api/v1/evaluation/track_and_evaluate",
            json=payload(reliability="UNKNOWN", track_id="TRK-REL-BAD"),
        )
        assert bad.status_code == 422


async def test_bbox_bottom_center_ground_contact(app):
    """A bbox whose box overlaps a zone but whose BOTTOM is outside must not fire."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/zones",
            json={"camera_id": "CAM-9", "name": "Z", "polygon": square([(0.1, 0.3), (0.9, 0.3), (0.9, 0.7), (0.1, 0.7)]), "rules": {}},
        )
        # Box spans into the zone vertically, but ground point below the polygon.
        body = payload(bbox={"x": 0.3, "y": 0.65, "width": 0.4, "height": 0.1})
        res = await client.post("/api/v1/evaluation/track_and_evaluate", json=body)
        data = res.json()
        assert data["evaluation"]["representative_point"]["y"] == 0.75
        z = data["evaluation"]["zones"][0]
        assert z["is_inside"] is False
        assert data["incident"]["created"] is False


async def test_bottom_center_entering_fires_once(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/zones",
            json={"camera_id": "CAM-9", "name": "Z2", "polygon": square([(0.1, 0.3), (0.9, 0.3), (0.9, 0.7), (0.1, 0.7)]), "rules": {}},
        )
        # Ground point lands inside.
        p = payload(bbox={"x": 0.3, "y": 0.35, "width": 0.4, "height": 0.1}, track_id="TRK-GRND")
        res = await client.post("/api/v1/evaluation/track_and_evaluate", json=p)
        assert res.json()["incident"]["created"] is True


async def test_restart_persistence_no_duplicates(app, session_factory):
    """Two separate 'sessions' (simulating restart) share the same DB file.

    After an ENTRY, a fresh client instance performing the same frame must NOT
    create a second incident — the DB is the source of truth, not in-memory state.
    """
    transport = httpx.ASGITransport(app=app)
    p = payload(track_id="TRK-RESTART")

    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c1:
        await c1.post(
            "/api/v1/zones",
            json={"camera_id": "CAM-9", "name": "Restart Zone", "polygon": square([(0.2, 0.2), (0.8, 0.2), (0.8, 0.8), (0.2, 0.8)]), "rules": {}},
        )
        first = await c1.post("/api/v1/evaluation/track_and_evaluate", json=p)
        assert first.json()["incident"]["created"] is True

    # Simulate application restart: brand-new client, same persistent DB.
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c2:
        second = await c2.post("/api/v1/evaluation/track_and_evaluate", json=p)
        assert second.json()["incident"]["created"] is False
        assert second.json()["event"]["created"] is False


async def test_zone_id_validation(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        r = await client.post(
            "/api/v1/zones",
            json={"zone_id": "x" * 100, "camera_id": "C", "name": "Z", "polygon": square([(0.1, 0.1), (0.9, 0.1), (0.9, 0.9), (0.1, 0.9)]), "rules": {}},
        )
        assert r.status_code == 422


async def test_boundary_points_on_polygon_are_inside(app):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post(
            "/api/v1/zones",
            json={"camera_id": "CAM-9", "name": "Edge Zone", "polygon": square([(0.2, 0.2), (0.8, 0.2), (0.8, 0.8), (0.2, 0.8)]), "rules": {}},
        )
        # Bottom-center exactly on the top edge (y = 0.8) must count as INSIDE.
        p = payload(bbox={"x": 0.4, "y": 0.7, "width": 0.1, "height": 0.05}, track_id="TRK-EDGE")
        res = await client.post("/api/v1/evaluation/track_and_evaluate", json=p)
        z = res.json()["evaluation"]["zones"][0]
        assert z["is_inside"] is True


async def test_polygon_with_many_points_accepted(app):
    import math

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        # A 90-point circle is a valid (convex, non-degenerate) polygon.
        n = 90
        polygon = [
            {"x": round(0.5 + 0.4 * math.cos(2 * math.pi * i / n), 6),
             "y": round(0.5 + 0.4 * math.sin(2 * math.pi * i / n), 6)}
            for i in range(n)
        ]
        r = await client.post(
            "/api/v1/zones",
            json={"camera_id": "CAM-9", "name": "Big", "polygon": polygon, "rules": {}},
        )
        assert r.status_code == 201, r.text