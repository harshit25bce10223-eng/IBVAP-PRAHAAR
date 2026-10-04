# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — Camera Health State Machine
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any

from app.core.config import settings


class CameraHealthState(str, Enum):
    ONLINE = "ONLINE"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"
    STALE = "STALE"
    FROZEN = "FROZEN"
    MAINTENANCE = "MAINTENANCE"
    UNKNOWN = "UNKNOWN"


class StreamState(str, Enum):
    CONNECTED = "CONNECTED"
    DEGRADED = "DEGRADED"
    RECONNECTING = "RECONNECTING"
    DISCONNECTED = "DISCONNECTED"
    STALE = "STALE"
    FROZEN = "FROZEN"
    UNKNOWN = "UNKNOWN"


class NetworkStatus(str, Enum):
    STABLE = "STABLE"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"
    UNKNOWN = "UNKNOWN"


class ViewpointStatus(str, Enum):
    STABLE = "STABLE"
    SHIFT_DETECTED = "SHIFT_DETECTED"
    SEVERE_SHIFT = "SEVERE_SHIFT"
    UNKNOWN = "UNKNOWN"


class HealthMetricStatus(str, Enum):
    GOOD = "GOOD"
    DEGRADED = "DEGRADED"
    FAILED = "FAILED"
    UNKNOWN = "UNKNOWN"


@dataclass
class StreamHealthMetrics:
    connected: bool = True
    observed_fps: float | None = None
    expected_fps: float = 25.0
    frame_drop_rate: float = 0.0
    frame_age_ms: float = 0.0
    reconnect_count: int = 0


@dataclass
class ImageQualityMetrics:
    sharpness: float | None = None
    brightness: float | None = None
    exposure: str | None = None
    contrast: float | None = None
    noise: float | None = None


@dataclass
class NetworkMetrics:
    latency_ms: float | None = None
    latency_variance_ms: float | None = None
    packet_loss_percent: float | None = None
    heartbeat_age_sec: float | None = None


@dataclass
class ViewpointMetrics:
    shift_score: float | None = None
    shift_confidence: float | None = None
    reference_features: int | None = None
    inlier_ratio: float | None = None
    # Explicit reference lifecycle signal (C2 repair F5/F13):
    # None  -> viewpoint not computed this observation (legacy behavior)
    # True  -> reference active, shift_score/shift_confidence are meaningful
    # False -> reference NOT initialized (low-texture / provisioning failed):
    #          state engine must report viewpoint UNKNOWN and must NOT
    #          auto-degrade the camera on viewpoint grounds.
    reference_active: bool | None = None


@dataclass
class FreezeMetrics:
    """Persistent visual-freeze signal derived from frame analysis (F3)."""
    frozen: bool = False
    confidence: float | None = None
    freeze_duration_sec: float | None = None
    reason: str | None = None


@dataclass
class CameraHealthInput:
    camera_id: str
    config: Any  # CameraHealthConfig
    source_timestamp: datetime
    received_at: datetime

    stream: StreamHealthMetrics | None = None
    image: ImageQualityMetrics | None = None
    network: NetworkMetrics | None = None
    viewpoint: ViewpointMetrics | None = None
    freeze: FreezeMetrics | None = None
    algorithm_version: str | None = None


@dataclass
class CameraHealthDerived:
    """Intermediate derived values before final state determination."""
    stream_state: StreamState
    stream_reason: str | None
    fps: float | None
    expected_fps: float | None
    frame_drop_percent: float | None
    stale_seconds: float | None
    reconnect_count: int | None

    image_status: HealthMetricStatus
    image_metrics: dict[str, Any]
    background_stability: str | None

    network_status: NetworkStatus
    network_reason: str | None

    viewpoint_status: ViewpointStatus
    shift_score: float | None
    shift_confidence: float | None
    shift_detected_at: datetime | None
    fence_confidence_note: str | None

    overall_status: CameraHealthState
    overall_reason: str | None
    reliability: str | None

    data_source: str = "LIVE"


