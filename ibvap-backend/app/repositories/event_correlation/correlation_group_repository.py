# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 4 — Correlation Group Repository
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.event_correlation import (
    CorrelationGroup,
    CorrelationGroupMember,
    CorrelationGroupState,
)
from app.models.event import Event
from app.models.incident import Incident

_ACTIVE_STATES = (
    CorrelationGroupState.OPEN,
    CorrelationGroupState.ACTIVE,
    CorrelationGroupState.STABLE,
)

# Severity bands derived from the ONE canonical threshold set (settings), so a
# numeric pre-filter on risk_score cannot drift from severity_for_score().
_SEVERITY_BANDS = {
    "LOW": (0, settings.SEVERITY_MEDIUM_THRESHOLD - 1),
    "MEDIUM": (settings.SEVERITY_MEDIUM_THRESHOLD, settings.SEVERITY_HIGH_THRESHOLD - 1),
    "HIGH": (settings.SEVERITY_HIGH_THRESHOLD, settings.SEVERITY_CRITICAL_THRESHOLD - 1),
    "CRITICAL": (settings.SEVERITY_CRITICAL_THRESHOLD, 100),
}

# Same vocabulary as the Event Log time-range control.
_TIME_RANGE_MINUTES = {"15m": 15, "1h": 60, "today": 24 * 60}

_SORTABLE_COLUMNS = {
    "started_at",
    "updated_at",
    "created_at",
    "event_count",
    "confidence",
    "status",
    "state",
    "correlation_id",
}


