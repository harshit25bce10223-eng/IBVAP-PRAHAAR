# ─────────────────────────────────────────────────────────────────────────────
# IBVAP — Track Repository
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.tracking import track_state
from app.domain.geometry.bbox import get_representative_point
from app.models.track import Track


class TrackRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, track_id: str) -> Track | None:
        res = await self.session.execute(select(Track).where(Track.track_id == track_id))
        return res.scalar_one_or_none()

    async def get_or_create(
        self, *, track_id: str, camera_id: str, object_type: str
    ) -> Track:
        from sqlalchemy.exc import IntegrityError

        track = await self.get(track_id)
        if track is not None:
            return track
        now = datetime.now(timezone.utc)
        track = Track(
            track_id=track_id,
            camera_id=camera_id,
            object_type=object_type,
            first_seen=now,
            last_seen=now,
            created_at=now,
            updated_at=now,
        )
        self.session.add(track)
        try:
            await self.session.flush()
        except IntegrityError:
            # A concurrent request created the same track first; adopt it.
            await self.session.rollback()
            existing = await self.get(track_id)
            if existing is not None:
                return existing
            raise
        return track

    async def update_state(
        self,
        *,
        track: Track,
        object_type: str,
        bbox: dict[str, float] | None,
        membership: dict[str, bool],
        now: datetime,
    ) -> None:
        track.object_type = object_type
        if bbox is not None:
            track.previous_bbox_json = track.current_bbox_json
            track.current_bbox_json = json.dumps(bbox)

            rep = get_representative_point(bbox)
            path = track_state.append_position(
                track_state.parse_path(track.path_json),
                {"x": rep["x"], "y": rep["y"], "ts": now.isoformat()},
            )
            track.path_json = json.dumps(path)

        track.previous_membership_json = track.current_membership_json
        track.current_membership_json = json.dumps(membership)
        track.last_seen = now
        track.updated_at = now
        await self.session.flush()