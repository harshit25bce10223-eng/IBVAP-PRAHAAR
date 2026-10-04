# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — Camera Frozen Frame Detection
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import numpy as np


@dataclass
class FreezeResult:
    frozen: bool
    confidence: float  # 0-1
    similarity_score: float  # 0-1, higher = more similar to previous
    freeze_duration_sec: float | None = None
    reason: str | None = None


class FreezeDetector:
    """
    Detects frozen camera streams using absolute temporal activity analysis.

    Key principles (repaired in C2 re-open — F4/F11):
    - Not timestamp-based: a frozen encoder keeps advancing timestamps.
    - ABSOLUTE pixel-difference activity, not normalized correlation:
      mean-normalized NCC is scale-invariant and correlates ~0.995+ on any
      quiet structured scene regardless of sensor-noise magnitude, which is
      what produced false FROZEN verdicts on healthy quiet feeds. The
      decision statistic here is the median ABSOLUTE per-region frame
      difference on a small uniform ROI grid, compared against the
      configured `noise_floor` (a live sensor always injects at least the
      camera's native noise; a repeated/duplicated frame carries none).
    - Bit-exact short-circuit: pixel-identical consecutive frames are frozen
      evidence regardless of thresholds.
    - ROI-aware movement guard: real motion in ANY grid region vetoes a
      freeze verdict (a distant pedestrian changing one region must not be
      masked by a static background in the other regions), while per-region
      noise spread does not.
    - Temporal persistence before confirming, so single coincidences do not
      raise FROZEN.
    - Generic uniform grid only — no benchmark-specific or hard-coded ROIs.
    """

    # Uniform, generic ROI grid: rows x cols split over the downscaled frame.
    REGION_GRID = (4, 4)

    def __init__(
        self,
        scale_factor: float = 0.125,        # Heavy downscale for speed
        similarity_threshold: float = 0.995, # Kept for API compat (1 - activity)
        persistence_frames: int = 10,        # Frames to persist before confirming
        min_frame_interval_sec: float = 0.5, # Min time between analyzed frames
        noise_floor: float = 0.001,          # Absolute activity floor (0-1 scale)
    ):
        self.scale_factor = scale_factor
        self.similarity_threshold = similarity_threshold
        self.persistence_frames = persistence_frames
        self.min_frame_interval = timedelta(seconds=min_frame_interval_sec)
        self.noise_floor = noise_floor

        # Movement guard: a region is "moving" when its activity exceeds the
        # per-region noise spread by this factor (plus a small absolute floor).
        self.movement_spread_factor = 8.0

        # State
        self._prev_frame: np.ndarray | None = None
        self._prev_timestamp: datetime | None = None
        self._consecutive_similar: int = 0
        self._freeze_start: datetime | None = None
        self._last_activity: float | None = None

        # Try to import cv2
        self._cv2_available = False
        try:
            import cv2
            self._cv2 = cv2
            self._cv2_available = True
        except ImportError:
            self._cv2 = None

    def _preprocess(self, frame: np.ndarray) -> np.ndarray:
        """Preprocess frame for comparison."""
        if not self._cv2_available:
            return frame

        # Downscale heavily
        h, w = frame.shape[:2]
        small = self._cv2.resize(
            frame, (int(w * self.scale_factor), int(h * self.scale_factor))
        )

        # Convert to grayscale
        if len(small.shape) == 3:
            small = self._cv2.cvtColor(small, self._cv2.COLOR_BGR2GRAY)

        # Normalize to float [0,1]
        small = small.astype(np.float32) / 255.0

        return small

    def _region_activities(self, diff: np.ndarray) -> np.ndarray:
        """Mean absolute difference per cell of the uniform ROI grid.

        The frame is partitioned into REGION_GRID contiguous blocks; each
        block's mean of the absolute inter-frame difference (0-1 scale) is
        its activity. Returns a 1-D array of per-region activities.
        """
        rows, cols = self.REGION_GRID
        acts: list[float] = []
        for row_block in np.array_split(diff, rows, axis=0):
            for cell in np.array_split(row_block, cols, axis=1):
                acts.append(float(cell.mean()) if cell.size else 0.0)
        return np.asarray(acts, dtype=np.float64)

    def analyze(
        self,
        frame: np.ndarray,
        timestamp: datetime,
        stream_fps: float | None = None,
    ) -> FreezeResult:
        """Analyze a frame for freeze detection.

        Decision core (F4/F11 repair):
          1. Bit-exact short-circuit — pixel-identical consecutive frames are
             freeze evidence regardless of thresholds.
          2. Absolute activity test — median per-region mean absolute
             difference must be <= noise_floor. A live sensor always injects
             at least its native noise; a repeated/duplicated frame carries
             none (or only sub-floor re-encode dithering).
          3. ROI movement guard — even when the median is quiet, real motion
             in ANY region vetoes the verdict: (max region activity - median)
             must stay within the per-region noise spread (8 x MAD) or the
             absolute floor (4 x noise_floor). Uniform sensor noise does not
             veto; localized movement does.
          4. Persistence — the candidate condition must hold for
             `persistence_frames` consecutive analyzed frames.
        """
        if not self._cv2_available:
            return FreezeResult(
                frozen=False,
                confidence=0.0,
                similarity_score=0.0,
                reason="OpenCV not available",
            )

        processed = self._preprocess(frame)
        now = timestamp

        # Check minimum frame interval
        if self._prev_timestamp and (now - self._prev_timestamp) < self.min_frame_interval:
            # Too soon since last analysis
            return FreezeResult(
                frozen=False,
                confidence=0.0,
                similarity_score=0.0,
                reason="Frame interval too short",
            )

        if self._prev_frame is None:
            # First frame
            self._prev_frame = processed
            self._prev_timestamp = now
            return FreezeResult(
                frozen=False,
                confidence=0.0,
                similarity_score=0.0,
                reason="First frame",
            )

        # Shape change (resolution switch / decoder restart): state is not
        # comparable — reset comparison state instead of crashing.
        if processed.shape != self._prev_frame.shape:
            self._prev_frame = processed
            self._prev_timestamp = now
            self._consecutive_similar = 0
            self._freeze_start = None
            return FreezeResult(
                frozen=False,
                confidence=0.0,
                similarity_score=0.0,
                reason="Frame geometry changed",
            )

        # Absolute per-region temporal activity
        diff = np.abs(processed - self._prev_frame)
        bit_exact = bool(np.array_equal(processed, self._prev_frame))
        region_acts = self._region_activities(diff)
        activity = float(np.median(region_acts))
        mad = float(np.median(np.abs(region_acts - activity)))
        spread = float(region_acts.max() - activity)
        self._last_activity = activity

        # similarity_score retained for API/observability compat (1 - activity)
        similarity = 1.0 - min(activity, 1.0)

        # Update state
        self._prev_frame = processed
        self._prev_timestamp = now

        # Decision core
        spread_limit = max(self.movement_spread_factor * mad, 4.0 * self.noise_floor)
        candidate = bit_exact or (activity <= self.noise_floor and spread <= spread_limit)

        if candidate:
            self._consecutive_similar += 1

            if self._consecutive_similar == 1:
                self._freeze_start = now

            # Check persistence
            if self._consecutive_similar >= self.persistence_frames:
                freeze_duration = (now - self._freeze_start).total_seconds() if self._freeze_start else 0
                if bit_exact:
                    reason = (
                        f"Bit-exact repeated frames for {self._consecutive_similar} "
                        f"consecutive checks (encoder is repeating a frame)"
                    )
                else:
                    reason = (
                        f"Pixel activity {activity:.5f} <= noise floor {self.noise_floor:.5f} "
                        f"for {self._consecutive_similar} consecutive checks (repeated frame)"
                    )
                return FreezeResult(
                    frozen=True,
                    confidence=min(1.0, 1.0 - activity),
                    similarity_score=similarity,
                    freeze_duration_sec=freeze_duration,
                    reason=reason,
                )
            else:
                return FreezeResult(
                    frozen=False,
                    confidence=similarity,
                    similarity_score=similarity,
                    reason=f"Static content ({self._consecutive_similar}/{self.persistence_frames})",
                )
        else:
            # Reset on significant change or movement
            self._consecutive_similar = 0
            self._freeze_start = None
            if activity > self.noise_floor:
                reason = f"Frame content active (activity {activity:.5f} > floor {self.noise_floor:.5f})"
            else:
                reason = f"Localized movement detected in ROI grid (spread {spread:.5f} > {spread_limit:.5f})"
            return FreezeResult(
                frozen=False,
                confidence=1.0 - similarity,
                similarity_score=similarity,
                reason=reason,
            )

    def reset(self) -> None:
        """Reset detector state."""
        self._prev_frame = None
        self._prev_timestamp = None
        self._consecutive_similar = 0
        self._freeze_start = None
        self._last_activity = None

    def force_unfreeze(self) -> None:
        """Force unfreeze (e.g., after confirmed stream recovery)."""
        self._consecutive_similar = 0
        self._freeze_start = None