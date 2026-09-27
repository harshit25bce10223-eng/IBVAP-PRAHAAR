# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 7 — ANPR + Vehicle Intelligence ORM Models
#
# Tables:
#   vehicle_sightings     — canonical vehicle sighting entity
#   plate_reads           — plate observation records (raw + normalized)
#   plate_candidates      — per-read OCR candidates
#   anpr_configs          — per-camera ANPR configuration
#
# Design principles:
#   · Raw plate reads NEVER overwritten; normalized kept separate
#   · Multiple candidates preserved per read
#   · Vehicle sighting links to existing Track (Component 6) and Detection (Component 5)
#   · Quality states preserved; never collapsed into "identity confidence"
#   · Edge-sync fields included where platform architecture supports them
#   · All IDs use prefixed UUID hex format consistent with PRHAAR
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

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

def _sv_id() -> str:
    return f"SGT-{uuid.uuid4().hex[:8].upper()}"


def _pr_id() -> str:
    return f"PRD-{uuid.uuid4().hex[:8].upper()}"


def _pc_id() -> str:
    return f"PCAND-{uuid.uuid4().hex[:8].upper()}"


def _anc_id() -> str:
    return f"ANCFG-{uuid.uuid4().hex[:8].upper()}"


# ─────────────────────────────────────────────────────────────────────────────
# String constant sets (mirrored in frontend types/anpr.ts)
# ─────────────────────────────────────────────────────────────────────────────

PLATE_QUALITIES = [
    "GOOD", "FAIR", "POOR", "UNREADABLE", "PARTIAL",
    "GLARE", "MOTION_BLUR", "OCCLUDED", "EXTREME_ANGLE", "DIRTY", "LOW_LIGHT", "UNKNOWN",
]

VEHICLE_CLASSES = [
    "PERSONAL_CAR", "SUV", "TRUCK", "BUS", "VAN",
    "MOTORCYCLE", "SCOOTER", "TRACTOR", "THREE_WHEELER", "UTILITY", "OTHER", "UNKNOWN",
]

VEHICLE_COLORS = [
    "WHITE", "BLACK", "GREY", "SILVER", "RED", "BLUE",
    "GREEN", "YELLOW", "BROWN", "OTHER", "UNKNOWN",
]

VEHICLE_DIRECTIONS = [
    "NORTH", "SOUTH", "EAST", "WEST", "INBOUND", "OUTBOUND", "UNKNOWN",
]

PLATE_FORMAT_STATUSES = [
    "VALID_FORMAT", "POSSIBLE_FORMAT", "INVALID_FORMAT", "UNKNOWN_FORMAT", "NOT_ENOUGH_DATA",
]

WATCHLIST_STATUSES = [
    "WATCHLIST_MATCH", "NO_MATCH", "UNKNOWN", "NOT_CHECKED",
]

ANPR_SYNC_STATES = [
    "LOCAL_ONLY", "SYNC_PENDING", "SYNCED", "SYNC_FAILED", "UNKNOWN",
]

ANPR_SOURCES = ["LIVE", "EDGE", "CENTRAL", "DEMO", "UNKNOWN"]


# ─────────────────────────────────────────────────────────────────────────────
# VehicleSighting — one vehicle observation with plate read + candidates
# ─────────────────────────────────────────────────────────────────────────────

