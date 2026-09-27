# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — Camera Image Quality Analysis
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np


@dataclass
class ImageQualityResult:
    sharpness: float | None = None          # Normalized 0-1
    brightness: float | None = None         # Normalized 0-1
    exposure: str | None = None             # "NORMAL" | "UNDEREXPOSED" | "OVEREXPOSED"
    contrast: float | None = None           # Normalized 0-1
    noise: float | None = None              # Normalized 0-1
    illumination_regime: str | None = None  # "DAY" | "LOW_LIGHT" | "NIGHT" | "IR"


class ImageQualityAnalyzer:
    """
    Deterministic no-reference image quality metrics.
    
    Based on established computer vision techniques:
    - Sharpness: Variance of Laplacian / Tenengrad
    - Brightness: Mean luminance
    - Exposure: Clipping/percentile analysis
    - Contrast: RMS contrast or Michelson contrast
    - Noise: Estimated from high-frequency residuals
    
    Research references:
    - "No-reference blurred image quality assessment based on structure of structure features" (Chen et al., 2023)
    - Classical no-reference IQA: Laplacian variance, Tenengrad, Brenner
    
    Normalization: Metrics are normalized to 0-1 range using camera-specific baselines
    where available, otherwise using empirical ranges.
    """

    def __init__(self):
        self._cv2_available = False
        try:
            import cv2
            self._cv2 = cv2
            self._cv2_available = True
        except ImportError:
            self._cv2 = None

    def _to_grayscale(self, frame: np.ndarray) -> np.ndarray:
        """Convert frame to grayscale float32 [0,1]."""
        if len(frame.shape) == 3:
            if frame.shape[2] == 3:
                gray = self._cv2.cvtColor(frame, self._cv2.COLOR_BGR2GRAY)
            elif frame.shape[2] == 4:
                gray = self._cv2.cvtColor(frame, self._cv2.COLOR_BGRA2GRAY)
            else:
                gray = frame[:, :, 0]
        else:
            gray = frame
        return gray.astype(np.float32) / 255.0

    def _ensure_cv2(self) -> bool:
        if not self._cv2_available:
            return False
        return True

    def analyze(self, frame: np.ndarray) -> ImageQualityResult:
        """Analyze image quality metrics from a frame."""
        if not self._cv2_available:
            return ImageQualityResult(
                sharpness=None,
                brightness=None,
                exposure="UNKNOWN",
                contrast=None,
                noise=None,
                illumination_regime="UNKNOWN",
            )

        # Convert to grayscale float [0,1]
        gray = self._to_grayscale(frame)

        # Sharpness: Variance of Laplacian (classic no-reference blur metric)
        sharpness = self._compute_sharpness(frame)

        # Brightness: Mean luminance
        brightness = float(np.mean(frame)) / 255.0 if len(frame.shape) == 2 else float(np.mean(frame)) / 255.0

        # Exposure: Clipping analysis
        exposure = self._compute_exposure(frame)

        # Contrast: RMS contrast
        contrast = self._compute_contrast(frame)

        # Noise: Estimated from high-frequency residuals
        noise = self._compute_noise(frame)

        # Illumination regime
        regime = self._determine_regime(brightness, sharpness)

        return ImageQualityResult(
            sharpness=self._normalize_sharpness(sharpness),
            brightness=brightness,
            exposure=exposure,
            contrast=self._normalize_contrast(contrast),
            noise=self._normalize_noise(noise),
            illumination_regime=regime,
        )

    def _compute_sharpness(self, frame: np.ndarray) -> float:
        """Compute sharpness using Variance of Laplacian."""
        if len(frame.shape) == 3:
            gray = self._cv2.cvtColor(frame, self._cv2.COLOR_BGR2GRAY)
        else:
            gray = frame

        laplacian = self._cv2.Laplacian(frame, self._cv2.CV_64F)
        return float(np.var(laplacian))

    def _normalize_sharpness(self, raw: float) -> float:
        """Normalize raw Laplacian variance to 0-1."""
        # Empirical ranges: sharp ~1000+, blurry ~<100
        # Using sigmoid-like normalization
        import math
        # Typical range: 0-3000 for 8-bit images
        normalized = 1 / (1 + math.exp(-(raw - 500) / 300))
        return max(0.0, min(1.0, normalized))

    def _compute_exposure(self, frame: np.ndarray) -> str:
        """Determine exposure status from histogram clipping."""
        if len(frame.shape) == 3:
            # Check each channel
            clipped_low = 0
            clipped_high = 0
            total = 0
            for c in range(3):
                channel = frame[:, :, c]
                low = np.sum(channel <= 2)
                high = np.sum(channel >= 253)
                clipped_low += low
                clipped_high += high
                total += channel.size

            low_ratio = clipped_low / total if total > 0 else 0
            high_ratio = clipped_high / total if total > 0 else 0

            if high_ratio > 0.01:  # >1% clipped highlights
                return "OVEREXPOSED"
            if low_ratio > 0.01:  # >1% clipped shadows
                return "UNDEREXPOSED"
        return "NORMAL"

    def _compute_contrast(self, frame: np.ndarray) -> float:
        """Compute RMS contrast."""
        if len(frame.shape) == 3:
            gray = self._cv2.cvtColor(frame, self._cv2.COLOR_BGR2GRAY)
        else:
            gray = frame

        gray_float = gray.astype(np.float32) / 255.0
        return float(np.std(gray_float))

    def _normalize_contrast(self, raw: float) -> float:
        """Normalize RMS contrast to 0-1."""
        # Typical RMS contrast range: 0.0-0.5 for natural images
        normalized = min(raw / 0.3, 1.0)
        return max(0.0, min(1.0, normalized))

    def _compute_noise(self, frame: np.ndarray) -> float:
        """Estimate noise from high-frequency residuals."""
        if len(frame.shape) == 3:
            gray = self._cv2.cvtColor(frame, self._cv2.COLOR_BGR2GRAY)
        else:
            gray = frame

        # Gaussian blur to get low-frequency component
        blurred = self._cv2.GaussianBlur(gray, (5, 5), 0)
        # High-frequency residual = noise
        residual = gray.astype(np.float32) - blurred.astype(np.float32)
        noise = float(np.std(residual))
        return noise

    def _normalize_noise(self, raw: float) -> float:
        """Normalize noise estimate to 0-1 (lower is better)."""
        # Typical noise: 0-20 for 8-bit
        # Normalize: 0 noise = 1.0 (best), high noise -> 0
        normalized = 1.0 - min(raw / 20.0, 1.0)
        return max(0.0, min(1.0, normalized))

    def _determine_regime(self, brightness: float, sharpness: float) -> str:
        """Determine illumination regime."""
        if brightness < 0.1:
            return "NIGHT"
        elif brightness < 0.25:
            return "LOW_LIGHT"
        elif brightness > 0.8 and sharpness > 0.7:
            return "DAY"
        elif brightness > 0.7:
            return "DAY"
        else:
            return "LOW_LIGHT"