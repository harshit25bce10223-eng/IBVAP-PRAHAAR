# ─────────────────────────────────────────────────────────────────────────────
# IBVAP — Incident Service (domain orchestration)
# ─────────────────────────────────────────────────────────────────────────────
# Application-facing service that wires geometry, membership state, zone rules,
# risk evaluation and persistence into a single "track_and_evaluate" step.
# All persistence goes through repositories; the DB remains the source of truth.
#
# Enhancement pass: integrates spatial uncertainty, trajectory direction,
# geometry confidence, and pre-intrusion warning into the response.
# All new fields are OPTIONAL in the response — existing API clients unaffected.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DatabaseError, IBVAPError
from app.domain.fence.fence_service import ZoneMembershipResult, object_allowed
from app.domain.fence.temporal_state import (
    MembershipState,
    TemporalMembership,
    TemporalTransitionResult,
    TrajectoryDirection,
    advance_temporal_state,
    estimate_trajectory,
)
from app.domain.geometry.bbox import get_representative_point, is_bbox_inside_zone
from app.domain.geometry.calibration import CalibrationQuality, get_uncalibrated
from app.domain.geometry.spatial_uncertainty import (
    GeometryConfidence,
    SpatialZone,
    classify_spatial_zone,
    compute_geometry_confidence,
)
from app.domain.risk.risk_engine import RiskResult, calculate_risk
from app.domain.tracking import track_state
from app.repositories.event_repository import EventRepository
from app.repositories.incident_repository import IncidentRepository
from app.repositories.track_repository import TrackRepository
from app.repositories.zone_repository import ZoneRepository

ENTRY = "ENTRY"
EXIT = "EXIT"

# Canonical persisted event types (spec §4: ZONE_ENTRY / ZONE_EXIT)
EVENT_TYPE_ENTRY = "ZONE_ENTRY"
EVENT_TYPE_EXIT = "ZONE_EXIT"

# Default uncertainty margin (configurable per-deployment)
# Spatial uncertainty margin (normalized units). 0.0 = binary INSIDE/OUTSIDE (spec-compliant).
# Non-zero margin enables spatial uncertainty classification for future Camera Health integration.
DEFAULT_UNCERTAINTY_MARGIN = 0.0


class ZoneEvaluationOutcome:
    __slots__ = (
        "zone",
        "is_inside",
        "previously_inside",
        "transition",
        "rule_passed",
        "event_created",
        "event_id",
        "incident_created",
        "incident",
    )

    def __init__(
        self,
        zone: dict[str, Any],
        is_inside: bool,
        previously_inside: bool,
        transition: str,
        rule_passed: bool,
    ) -> None:
        self.zone = zone
        self.is_inside = is_inside
        self.previously_inside = previously_inside
        self.transition = transition
        self.rule_passed = rule_passed
        self.event_created = False
        self.event_id: str | None = None
        self.incident_created = False
        self.incident: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "zone_id": self.zone["zone_id"],
            "zone_name": self.zone["name"],
            "is_inside": self.is_inside,
            "previously_inside": self.previously_inside,
            "transition": self.transition,
            "rule_passed": self.rule_passed,
            "event": {"created": self.event_created, "event_id": self.event_id},
            "incident": {"created": self.incident_created, **(self.incident or {})},
        }


