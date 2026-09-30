# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 6 — Tracking Engine Constants
#
# All canonical string literals used across the tracking domain.
# These mirror the locked TypeScript types in tracking.ts.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from typing import Literal

# ── Track lifecycle states ────────────────────────────────────────────────────
#
# TENTATIVE:   Hypothesis forming — continuity not yet established.
# ACTIVE:      Receiving valid observations from the provider.
# LOST:        Temporarily unobserved (occlusion, gap). NOT ended.
# REACQUIRED:  Observation received after a LOST period.
# ENDED:       Lifecycle complete (natural exit from scene/sector).
# STALE:       Data age exceeds freshness window — position cannot be trusted.
# INVALID:     Provider or backend invalidated this track.
# UNKNOWN:     Insufficient data to classify.
#
# LOST ≠ ENDED: A LOST track may be reacquired. An ENDED track must not
# spontaneously continue without explicit backend semantics.

TrackStatus = Literal[
    "TENTATIVE", "ACTIVE", "LOST", "REACQUIRED",
    "ENDED", "STALE", "INVALID", "UNKNOWN",
]

TRACK_STATUS_ACTIVE = "ACTIVE"
TRACK_STATUS_TENTATIVE = "TENTATIVE"
TRACK_STATUS_LOST = "LOST"
TRACK_STATUS_REACQUIRED = "REACQUIRED"
TRACK_STATUS_ENDED = "ENDED"
TRACK_STATUS_STALE = "STALE"
TRACK_STATUS_INVALID = "INVALID"
TRACK_STATUS_UNKNOWN = "UNKNOWN"

TRACK_STATUSES_ACTIVE_SET = frozenset({"TENTATIVE", "ACTIVE", "REACQUIRED"})
TRACK_STATUSES_TERMINAL_SET = frozenset({"ENDED", "INVALID"})
TRACK_STATUSES_INACTIVE_SET = frozenset({"LOST", "STALE", "ENDED", "INVALID", "UNKNOWN"})

# ── Source / data origin ──────────────────────────────────────────────────────
TrackSource = Literal["LIVE", "EDGE", "CENTRAL", "DEMO", "UNKNOWN"]

TRACK_SOURCE_LIVE = "LIVE"
TRACK_SOURCE_EDGE = "EDGE"
TRACK_SOURCE_CENTRAL = "CENTRAL"
TRACK_SOURCE_DEMO = "DEMO"
TRACK_SOURCE_UNKNOWN = "UNKNOWN"

TRACK_SOURCES_SET = frozenset({"LIVE", "EDGE", "CENTRAL", "DEMO", "UNKNOWN"})

# ── Continuity quality ────────────────────────────────────────────────────────
# Provider-reported; never computed from a fake formula.
TrackContinuityQuality = Literal["STRONG", "MODERATE", "WEAK", "UNKNOWN"]

CONTINUITY_STRONG = "STRONG"
CONTINUITY_MODERATE = "MODERATE"
CONTINUITY_WEAK = "WEAK"
CONTINUITY_UNKNOWN = "UNKNOWN"

# ── Tracking feed availability ────────────────────────────────────────────────
TrackingFeedState = Literal[
    "READY", "PROCESSING", "DEGRADED", "UNAVAILABLE", "STALE", "OFFLINE", "UNKNOWN",
]

# ── Edge sync states ──────────────────────────────────────────────────────────
TrackSyncState = Literal[
    "LOCAL_ONLY", "SYNC_PENDING", "SYNCED", "SYNC_FAILED", "UNKNOWN",
]

SYNC_LOCAL_ONLY = "LOCAL_ONLY"
SYNC_PENDING = "SYNC_PENDING"
SYNC_SYNCED = "SYNCED"
SYNC_FAILED = "SYNC_FAILED"
SYNC_UNKNOWN = "UNKNOWN"

# ── Cross-camera candidate relation types ─────────────────────────────────────
# Never use "CONFIRMED_PERSON", "IDENTIFIED", etc.
CandidateRelationType = Literal["POSSIBLE_CONTINUATION", "POSSIBLE_SAME_ENTITY"]

CANDIDATE_POSSIBLE_CONTINUATION = "POSSIBLE_CONTINUATION"
CANDIDATE_POSSIBLE_SAME_ENTITY = "POSSIBLE_SAME_ENTITY"

# ── Candidate status ──────────────────────────────────────────────────────────
CandidateStatus = Literal["OPEN", "ACCEPTED", "REJECTED", "EXPIRED", "UNKNOWN"]

# ── Provider health states ────────────────────────────────────────────────────
ProviderHealthState = Literal[
    "READY", "WARMING", "DEGRADED", "UNAVAILABLE", "OFFLINE", "UNKNOWN",
]

PROVIDER_READY = "READY"
PROVIDER_WARMING = "WARMING"
PROVIDER_DEGRADED = "DEGRADED"
PROVIDER_UNAVAILABLE = "UNAVAILABLE"
PROVIDER_OFFLINE = "OFFLINE"
PROVIDER_UNKNOWN = "UNKNOWN"

# ── Association results ───────────────────────────────────────────────────────
AssociationResult = Literal[
    "MATCHED_TO_TRACK", "NEW_TRACK", "UNMATCHED", "REJECTED",
]

ASSOC_MATCHED = "MATCHED_TO_TRACK"
ASSOC_NEW_TRACK = "NEW_TRACK"
ASSOC_UNMATCHED = "UNMATCHED"
ASSOC_REJECTED = "REJECTED"

# ── Data completeness ─────────────────────────────────────────────────────────
DataCompleteness = Literal["COMPLETE", "PARTIAL", "UNKNOWN"]

# ── Lifecycle transition reasons ──────────────────────────────────────────────
REASON_DETECTION_RECEIVED  = "DETECTION_RECEIVED"
REASON_NO_OBSERVATIONS     = "NO_OBSERVATIONS"
REASON_PROVIDER_REACQUIRED = "PROVIDER_REACQUIRED"
REASON_PROVIDER_ENDED      = "PROVIDER_ENDED"
REASON_TIMEOUT             = "TIMEOUT"
REASON_STALE_AGE           = "STALE_AGE"
REASON_PROVIDER_INVALID    = "PROVIDER_INVALID"
REASON_OPERATOR_OVERRIDE   = "OPERATOR_OVERRIDE"
REASON_RECOVERY            = "RECOVERY"