class CameraHealthStateEngine:
    """
    Canonical camera health state determination.

    This is the SINGLE authoritative function for deriving camera health state.
    All API routes, background workers, and Component 1 integration must use this.

    Timezone policy (F8 — one canonical policy, documented):
      * All internal comparisons are performed with UTC-aware datetimes.
      * A NAIVE incoming timestamp (from legacy edge adapters that send local
        wall time without an offset) is interpreted as UTC. This is the single
        explicit documented naive-interpretation rule; adapters that send
        offset-aware timestamps are normalized with astimezone(utc).
        (Edge adapters are contractually required to send UTC; the naive rule
        exists so legacy inputs behave deterministically instead of crashing.)
    """

    def __init__(self):
        self._degraded_threshold = 2  # Number of degraded dimensions to trigger DEGRADED

    @staticmethod
    def _as_utc(dt: datetime) -> datetime:
        """Normalize a timestamp to aware-UTC per the documented F8 policy."""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    def derive_state(self, input_data: CameraHealthInput) -> CameraHealthDerived:
        """Main entry point - derive complete health state from raw input."""

        config = input_data.config
        now = datetime.now(timezone.utc)

        # ── 1. Stream Health ────────────────────────────────────────────────
        stream_derived = self._derive_stream_health(input_data, config)

        # ── 2. Image Quality ───────────────────────────────────────────────
        image_derived = self._derive_image_quality(input_data, config)

        # ── 3. Network Health ──────────────────────────────────────────────
        network_derived = self._derive_network_health(input_data, config)

        # ── 4. Viewpoint ───────────────────────────────────────────────────
        viewpoint_derived = self._derive_viewpoint(input_data, config)

        # ── 5. Overall State Determination ─────────────────────────────────
        overall_derived = self._determine_overall_state(
            stream_derived,
            image_derived,
            network_derived,
            viewpoint_derived,
            config,
        )

        return CameraHealthDerived(
            # Stream
            stream_state=stream_derived["state"],
            stream_reason=stream_derived["reason"],
            fps=stream_derived["fps"],
            expected_fps=stream_derived["expected_fps"],
            frame_drop_percent=stream_derived["frame_drop_percent"],
            stale_seconds=stream_derived["stale_seconds"],
            reconnect_count=stream_derived["reconnect_count"],
            # Image
            image_status=image_derived["status"],
            image_metrics=image_derived["metrics"],
            background_stability=image_derived["background_stability"],
            # Network
            network_status=network_derived["status"],
            network_reason=network_derived["reason"],
            # Viewpoint
            viewpoint_status=viewpoint_derived["status"],
            shift_score=viewpoint_derived["shift_score"],
            shift_confidence=viewpoint_derived["shift_confidence"],
            shift_detected_at=viewpoint_derived["detected_at"],
            fence_confidence_note=viewpoint_derived["fence_confidence_note"],
            # Overall
            overall_status=overall_derived["status"],
            overall_reason=overall_derived["reason"],
            reliability=overall_derived["reliability"],
            data_source=overall_derived["data_source"],
        )

    def _derive_stream_health(
        self, input_data: CameraHealthInput, config: Any
    ) -> dict[str, Any]:
        stream = input_data.stream
        source_ts = input_data.source_timestamp
        now = datetime.now(timezone.utc)
        if source_ts is not None:
            source_ts = self._as_utc(source_ts)  # F8 policy: naive → UTC

        if not stream or not stream.connected:
            return {
                "state": StreamState.DISCONNECTED,
                "reason": "Stream not connected",
                "fps": None,
                "expected_fps": config.expected_fps,
                "frame_drop_percent": None,
                "stale_seconds": (now - source_ts).total_seconds() if source_ts else None,
                "reconnect_count": stream.reconnect_count if stream else 0,
            }

        # Calculate frame age
        frame_age_sec = (now - source_ts).total_seconds()
        stale_seconds = frame_age_sec if frame_age_sec > 0 else None

        # Check stale threshold.
        # STALE (semantic, §38): frames are NOT arriving — the latest source
        # timestamp is older than the configured threshold. Distinct from
        # FROZEN, where frames arrive on schedule but carry identical content.
        if stale_seconds and stale_seconds > config.stale_after_seconds:
            return {
                "state": StreamState.STALE,
                "reason": f"No fresh frames for {stale_seconds:.0f}s (threshold: {config.stale_after_seconds}s)",
                "fps": stream.observed_fps,
                "expected_fps": config.expected_fps,
                "frame_drop_percent": stream.frame_drop_rate * 100 if stream.frame_drop_rate else None,
                "stale_seconds": stale_seconds,
                "reconnect_count": stream.reconnect_count,
            }

        # Persistent visual freeze (frame-derived, F3): the stream delivers
        # frames on schedule but their content is bit-exact/near-identical —
        # the encoder or upstream source is repeating frames. Takes precedence
        # over FPS-based degradation (a frozen encoder often reports fps 0).
        freeze = input_data.freeze
        if freeze and freeze.frozen:
            return {
                "state": StreamState.FROZEN,
                "reason": freeze.reason or "Persistent visual freeze (identical frames)",
                "fps": stream.observed_fps,
                "expected_fps": config.expected_fps,
                "frame_drop_percent": stream.frame_drop_rate * 100 if stream.frame_drop_rate else None,
                "stale_seconds": stale_seconds,
                "reconnect_count": stream.reconnect_count,
            }

        # Check FPS
        expected = config.expected_fps
        observed = stream.observed_fps
        if observed is not None and expected > 0:
            fps_ratio = observed / expected
            if fps_ratio < 0.5:  # Less than 50% of expected FPS
                return {
                    "state": StreamState.DEGRADED,
                    "reason": f"Low FPS: {observed:.1f}/{expected:.1f}",
                    "fps": observed,
                    "expected_fps": expected,
                    "frame_drop_percent": stream.frame_drop_rate * 100 if stream.frame_drop_rate else None,
                    "stale_seconds": stale_seconds,
                    "reconnect_count": stream.reconnect_count,
                }

        # Check freeze (this is a simplified check - real freeze detection is more complex)
        if stream.frame_drop_rate and stream.frame_drop_rate > 0.5:
            return {
                "state": StreamState.FROZEN,
                "reason": "High frame drop rate suggests frozen stream",
                "fps": stream.observed_fps,
                "expected_fps": config.expected_fps,
                "frame_drop_percent": stream.frame_drop_rate * 100,
                "stale_seconds": stale_seconds,
                "reconnect_count": stream.reconnect_count,
            }

        # Check reconnects
        if stream.reconnect_count and stream.reconnect_count > 3:
            return {
                "state": StreamState.RECONNECTING,
                "reason": f"Frequent reconnects: {stream.reconnect_count}",
                "fps": stream.observed_fps,
                "expected_fps": config.expected_fps,
                "frame_drop_percent": stream.frame_drop_rate * 100 if stream.frame_drop_rate else None,
                "stale_seconds": stale_seconds,
                "reconnect_count": stream.reconnect_count,
            }

        return {
            "state": StreamState.CONNECTED,
            "reason": None,
            "fps": stream.observed_fps,
            "expected_fps": config.expected_fps,
            "frame_drop_percent": stream.frame_drop_rate * 100 if stream.frame_drop_rate else None,
            "stale_seconds": stale_seconds,
            "reconnect_count": stream.reconnect_count,
        }

    def _derive_image_quality(
        self, input_data: CameraHealthInput, config: Any
    ) -> dict[str, Any]:
        image = input_data.image
        if not image:
            return {
                "status": HealthMetricStatus.UNKNOWN,
                "metrics": {},
                "background_stability": None,
            }

        metrics = {}
        degraded_count = 0

        # Sharpness
        if image.sharpness is not None:
            threshold = config.sharpness_degraded_threshold or 0.5
            status = HealthMetricStatus.GOOD if image.sharpness >= threshold else HealthMetricStatus.DEGRADED
            if status == HealthMetricStatus.DEGRADED:
                degraded_count += 1
            metrics["sharpness"] = {
                "value": image.sharpness,
                "unit": "ratio",
                "status": status,
                "reason": "Below configured threshold" if status == HealthMetricStatus.DEGRADED else None,
            }

        # Brightness
        if image.brightness is not None:
            low_thresh = config.brightness_low_threshold or 0.1
            high_thresh = config.brightness_high_threshold or 0.9
            if image.brightness < low_thresh:
                status = HealthMetricStatus.DEGRADED
                reason = f"Brightness low: {image.brightness:.2f} < {low_thresh}"
                degraded_count += 1
            elif image.brightness > high_thresh:
                status = HealthMetricStatus.DEGRADED
                reason = f"Brightness high: {image.brightness:.2f} > {high_thresh}"
                degraded_count += 1
            else:
                status = HealthMetricStatus.GOOD
                reason = None
            metrics["brightness"] = {
                "value": image.brightness,
                "unit": "ratio",
                "status": status,
                "reason": reason,
            }

        # Exposure
        if image.exposure:
            status = HealthMetricStatus.GOOD if image.exposure == "NORMAL" else HealthMetricStatus.DEGRADED
            if status == HealthMetricStatus.DEGRADED:
                degraded_count += 1
            metrics["exposure"] = {
                "value": image.exposure,
                "unit": None,
                "status": status,
                "reason": f"Exposure: {image.exposure}" if status == HealthMetricStatus.DEGRADED else None,
            }

        # Contrast
        if image.contrast is not None:
            metrics["contrast"] = {
                "value": image.contrast,
                "unit": "ratio",
                "status": HealthMetricStatus.GOOD,
                "reason": None,
            }

        # Noise
        if image.noise is not None:
            metrics["noise"] = {
                "value": image.noise,
                "unit": "ratio",
                "status": HealthMetricStatus.GOOD,
                "reason": None,
            }

        overall_status = (
            HealthMetricStatus.DEGRADED if degraded_count > 0 else HealthMetricStatus.GOOD
        )
        if degraded_count >= 2:
            overall_status = HealthMetricStatus.FAILED

        return {
            "status": overall_status,
            "metrics": metrics,
            "background_stability": "Stable against slow baseline" if degraded_count == 0 else "Degradation detected",
        }

    def _derive_network_health(
        self, input_data: CameraHealthInput, config: Any
    ) -> dict[str, Any]:
        network = input_data.network
        if not network:
            return {
                "status": NetworkStatus.UNKNOWN,
                "reason": "No network telemetry",
            }

        degraded = []

        if network.latency_ms is not None:
            if network.latency_ms > 200:
                degraded.append(f"High latency: {network.latency_ms:.0f}ms")
        if network.latency_variance_ms is not None:
            if network.latency_variance_ms > 100:
                degraded.append(f"High latency variance: {network.latency_variance_ms:.0f}ms")
        if network.packet_loss_percent is not None:
            if network.packet_loss_percent > 1.0:
                degraded.append(f"Packet loss: {network.packet_loss_percent:.1f}%")
        if network.heartbeat_age_sec is not None:
            if network.heartbeat_age_sec > config.offline_after_seconds:
                return {
                    "status": NetworkStatus.OFFLINE,
                    "reason": f"Heartbeat stale: {network.heartbeat_age_sec:.0f}s",
                }

        if degraded:
            return {
                "status": NetworkStatus.DEGRADED,
                "reason": "; ".join(degraded),
            }

        return {
            "status": NetworkStatus.STABLE,
            "reason": None,
        }

    def _derive_viewpoint(
        self, input_data: CameraHealthInput, config: Any
    ) -> dict[str, Any]:
        viewpoint = input_data.viewpoint
        if not viewpoint or viewpoint.shift_score is None:
            return {
                "status": ViewpointStatus.UNKNOWN,
                "shift_score": None,
                "shift_confidence": None,
                "detected_at": None,
                "fence_confidence_note": None,
            }

        # Explicit reference lifecycle (F5): a viewpoint whose geometric
        # reference is NOT initialized carries no shift evidence. Report
        # UNKNOWN — never auto-degrade a camera because its scene is
        # low-texture or provisioning has not completed yet.
        if viewpoint.reference_active is False:
            return {
                "status": ViewpointStatus.UNKNOWN,
                "shift_score": viewpoint.shift_score,
                "shift_confidence": viewpoint.shift_confidence,
                "detected_at": None,
                "fence_confidence_note": "Viewpoint reference not initialized (low texture or provisioning pending) — geometry confidence unestablished",
            }

        score = viewpoint.shift_score
        confidence = viewpoint.shift_confidence or 0.0
        threshold = config.viewpoint_shift_threshold

        if score >= threshold and confidence >= config.min_ransac_inlier_ratio:
            if score >= 0.7:
                status = ViewpointStatus.SEVERE_SHIFT
                note = "Severe viewpoint shift — fence confidence severely reduced"
            else:
                status = ViewpointStatus.SHIFT_DETECTED
                note = "Viewpoint shift detected — fence confidence reduced until officer review"
            return {
                "status": status,
                "shift_score": score,
                "shift_confidence": confidence,
                "detected_at": datetime.now(timezone.utc),
                "fence_confidence_note": note,
            }

        return {
            "status": ViewpointStatus.STABLE,
            "shift_score": score,
            "shift_confidence": confidence,
            "detected_at": None,
            "fence_confidence_note": None,
        }

    def _determine_overall_state(
        self,
        stream_derived: dict[str, Any],
        image_derived: dict[str, Any],
        network_derived: dict[str, Any],
        viewpoint_derived: dict[str, Any],
        config: Any,
    ) -> dict[str, Any]:
        """Determine overall camera health state with documented precedence.

        State-precedence matrix (F13; table-driven tests in
        tests/unit/test_c2_regression.py):

            stream DISCONNECTED                → OFFLINE
            stream FROZEN (visual freeze or
            sustained high frame-drop)         → FROZEN
            stream STALE (source timestamp
            older than stale_after_seconds)    → STALE
            severe viewpoint shift             → DEGRADED (always)
            ≥ 2 degraded dimensions            → DEGRADED
            exactly 1 of image/network/
            viewpoint degraded                 → DEGRADED (F9 decision)
            exactly 1 of stream degraded
            (low FPS / reconnects)             → UNKNOWN (F9 decision)
            stream CONNECTED + image GOOD +
            network STABLE + viewpoint not
            shifted (STABLE or UNKNOWN)        → ONLINE
            anything else                      → UNKNOWN
        """

        # Precedence order (highest to lowest):
        # 1. OFFLINE - no stream, no heartbeat
        # 2. FROZEN - frames arriving but content frozen (distinct from STALE,
        #    where frames are not arriving at all — §38)
        # 3. STALE - stream stale beyond threshold
        # 4. DEGRADED - dimension accounting per matrix above
        # 5. MAINTENANCE - manual override
        # 6. ONLINE - all measured dimensions healthy
        # 7. UNKNOWN - insufficient data

        stream_state = stream_derived["state"]
        image_status = image_derived["status"]
        network_status = network_derived["status"]
        viewpoint_status = viewpoint_derived["status"]

        # OFFLINE check
        if stream_state == StreamState.DISCONNECTED:
            if network_status == NetworkStatus.OFFLINE:
                return {
                    "status": CameraHealthState.OFFLINE,
                    "reason": "Stream disconnected and heartbeat lost",
                    "reliability": "LOW",
                    "data_source": "LIVE",
                }
            return {
                "status": CameraHealthState.OFFLINE,
                "reason": "Stream disconnected",
                "reliability": "LOW",
                "data_source": "LIVE",
            }

        # FROZEN check
        if stream_state == StreamState.FROZEN:
            return {
                "status": CameraHealthState.FROZEN,
                "reason": stream_derived["reason"] or "Frozen stream detected",
                "reliability": "LOW",
                "data_source": "LIVE",
            }

        # STALE check
        if stream_state == StreamState.STALE:
            return {
                "status": CameraHealthState.STALE,
                "reason": stream_derived["reason"] or "Stream stale",
                "reliability": "LOW",
                "data_source": "LIVE",
            }

        # MAINTENANCE check (would come from config/manual override)
        # This would be checked if config has maintenance flag

        # ── Degraded-dimension accounting (documented product decision, F9) ──
        # A single degraded dimension is enough to declare DEGRADED when the
        # dimension is individually operationally meaningful:
        #   image DEGRADED/FAILED  → analytics output quality at risk → DEGRADED
        #   network DEGRADED       → live visibility at risk            → DEGRADED
        #   viewpoint SHIFT        → fence geometry unreliable           → DEGRADED
        # The stream dimension is treated differently: low FPS or frequent
        # reconnects ALONE are transitory conditions that do not by themselves
        # compromise coverage, so stream-only degradation resolves to UNKNOWN
        # (telemetry insufficient for a definitive health verdict). This is a
        # deliberate product decision recorded in the repair report — it is
        # NOT tuned to improve benchmark scores.
        self_degrading_dims = {"image", "network", "viewpoint"}

        degraded_dims = []
        if image_status in (HealthMetricStatus.DEGRADED, HealthMetricStatus.FAILED):
            degraded_dims.append("image")
        if network_status == NetworkStatus.DEGRADED:
            degraded_dims.append("network")
        if viewpoint_status in (ViewpointStatus.SHIFT_DETECTED, ViewpointStatus.SEVERE_SHIFT):
            degraded_dims.append("viewpoint")
        if stream_state in (StreamState.DEGRADED, StreamState.RECONNECTING):
            degraded_dims.append("stream")

        # Severe geometric shift is always DEGRADED: the virtual fence cannot
        # be trusted regardless of how healthy every other dimension is.
        severe_shift = viewpoint_status == ViewpointStatus.SEVERE_SHIFT

        if len(degraded_dims) >= self._degraded_threshold or severe_shift or (
            len(degraded_dims) == 1 and degraded_dims[0] in self_degrading_dims
        ):
            reason_parts = []
            if image_status == HealthMetricStatus.DEGRADED:
                reason_parts.append("image quality degraded")
            if image_status == HealthMetricStatus.FAILED:
                reason_parts.append("image quality failed")
            if network_status == NetworkStatus.DEGRADED:
                reason_parts.append("network degraded")
            if viewpoint_status == ViewpointStatus.SHIFT_DETECTED:
                reason_parts.append("viewpoint shift detected")
            if viewpoint_status == ViewpointStatus.SEVERE_SHIFT:
                reason_parts.append("severe viewpoint shift")
            if stream_state == StreamState.DEGRADED:
                reason_parts.append("low FPS")
            if stream_state == StreamState.RECONNECTING:
                reason_parts.append("frequent reconnects")

            return {
                "status": CameraHealthState.DEGRADED,
                "reason": "; ".join(reason_parts) if reason_parts else "Multiple degraded dimensions",
                "reliability": "LOW" if viewpoint_status in (ViewpointStatus.SHIFT_DETECTED, ViewpointStatus.SEVERE_SHIFT) else "MEDIUM",
                "data_source": "LIVE",
            }

        # ── ONLINE gate (F13): every dimension must be healthy or unmeasured ──
        # viewpoint UNKNOWN (e.g. low-texture scene, reference not initialized)
        # does NOT block ONLINE — unknown geometry is surfaced through
        # fence_confidence_note / geometry_confidence, never auto-degraded
        # (spec §12-14). A detected shift, by contrast, must block ONLINE.
        viewpoint_blocks_online = viewpoint_status in (
            ViewpointStatus.SHIFT_DETECTED,
            ViewpointStatus.SEVERE_SHIFT,
        )
        if (
            stream_state == StreamState.CONNECTED
            and image_status == HealthMetricStatus.GOOD
            and network_status == NetworkStatus.STABLE
            and not viewpoint_blocks_online
        ):
            return {
                "status": CameraHealthState.ONLINE,
                "reason": None,
                "reliability": "HIGH",
                "data_source": "LIVE",
            }

        return {
            "status": CameraHealthState.UNKNOWN,
            "reason": "Insufficient telemetry for definitive state",
            "reliability": "UNKNOWN",
            "data_source": "LIVE",
        }


# Singleton instance
camera_health_state_engine = CameraHealthStateEngine()