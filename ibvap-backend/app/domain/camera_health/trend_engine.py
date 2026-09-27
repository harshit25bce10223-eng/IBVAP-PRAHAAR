# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — Camera Health Trend Engine
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
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
    ):
        self.window_days = window_days
        self.persistence_days = persistence_days
        self.min_samples = min_samples
        self.degradation_threshold = degradation_threshold_percent

        # In-memory sample storage (in production, query from database)
        self._samples: dict[str, deque[TrendSample]] = {}

    def add_sample(self, metric: str, timestamp: datetime, value: float) -> None:
        """Add a new sample for a metric."""
        if metric not in self._samples:
            self._samples[metric] = deque(maxlen=10000)
        self._samples[metric].append(TrendSample(timestamp=timestamp, value=value))

    def add_samples_from_history(self, metric: str, samples: list[tuple[datetime, float]]) -> None:
        """Bulk load historical samples."""
        if metric not in self._samples:
            self._samples[metric] = deque(maxlen=10000)
        for ts, val in samples:
            self._samples[metric].append(TrendSample(timestamp=ts, value=val))

    def calculate_trend(
        self, metric: str, label: str, now: datetime | None = None
    ) -> TrendResult:
        """Calculate trend for a metric over the configured window."""
        now = now or datetime.now()
        window_start = now - timedelta(days=self.window_days)

        if metric not in self._samples:
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

        # Filter samples within window
        samples = [
            s for s in self._samples[metric]
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

        values = [s.value for s in samples]
        times = [(s.timestamp - samples[0].timestamp).total_seconds() for s in samples]

        # Theil-Sen slope estimator (robust)
        slopes = []
        for i in range(len(samples)):
            for j in range(i + 1, len(samples)):
                dt = times[j] - times[i]
                if dt > 0:
                    slopes.append((values[j] - values[i]) / dt)

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

    def get_series(self, metric: str, max_points: int = 100) -> list[float]:
        """Get recent series for sparkline."""
        if metric not in self._samples:
            return []
        return [s.value for s in list(self._samples[metric])[-max_points:]]

    def clear_metric(self, metric: str) -> None:
        """Clear samples for a metric (e.g., after baseline reset)."""
        if metric in self._samples:
            self._samples[metric].clear()


# Global trend engine instance (in production, this would be per-camera or request-scoped)
trend_engine = TrendEngine()