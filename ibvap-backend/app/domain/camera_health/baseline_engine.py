# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — Camera Health Baseline Engine
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

import statistics


class IlluminationRegime(str, Enum):
    DAY = "DAY"
    LOW_LIGHT = "LOW_LIGHT"
    NIGHT = "NIGHT"
    IR = "IR"
    UNKNOWN = "UNKNOWN"


@dataclass
class BaselineStats:
    median: float
    mad: float  # Median Absolute Deviation
    p05: float
    p95: float
    ewma: float
    sample_count: int


class BaselineEngine:
    """
    Maintains camera-specific adaptive baselines for health metrics.
    
    Supports two baseline speeds:
    - FAST: adapts quickly (minutes/hours) for sudden changes like camera shift
    - SLOW: adapts slowly (days/weeks) for gradual changes like lens degradation
    
    Uses robust statistics (median, MAD, percentiles) to resist outliers.
    Never learns from anomalous samples (frozen, shifted, degraded states).
    """

    def __init__(
        self,
        fast_alpha: float = 0.3,      # Fast EWMA smoothing
        slow_alpha: float = 0.01,     # Slow EWMA smoothing
        min_samples: int = 10,        # Minimum samples before baseline is valid
        max_samples: int = 1000,      # Maximum history for percentile calc
        outlier_mad_threshold: float = 3.0,  # MAD threshold for outlier rejection
    ):
        self.fast_alpha = fast_alpha
        self.slow_alpha = slow_alpha
        self.min_samples = min_samples
        self.max_samples = max_samples
        self.outlier_mad_threshold = outlier_mad_threshold

        # In-memory storage: camera_id -> metric -> regime -> list of values
        self._fast_values: dict[str, dict[str, dict[str, list[float]]]] = {}
        self._slow_values: dict[str, dict[str, dict[str, list[float]]]] = {}
        self._fast_ewma: dict[str, dict[str, dict[str, float]]] = {}
        self._slow_ewma: dict[str, dict[str, dict[str, float]]] = {}

    def _get_key(self, camera_id: str, metric: str, regime: str) -> tuple:
        return (camera_id, metric, regime)

    def update(
        self,
        camera_id: str,
        metric: str,
        value: float,
        regime: str = IlluminationRegime.UNKNOWN,
        is_healthy: bool = True,
        is_anomaly: bool = False,
    ) -> None:
        """Update baselines with a new observation."""
        if is_anomaly:
            # Never learn from anomalous samples (frozen, shifted, severely degraded)
            return

        key = self._get_key(camera_id, metric, regime)

        # Initialize storage
        for storage in [self._fast_values, self._slow_values]:
            if camera_id not in storage:
                storage[camera_id] = {}
            if metric not in storage[camera_id]:
                storage[camera_id][metric] = {}
            if regime not in storage[camera_id][metric]:
                storage[camera_id][metric][regime] = []

        # Fast baseline update
        fast_list = self._fast_values[camera_id][metric][regime]
        fast_list.append(value)
        if len(fast_list) > self.max_samples:
            fast_list.pop(0)

        # Slow baseline update (only if healthy)
        if is_healthy:
            slow_list = self._slow_values[camera_id][metric][regime]
            slow_list.append(value)
            if len(slow_list) > self.max_samples:
                slow_list.pop(0)

        # Update EWMAs
        self._update_ewma(self._fast_ewma, key, value, self.fast_alpha)
        if is_healthy:
            self._update_ewma(self._slow_ewma, key, value, self.slow_alpha)

    def _update_ewma(self, ewma_store: dict, key: tuple, value: float, alpha: float) -> None:
        if key not in ewma_store:
            ewma_store[key] = value
        else:
            ewma_store[key] = alpha * value + (1 - alpha) * ewma_store[key]

    def get_stats(
        self,
        camera_id: str,
        metric: str,
        regime: str = IlluminationRegime.UNKNOWN,
        use_slow: bool = True,
    ) -> BaselineStats | None:
        """Get robust statistics for a metric's baseline."""
        key = self._get_key(camera_id, metric, regime)
        storage = self._slow_values if use_slow else self._fast_values
        ewma_store = self._slow_ewma if use_slow else self._fast_ewma

        if camera_id not in storage or metric not in storage[camera_id] or regime not in storage[camera_id][metric]:
            return None

        values = storage[camera_id][metric][regime]
        if len(values) < self.min_samples:
            return None

        median = statistics.median(values)
        mad = statistics.median([abs(v - median) for v in values])
        p05 = statistics.quantiles(values, n=20)[0] if len(values) >= 20 else min(values)
        p95 = statistics.quantiles(values, n=20)[18] if len(values) >= 20 else max(values)
        ewma = ewma_store.get(key, median)

        return BaselineStats(
            median=median,
            mad=mad,
            p05=p05,
            p95=p95,
            ewma=ewma,
            sample_count=len(values),
        )

    def get_score(
        self,
        camera_id: str,
        metric: str,
        value: float,
        regime: str = IlluminationRegime.UNKNOWN,
        use_slow: bool = True,
    ) -> float | None:
        """
        Calculate normalized score (0-1) of how typical a value is.
        
        Returns:
        - ~0.5 for typical values near median
        - >0.5 for values above baseline
        - <0.5 for values below baseline
        - None if baseline not established
        """
        stats = self.get_stats(camera_id, metric, regime, use_slow)
        if not stats:
            return None

        # Use MAD-based z-score (robust)
        if stats.mad > 0:
            z = (value - stats.median) / (stats.mad * 1.4826)  # MAD to std conversion
        else:
            z = 0.0

        # Convert z-score to 0-1 using sigmoid-like function
        # z=0 -> 0.5, z=2 -> ~0.88, z=-2 -> ~0.12
        import math
        score = 1 / (1 + math.exp(-z / 2))
        return max(0.0, min(1.0, score))

    def is_degraded(
        self,
        camera_id: str,
        metric: str,
        value: float,
        regime: str = IlluminationRegime.UNKNOWN,
        threshold_mad: float = 2.0,
        use_slow: bool = True,
    ) -> bool:
        """Check if a value is significantly degraded from baseline."""
        stats = self.get_stats(camera_id, metric, regime, use_slow)
        if not stats or stats.mad == 0:
            return False

        # Value is degraded if it's below median by more than threshold MADs
        # (assuming lower is worse for metrics like sharpness)
        mad_diff = (stats.median - value) / stats.mad
        return mad_diff > threshold_mad

    def freeze_baseline(
        self,
        camera_id: str,
        metric: str,
        regime: str = IlluminationRegime.UNKNOWN,
    ) -> None:
        """Prevent baseline updates (e.g., during suspected tamper)."""
        # In a full implementation, this would set a flag in persistent storage
        # For now, we just don't update when is_anomaly=True
        pass

    def reset_baseline(
        self,
        camera_id: str,
        metric: str,
        regime: str = IlluminationRegime.UNKNOWN,
    ) -> None:
        """Reset baseline after maintenance."""
        key = self._get_key(camera_id, metric, regime)
        for storage in [self._fast_values, self._slow_values]:
            if camera_id in storage and metric in storage[camera_id]:
                storage[camera_id][metric][regime] = []
        for ewma in [self._fast_ewma, self._slow_ewma]:
            if key in ewma:
                del ewma[key]

    def get_all_metrics(self, camera_id: str) -> dict[str, dict[str, BaselineStats]]:
        """Get all baseline stats for a camera (for debugging/monitoring)."""
        result = {}
        if camera_id not in self._slow_values:
            return result
        for metric, regimes in self._slow_values[camera_id].items():
            result[metric] = {}
            for regime in regimes:
                stats = self.get_stats(camera_id, metric, regime, use_slow=True)
                if stats:
                    result[metric][regime] = stats
        return result


# Global instance
baseline_engine = BaselineEngine()