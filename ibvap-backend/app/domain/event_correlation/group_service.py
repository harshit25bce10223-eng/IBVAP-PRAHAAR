# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 4 — Correlation Group Service
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import json
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.event_correlation import (
    CorrelationGroup,
    CorrelationGroupMember,
    CorrelationRelationship,
    CorrelationHistory,
    CorrelationConfig,
    CorrelationStatus,
    CorrelationGroupState,
    CorrelationCompleteness,
)
from app.models.event import Event
from app.models.incident import Incident

from app.domain.event_correlation.temporal_engine import TemporalRelationEngine
from app.domain.event_correlation.spatial_engine import SpatialRelationEngine
from app.domain.event_correlation.entity_engine import EntityRelationEngine
from app.domain.event_correlation.rule_engine import CorrelationRuleEngine, CorrelationResult
from app.repositories.event_correlation import (
    CorrelationGroupRepository,
    CorrelationGroupMemberRepository,
    CorrelationRelationshipRepository,
    CorrelationHistoryRepository,
    CorrelationConfigRepository,
)

UNKNOWN_TOKEN = "UNKNOWN"
DEFAULT_PROFILE = "MIXED_BORDER_SECTOR"


def _to_aware(value: Any) -> datetime | None:
    """Normalize a datetime (str, naive, aware) to an aware UTC datetime.

    Aware values from any offset are converted to UTC (not just re-labelled):
    aiosqlite stores wall-clock strings and drops tzinfo, so comparisons against
    values re-read from the database are only correct in UTC.
    """
    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    if isinstance(value, datetime):
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
    return None


async def _load_events_by_id(
    session: AsyncSession, event_ids: list[str]
) -> dict[str, Event]:
    """Load Event rows by id with chunked IN-queries (SQLite variable limit)."""
    events_by_id: dict[str, Event] = {}
    unique_ids = list(dict.fromkeys(event_ids))
    chunk_size = 500
    for start in range(0, len(unique_ids), chunk_size):
        chunk = unique_ids[start : start + chunk_size]
        stmt = select(Event).where(Event.event_id.in_(chunk))
        result = await session.execute(stmt)
        for event in result.scalars().all():
            events_by_id[event.event_id] = event
    return events_by_id


def _build_group_dict(
    group: CorrelationGroup,
    members: list,
    events_by_id: dict[str, Event],
) -> dict | None:
    """Build the rule-engine group dict from already-loaded members/events.

    Pure extraction of the former inline body of ``_group_to_dict`` — same
    member ordering, same UNKNOWN-token handling, same None cases — shared by
    the per-group and batched (ingest/list) call sites so both produce
    byte-identical dicts.
    """
    camera_ids: list[str] = []
    zone_ids: list[str] = []
    track_ids: list[str] = []
    member_events: list[dict] = []
    latest_ts: datetime | None = None
    seen_cameras: set[str] = set()
    seen_zones: set[str] = set()
    seen_tracks: set[str] = set()

    for member in members:
        event = events_by_id.get(member.event_id)
        if event is None:
            continue
        if event.camera_id != UNKNOWN_TOKEN:
            if event.camera_id not in seen_cameras:
                seen_cameras.add(event.camera_id)
                camera_ids.append(event.camera_id)
        if event.zone_id != UNKNOWN_TOKEN:
            if event.zone_id not in seen_zones:
                seen_zones.add(event.zone_id)
                zone_ids.append(event.zone_id)
        if event.track_id != UNKNOWN_TOKEN:
            if event.track_id not in seen_tracks:
                seen_tracks.add(event.track_id)
                track_ids.append(event.track_id)
        if latest_ts is None or event.ts > latest_ts:
            latest_ts = event.ts
        payload = None
        if event.payload_json:
            try:
                payload = json.loads(event.payload_json)
            except (TypeError, ValueError):
                payload = None
        payload = payload if isinstance(payload, dict) else None
        member_events.append({
            "event_id": event.event_id,
            "event_time": event.ts,
            "camera_id": event.camera_id if event.camera_id != UNKNOWN_TOKEN else None,
            "zone_id": event.zone_id if event.zone_id != UNKNOWN_TOKEN else None,
            "sector_id": group.sector_id,
            "track_id": event.track_id if event.track_id != UNKNOWN_TOKEN else None,
            "reid_candidate": (payload or {}).get("reid_candidate"),
            "location": (payload or {}).get("location"),
        })

    if not member_events:
        return None

    sector_ids = [group.sector_id] if group.sector_id else []
    return {
        "correlation_id": group.correlation_id,
        "started_at": group.started_at,
        "ended_at": latest_ts,
        "sources": group.sources or [],
        "camera_ids": camera_ids,
        "zone_ids": zone_ids,
        "sector_ids": sector_ids,
        "track_ids": track_ids,
        "revision": group.revision,
        "event_count": len(member_events),
        "member_events": member_events,
    }


