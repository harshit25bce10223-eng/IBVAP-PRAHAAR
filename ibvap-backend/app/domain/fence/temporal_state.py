# ─────────────────────────────────────────────────────────────────────────────
# IBVAP — Temporal Membership State Machine
# ─────────────────────────────────────────────────────────────────────────────
# Replaces single-frame binary membership with a configurable state machine:
#
#   OUTSIDE
#   APPROACHING          (trajectory directed toward zone)
#   BOUNDARY_UNCERTAIN   (in spatial uncertainty band)
#   CROSSING_CANDIDATE   (consecutive inside observations accumulating)
#   INTRUSION_CONFIRMED  (threshold crossed — generates incident)
#   DWELLING             (confirmed and still inside)
#   EXITING              (consecutive outside observations accumulating)
#   OUTSIDE              (confirmed exit)
#
# SSB rationale:
#   One noisy frame inside a polygon ≠ confirmed border intrusion.
#   Multiple consistent observations reduce false-positive rate significantly.
#
# IMPORTANT:
#   - PRE_INTRUSION_WARNING fires as a non-incident alert when trajectory
#     indicates imminent crossing (before INTRUSION_CONFIRMED).
#   - Only INTRUSION_CONFIRMED creates an incident record.
#   - Configurable confirmation frame counts prevent jitter-based duplicates.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class MembershipState(str, Enum):
    OUTSIDE             = "OUTSIDE"
    APPROACHING         = "APPROACHING"
    BOUNDARY_UNCERTAIN  = "BOUNDARY_UNCERTAIN"
    CROSSING_CANDIDATE  = "CROSSING_CANDIDATE"
    PRE_INTRUSION_WARNING = "PRE_INTRUSION_WARNING"
    INTRUSION_CONFIRMED = "INTRUSION_CONFIRMED"
    DWELLING            = "DWELLING"
    EXITING             = "EXITING"


class TrajectoryDirection(str, Enum):
    APPROACHING_ZONE  = "APPROACHING_ZONE"
    MOVING_AWAY       = "MOVING_AWAY"
    STATIONARY        = "STATIONARY"
    INSIDE_ZONE       = "INSIDE_ZONE"
    EXITING_ZONE      = "EXITING_ZONE"
    UNKNOWN           = "UNKNOWN"


@dataclass
class TemporalMembership:
    """
    Per-track, per-zone temporal membership tracking.

    Stored in the database's track_memberships table (serialized as JSON).
    Recovered on restart so duplicate incidents cannot fire after restart.
    """
    track_id: str
    zone_id: str
    state: MembershipState = MembershipState.OUTSIDE
    # Frames seen consecutively in current candidate state
    candidate_frames: int = 0
    # Frames seen consecutively in exit candidate state
    exit_candidate_frames: int = 0
    # Whether an incident has been created for the CURRENT inside episode
    incident_created_this_episode: bool = False
    # Timestamp of entry confirmation (ISO string)
    confirmed_entry_ts: str | None = None
    # Last known trajectory direction
    trajectory_direction: TrajectoryDirection = TrajectoryDirection.UNKNOWN
    # Whether a pre-intrusion warning has been issued for current approach
    pre_warning_issued: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "track_id": self.track_id,
            "zone_id": self.zone_id,
            "state": self.state.value,
            "candidate_frames": self.candidate_frames,
            "exit_candidate_frames": self.exit_candidate_frames,
            "incident_created_this_episode": self.incident_created_this_episode,
            "confirmed_entry_ts": self.confirmed_entry_ts,
            "trajectory_direction": self.trajectory_direction.value,
            "pre_warning_issued": self.pre_warning_issued,
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "TemporalMembership":
        return cls(
            track_id=d["track_id"],
            zone_id=d["zone_id"],
            state=MembershipState(d.get("state", "OUTSIDE")),
            candidate_frames=d.get("candidate_frames", 0),
            exit_candidate_frames=d.get("exit_candidate_frames", 0),
            incident_created_this_episode=d.get("incident_created_this_episode", False),
            confirmed_entry_ts=d.get("confirmed_entry_ts"),
            trajectory_direction=TrajectoryDirection(
                d.get("trajectory_direction", "UNKNOWN")
            ),
            pre_warning_issued=d.get("pre_warning_issued", False),
        )


def estimate_trajectory(
    path: list[dict[str, Any]],
    zone_polygon: list[dict[str, float]],
    current_point: dict[str, float],
    min_positions: int = 2,
    stationary_threshold: float = 0.005,
) -> TrajectoryDirection:
    """
    Lightweight deterministic trajectory direction estimation.

    NOT an ML model. Uses recent position deltas only.
    Never infers intent — only geometric direction.

    Args:
        path: list of {"x": float, "y": float, "ts": str} recent positions
        zone_polygon: fence polygon for proximity context
        current_point: current representative point
        min_positions: minimum positions to estimate direction
        stationary_threshold: minimum movement to count as non-stationary

    Returns:
        TrajectoryDirection enum — conservative UNKNOWN if history is insufficient.
    """
    if len(path) < min_positions:
        return TrajectoryDirection.UNKNOWN

    # Use last two positions for velocity
    prev = path[-2] if len(path) >= 2 else path[0]
    dx = current_point["x"] - float(prev.get("x", current_point["x"]))
    dy = current_point["y"] - float(prev.get("y", current_point["y"]))
    dist = (dx*dx + dy*dy) ** 0.5

    if dist < stationary_threshold:
        return TrajectoryDirection.STATIONARY

    # Project forward 3× the step distance and check if it lands inside the zone
    from app.domain.geometry.point_in_polygon import check_point_in_polygon
    projected = {
        "x": max(0.0, min(1.0, current_point["x"] + dx * 3)),
        "y": max(0.0, min(1.0, current_point["y"] + dy * 3)),
    }
    projected_inside = check_point_in_polygon(projected, zone_polygon)
    current_inside = check_point_in_polygon(current_point, zone_polygon)

    if current_inside:
        if not projected_inside:
            return TrajectoryDirection.EXITING_ZONE
        return TrajectoryDirection.INSIDE_ZONE

    if projected_inside:
        return TrajectoryDirection.APPROACHING_ZONE

    return TrajectoryDirection.MOVING_AWAY