class VehicleSighting(Base):
    """
    Canonical vehicle sighting entity.

    A sighting represents "vehicle observed at time T on camera C"
    with optional plate read. It does NOT imply legal identity.
    """
    __tablename__ = "vehicle_sightings"

    __table_args__ = (
        Index("ix_vs_camera_time", "camera_id", "observed_at"),
        Index("ix_vs_track", "track_id"),
        Index("ix_vs_detection", "detection_id"),
        Index("ix_vs_vehicle", "vehicle_id"),
        Index("ix_vs_plate", "plate_read_id"),
        Index("ix_vs_quality", "plate_quality"),
        Index("ix_vs_class", "vehicle_class"),
        Index("ix_vs_direction", "vehicle_direction"),
        Index("ix_vs_incident", "incident_id"),
        Index("ix_vs_event", "event_id"),
        Index("ix_vs_correlation", "correlation_id"),
        Index("ix_vs_evidence", "evidence_id"),
        Index("ix_vs_provider", "provider"),
        Index("ix_vs_sync", "sync_state"),
    )

    # ── Primary key ─────────────────────────────────────────────────────────────
    sighting_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=_sv_id
    )

    # ── Camera ──────────────────────────────────────────────────────────────────
    camera_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    # ── Component 5 / 6 linkage (soft references, no hard FKs) ──────────────────
    # Soft reference to Detection (Component 5)
    detection_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Soft reference to Track (Component 6) — same vehicle over time
    track_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Vehicle-scoped identity within PRHAAR (not legal registration)
    vehicle_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # ── Timestamps ──────────────────────────────────────────────────────────────
    # Original sensor timestamp
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), index=True, nullable=False
    )
    # Server ingestion timestamp
    received_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # ── Vehicle attributes ──────────────────────────────────────────────────────
    vehicle_class: Mapped[str] = mapped_column(
        String(32), default="UNKNOWN", nullable=False
    )
    vehicle_color: Mapped[str | None] = mapped_column(String(32), nullable=True)
    vehicle_direction: Mapped[str] = mapped_column(
        String(16), default="UNKNOWN", nullable=False
    )

    # ── Plate observation (soft reference) ──────────────────────────────────────
    plate_read_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # ── Plate quality (separate from detection confidence) ──────────────────────
    plate_quality: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # ── Detection/observation quality context ───────────────────────────────────
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    detection_quality: Mapped[str | None] = mapped_column(String(32), nullable=True)

    # ── Camera Health context snapshot ──────────────────────────────────────────
    # JSON blob: {state, reliability, viewpoint_shift, captured_at}
    camera_health_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    camera_health_context_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ── Location / operational context ──────────────────────────────────────────
    location_context: Mapped[str | None] = mapped_column(String(256), nullable=True)
    sector_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    zone_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # ── Downstream component references (soft) ──────────────────────────────────
    watchlist_status: Mapped[str] = mapped_column(
        String(32), default="NOT_CHECKED", nullable=False
    )
    evidence_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    event_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    correlation_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    incident_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # ── Media references ────────────────────────────────────────────────────────
    thumbnail_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    plate_crop_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # ── Provider provenance ─────────────────────────────────────────────────────
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source: Mapped[str] = mapped_column(String(16), default="LIVE", nullable=False)

    # ── Optimistic locking / edge sync ──────────────────────────────────────────
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    schema_version: Mapped[str] = mapped_column(String(16), default="1.0", nullable=False)
    sync_state: Mapped[str] = mapped_column(String(16), default="LOCAL_ONLY", nullable=False)
    sync_payload_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    edge_device_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # ── Timestamps ──────────────────────────────────────────────────────────────
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # ── Relationships ───────────────────────────────────────────────────────────
    plate_read: Mapped["PlateRead | None"] = relationship(
        "PlateRead", back_populates="sighting", uselist=False
    )
    candidates: Mapped[list["PlateCandidate"]] = relationship(
        "PlateCandidate", back_populates="sighting",
        cascade="all, delete-orphan", order_by="PlateCandidate.rank"
    )


# ─────────────────────────────────────────────────────────────────────────────
# PlateRead — one plate observation (raw + normalized) linked to a sighting
# ─────────────────────────────────────────────────────────────────────────────