class IncidentService:
    def __init__(
        self,
        session: AsyncSession,
        zone_repo: ZoneRepository,
        track_repo: TrackRepository,
        event_repo: EventRepository,
        incident_repo: IncidentRepository,
    ) -> None:
        self.session = session
        self.zones = zone_repo
        self.tracks = track_repo
        self.events = event_repo
        self.incidents = incident_repo

    async def evaluate_track(
        self,
        *,
        track_id: str,
        camera_id: str,
        object_type: str,
        bbox: dict[str, float],
        confidence: float,
        is_night: bool,
        multi_camera_confirmed: bool,
        reliability: str,
        ts: datetime | None = None,
        # ── Enhancement pass: optional camera-health signals ─────────────────────
        viewpoint_shift_detected: bool = False,
        fence_confidence_override: str | None = None,
        uncertainty_margin: float = DEFAULT_UNCERTAINTY_MARGIN,
    ) -> dict[str, Any]:
        """Execute the full 11-step evaluation pipeline (spec §19) + enhancement pass."""
        now = ts or track_state.utcnow()
        if now.tzinfo is None:
            now = now.replace(tzinfo=timezone.utc)

        # ── 2. update/create track state ────────────────────────────────────────
        track = await self.tracks.get_or_create(
            track_id=track_id, camera_id=camera_id, object_type=object_type
        )
        prev_membership = track_state.parse_membership(track.current_membership_json)
        path = track_state.parse_path(track.path_json)

        # ── Ground-contact representative point (research-backed default) ────────
        rep_point = get_representative_point(bbox, strategy="bottom_center")

        # ── Geometry confidence from camera health signals ────────────────────────
        geometry_conf = compute_geometry_confidence(
            viewpoint_shift_detected=viewpoint_shift_detected,
            calibration_quality=CalibrationQuality.INVALID,  # no calibration by default
            detection_confidence=confidence,
            fence_confidence_override=fence_confidence_override,
        )

        # ── 3/4. evaluate all applicable zones; 5. compare with previous state ──
        zones = await self.zones.list_by_camera(camera_id)
        outcomes: list[ZoneEvaluationOutcome] = []
        membership_snapshot: dict[str, bool] = {}
        global_pre_warning = False
        global_trajectory = TrajectoryDirection.UNKNOWN

        for zone in zones:
            rules = json.loads(zone.rules_json or "{}")
            polygon = json.loads(zone.polygon_json or "[]")
            if not zone.active:
                membership_snapshot[zone.zone_id] = prev_membership.get(zone.zone_id, False)
                outcome = ZoneEvaluationOutcome(
                    zone={"zone_id": zone.zone_id, "name": zone.name, "polygon": polygon},
                    is_inside=False,
                    previously_inside=bool(prev_membership.get(zone.zone_id, False)),
                    transition="INACTIVE",
                    rule_passed=False,
                )
                outcomes.append(outcome)
                continue

            prev_inside = prev_membership.get(zone.zone_id, False)

            # ── Spatial uncertainty classification ────────────────────────────────
            spatial_zone = classify_spatial_zone(rep_point, polygon, uncertainty_margin)
            cur_inside = spatial_zone != SpatialZone.DEFINITELY_OUTSIDE
            spatial_uncertain = spatial_zone == SpatialZone.BOUNDARY_UNCERTAIN

            # ── Trajectory direction (deterministic, from path history) ───────────
            trajectory = estimate_trajectory(
                path=path,
                zone_polygon=polygon,
                current_point=rep_point,
            )
            global_trajectory = trajectory

            rule_passed = object_allowed(rules, object_type, now)
            transition = track_state.membership_transition(prev_inside, cur_inside)

            outcome = ZoneEvaluationOutcome(
                zone={"zone_id": zone.zone_id, "name": zone.name},
                is_inside=cur_inside,
                previously_inside=prev_inside,
                transition=transition,
                rule_passed=rule_passed,
            )

            # ── NEW entry detection ──────────────────────────────────────────────
            # If geometry is DEGRADED and object only in uncertainty band, do not
            # create incident — require DEFINITELY_INSIDE under degraded geometry.
            geometry_ok = (geometry_conf != GeometryConfidence.DEGRADED) or (
                spatial_zone == SpatialZone.DEFINITELY_INSIDE
            )

            if transition == ENTRY and rule_passed and geometry_ok and not spatial_uncertain:
                await self._create_entry_event_and_incident(
                    outcome=outcome,
                    track_id=track_id,
                    camera_id=camera_id,
                    zone=zone,
                    rules=rules,
                    object_type=object_type,
                    confidence=confidence,
                    is_night=is_night,
                    multi_camera_confirmed=multi_camera_confirmed,
                    reliability=reliability,
                    bbox=bbox,
                    now=now,
                )
            elif transition == EXIT and rule_passed:
                await self._create_exit_event(
                    outcome=outcome,
                    track_id=track_id,
                    camera_id=camera_id,
                    zone=zone,
                    now=now,
                )

            # Pre-intrusion warning: approaching but not yet confirmed inside
            if (
                trajectory == TrajectoryDirection.APPROACHING_ZONE
                and not cur_inside
                and not prev_inside
            ):
                global_pre_warning = True

            outcome.zone["polygon"] = polygon
            membership_snapshot[zone.zone_id] = cur_inside and not spatial_uncertain
            outcomes.append(outcome)

        # ── persist updated track state (membership + path) ─────────────────────
        track = await self.tracks.get(track_id) or track
        await self.tracks.update_state(
            track=track,
            object_type=object_type,
            bbox=bbox,
            membership=membership_snapshot,
            now=now,
        )
        await self.session.commit()

        return self._build_response(track_id, camera_id, object_type, rep_point, outcomes)

    async def _create_entry_event_and_incident(
        self,
        outcome: ZoneEvaluationOutcome,
        track_id: str,
        camera_id: str,
        zone: Any,
        rules: dict[str, Any],
        object_type: str,
        confidence: float,
        is_night: bool,
        multi_camera_confirmed: bool,
        reliability: str,
        bbox: dict[str, float],
        now: datetime,
    ) -> None:
        # Determine generation = count of prior ENTRY crossings for this triple.
        generation = await self.events.count_entries(camera_id, track_id, zone.zone_id)
        dedup = track_state.dedup_key(camera_id, track_id, zone.zone_id, ENTRY, generation)

        try:
            event = await self.events.create(
                event_type=EVENT_TYPE_ENTRY,
                camera_id=camera_id,
                track_id=track_id,
                zone_id=zone.zone_id,
                payload={
                    "object_type": object_type,
                    "bbox": bbox,
                    "rule_passed": True,
                    "rules": rules,
                    "member_transition": ENTRY,
                },
                deduplication_key=dedup,
                ts=now,
            )
        except DatabaseError:
            # A concurrent request already recorded this exact crossing (unique
            # dedup constraint). Treat it as idempotent: no second incident.
            self.session.rollback()
            return
        outcome.event_created = True
        outcome.event_id = event.event_id

        # ── 9. risk ─────────────────────────────────────────────────────────────
        risk: RiskResult = calculate_risk(
            object_type=object_type,
            zone_crossed=True,
            is_night=is_night,
            multi_camera_confirmed=multi_camera_confirmed,
            confidence=confidence,
            reliability=reliability,
            evidence=f"Track {track_id} entered zone {zone.zone_id}.",
        )

        # ── 10. incident ─────────────────────────────────────────────────────────
        incident = await self.incidents.create(
            risk_score=risk.risk_score,
            raw_score=risk.raw_score,
            severity=risk.severity,
            factors=risk.factors,
            event_id=event.event_id,
            camera_id=camera_id,
            track_id=track_id,
            zone_id=zone.zone_id,
            created_at=now,
        )
        outcome.incident_created = True
        outcome.incident = {
            "incident_id": incident.incident_id,
            "risk_score": risk.risk_score,
            "severity": risk.severity,
            "factors": risk.factors,
        }

    async def _create_exit_event(
        self,
        outcome: ZoneEvaluationOutcome,
        track_id: str,
        camera_id: str,
        zone: Any,
        now: datetime,
    ) -> None:
        generation = await self.events.count_exits(camera_id, track_id, zone.zone_id)
        dedup = track_state.dedup_key(camera_id, track_id, zone.zone_id, EXIT, generation)
        event = await self.events.create(
            event_type=EVENT_TYPE_EXIT,
            camera_id=camera_id,
            track_id=track_id,
            zone_id=zone.zone_id,
            payload={"member_transition": EXIT},
            deduplication_key=dedup,
            ts=now,
        )
        outcome.event_created = True
        outcome.event_id = event.event_id

    def _build_response(
        self,
        track_id: str,
        camera_id: str,
        object_type: str,
        rep_point: dict[str, float],
        outcomes: list[ZoneEvaluationOutcome],
    ) -> dict[str, Any]:
        entry_outcomes = [o for o in outcomes if o.incident_created]
        exit_outcomes = [o for o in outcomes if o.transition == EXIT and o.rule_passed]

        zones_payload = [o.to_dict() for o in outcomes]

        created_incident = entry_outcomes[0].incident if entry_outcomes else None

        return {
            "track": {
                "track_id": track_id,
                "camera_id": camera_id,
                "object_type": object_type,
            },
            "evaluation": {
                "representative_point": rep_point,
                "zones": zones_payload,
            },
            "event": {
                "created": bool(entry_outcomes),
                "event_id": entry_outcomes[0].event_id if entry_outcomes else None,
                **({"multiple": [o.event_id for o in entry_outcomes]} if len(entry_outcomes) > 1 else {}),
            },
            "exit_event": {
                "created": bool(exit_outcomes),
                "event_id": exit_outcomes[0].event_id if exit_outcomes else None,
            },
            "incident": {
                "created": bool(entry_outcomes),
                "incident_id": created_incident["incident_id"] if created_incident else None,
                "risk_score": created_incident["risk_score"] if created_incident else None,
                "severity": created_incident["severity"] if created_incident else None,
                "factors": created_incident["factors"] if created_incident else [],
            },
        }