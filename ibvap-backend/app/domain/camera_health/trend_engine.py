# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — Camera Health Trend Engine
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Any
from collections import deque

import statistics


class TrendDirection(str, Enum):
    IMPROVING = "IMPROVING"
    STABLE = "STABLE"
    DEGRADING = "DEGRADING"
    UNKNOWN = "UNKNOWN"


class TrendPersistenceState(str, Enum):
    NORMAL = "NORMAL"
    WATCH = "WATCH"
    DEGRADING = "DEGRADING"
    MAINTENANCE_RECOMMENDED = "MAINTENANCE_RECOMMENDED"
    CRITICAL = "CRITICAL"


@dataclass
class TrendSample:
    timestamp: datetime
    value: float


@dataclass
class TrendResult:
    metric: str
    label: str
    direction: TrendDirection
    delta_percent: float | None
    window: str | None
    persistence: str | None
    persistence_state: TrendPersistenceState
    series: list[float]


class TrendEngine:
    """
    Calculates trends from time-series metric samples.
    
    Uses robust statistics (median, MAD, Theil-Sen slope) to be resistant to outliers.
    Maintains persistence tracking to avoid false alarms from single bad samples.
    """

    def __init__(
        self,
        window_days: int = 7,
        persistence_days: int = 3,
        min_samples: int = 5,
        degradation_threshold_percent: float = -5.0,
        max_slope_samples: int = 100,
    ):
        self.window_days = window_days
        self.persistence_days = persistence_days
        self.min_samples = min_samples
        self.degradation_threshold = degradation_threshold_percent
        # §42 performance bound: caps how many in-window points feed the
        # all-pairs Theil-Sen slope (see calculate_trend). 100 uniformly
        # sampled points still yield ~4,950 pairwise slopes per metric — far
        # more than needed for a robust median slope — while keeping the
        # per-observation cost flat in history length.
        self.max_slope_samples = max_slope_samples

        # In-memory sample storage, keyed per camera+metric (F2/F8): a single
        # global metric key mixed samples from different cameras into one
        # series, corrupting trend calculations in multi-camera deployments.
        self._samples: dict[str, deque[TrendSample]] = {}

    @staticmethod
    def _as_utc(dt: datetime) -> datetime:
        """F8 canonical policy: naive timestamps are interpreted as UTC."""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)

    @staticmethod
    def _key(camera_id: str, metric: str) -> str:
        return f"{camera_id}:{metric}"

    def add_sample(self, camera_id: str, metric: str, timestamp: datetime, value: float) -> None:
        """Add a new sample for a camera's metric (F8: normalized to UTC)."""
        key = self._key(camera_id, metric)
        if key not in self._samples:
            self._samples[key] = deque(maxlen=10000)
        self._samples[key].append(
            TrendSample(timestamp=self._as_utc(timestamp), value=value)
        )

    def add_samples_from_history(
        self, camera_id: str, metric: str, samples: list[tuple[datetime, float]]
    ) -> None:
        """Bulk load historical samples for a camera's metric."""
        key = self._key(camera_id, metric)
        if key not in self._samples:
            self._samples[key] = deque(maxlen=10000)
        for ts, val in samples:
            self._samples[key].append(
                TrendSample(timestamp=self._as_utc(ts), value=val)
            )

    def calculate_trend(
        self, camera_id: str, metric: str, label: str, now: datetime | None = None
    ) -> TrendResult:
        """Calculate trend for a camera's metric over the configured window."""
        now = self._as_utc(now) if now is not None else datetime.now(timezone.utc)
        window_start = now - timedelta(days=self.window_days)

        key = self._key(camera_id, metric)
        if key not in self._samples:
            return TrendResult(
                metric=metric,
                label=label,
                direction=TrendDirection.UNKNOWN,
                delta_percent=None,
                window=f"{self.window_days} DAYS",
                persistence=None,
                persistence_state=TrendPersistenceState.NORMAL,
                series=[],
            )

        # Filter samples within window (all stored as aware-UTC)
        samples = [
            s for s in self._samples[key]
            if s.timestamp >= window_start
        ]

        if len(samples) < self.min_samples:
            return TrendResult(
                metric=metric,
                label=label,
                direction=TrendDirection.UNKNOWN,
                delta_percent=None,
                window=f"{self.window_days} DAYS",
                persistence=None,
                persistence_state=TrendPersistenceState.NORMAL,
                series=[s.value for s in samples[-20:]],
            )

        # Sort by timestamp
        samples.sort(key=lambda s: s.timestamp)

        values = [s.value for s in samples]  # full window: series + reference value

        # Theil-Sen is all-pairs O(k^2) per call and this runs ~4x per
        # observation (sharpness/brightness/latency + maintenance check).
        # §42 performance measurement: full analyze_observation p50 grew
        # 15.5 ms (k~100) -> 319.9 ms (k=1000), with the k^2 slope work as the
        # only growing component. Bound the slope estimate to at most
        # max_slope_samples points taken at a uniform stride across the window
        # (plus the newest sample), so cost is flat in history length while
        # the estimate still spans the whole window. For k <= max_slope_samples
        # this is bit-identical to the all-pairs computation (the frozen v1.1
        # benchmark digests must remain unchanged).
        if len(samples) > self.max_slope_samples:
            stride = -(-len(samples) // self.max_slope_samples)  # ceil division
            slope_samples = samples[::stride]
            if slope_samples[-1] is not samples[-1]:
                slope_samples.append(samples[-1])
        else:
            slope_samples = samples

        slope_values = [s.value for s in slope_samples]
        slope_times = [
            (s.timestamp - slope_samples[0].timestamp).total_seconds()
            for s in slope_samples
        ]

        # Theil-Sen slope estimator (robust)
        slopes = []
        for i in range(len(slope_samples)):
            for j in range(i + 1, len(slope_samples)):
                dt = slope_times[j] - slope_times[i]
                if dt > 0:
                    slopes.append((slope_values[j] - slope_values[i]) / dt)

        if not slopes:
            slope = 0.0
        else:
            slope = statistics.median(slopes)

        # Convert slope to percent change over window
        first_val = values[0]
        if first_val != 0:
            delta_percent = (slope * (self.window_days * 86400)) / first_val * 100
        else:
            delta_percent = 0.0

        # Determine direction
        if delta_percent > 2.0:
            direction = TrendDirection.IMPROVING
        elif delta_percent < -2.0:
            direction = TrendDirection.DEGRADING
        else:
            direction = TrendDirection.STABLE

        # Persistence tracking
        persistence_state = self._assess_persistence(
            metric, direction, delta_percent, samples
        )

        # Persistence label
        persistence_label = self._format_persistence(persistence_state, samples, now)

        return TrendResult(
            metric=metric,
            label=label,
            direction=direction,
            delta_percent=round(delta_percent, 1),
            window=f"{self.window_days} DAYS",
            persistence=persistence_label,
            persistence_state=persistence_state,
            series=values[-50:],  # Last 50 points for sparkline
        )

    def _assess_persistence(
        self, metric: str, direction: TrendDirection, delta_percent: float, samples: list[TrendSample]
    ) -> TrendPersistenceState:
        """Assess how persistent a trend is."""
        if direction != TrendDirection.DEGRADING:
            return TrendPersistenceState.NORMAL

        # Check if degradation has persisted
        degrading_count = 0
        for s in reversed(samples):
            # This is a simplified check - in reality we'd track state over time
            if s.value < samples[0].value * 0.95:  # 5% below start
                degrading_count += 1
            else:
                break

        if degrading_count >= self.persistence_days * 2:  # Roughly 2 samples per day
            return TrendPersistenceState.MAINTENANCE_RECOMMENDED
        elif degrading_count >= self.persistence_days:
            return TrendPersistenceState.DEGRADING
        else:
            return TrendPersistenceState.WATCH

    def _format_persistence(
        self, state: TrendPersistenceState, samples: list[TrendSample], now: datetime
    ) -> str | None:
        if state == TrendPersistenceState.NORMAL:
            return None
        # Simplified - in production, track actual start time of condition
        return f"{self.persistence_days} days"

    def get_series(self, camera_id: str, metric: str, max_points: int = 100) -> list[float]:
        """Get recent series for sparkline."""
        key = self._key(camera_id, metric)
        if key not in self._samples:
            return []
        return [s.value for s in list(self._samples[key])[-max_points:]]

    def clear_metric(self, camera_id: str, metric: str) -> None:
        """Clear samples for a camera's metric (e.g., after baseline reset)."""
        key = self._key(camera_id, metric)
        if key in self._samples:
            self._samples[key].clear()


# Global trend engine instance (in production, this would be per-camera or request-scoped)
trend_engine = TrendEngine()