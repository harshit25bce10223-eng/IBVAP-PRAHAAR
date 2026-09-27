"""Concurrency / race-condition tests (spec §22).

Two near-simultaneous frames for the same track entering the same zone must
produce exactly ONE ZONE_ENTRY event and ONE incident. The database-level
unique constraint on `deduplication_key` is the authoritative guard.
"""
import asyncio

import httpx


def square(poly):
    return [{"x": x, "y": y} for x, y in poly]


def track_payload(track_id="TRK-CONCURRENT", **kw):
    base = {
        "track_id": track_id,
        "camera_id": "CAM-12",
        "object_type": "HUMAN",
        "bbox": {"x": 0.42, "y": 0.35, "width": 0.08, "height": 0.25},
        "confidence": 0.92,
        "is_night": True,
        "multi_camera_confirmed": True,
        "reliability": "HIGH",
        "timestamp": "2026-09-07T02:17:43Z",
    }
    base.update(kw)
    return base


def create_zone_via_app(app):
    transport = httpx.ASGITransport(app=app)
    import json

    async def create():
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            return await client.post(
                "/api/v1/zones",
                json={
                    "camera_id": "CAM-12",
                    "name": "Concurrent Zone",
                    "polygon": square([(0.2, 0.2), (0.8, 0.2), (0.8, 0.8), (0.2, 0.8)]),
                    "rules": {},
                },
            )

    return asyncio.run(create())


async def test_concurrent_entry_single_incident(app, session_factory, engine):
    # Set up the zone through the same app/db.
    import httpx as _h

    transport = _h.ASGITransport(app=app)
    async with _h.AsyncClient(transport=transport, base_url="http://test") as zc:
        zr = await zc.post(
            "/api/v1/zones",
            json={
                "camera_id": "CAM-12",
                "name": "Concurrent Zone",
                "polygon": square([(0.2, 0.2), (0.8, 0.2), (0.8, 0.8), (0.2, 0.8)]),
                "rules": {},
            },
        )
        assert zr.status_code == 201
        zone_id = zr.json()["zone_id"]

    async with _h.AsyncClient(transport=transport, base_url="http://test") as client:
        payload = track_payload()
        responses = await asyncio.gather(
            client.post("/api/v1/evaluation/track_and_evaluate", json=payload),
            client.post("/api/v1/evaluation/track_and_evaluate", json=payload),
        )

    statuses = [r.status_code for r in responses]
    bodies = [r.json() for r in responses]
    print("statuses:", statuses)
    for body in bodies:
        print("incident.created:", body.get("incident", {}).get("created"))
        print("event.created:", body.get("event", {}).get("created"))

    # At least one request created the incident.
    created_flags = [b.get("incident", {}).get("created") for b in bodies]
    assert any(created_flags)

    # Exactly one incident exists in the DB.
    from sqlalchemy import func, select

    from app.models.incident import Incident

    async with session_factory() as session:
        result = await session.execute(select(func.count()).select_from(Incident))
        incident_count = result.scalar_one()
        assert incident_count == 1

    # Exactly one ZONE_ENTRY event exists.
    from app.models.event import Event

    async with session_factory() as session:
        result = await session.execute(
            select(func.count()).select_from(Event).where(Event.event_type == "ZONE_ENTRY")
        )
        assert result.scalar_one() == 1

    # Zone detail records the crossing.
    create_zone_ids = [
        z.get("zone_id")
        for b in bodies
        if b.get("incident", {}).get("created")
        for z in b.get("evaluation", {}).get("zones", [])
        if z.get("transition") == "ENTRY"
    ]
    assert zone_id in create_zone_ids