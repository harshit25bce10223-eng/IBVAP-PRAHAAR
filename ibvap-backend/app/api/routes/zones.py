# ─────────────────────────────────────────────────────────────────────────────
# IBVAP — Zone Routes
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import json

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import ZoneNotFoundError, IBVAPError
from app.domain.fence.membership import validate_polygon
from app.db.database import get_db_session
from app.repositories.zone_repository import ZoneRepository
from app.schemas.zone import ZoneCreate, ZoneOut, ZoneUpdate

router = APIRouter(prefix="/zones", tags=["zones"])


def _to_out(zone) -> ZoneOut:
    return ZoneOut(
        zone_id=zone.zone_id,
        camera_id=zone.camera_id,
        name=zone.name,
        polygon=json.loads(zone.polygon_json),
        rules=json.loads(zone.rules_json),
        active=zone.active,
        created_at=zone.created_at,
        updated_at=zone.updated_at,
    )


@router.get("", response_model=list[ZoneOut])
async def list_zones(
    camera_id: str | None = None,
    active_only: bool = False,
    session: AsyncSession = Depends(get_db_session),
):
    repo = ZoneRepository(session)
    if camera_id:
        zones = await repo.list_by_camera(camera_id, active_only=active_only)
    else:
        zones = await repo.list_all()
    return [_to_out(z) for z in zones]


@router.get("/{zone_id}", response_model=ZoneOut)
async def get_zone(zone_id: str, session: AsyncSession = Depends(get_db_session)):
    repo = ZoneRepository(session)
    zone = await repo.get(zone_id)
    if zone is None:
        raise ZoneNotFoundError(zone_id)
    return _to_out(zone)


@router.post("", response_model=ZoneOut, status_code=201)
async def create_zone(body: ZoneCreate, session: AsyncSession = Depends(get_db_session)):
    repo = ZoneRepository(session)
    polygon = [p.model_dump() for p in body.polygon]

    # Domain-level geometry validation (rejects degenerate & self-intersecting shapes)
    try:
        validate_polygon(polygon)
    except IBVAPError as exc:
        raise exc

    zone = await repo.create(
        zone_id=body.zone_id,
        camera_id=body.camera_id,
        name=body.name,
        polygon=polygon,
        rules=body.rules.model_dump(exclude_none=True) if body.rules else {},
        active=body.active,
    )
    await session.commit()
    return _to_out(zone)


@router.put("/{zone_id}", response_model=ZoneOut)
async def update_zone(
    zone_id: str, body: ZoneUpdate, session: AsyncSession = Depends(get_db_session)
):
    repo = ZoneRepository(session)
    zone = await repo.get(zone_id)
    if zone is None:
        raise ZoneNotFoundError(zone_id)

    polygon = [p.model_dump() for p in body.polygon] if body.polygon is not None else None
    if polygon is not None:
        try:
            validate_polygon(polygon)
        except IBVAPError as exc:
            raise exc

    zone = await repo.update(
        zone,
        name=body.name,
        polygon=polygon,
        rules=body.rules.model_dump(exclude_none=True) if body.rules is not None else None,
        active=body.active,
    )
    await session.commit()
    return _to_out(zone)


@router.delete("/{zone_id}", status_code=204)
async def delete_zone(zone_id: str, session: AsyncSession = Depends(get_db_session)):
    repo = ZoneRepository(session)
    deleted = await repo.delete(zone_id)
    if not deleted:
        raise ZoneNotFoundError(zone_id)
    await session.commit()