class CorrelationGroupRepository:
    def __init__(self, session) -> None:
        self.session = session

    async def get(self, correlation_id: str) -> Any | None:
        stmt = select(CorrelationGroup).where(
            CorrelationGroup.correlation_id == correlation_id
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def create(self, **data: Any) -> Any:
        group = CorrelationGroup(**data)
        self.session.add(group)
        await self.session.flush()
        return group

    async def update(self, correlation_id: str, **data: Any) -> Any | None:
        group = await self.get(correlation_id)
        if not group:
            return None
        for key, value in data.items():
            if hasattr(group, key):
                setattr(group, key, value)
        group.revision += 1
        group.updated_at = datetime.now(timezone.utc)
        await self.session.flush()
        return group

    async def delete(self, correlation_id: str) -> bool:
        group = await self.get(correlation_id)
        if not group:
            return False
        await self.session.delete(group)
        return True

    async def list_paginated(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str | None = None,
        camera_id: str | None = None,
        sector_id: str | None = None,
        source: str | None = None,
        search: str | None = None,
        severity: str | None = None,
        time_range: str | None = None,
        sort: str = "started_at",
        order: str = "desc",
    ) -> tuple[list, int]:
        conditions = []
        if status:
            conditions.append(CorrelationGroup.status == status)
        if sector_id:
            conditions.append(CorrelationGroup.sector_id == sector_id)
        if source:
            conditions.append(
                CorrelationGroup.sources.contains(source)
            )

        if camera_id:
            camera_filter = (
                select(CorrelationGroupMember.correlation_id)
                .join(Event, Event.event_id == CorrelationGroupMember.event_id)
                .where(Event.camera_id == camera_id)
                .distinct()
            )
            conditions.append(CorrelationGroup.correlation_id.in_(camera_filter))

        if severity:
            band = _SEVERITY_BANDS.get(severity.upper())
            if band is not None:
                low, high = band
                # Matches _apply_risk_reference semantics: a group's severity is
                # the band of its highest-scoring referenced incident.
                risk_per_group = (
                    select(
                        CorrelationGroupMember.correlation_id.label("cid"),
                        func.max(Incident.risk_score).label("max_score"),
                    )
                    .join(Event, Event.event_id == CorrelationGroupMember.event_id)
                    .join(Incident, Incident.event_id == Event.event_id)
                    .group_by(CorrelationGroupMember.correlation_id)
                    .subquery()
                )
                severity_filter = select(risk_per_group.c.cid).where(
                    risk_per_group.c.max_score >= low,
                    risk_per_group.c.max_score <= high,
                )
                conditions.append(
                    CorrelationGroup.correlation_id.in_(severity_filter)
                )

        if time_range:
            minutes = _TIME_RANGE_MINUTES.get(time_range)
            if minutes is not None:
                # Mirrors get_recent(): aware-UTC cutoff, coerced to naive UTC
                # by the SQLite driver the same way stored values are.
                cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)
                conditions.append(CorrelationGroup.started_at >= cutoff)

        if search:
            pattern = f"%{search}%"
            column_match = (
                CorrelationGroup.correlation_id.ilike(pattern)
                | CorrelationGroup.primary_event_id.ilike(pattern)
                | CorrelationGroup.sector_id.ilike(pattern)
                | CorrelationGroup.track_candidate_id.ilike(pattern)
            )
            # Same CAM / EV / TRK vocabulary the Event Log search box promises:
            # member event ids plus the camera and track carried by those events.
            member_match = CorrelationGroup.correlation_id.in_(
                select(CorrelationGroupMember.correlation_id)
                .join(Event, Event.event_id == CorrelationGroupMember.event_id)
                .where(
                    CorrelationGroupMember.event_id.ilike(pattern)
                    | Event.camera_id.ilike(pattern)
                    | Event.track_id.ilike(pattern)
                )
                .distinct()
            )
            # INC-… resolves through the C1-owned incident referencing a member
            # event; correlation still stores no incident state of its own.
            incident_match = CorrelationGroup.correlation_id.in_(
                select(CorrelationGroupMember.correlation_id)
                .join(Event, Event.event_id == CorrelationGroupMember.event_id)
                .join(Incident, Incident.event_id == Event.event_id)
                .where(Incident.incident_id.ilike(pattern))
                .distinct()
            )
            conditions.append(column_match | member_match | incident_match)

        filter_stmt = select(CorrelationGroup.correlation_id)
        if conditions:
            filter_stmt = filter_stmt.where(*conditions)

        count_stmt = select(func.count()).select_from(filter_stmt.subquery())
        total = (await self.session.execute(count_stmt)).scalar_one()

        stmt = select(CorrelationGroup).where(
            CorrelationGroup.correlation_id.in_(filter_stmt)
        )

        if sort not in _SORTABLE_COLUMNS:
            sort = "started_at"
        sort_column = getattr(CorrelationGroup, sort)
        if order == "asc":
            stmt = stmt.order_by(sort_column.asc())
        else:
            stmt = stmt.order_by(sort_column.desc())

        stmt = stmt.offset((page - 1) * page_size).limit(page_size)
        res = await self.session.execute(stmt)
        records = list(res.scalars().all())

        return records, total

    async def list_active(self) -> list:
        stmt = select(CorrelationGroup).where(
            CorrelationGroup.state.in_(_ACTIVE_STATES),
            CorrelationGroup.ended_at.is_(None),
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_active_snapshot(self) -> list:
        return await self.list_active()

    async def list_by_camera(self, camera_id: str, limit: int = 50) -> list:
        stmt = (
            select(CorrelationGroup)
            .join(CorrelationGroupMember)
            .join(Event, Event.event_id == CorrelationGroupMember.event_id)
            .where(Event.camera_id == camera_id)
            .distinct()
            .order_by(CorrelationGroup.started_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def list_by_event(self, event_id: str) -> list:
        stmt = (
            select(CorrelationGroup)
            .join(CorrelationGroupMember)
            .where(CorrelationGroupMember.event_id == event_id)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_by_event(self, event_id: str) -> list:
        """Get all correlation groups that contain a specific event"""
        return await self.list_by_event(event_id)

    async def get_active_for_camera(self, camera_id: str) -> list:
        stmt = (
            select(CorrelationGroup)
            .join(CorrelationGroupMember)
            .join(Event, Event.event_id == CorrelationGroupMember.event_id)
            .where(
                Event.camera_id == camera_id,
                CorrelationGroup.state.in_(_ACTIVE_STATES),
                CorrelationGroup.ended_at.is_(None),
            )
            .distinct()
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_active_for_probe(self, camera_id: str) -> list:
        return await self.get_active_for_camera(camera_id)

    async def get_recent(self, hours: int = 24, limit: int = 100) -> list:
        now = datetime.now(timezone.utc)
        cutoff = now - timedelta(hours=hours)
        stmt = (
            select(CorrelationGroup)
            .where(CorrelationGroup.started_at >= cutoff)
            .order_by(CorrelationGroup.started_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())