class PlateRead(Base):
    """
    Single plate observation from one frame.

    CRITICAL: raw_read is NEVER overwritten. normalized_read is computed separately.
    Multiple candidates preserved in PlateCandidate.
    """
    __tablename__ = "plate_reads"

    __table_args__ = (
        UniqueConstraint("sighting_id", name="uq_pr_sighting"),
        Index("ix_pr_normalized", "normalized_read"),
        Index("ix_pr_raw", "raw_read"),
    )

    plate_read_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=_pr_id
    )
    sighting_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("vehicle_sightings.sighting_id"), nullable=False
    )

    # Original OCR output — never modified
    raw_read: Mapped[str] = mapped_column(String(64), nullable=False)

    # Normalized (format-corrected) version — may be null if unreadable
    normalized_read: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Display version: normalized if available, else raw
    display_read: Mapped[str] = mapped_column(String(64), nullable=False)

    # OCR confidence for the top candidate
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # Per-character confidence array (if provider supplies it)
    character_confidence: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Format validation status
    format_status: Mapped[str] = mapped_column(String(32), default="UNKNOWN_FORMAT", nullable=False)

    # Quality of this plate read (separate from detection quality)
    quality: Mapped[str] = mapped_column(String(32), default="UNKNOWN", nullable=False)

    # Evidence/media references
    crop_reference: Mapped[str | None] = mapped_column(String(128), nullable=True)
    source_frame_ref: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Timestamps
    observed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Provider provenance
    provider: Mapped[str | None] = mapped_column(String(64), nullable=True)
    provider_version: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Relationship
    sighting: Mapped["VehicleSighting"] = relationship(
        "VehicleSighting", back_populates="plate_read"
    )
    candidates: Mapped[list["PlateCandidate"]] = relationship(
        "PlateCandidate", back_populates="plate_read",
        cascade="all, delete-orphan", order_by="PlateCandidate.rank"
    )


# ─────────────────────────────────────────────────────────────────────────────
# PlateCandidate — one OCR candidate for a plate read
# ─────────────────────────────────────────────────────────────────────────────

class PlateCandidate(Base):
    """
    One candidate interpretation of a plate read.

    Multiple candidates may exist per PlateRead (e.g., OCR ambiguity).
    Rank 1 is the top candidate used for display/normalized_read.
    """
    __tablename__ = "plate_candidates"

    __table_args__ = (
        Index("ix_pc_plate_read", "plate_read_id"),
        Index("ix_pc_sighting", "sighting_id"),
        Index("ix_pc_rank", "sighting_id", "rank"),
    )

    candidate_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=_pc_id
    )

    # Soft references for query convenience
    sighting_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("vehicle_sightings.sighting_id"), nullable=False
    )
    plate_read_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("plate_reads.plate_read_id"), nullable=False
    )

    # Rank: 1 = top candidate (used for normalized_read/display)
    rank: Mapped[int] = mapped_column(Integer, nullable=False)

    # Candidate text (raw OCR output)
    raw_read: Mapped[str] = mapped_column(String(64), nullable=False)

    # Normalized version of this candidate
    normalized_read: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Confidence for this specific candidate
    confidence: Mapped[float] = mapped_column(Float, nullable=False)

    # Per-character confidence (JSON array string)
    character_confidence: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Format validation for this candidate
    format_status: Mapped[str] = mapped_column(
        String(32), default="UNKNOWN_FORMAT", nullable=False
    )

    # Relationships
    sighting: Mapped["VehicleSighting"] = relationship(
        "VehicleSighting", back_populates="candidates"
    )
    plate_read: Mapped["PlateRead"] = relationship(
        "PlateRead", back_populates="candidates"
    )


# ─────────────────────────────────────────────────────────────────────────────
# ANPRConfig — per-camera ANPR configuration
# ─────────────────────────────────────────────────────────────────────────────

class ANPRConfig(Base):
    """
    Per-camera ANPR configuration.

    Allows different cameras to use different providers/profiles.
    """
    __tablename__ = "anpr_configs"

    __table_args__ = (
        Index("ix_anc_camera", "camera_id"),
        Index("ix_anc_active", "active"),
    )

    config_id: Mapped[str] = mapped_column(
        String(64), primary_key=True, default=_anc_id
    )
    camera_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)

    # Provider to use (e.g., "ANPR-ENGINE-v2", "DEMO")
    provider: Mapped[str] = mapped_column(String(64), nullable=False)

    # Tracker/model name if applicable
    tracker_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tracker_version: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Association/profile for this camera
    association_profile: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Max age before sighting considered stale
    max_sighting_age_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Association/OCR configuration (JSON)
    association_config_json: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Sample rate / frame skipping
    sample_rate: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    min_frame_interval_ms: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Region/sector profile
    region_profile: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Active flag
    active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Optimistic locking
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    configuration_version: Mapped[str] = mapped_column(String(32), default="1.0", nullable=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )