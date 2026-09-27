# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 6 — Tracking Engine ORM Models
#
# Tables:
#   tracks               — canonical track entity (extends legacy track shape)
#   track_observations   — per-detection observation records
#   track_history        — lifecycle state-change audit log
#   track_candidates     — cross-camera continuation hypotheses
#   tracking_configs     — per-camera tracking configuration
#
# Design principles:
#   · Track lifecycle states are TENTATIVE→ACTIVE→LOST→REACQUIRED→ENDED/STALE/INVALID
#   · Track is NOT identity (no Re-ID, no face data, no biometric vectors)
#   · Tracks are camera-scoped; cross-camera candidates use track_candidates
#   · Revision field supports optimistic locking (concurrent workers, edge sync)
#   · All IDs use prefixed UUID hex format consistent with the rest of PRHAAR
#   · SQLite + asyncio in development; schema is PostgreSQL-compatible
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.sqlite import JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.database import Base

if TYPE_CHECKING:
    pass  # future: typed relationships across components


# ─────────────────────────────────────────────────────────────────────────────
# ID generators — consistent prefix convention with the rest of PRHAAR
# ─────────────────────────────────────────────────────────────────────────────

def _trk_id() -> str:
    return f"TRK-{uuid.uuid4().hex[:10].upper()}"


def _obs_id() -> str:
    return f"OBS-{uuid.uuid4().hex[:10].upper()}"


def _thist_id() -> str:
    return f"THIST-{uuid.uuid4().hex[:8].upper()}"


def _tcand_id() -> str:
    return f"TCAND-{uuid.uuid4().hex[:8].upper()}"


def _trcfg_id() -> str:
    return f"TRCFG-{uuid.uuid4().hex[:8].upper()}"


# ─────────────────────────────────────────────────────────────────────────────
# String constant sets (mirrored in domain/tracking/constants.py as Literals)
# These are kept here as plain strings so migration introspection stays simple.
# ─────────────────────────────────────────────────────────────────────────────

TRACK_STATUSES = [
    "TENTATIVE", "ACTIVE", "LOST", "REACQUIRED",
    "ENDED", "STALE", "INVALID", "UNKNOWN",
]

TRACK_SOURCES = ["LIVE", "EDGE", "CENTRAL", "DEMO", "UNKNOWN"]

TRACK_SYNC_STATES = [
    "LOCAL_ONLY", "SYNC_PENDING", "SYNCED", "SYNC_FAILED", "UNKNOWN",
]

TRACK_CONTINUITY_QUALITY = ["STRONG", "MODERATE", "WEAK", "UNKNOWN"]

CANDIDATE_STATUSES = ["OPEN", "ACCEPTED", "REJECTED", "EXPIRED", "UNKNOWN"]

CANDIDATE_RELATION_TYPES = ["POSSIBLE_CONTINUATION", "POSSIBLE_SAME_ENTITY"]


# ─────────────────────────────────────────────────────────────────────────────
# Track — canonical tracking entity
#
# Extends the legacy minimal track table (which had only zone-membership fields).
# The migration (20260912_*_add_tracking_tables.py) uses ALTER TABLE (batch mode)
# to add the new columns while preserving the existing rows and Component 1 data.
# ─────────────────────────────────────────────────────────────────────────────