class CorrelationService:
    """
    Main orchestration service for event correlation.

    Orchestrates:
    - Event ingestion, duplicate detection and Event-row persistence
    - Candidate group discovery (active groups only)
    - Rule-engine-driven correlation scoring (temporal/spatial/entity)
    - Correlation group creation, updates, counts and lifecycle history
    - Integrity verification
    """

    def __init__(self, session: AsyncSession):
        self.session = session
        self.group_repo = CorrelationGroupRepository(session)
        self.member_repo = CorrelationGroupMemberRepository(session)
        self.relationship_repo = CorrelationRelationshipRepository(session)
        self.history_repo = CorrelationHistoryRepository(session)
        self.config_repo = CorrelationConfigRepository(session)

    # ─────────────────────────────────────────────────────────────────────────
    # Main Entry Point
    # ─────────────────────────────────────────────────────────────────────────

    async def ingest_event(
        self,
        event_data: dict,
        source: str = "SYSTEM",
    ) -> dict:
        normalized = self._normalize_event(event_data, source)

        # 1. Idempotency / duplicate detection (event_id and dedup key)
        existing = await self._find_existing_membership(normalized)
        if existing:
            group_id = existing.get("correlation_id")
            return {
                "correlation_id": group_id,
                "action": "DUPLICATE",
                "group_id": group_id,
                "message": "Duplicate event ignored",
            }

        # 2. Persist an Event row (FK anchor for members/history/relationships)
        event = await self._persist_event(normalized)
        if event is None:
            # Concurrent ingest of the same event won the race.
            existing = await self._find_existing_membership(normalized)
            group_id = existing.get("correlation_id") if existing else None
            return {
                "correlation_id": group_id,
                "action": "DUPLICATE",
                "group_id": group_id,
                "message": "Duplicate event ignored (concurrent ingest)",
            }

        # 3. Build the configured rule engine for this environment
        rule = await self._build_rule_engine(normalized)

        # 4. Candidate groups as rule-engine group dicts.
        # Batched variant of _group_to_dict: members and events for every active
        # group are fetched with chunked IN-queries instead of one member query
        # + one get() per member per group. Output is identical (shared
        # _build_group_dict); the per-round-trip cost of the per-group form grows
        # linearly with the active-group count and dominates ingest at scale.
        # The temporal prefilter is semantics-preserving (see its docstring):
        # groups it drops could never pass the rule engine's first gate.
        active_groups = await self.group_repo.list_active()
        active_groups = await self._temporal_candidate_prefilter(
            active_groups, rule, event.ts
        )
        group_dicts = await self._group_dicts_batched(active_groups)

        # 5. Score against existing groups
        engine_event = self._engine_event_dict(normalized, event)
        result: CorrelationResult = rule.evaluate_event(engine_event, group_dicts)

        if result.action == "UPDATED" and result.group_id:
            group = await self.group_repo.get(result.group_id)
            if group is None:
                result = None  # defensive: group deleted between read and write
            else:
                await self._add_to_group(
                    group, normalized, event, result, rule
                )
                membership_type = "SUPPORTING" if result.confidence and result.confidence >= 70 else "CONTEXT"
                await self.session.commit()
                return {
                    "correlation_id": group.correlation_id,
                    "action": "UPDATED",
                    "group_id": group.correlation_id,
                    "score": result.confidence,
                    "status": result.status,
                    "event_id": event.event_id,
                    "membership_type": membership_type,
                    "relationships": len(result.relationships),
                }

        # 6. No candidate above threshold -> new standalone group
        group = await self._create_new_group(normalized, event, rule)
        await self.session.commit()
        return {
            "correlation_id": group.correlation_id,
            "action": "CREATED",
            "group_id": group.correlation_id,
            "score": 0,
            "status": CorrelationStatus.STANDALONE,
            "event_id": event.event_id,
            "membership_type": "PRIMARY",
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Normalization / persistence helpers
    # ─────────────────────────────────────────────────────────────────────────

    def _normalize_event(self, event_data: dict, source: str) -> dict:
        """Normalize incoming event data to canonical format.

        The upstream source identifier is preserved; caller-provided source
        wins over the routing default so domain semantics are not lost.
        """
        event_time = _to_aware(
            event_data.get("event_time") or event_data.get("ts")
        ) or datetime.now(timezone.utc)

        camera_id = event_data.get("camera_id")
        track_id = event_data.get("track_id")
        zone_id = event_data.get("zone_id")

        return {
            "event_id": event_data.get("event_id") or f"EVT-{uuid.uuid4().hex[:12].upper()}",
            "event_type": event_data.get("event_type") or event_data.get("kind") or "DETECTION",
            "source": event_data.get("source") or source,
            "camera_id": camera_id,
            "zone_id": zone_id,
            "sector_id": event_data.get("sector_id"),
            "region_profile": event_data.get("region_profile")
            or event_data.get("profile"),
            "track_id": track_id,
            "event_time": event_time,
            "source_event_id": event_data.get("source_event_id"),
            "source_sequence": event_data.get("source_sequence"),
            "object_type": event_data.get("object_type"),
            "bbox": event_data.get("bbox"),
            "confidence": event_data.get("confidence"),
            "is_night": event_data.get("is_night", False),
            "multi_camera_confirmed": event_data.get("multi_camera_confirmed", False),
            "reliability": event_data.get("reliability", "HIGH"),
            "modality": event_data.get("modality") or "VIDEO",
            "reid_candidate": event_data.get("reid_candidate"),
            "location": event_data.get("location"),
            "payload": event_data.get("payload"),
        }

    async def _persist_event(self, normalized: dict) -> Event | None:
        """Insert the Event row that anchors members/history/relationships.

        The Event model requires camera/track/zone (all NOT NULL). Events that
        genuinely lack that context (e.g. audio anomalies) use UNKNOWN tokens;
        engines treat those tokens as absent so no false relationships form.

        The deduplication key is checked BEFORE insert: savepoints do not
        isolate IntegrityError under this engine configuration, so a
        SELECT-before-INSERT pre-check is the primary defense (the
        flush-and-rollback path remains only as a race fallback).
        """
        event = await self.session.get(Event, normalized["event_id"])
        if event is not None:
            return event

        camera_id = normalized.get("camera_id") or UNKNOWN_TOKEN
        track_id = normalized.get("track_id") or UNKNOWN_TOKEN
        zone_id = normalized.get("zone_id") or UNKNOWN_TOKEN

        source_event_id = normalized.get("source_event_id")
        source_sequence = normalized.get("source_sequence")
        if source_event_id and source_sequence is not None:
            dedup_key = f"{camera_id}|{source_event_id}|{source_sequence}"
        else:
            dedup_key = f"{camera_id}|{normalized.get('source')}|{normalized['event_id']}"

        duplicate = await self._find_event_by_dedup_key(dedup_key)
        if duplicate is not None:
            return None

        payload = normalized.get("payload")
        if payload is not None and not isinstance(payload, dict):
            payload = None
        extras = {}
        if normalized.get("reid_candidate") is not None:
            extras["reid_candidate"] = normalized.get("reid_candidate")
        if normalized.get("location") is not None:
            extras["location"] = normalized.get("location")
        if payload is None:
            payload = extras or None
        elif extras:
            payload = {**extras, **payload}

        event = Event(
            event_id=normalized["event_id"],
            event_type=normalized.get("event_type") or "DETECTION",
            camera_id=camera_id,
            track_id=track_id,
            zone_id=zone_id,
            ts=normalized["event_time"],
            deduplication_key=dedup_key,
            payload_json=json.dumps(payload) if payload is not None else None,
        )
        self.session.add(event)
        try:
            await self.session.flush()
        except IntegrityError:
            await self.session.rollback()
            duplicate = await self._find_event_by_dedup_key(dedup_key)
            if duplicate is not None:
                return None
            raise
        return event

    async def _find_event_by_dedup_key(self, dedup_key: str) -> Event | None:
        stmt = select(Event).where(Event.deduplication_key == dedup_key)
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()

    async def _find_existing_membership(self, normalized: dict) -> dict | None:
        """Find whether the event already belongs to a group (idempotency)."""
        members = await self.member_repo.list_by_event(normalized["event_id"])
        if members:
            return {"correlation_id": members[0].correlation_id}

        camera = normalized.get("camera_id") or UNKNOWN_TOKEN
        source_event_id = normalized.get("source_event_id")
        source_sequence = normalized.get("source_sequence")
        if source_event_id and source_sequence is not None:
            dedup_key = f"{camera}|{source_event_id}|{source_sequence}"
            event = await self._find_event_by_dedup_key(dedup_key)
            if event is not None:
                members = await self.member_repo.list_by_event(event.event_id)
                if members:
                    return {"correlation_id": members[0].correlation_id}
        return None

    def _engine_event_dict(self, normalized: dict, event: Event) -> dict:
        """Build the engine-facing event dict, treating UNKNOWN tokens as absent."""
        camera = normalized.get("camera_id")
        zone = normalized.get("zone_id")
        sector = normalized.get("sector_id")
        track = normalized.get("track_id")
        return {
            "event_id": event.event_id,
            "event_time": event.ts,
            "camera_id": camera if (camera and camera != UNKNOWN_TOKEN) else None,
            "zone_id": zone if (zone and zone != UNKNOWN_TOKEN) else None,
            "sector_id": sector if (sector and sector != UNKNOWN_TOKEN) else None,
            "track_id": track if (track and track != UNKNOWN_TOKEN) else None,
            "source": normalized.get("source") or "UNKNOWN",
            "event_type": event.event_type,
            "reid_candidate": normalized.get("reid_candidate"),
            "location": normalized.get("location"),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # Config / rule engine construction
    # ─────────────────────────────────────────────────────────────────────────

    async def _build_rule_engine(self, normalized: dict) -> CorrelationRuleEngine:
        profile = normalized.get("region_profile") or DEFAULT_PROFILE
        configs = await self.config_repo.get_active_for_profile(profile)

        config_dict: dict[str, Any] = {}
        camera_adjacency: dict[str, list[str]] = {}
        if configs is not None:
            config_dict["temporal_window_seconds"] = configs.temporal_window_seconds
            config_dict["max_group_duration_seconds"] = configs.max_group_duration_seconds
            config_dict["min_relationship_strength"] = configs.min_relationship_strength
            config_dict["min_support_events"] = configs.min_support_events
            adjacency = configs.camera_adjacency or {}
            camera_adjacency = {
                str(k): [str(v) for v in vs] for k, vs in adjacency.items()
            } if isinstance(adjacency, dict) else {}

        spatial = SpatialRelationEngine(camera_adjacency=camera_adjacency)
        if config_dict and "temporal_window_seconds" in config_dict:
            temp = TemporalRelationEngine(
                default_window_seconds=config_dict["temporal_window_seconds"]
            )
        else:
            temp = TemporalRelationEngine()
        entity = EntityRelationEngine()
        rule_config = {
            "min_correlation_score": config_dict.get("min_relationship_strength", 50),
            "max_group_duration_seconds": config_dict.get("max_group_duration_seconds", 300),
            "temporal_window_seconds": config_dict.get("temporal_window_seconds", 60),
            "min_support_events": config_dict.get("min_support_events", 1),
        }
        return CorrelationRuleEngine(
            temporal_engine=temp,
            spatial_engine=spatial,
            entity_engine=entity,
            config=rule_config,
        )

    async def _load_active_config(self, profile: str | None) -> CorrelationConfig | None:
        configs = await self.config_repo.get_active_for_profile(
            profile or DEFAULT_PROFILE
        )
        return configs

    # ─────────────────────────────────────────────────────────────────────────
    # Group dict construction for the rule engine
    # ─────────────────────────────────────────────────────────────────────────

    async def _group_to_dict(self, group: CorrelationGroup) -> dict | None:
        members = await self.member_repo.list_by_group(group.correlation_id)
        if not members:
            return None
        events_by_id = await _load_events_by_id(
            self.session, [m.event_id for m in members]
        )
        return _build_group_dict(group, members, events_by_id)

    async def _group_dicts_batched(
        self, groups: list[CorrelationGroup]
    ) -> list[dict]:
        """Batched, output-identical variant of per-group ``_group_to_dict``.

        Fetches member rows for every group with chunked IN-queries and loads
        the referenced events once, instead of one member query + one get() per
        member per group. Groups without members (or without any loadable
        member event) are skipped, exactly like ``_group_to_dict`` returning
        None; the order of the returned dicts follows ``groups``.
        """
        if not groups:
            return []
        members_by_group = await self.member_repo.list_by_groups(
            [g.correlation_id for g in groups]
        )
        event_ids = [
            m.event_id for members in members_by_group.values() for m in members
        ]
        events_by_id = await _load_events_by_id(self.session, event_ids)
        group_dicts: list[dict] = []
        for group in groups:
            members = members_by_group.get(group.correlation_id)
            if not members:
                continue
            gd = _build_group_dict(group, members, events_by_id)
            if gd is not None:
                group_dicts.append(gd)
        return group_dicts

    async def _temporal_candidate_prefilter(
        self,
        groups: list[CorrelationGroup],
        rule: CorrelationRuleEngine,
        event_ts: datetime | None,
    ) -> list[CorrelationGroup]:
        """Drop groups the rule engine's temporal gate would skip anyway.

        Semantics-preserving prefilter for the ingest hot path. The engine's
        first gate (``find_candidate_groups``) discards any group without a
        temporal relation to the event before spatial/entity/source gates and
        scoring run. Ingest events are always point events (the engine event
        dict carries no ``end_time``), and a point-vs-point relation exists
        exactly when the event timestamp is within ``window + 2*clock_skew`` of
        EITHER the group's ``started_at`` OR its latest member timestamp --
        the two bounds ``TemporalRelationEngine.classify_relation`` compares
        against. Groups that fail both bounds can never become candidates, so
        hydrating their members and events is pure overhead; without this
        prefilter the per-ingest cost grows linearly with the number of active
        groups (which C4 never auto-closes, B-06).
        """
        if not groups:
            return []
        anchor = _to_aware(event_ts)
        if anchor is None:
            # Defensive: no comparable time anchor -> keep the full set and let
            # the engine decide (it treats a missing event time as no relation).
            return groups
        window = getattr(rule, "temporal_window", None) or 60
        skew = getattr(getattr(rule, "temporal", None), "clock_skew_tolerance", 5)
        tolerance = timedelta(seconds=window + 2 * skew)
        latest_by_group = await self.member_repo.latest_event_ts_by_groups(
            [g.correlation_id for g in groups]
        )
        kept: list[CorrelationGroup] = []
        for group in groups:
            for bound in (
                group.started_at,
                latest_by_group.get(group.correlation_id),
            ):
                bound_ts = _to_aware(bound)
                if bound_ts is not None and abs(anchor - bound_ts) <= tolerance:
                    kept.append(group)
                    break
        return kept

    # ─────────────────────────────────────────────────────────────────────────
    # Group creation / update
    # ─────────────────────────────────────────────────────────────────────────

    async def _create_new_group(
        self,
        normalized: dict,
        event: Event,
        rule: CorrelationRuleEngine,
    ) -> CorrelationGroup:
        camera = normalized.get("camera_id")
        zone = normalized.get("zone_id")
        camera_count = 1 if (camera and camera != UNKNOWN_TOKEN) else 0
        zone_count = 1 if (zone and zone != UNKNOWN_TOKEN) else 0
        source = normalized.get("source") or "SYSTEM"

        group = await self.group_repo.create(
            status=CorrelationStatus.STANDALONE,
            state=CorrelationGroupState.OPEN,
            started_at=event.ts,
            primary_event_id=event.event_id,
            event_count=1,
            camera_count=camera_count,
            zone_count=zone_count,
            source_count=1,
            sources=[source],
            modalities=[normalized.get("modality") or "VIDEO"],
            sector_id=normalized.get("sector_id"),
            region_profile=normalized.get("region_profile"),
            camera_chain=[camera] if camera and camera != UNKNOWN_TOKEN else None,
            completeness=CorrelationCompleteness.UNKNOWN,
            algorithm_version="1.0",
            configuration_version="1.0",
        )

        await self.member_repo.add_member(
            correlation_id=group.correlation_id,
            event_id=event.event_id,
            membership_type="PRIMARY",
            confidence=100,
            reason="Primary event of new correlation group",
        )

        await self.history_repo.log_transition(
            correlation_id=group.correlation_id,
            old_status=None,
            new_status=CorrelationStatus.STANDALONE,
            reason="Group created with primary event",
            trigger_event_id=event.event_id,
            state=CorrelationGroupState.OPEN,
            revision=group.revision,
            snapshot_json={
                "event_count": 1,
                "status": CorrelationStatus.STANDALONE,
                "state": CorrelationGroupState.OPEN,
            },
        )
        return group

    async def _add_to_group(
        self,
        group: CorrelationGroup,
        normalized: dict,
        event: Event,
        result: CorrelationResult,
        rule: CorrelationRuleEngine,
    ) -> None:
        membership_type = (
            "SUPPORTING" if (result.confidence and result.confidence >= 70) else "CONTEXT"
        )
        await self.member_repo.add_member(
            correlation_id=group.correlation_id,
            event_id=event.event_id,
            membership_type=membership_type,
            confidence=result.confidence,
            reason=result.reason,
        )

        # Persist explicit relationships (deduped)
        for rel in result.relationships:
            await self.relationship_repo.upsert_relationship(
                correlation_id=group.correlation_id,
                from_event_id=rel.get("from_event_id"),
                to_event_id=rel.get("to_event_id"),
                rel_type=rel.get("type"),
                strength=rel.get("strength"),
                evidence_json=rel.get("evidence"),
                explanation=rel.get("explanation"),
            )

        # Recompute counts from authoritative member rows
        members = await self.member_repo.list_by_group(group.correlation_id)
        cameras: set[str] = set()
        zones: set[str] = set()
        sources: list[str] = list(group.sources or [])
        camera_chain: list[str] = []
        seen_camera_chain: set[str] = set()
        for member in members:
            member_event = await self.session.get(Event, member.event_id)
            if member_event is None:
                continue
            if member_event.camera_id != UNKNOWN_TOKEN:
                cameras.add(member_event.camera_id)
                if member_event.camera_id not in seen_camera_chain:
                    seen_camera_chain.add(member_event.camera_id)
                    camera_chain.append(member_event.camera_id)
            if member_event.zone_id != UNKNOWN_TOKEN:
                zones.add(member_event.zone_id)

        event_source = normalized.get("source") or "SYSTEM"
        if event_source not in sources:
            sources.append(event_source)

        new_status = result.status
        old_status = group.status
        event_count = len(members)
        if event_count >= 3:
            new_state = CorrelationGroupState.ACTIVE
        elif event_count == 2:
            new_state = CorrelationGroupState.ACTIVE
        else:
            new_state = group.state or CorrelationGroupState.OPEN

        group.event_count = event_count
        group.camera_count = len(cameras)
        group.zone_count = len(zones)
        group.source_count = len(sources)
        group.sources = sources
        group.camera_chain = camera_chain or None
        group.status = new_status
        group.state = new_state
        group.confidence = result.confidence
        group.completeness = result.completeness
        group.revision += 1
        group.ended_at = None  # B-06: never auto-close on add
        await self.session.flush()

        await self.history_repo.log_transition(
            correlation_id=group.correlation_id,
            old_status=old_status,
            new_status=new_status,
            reason=result.reason,
            trigger_event_id=event.event_id,
            state=new_state,
            revision=group.revision,
            snapshot_json={
                "event_count": event_count,
                "status": new_status,
                "state": new_state,
                "confidence": result.confidence,
            },
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Integrity verification
    # ─────────────────────────────────────────────────────────────────────────

    async def verify_correlation(self, correlation_id: str) -> dict:
        """Verify a correlation group's internal integrity.

        Correlation-integrity only (NOT Component 3 evidence hashing):
        - active members must be connected via at least one relationship
        - the primary event must still be a member
        - the group must have a coherent revision trail
        """
        group = await self.group_repo.get(correlation_id)
        if not group:
            return {"status": "NOT_FOUND", "correlation_id": correlation_id}

        members = await self.member_repo.list_by_group(correlation_id)
        relationships = await self.relationship_repo.list_by_group(correlation_id)
        history = await self.history_repo.list_by_correlation(
            correlation_id, limit=None
        )

        related_event_ids: set[str] = set()
        for rel in relationships:
            related_event_ids.add(rel.from_event_id)
            related_event_ids.add(rel.to_event_id)

        # Members in a supporting/contextual role must be reachable via a relation.
        orphaned_members = [
            m.event_id
            for m in members
            if m.removed_at is None
            and m.membership_type in ("SUPPORTING", "CONTEXT")
            and m.event_id not in related_event_ids
        ]

        primary_ok = (
            group.primary_event_id is None
            or any(m.event_id == group.primary_event_id for m in members)
        )

        status = (
            "VERIFIED"
            if not orphaned_members and primary_ok and group.revision >= 1
            else "INCONSISTENT"
        )
        return {
            "correlation_id": correlation_id,
            "status": status,
            "member_count": len(members),
            "relationship_count": len(relationships),
            "history_entries": len(history),
            "orphaned_members": orphaned_members,
            "revision": group.revision,
        }


# ─────────────────────────────────────────────────────────────────────────────
# Ingestion Endpoint Handler
# ─────────────────────────────────────────────────────────────────────────────

async def ingest_event(
    session: AsyncSession,
    event_data: dict,
    source: str = "SYSTEM",
) -> dict:
    service = CorrelationService(session)
    return await service.ingest_event(event_data, source)


def _serialize_member(m) -> dict:
    return {
        "id": m.id,
        "correlation_id": m.correlation_id,
        "event_id": m.event_id,
        "membership_type": m.membership_type,
        "confidence": m.confidence,
        "membership_confidence": m.membership_confidence,
        "reason": m.reason,
        "added_at": m.added_at.isoformat() if m.added_at else None,
        "removed_at": m.removed_at.isoformat() if m.removed_at else None,
        "revision": m.revision,
    }


_VALID_SEVERITIES = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}


def _source_for_kind(kind: str) -> str:
    return {
        "ANPR_READ": "ANPR",
        "AUDIO_ANOMALY": "AUDIO",
        "REID_CANDIDATE": "RE_ID",
        "TRACK": "TRACKING",
        "ZONE_ENTRY": "VIRTUAL_FENCE",
        "ZONE_EXIT": "VIRTUAL_FENCE",
        "DETECTION": "VIRTUAL_FENCE",
        "SURFACE_ANOMALY": "SURFACE_ANOMALY",
        "SUSPICIOUS_ACTIVITY": "SUSPICIOUS_ACTIVITY",
    }.get(kind, "UNKNOWN")


def _modality_for_kind(kind: str) -> str:
    if kind == "ANPR_READ":
        return "ANPR"
    if kind == "AUDIO_ANOMALY":
        return "AUDIO"
    return "VIDEO"


async def _serialize_member_full(
    session: AsyncSession,
    member: CorrelationGroupMember,
    sector_id: str | None,
    events_by_id: dict[str, Event] | None = None,
) -> dict:
    """Serialize a member plus its event-derived attributes for the frontend.

    The Event row holds camera/zone/track/timestamp/type (authoritative). The
    raw upstream payload may additionally carry severity/reliability/confidence
    which are surfaced verbatim — never derived. Unknown context is null, never
    fabricated.

    ``events_by_id`` optionally supplies pre-fetched Event rows (batched
    callers); when omitted the event is loaded here, unchanged.
    """
    d = _serialize_member(member)
    if events_by_id is not None:
        event = events_by_id.get(member.event_id)
    else:
        event = await session.get(Event, member.event_id)
    if event is None:
        d.update({
            "kind": "UNKNOWN",
            "camera_id": None,
            "zone_id": None,
            "track_id": None,
            "sector_id": sector_id,
            "timestamp": None,
            "source": "UNKNOWN",
            "modality": "UNKNOWN",
            "severity": None,
            "reliability": None,
            "confidence": None,
            "evidence_ids": [],
            "health_context": None,
        })
        return d

    payload = None
    if event.payload_json:
        try:
            payload = json.loads(event.payload_json)
        except (TypeError, ValueError):
            payload = None
    payload = payload if isinstance(payload, dict) else None

    d["kind"] = event.event_type or "UNKNOWN"
    d["camera_id"] = None if event.camera_id == UNKNOWN_TOKEN else event.camera_id
    d["zone_id"] = None if event.zone_id == UNKNOWN_TOKEN else event.zone_id
    d["track_id"] = None if event.track_id == UNKNOWN_TOKEN else event.track_id
    d["sector_id"] = sector_id
    d["timestamp"] = event.ts.isoformat() if event.ts else None
    d["source"] = _source_for_kind(event.event_type)
    d["modality"] = _modality_for_kind(event.event_type)
    d["severity"] = None
    d["reliability"] = None
    d["confidence"] = None
    d["evidence_ids"] = []
    d["health_context"] = None
    # Optional downstream reference surfaces (C5/C6/C7) — surfaced verbatim
    # only when the upstream payload actually supplied them, never derived.
    d["detection_id"] = None
    d["anpr_plate"] = None
    d["anpr_plate_confidence"] = None
    d["anpr_quality"] = None
    d["anpr_sighting_id"] = None
    d["track_candidate"] = None
    if payload:
        if payload.get("severity") in _VALID_SEVERITIES:
            d["severity"] = payload.get("severity")
        reliability = payload.get("reliability")
        if isinstance(reliability, str) and reliability.upper() in ("HIGH", "MEDIUM", "LOW", "UNKNOWN"):
            d["reliability"] = reliability.upper()
        if isinstance(payload.get("confidence"), (int, float)) and not isinstance(payload.get("confidence"), bool):
            d["confidence"] = payload.get("confidence")
        if isinstance(payload.get("evidence_ids"), list):
            d["evidence_ids"] = payload["evidence_ids"]
        if isinstance(payload.get("detection_id"), str):
            d["detection_id"] = payload["detection_id"]
        if isinstance(payload.get("anpr_plate"), str):
            d["anpr_plate"] = payload["anpr_plate"]
        if isinstance(payload.get("anpr_plate_confidence"), (int, float)) and not isinstance(payload.get("anpr_plate_confidence"), bool):
            d["anpr_plate_confidence"] = payload["anpr_plate_confidence"]
        if isinstance(payload.get("anpr_quality"), str):
            d["anpr_quality"] = payload["anpr_quality"]
        if isinstance(payload.get("anpr_sighting_id"), str):
            d["anpr_sighting_id"] = payload["anpr_sighting_id"]
        if isinstance(payload.get("track_candidate"), dict):
            d["track_candidate"] = payload["track_candidate"]
    return d


def _serialize_relationship(r) -> dict:
    return {
        "id": r.id,
        "correlation_id": r.correlation_id,
        "from_event_id": r.from_event_id,
        "to_event_id": r.to_event_id,
        "type": r.type,
        "strength": r.strength,
        "evidence_json": r.evidence_json,
        "explanation": r.explanation,
        "algorithm_version": r.algorithm_version,
        "revision": r.revision,
        "created_at": r.created_at.isoformat() if r.created_at else None,
        "updated_at": r.updated_at.isoformat() if r.updated_at else None,
    }


def _serialize_history(h) -> dict:
    return {
        "id": h.id,
        "correlation_id": h.correlation_id,
        "revision": h.revision,
        "status": h.status,
        "state": h.state,
        "snapshot_json": h.snapshot_json,
        "reason": h.reason,
        "trigger_event_id": h.trigger_event_id,
        "algorithm_version": h.algorithm_version,
        "configuration_version": h.configuration_version,
        "timestamp": h.timestamp.isoformat() if h.timestamp else None,
        "created_at": h.created_at.isoformat() if h.created_at else None,
    }


def _facet_for_relationship(rel) -> dict | None:
    """Map a persisted relationship row to a structured explanation facet."""
    rtype = (rel.type or "").upper()
    if rtype == "TEMPORAL":
        detail = "Related within the configured temporal window."
        label = "temporal"
    elif rtype == "SPATIAL":
        detail = "Related spatially (same/adjacent camera or zone)."
        label = "spatial"
    elif rtype == "ENTITY":
        detail = "Related by track/entity continuity."
        label = "entity"
    else:
        return None
    ev = rel.evidence_json or {}
    if rtype == "TEMPORAL" and ev.get("time_diff_seconds") is not None:
        label = f"{ev['time_diff_seconds']}s"
    if rtype == "SPATIAL" and ev.get("camera_id"):
        detail = f"Both events observed by camera {ev['camera_id']}."
    if rtype == "ENTITY" and ev.get("track_id"):
        detail = f"Same track {ev['track_id']} across both events."
    return {
        "facet": rtype,
        "label": label,
        "detail": detail,
    }


def _build_group_explanation(
    group,
    members: list,
    relationships: list,
) -> list[dict]:
    """Build structured explanation facets for a group from backend evidence only."""
    facets: list[dict] = []
    seen: set[str] = set()
    for rel in relationships:
        facet = _facet_for_relationship(rel)
        if facet and facet["facet"] not in seen:
            seen.add(facet["facet"])
            facets.append(facet)

    # Entity facet from track continuity not captured by explicit relationships.
    track_ids: list[str] = []
    for m in members:
        if m.get("track_id") and m["track_id"] not in track_ids:
            track_ids.append(m["track_id"])
    if len(track_ids) <= 1 and "ENTITY" not in seen and group.track_candidate_id:
        facets.append({
            "facet": "ENTITY",
            "label": "possible continuation",
            "detail": f"Candidate {group.track_candidate_id} links the signals (operational correlation, not identity).",
        })

    return facets


def _build_explanation_summary(
    group,
    members: list,
    relationships: list,
) -> str:
    """A human-readable one-line summary built ONLY from actual backend factors."""
    if not members:
        return "No member signals."

    signal_count = len(members)
    cameras: list[str] = []
    for m in members:
        if m.get("camera_id") and m["camera_id"] not in cameras:
            cameras.append(m["camera_id"])

    times = [m.get("timestamp") for m in members if m.get("timestamp")]
    span_sec: float | None = None
    if times:
        try:
            parsed = sorted(_to_aware(t) for t in times if _to_aware(t) is not None)
            if len(parsed) >= 2:
                span_sec = (parsed[-1] - parsed[0]).total_seconds()
        except Exception:
            span_sec = None

    timestr = f"{span_sec:.0f} seconds" if span_sec is not None else "an overlapping span"
    camstr = f"{len(cameras)} cameras" if cameras else "the source camera"

    relational = {
        r.type for r in relationships if r.type in ("TEMPORAL", "SPATIAL", "ENTITY")
    }
    basis = set()
    if "TEMPORAL" in relational or span_sec is not None:
        basis.add("time")
    if "SPATIAL" in relational or len(cameras) > 1:
        basis.add("space")
    if "ENTITY" in relational:
        basis.add("track continuity")
    because = ", ".join(sorted(basis)) if basis else "available signals"

    incident_txt = f" It became incident {group.incident_id}." if group.incident_id else ""
    return (
        f"{signal_count} signals were grouped because they occurred within "
        f"{timestr} across {camstr} and share {because}.{incident_txt}"
    )


def _correlation_strength_label(confidence: int | None) -> str:
    """Map the backend correlation confidence into a strength label.

    This is explicitly a CORRELATION strength, never a risk or identity claim.
    """
    if confidence is None:
        return "NONE"
    if confidence >= 85:
        return "HIGH"
    if confidence >= 60:
        return "MEDIUM"
    if confidence >= 30:
        return "LOW"
    return "NONE"


def _serialize_group(g: CorrelationGroup) -> dict:
    return {
        "correlation_id": g.correlation_id,
        "incident_id": g.incident_id,
        "primary_event_id": g.primary_event_id,
        "status": g.status,
        "state": g.state,
        "sector_id": g.sector_id,
        "region_profile": g.region_profile,
        "started_at": g.started_at.isoformat() if g.started_at else None,
        "ended_at": g.ended_at.isoformat() if g.ended_at else None,
        "event_count": g.event_count,
        "camera_count": g.camera_count,
        "zone_count": g.zone_count,
        "source_count": g.source_count,
        "confidence": g.confidence,
        "correlation_strength": _correlation_strength_label(g.confidence),
        "completeness": g.completeness,
        "uncertainty_reliability": g.uncertainty_reliability,
        "uncertainty_note": g.uncertainty_note,
        "track_candidate_id": g.track_candidate_id,
        "track_candidate_confidence": g.track_candidate_confidence,
        "track_candidate_label": g.track_candidate_label,
        "camera_chain": g.camera_chain,
        "modalities": g.modalities,
        "sources": g.sources,
        "health_context": g.health_context,
        "evidence_count": g.evidence_count,
        "connectivity": g.connectivity,
        "duplicated_or_suppressed": g.duplicated_or_suppressed,
        "revision": g.revision,
        "algorithm_version": g.algorithm_version,
        "configuration_version": g.configuration_version,
        "updated_at": g.updated_at.isoformat() if g.updated_at else None,
        "created_at": g.created_at.isoformat() if g.created_at else None,
    }


async def _fetch_incidents_by_event(
    session: AsyncSession, event_ids: list[str]
) -> dict[str, list]:
    """Look up C1 incidents by member event reference.

    Correlation surfaces risk BY REFERENCE only (C1 owns risk scoring);
    nothing here computes or estimates a score.
    """
    if not event_ids:
        return {}
    stmt = select(Incident).where(Incident.event_id.in_(event_ids))
    result = await session.execute(stmt)
    by_event: dict[str, list] = {}
    for incident in result.scalars().all():
        by_event.setdefault(incident.event_id, []).append(incident)
    return by_event


def _apply_risk_reference(
    group_dict: dict, risk_by_event: dict, event_ids: list[str]
) -> None:
    """Attach referenced incident risk (highest among linked incidents).

    Always present (null when no incident exists for any member event) so the
    frontend can render an honest "NOT SCORED" state instead of guessing.
    """
    incidents = [i for eid in event_ids for i in risk_by_event.get(eid, [])]
    if not incidents:
        group_dict["risk_score"] = None
        group_dict["risk_severity"] = None
        group_dict["risk_incident_ids"] = []
        return
    top = max(incidents, key=lambda i: i.risk_score)
    group_dict["risk_score"] = top.risk_score
    group_dict["risk_severity"] = top.severity
    group_dict["risk_incident_ids"] = sorted({i.incident_id for i in incidents})


async def get_correlation_group(
    session: AsyncSession,
    correlation_id: str,
) -> dict | None:
    """Get full correlation group details (group + members + relations + history)."""
    repo = CorrelationGroupRepository(session)
    group = await repo.get(correlation_id)
    if not group:
        return None

    member_repo = CorrelationGroupMemberRepository(session)
    members = await member_repo.list_by_group(correlation_id)

    rel_repo = CorrelationRelationshipRepository(session)
    relationships = await rel_repo.list_by_group(correlation_id)

    history_repo = CorrelationHistoryRepository(session)
    history = await history_repo.list_by_correlation(correlation_id, limit=None)

    events_by_id = await _load_events_by_id(session, [m.event_id for m in members])
    member_serialized = [
        await _serialize_member_full(session, m, group.sector_id, events_by_id)
        for m in members
    ]
    group_dict = _serialize_group(group)
    event_ids = [m.event_id for m in members]
    risk_by_event = await _fetch_incidents_by_event(session, event_ids)
    _apply_risk_reference(group_dict, risk_by_event, event_ids)
    group_dict["explanation"] = _build_group_explanation(
        group, member_serialized, relationships
    )
    group_dict["explanation_summary"] = _build_explanation_summary(
        group, member_serialized, relationships
    )

    return {
        "group": group_dict,
        "members": member_serialized,
        "relationships": [_serialize_relationship(r) for r in relationships],
        "history": [_serialize_history(h) for h in history],
    }


async def list_correlation_groups(
    session: AsyncSession,
    page: int = 1,
    page_size: int = 20,
    status: str | None = None,
    sector_id: str | None = None,
    camera_id: str | None = None,
    source: str | None = None,
    search: str | None = None,
    severity: str | None = None,
    time_range: str | None = None,
    sort: str = "started_at",
    order: str = "desc",
) -> tuple[list, int]:
    """List correlation groups with pagination and filtering."""
    repo = CorrelationGroupRepository(session)
    member_repo = CorrelationGroupMemberRepository(session)
    groups, total = await repo.list_paginated(
        page=page,
        page_size=page_size,
        status=status,
        camera_id=camera_id,
        sector_id=sector_id,
        source=source,
        search=search,
        severity=severity,
        time_range=time_range,
        sort=sort,
        order=order,
    )

    # Load member and relationship rows for the whole page with batched
    # queries and the referenced events once, instead of one member query +
    # one get() per member + one relationship query per group. Per-group rows
    # and their ordering are identical to the per-group calls.
    page_ids = [g.correlation_id for g in groups]
    members_by_group = await member_repo.list_by_groups(page_ids)
    rel_repo = CorrelationRelationshipRepository(session)
    rels_by_group = await rel_repo.list_by_groups(page_ids)

    per_group: list[tuple] = []
    all_event_ids: list[str] = []
    for g in groups:
        member_rows = members_by_group.get(g.correlation_id, [])
        event_ids = [m.event_id for m in member_rows]
        all_event_ids.extend(event_ids)
        per_group.append((g, member_rows, event_ids))

    risk_by_event = await _fetch_incidents_by_event(session, all_event_ids)
    events_by_id = await _load_events_by_id(session, all_event_ids)

    groups_list = []
    for g, member_rows, event_ids in per_group:
        gd = _serialize_group(g)
        member_serialized = [
            await _serialize_member_full(session, m, g.sector_id, events_by_id)
            for m in member_rows
        ]
        rel_members = rels_by_group.get(g.correlation_id, [])
        gd["member_events"] = member_serialized
        _apply_risk_reference(gd, risk_by_event, event_ids)
        gd["explanation"] = _build_group_explanation(
            g, member_serialized, rel_members
        )
        gd["explanation_summary"] = _build_explanation_summary(
            g, member_serialized, rel_members
        )
        groups_list.append(gd)
    return groups_list, total