@dataclass
class TemporalTransitionResult:
    """Result of one temporal state-machine step."""
    previous_state: MembershipState
    new_state: MembershipState
    is_new_confirmed_entry: bool   # True → create incident
    is_confirmed_exit: bool        # True → membership episode closed
    pre_intrusion_warning: bool    # True → issue non-incident warning alert
    trajectory_direction: TrajectoryDirection
    evidence: str                  # Human-readable explanation for the transition


def advance_temporal_state(
    membership: TemporalMembership,
    is_inside: bool,
    spatial_uncertain: bool,
    trajectory: TrajectoryDirection,
    entry_confirmation_frames: int = 1,
    exit_confirmation_frames: int = 1,
    current_ts: str | None = None,
) -> TemporalTransitionResult:
    """
    Advance the temporal state machine by one observation.

    Args:
        membership: mutable membership record (will be updated in place)
        is_inside: primary geometry result (binary inside/outside)
        spatial_uncertain: True if in the boundary uncertainty band
        trajectory: current trajectory direction from estimate_trajectory()
        entry_confirmation_frames: consecutive inside frames before confirming entry
        exit_confirmation_frames: consecutive outside frames before confirming exit
        current_ts: ISO timestamp of current observation

    Returns:
        TemporalTransitionResult describing what happened.
    """
    prev_state = membership.state
    pre_warning = False
    new_entry = False
    confirmed_exit = False
    evidence = ""

    membership.trajectory_direction = trajectory

    # ── INSIDE or BOUNDARY_UNCERTAIN ──────────────────────────────────────
    if is_inside or spatial_uncertain:
        membership.exit_candidate_frames = 0

        if spatial_uncertain and not is_inside:
            # In uncertainty band — not yet counted as inside
            if membership.state not in (
                MembershipState.INTRUSION_CONFIRMED,
                MembershipState.DWELLING,
            ):
                membership.state = MembershipState.BOUNDARY_UNCERTAIN
                membership.candidate_frames = 0
            evidence = "Representative point is within the boundary uncertainty margin."
        else:
            # Geometrically inside
            if membership.state in (
                MembershipState.INTRUSION_CONFIRMED,
                MembershipState.DWELLING,
            ):
                membership.state = MembershipState.DWELLING
                evidence = "Object continues inside zone."
            else:
                membership.candidate_frames += 1
                membership.state = MembershipState.CROSSING_CANDIDATE
                evidence = f"Inside observation {membership.candidate_frames}/{entry_confirmation_frames}."

                # Pre-intrusion warning if trajectory is approaching and we're accumulating
                if (
                    trajectory in (TrajectoryDirection.APPROACHING_ZONE, TrajectoryDirection.INSIDE_ZONE)
                    and not membership.pre_warning_issued
                ):
                    pre_warning = True
                    membership.pre_warning_issued = True

                # Confirm entry if we have enough consecutive inside frames
                if (
                    membership.candidate_frames >= entry_confirmation_frames
                    and not membership.incident_created_this_episode
                ):
                    membership.state = MembershipState.INTRUSION_CONFIRMED
                    membership.incident_created_this_episode = True
                    membership.confirmed_entry_ts = current_ts
                    new_entry = True
                    evidence = (
                        f"Intrusion confirmed after {membership.candidate_frames} "
                        f"consecutive inside observations."
                    )

    # ── OUTSIDE ──────────────────────────────────────────────────────────
    else:
        membership.candidate_frames = 0
        membership.pre_warning_issued = False

        if membership.state in (
            MembershipState.INTRUSION_CONFIRMED,
            MembershipState.DWELLING,
        ):
            membership.exit_candidate_frames += 1
            membership.state = MembershipState.EXITING
            evidence = (
                f"Exit candidate {membership.exit_candidate_frames}/{exit_confirmation_frames}."
            )
            if membership.exit_candidate_frames >= exit_confirmation_frames:
                membership.state = MembershipState.OUTSIDE
                membership.incident_created_this_episode = False  # allow re-entry to create new incident
                membership.confirmed_entry_ts = None
                confirmed_exit = True
                evidence = "Exit confirmed — episode closed."
        elif membership.state in (
            MembershipState.APPROACHING,
            MembershipState.BOUNDARY_UNCERTAIN,
            MembershipState.CROSSING_CANDIDATE,
            MembershipState.PRE_INTRUSION_WARNING,
        ):
            # Was approaching but didn't cross — reset
            membership.state = MembershipState.OUTSIDE
            membership.candidate_frames = 0
            evidence = "Object moved away without crossing."
        else:
            membership.state = MembershipState.OUTSIDE
            evidence = "Object is outside zone."

        # Update trajectory-based approaching state when outside
        if trajectory == TrajectoryDirection.APPROACHING_ZONE and membership.state == MembershipState.OUTSIDE:
            membership.state = MembershipState.APPROACHING

    return TemporalTransitionResult(
        previous_state=prev_state,
        new_state=membership.state,
        is_new_confirmed_entry=new_entry,
        is_confirmed_exit=confirmed_exit,
        pre_intrusion_warning=pre_warning,
        trajectory_direction=trajectory,
        evidence=evidence,
    )