class TrackV2(Base):
    """
    Full Component 6 tracking entity.

    Naming: TrackV2 avoids collision with the existing `Track` model imported
    by Component 1's IncidentService/TrackRepository.  Both map to the SAME
    `tracks` table — Component 6 migration adds the new columns.
    """
    # In both prod and test, use extend_existing=True to allow both Track and
    # TrackV2 to map to the same "tracks" table. In prod, migration adds columns.
    # In tests, fresh DB each time so extend_existing merges the definitions.
    __tablename__ = "tracks"
    
    __table_args__ = (
        Index("ix_tracks_camera_status",     "camera_id",   "status"),
        Index("ix_tracks_camera_class",      "camera_id",   "object_class"),
        Index("ix_tracks_camera_time",       "camera_id",   "last_seen_at"),
        Index("ix_tracks_status",            "status"),
        Index("ix_tracks_first_seen",        "first_seen_at"),
        Index("ix_tracks_last_seen",         "last_seen_at"),
        Index("ix_tracks_current_detection", "current_detection_id"),
        Index("ix_tracks_event",             "event_id"),
        Index("ix_tracks_incident",          "incident_id"),
        Index("ix_tracks_correlation",       "correlation_id"),
        Index("ix_tracks_evidence",          "evidence_id"),
        Index("ix_tracks_sector",            "sector_id"),
        Index("ix_tracks_region",            "region_profile"),
        Index("ix_tracks_source",            "source"),
        Index("ix_tracks_provider",          "provider"),
        Index("ix_tracks_sync_state",        "sync_state"),
        {"extend_existing": True},
    )

    # ── Primary key ───────────────────────────────────────────────────────────
    track_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=_trk_id
    )

    # ── Camera ────────────────────────────────────────────────────────────────
    # index=True removed - Track already defines index on camera_id;
    # TrackV2 uses composite indexes in __table_args__ instead.
    camera_id: Mapped[str] = mapped_column(String(64), nullable=False)

    # ── Legacy Component 1 columns (kept, nullable so old rows remain valid) ──
    object_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    current_bbox_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    previous_bbox_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    current_membership_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    previous_membership_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    path_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    first_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Component 6 lifecycle ─────────────────────────────────────────────────
    # index=True removed - explicit Index in __table_args__ used instead
    status: Mapped[str] = mapped_column(
        String(16), default="UNKNOWN", nullable=False
    )
    object_class: Mapped[str] = mapped_column(
        String(32), default="UNKNOWN", nullable=False
    )

    # ── Lifecycle timestamps ──────────────────────────────────────────────────
    # index=True removed - explicit Index in __table_args__ used instead
    first_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Current detection reference ───────────────────────────────────────────
    # Not a FK — detection_id lives in component 5 table; soft reference only.
    current_detection_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # ── Current bbox (flat columns — normalized [0,1]) ────────────────────────
    current_bbox_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_bbox_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_bbox_width: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_bbox_height: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Observation counter ───────────────────────────────────────────────────
    observation_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # ── Quality / confidence (nullable — not fabricated) ─────────────────────
    continuity_quality: Mapped[str | None] = mapped_column(String(16), nullable=True)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    # ── Source & provider provenance ──────────────────────────────────────────
    source: Mapped[str] = mapped_column(String(16), default="UNKNOWN", nullable=False)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    tracker_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tracker_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    algorithm_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    configuration_version: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # ── Downstream component references (soft, nullable) ─────────────────────
    event_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    incident_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    evidence_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    entity_candidate_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # ── Geographical / operational context ───────────────────────────────────
    sector_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    region_profile: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # ── Camera Health context snapshot ────────────────────────────────────────
    # JSON blob: {state, reliability, viewpoint_shift, captured_at}
    health_context_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Class change history (for reclassification tracking) ─────────────────
    previous_class: Mapped[str | None] = mapped_column(String(32), nullable=True)
    class_revision_reason: Mapped[str | None] = mapped_column(String(256), nullable=True)
    class_revised_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Gap / reacquisition tracking ──────────────────────────────────────────
    gap_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    reacquisition_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_gap_started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_reacquired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Data completeness ─────────────────────────────────────────────────────
    data_completeness: Mapped[str] = mapped_column(String(16), default="UNKNOWN", nullable=False)
    missing_observations_note: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # ── Optimistic locking / edge sync ───────────────────────────────────────
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(16), default="2.0", nullable=False)
    sync_state: Mapped[str] = mapped_column(String(16), default="LOCAL_ONLY", nullable=False)
    sync_payload_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    edge_device_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # ── Timestamps ────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ─────────────────────────────────────────────────────────
    observations: Mapped[list["TrackObservation"]] = relationship(
        "TrackObservation", back_populates="track",
        cascade="all, delete-orphan",
        order_by="TrackObservation.observed_at",
    )
    history: Mapped[list["TrackHistory"]] = relationship(
        "TrackHistory", back_populates="track",
        cascade="all, delete-orphan",
        order_by="TrackHistory.timestamp",
    )
    candidates_as_source: Mapped[list["TrackCandidate"]] = relationship(
        "TrackCandidate",
        foreign_keys="TrackCandidate.source_track_id",
        back_populates="source_track",
        cascade="all, delete-orphan",
    )


# ─────────────────────────────────────────────────────────────────────────────
# TrackObservation — one detection linked to one track
#
# Uniqueness: (track_id, detection_id) — prevents duplicate observations.
# A detection should not normally belong to multiple tracks.
# ─────────────────────────────────────────────────────────────────────────────

class TrackObservation(Base):
    __tablename__ = "track_observations"
    __table_args__ = (
        UniqueConstraint("track_id", "detection_id", name="uq_obs_track_detection"),
        Index("ix_tobs_track_time",    "track_id",    "observed_at"),
        Index("ix_tobs_detection",     "detection_id"),
        Index("ix_tobs_camera",        "camera_id"),
        Index("ix_tobs_observed",      "observed_at"),
        Index("ix_tobs_sequence",      "track_id",    "sequence"),
    )

    observation_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=_obs_id
    )
    track_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tracks.track_id"), index=True, nullable=False
    )
    # Soft reference to detections table (no FK to avoid cross-component hard coupling)
    detection_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    camera_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    # Timestamps — observed_at is the original sensor time, received_at is ingestion time
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    received_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Sequence number within the track (provider-assigned, may have gaps)
    sequence: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Bounding box (normalized [0,1]) — copied from detection at observation time
    bbox_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_width: Mapped[float | None] = mapped_column(Float, nullable=True)
    bbox_height: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Quality / confidence at observation time (nullable — not fabricated)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality: Mapped[str | None] = mapped_column(String(16), nullable=True)
    occlusion: Mapped[str | None] = mapped_column(String(16), nullable=True)

    # Motion — only set when provider explicitly supplies it; never fabricated
    velocity: Mapped[float | None] = mapped_column(Float, nullable=True)
    speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    direction: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Class at observation time (provider may reclassify over time)
    object_class: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # Source and provider provenance
    source: Mapped[str] = mapped_column(String(16), default="UNKNOWN", nullable=False)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Frame context
    frame_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    frame_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Evidence reference (soft)
    evidence_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # ── Relationship ──────────────────────────────────────────────────────────
    track: Mapped["TrackV2"] = relationship("TrackV2", back_populates="observations")


