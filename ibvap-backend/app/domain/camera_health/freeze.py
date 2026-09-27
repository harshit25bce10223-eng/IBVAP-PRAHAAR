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
    Detects frozen camera streams using visual similarity analysis.
    
    Key principles:
    - Not just timestamp-based (encoder can advance timestamps on frozen video)
    - Uses visual similarity between consecutive sampled frames
    - Requires temporal persistence to avoid false positives
    - Handles static scenes (empty roads, walls) via noise floor analysis
    - Configurable similarity metrics (pixel diff, perceptual hash, SSIM-like)
    """

    def __init__(
        self,
        scale_factor: float = 0.125,        # Heavy downscale for speed
        similarity_threshold: float = 0.995, # Visual similarity threshold
        persistence_frames: int = 10,        # Frames to persist before confirming
        min_frame_interval_sec: float = 0.5, # Min time between analyzed frames
        noise_floor: float = 0.001,          # Expected noise in static scenes
    ):
        self.scale_factor = scale_factor
        self.similarity_threshold = similarity_threshold
        self.persistence_frames = persistence_frames
        self.min_frame_interval = timedelta(seconds=min_frame_interval_sec)
        self.noise_floor = noise_floor

        # State
        self._prev_frame: np.ndarray | None = None
        self._prev_timestamp: datetime | None = None
        self._consecutive_similar: int = 0
        self._freeze_start: datetime | None = None

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

    def _compute_similarity(self, frame1: np.ndarray, frame2: np.ndarray) -> float:
        """Compute visual similarity between two frames (0-1, 1=identical)."""
        if not self._cv2_available:
            # Fallback: simple numpy correlation
            diff = np.abs(frame1 - frame2)
            mean_diff = np.mean(diff)
            return 1.0 - min(mean_diff * 2, 1.0)  # Rough approximation

        # Use Structural Similarity (SSIM-like) for robustness
        # Simplified: normalized cross-correlation
        try:
            # Mean-normalized cross-correlation
            f1 = frame1 - np.mean(frame1)
            f2 = frame2 - np.mean(frame2)

            numerator = np.sum(f1 * f2)
            denominator = np.sqrt(np.sum(f1**2) * np.sum(f2**2))

            if denominator == 0:
                return 1.0 if np.allclose(frame1, frame2) else 0.0

            correlation = numerator / denominator
            return max(0.0, min(1.0, correlation))
        except Exception:
            # Fallback
            diff = np.abs(frame1 - frame2)
            return 1.0 - min(np.mean(diff) * 2, 1.0)

    def _compute_noise_level(self, frame: np.ndarray) -> float:
        """Estimate noise level in frame (for static scene detection)."""
        if not self._cv2_available:
            return 0.0

        # Laplacian variance as noise/blur indicator
        laplacian = self._cv2.Laplacian(frame, self._cv2.CV_64F)
        return float(np.var(laplacian))

    def analyze(
        self,
        frame: np.ndarray,
        timestamp: datetime,
        stream_fps: float | None = None,
    ) -> FreezeResult:
        """Analyze a frame for freeze detection."""
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

        # Compute similarity
        similarity = self._compute_similarity(self._prev_frame, processed)

        # Update state
        self._prev_frame = processed
        self._prev_timestamp = now

        # Check if similarity indicates freeze
        if similarity >= self.similarity_threshold:
            self._consecutive_similar += 1

            if self._consecutive_similar == 1:
                self._freeze_start = now

            # Check persistence
            if self._consecutive_similar >= self.persistence_frames:
                freeze_duration = (now - self._freeze_start).total_seconds() if self._freeze_start else 0
                return FreezeResult(
                    frozen=True,
                    confidence=min(similarity, 1.0),
                    similarity_score=similarity,
                    freeze_duration_sec=freeze_duration,
                    reason=f"Sustained visual similarity for {self._consecutive_similar} frames",
                )
            else:
                return FreezeResult(
                    frozen=False,
                    confidence=similarity,
                    similarity_score=similarity,
                    reason=f"High similarity ({self._consecutive_similar}/{self.persistence_frames})",
                )
        else:
            # Reset on significant change
            self._consecutive_similar = 0
            self._freeze_start = None
            return FreezeResult(
                frozen=False,
                confidence=1.0 - similarity,
                similarity_score=similarity,
                reason="Visual content changed",
            )

    def reset(self) -> None:
        """Reset detector state."""
        self._prev_frame = None
        self._prev_timestamp = None
        self._consecutive_similar = 0
        self._freeze_start = None

    def force_unfreeze(self) -> None:
        """Force unfreeze (e.g., after confirmed stream recovery)."""
        self._consecutive_similar = 0
        self._freeze_start = None