# ─────────────────────────────────────────────────────────────────────────────
# TrackHistory — lifecycle state-change audit log
#
# Every status transition that changes track.status is recorded here.
# This enables full audit-trail queries: "why did this track end?"
# ─────────────────────────────────────────────────────────────────────────────

class TrackHistory(Base):
    __tablename__ = "track_history"
    __table_args__ = (
        Index("ix_thist_track_time",  "track_id", "timestamp"),
        Index("ix_thist_track",       "track_id"),
        Index("ix_thist_timestamp",   "timestamp"),
    )

    history_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=_thist_id
    )
    track_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tracks.track_id"), index=True, nullable=False
    )

    revision: Mapped[int] = mapped_column(Integer, nullable=False)

    old_status: Mapped[str | None] = mapped_column(String(16), nullable=True)
    new_status: Mapped[str] = mapped_column(String(16), nullable=False)

    reason: Mapped[str | None] = mapped_column(String(256), nullable=True)

    # Detection that triggered this transition (nullable — some transitions are backend-driven)
    trigger_detection_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Provider context at transition time
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    configuration_version: Mapped[str | None] = mapped_column(String(64), nullable=True)

    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
        index=True, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    # ── Relationship ──────────────────────────────────────────────────────────
    track: Mapped["TrackV2"] = relationship("TrackV2", back_populates="history")


# ─────────────────────────────────────────────────────────────────────────────
# TrackCandidate — cross-camera continuation hypothesis
#
# Represents a possible (NOT confirmed) same-entity relationship between
# a track on one camera and a track (or potential track) on another camera.
# This is NEVER an identity claim. The strongest allowable label is
# POSSIBLE_SAME_ENTITY or POSSIBLE_CONTINUATION.
# ─────────────────────────────────────────────────────────────────────────────

class TrackCandidate(Base):
    __tablename__ = "track_candidates"
    __table_args__ = (
        Index("ix_tcand_source",         "source_track_id"),
        Index("ix_tcand_target_camera",  "target_camera_id"),
        Index("ix_tcand_candidate",      "candidate_track_id"),
        Index("ix_tcand_status",         "status"),
        Index("ix_tcand_expires",        "expires_at"),
    )

    candidate_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=_tcand_id
    )
    source_track_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tracks.track_id"), index=True, nullable=False
    )
    target_camera_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    # May be NULL if the continuation track has not yet been created
    candidate_track_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # POSSIBLE_CONTINUATION | POSSIBLE_SAME_ENTITY — never CONFIRMED_PERSON
    relation_type: Mapped[str] = mapped_column(
        String(32), default="POSSIBLE_CONTINUATION", nullable=False
    )

    # Provider-supplied strength [0,1] — nullable, never fabricated
    strength: Mapped[float | None] = mapped_column(Float, nullable=True)
    reason: Mapped[str | None] = mapped_column(String(512), nullable=True)

    status: Mapped[str] = mapped_column(String(16), default="OPEN", nullable=False)

    source: Mapped[str] = mapped_column(String(16), default="UNKNOWN", nullable=False)
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Gap between the two tracks
    gap_duration_sec: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # ── Relationship ──────────────────────────────────────────────────────────
    source_track: Mapped["TrackV2"] = relationship(
        "TrackV2", foreign_keys=[source_track_id],
        back_populates="candidates_as_source"
    )


# ─────────────────────────────────────────────────────────────────────────────
# TrackingConfig — per-camera tracking configuration
#
# Keeps thresholds out of code. All thresholds must be validated against
# SSB target data before being set in production. None are hard-coded
# from research papers.
# ─────────────────────────────────────────────────────────────────────────────

class TrackingConfig(Base):
    __tablename__ = "tracking_configs"
    __table_args__ = (
        Index("ix_trcfg_camera",  "camera_id"),
        Index("ix_trcfg_active",  "active"),
    )

    config_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=_trcfg_id
    )
    camera_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    # Provider and tracker identification
    provider: Mapped[str] = mapped_column(String(64), nullable=False)
    tracker_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tracker_version: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Association configuration — extensible JSON for future tracker parameters
    # Do NOT hard-code IoU thresholds, max_age, etc. from research papers.
    association_profile: Mapped[str | None] = mapped_column(String(64), nullable=True)
    max_track_age_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)
    association_config_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Sampling
    sample_rate: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    min_frame_interval_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Region context
    region_profile: Mapped[str | None] = mapped_column(String(64), nullable=True)

    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    configuration_version: Mapped[str] = mapped_column(String(32), default="1.0", nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
