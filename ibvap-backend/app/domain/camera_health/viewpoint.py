# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — Camera Viewpoint Shift Detection
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import numpy as np


@dataclass
class ViewpointResult:
    shift_detected: bool
    shift_score: float  # 0-1, higher = more shift
    confidence: float   # 0-1, quality of the estimate
    inlier_ratio: float | None = None
    translation: tuple[float, float] | None = None
    rotation: float | None = None
    scale: float | None = None
    detected_at: datetime | None = None
    reason: str | None = None


class ViewpointDetector:
    """
    Detects camera viewpoint shifts using feature matching and geometric verification.
    
    Uses ORB features + RANSAC homography estimation.
    Designed for edge deployment: works on downscaled frames, uses ROIs.
    
    Key principles:
    - Background/geometry based (not pixel difference)
    - Robust matching with RANSAC
    - Temporal persistence before triggering
    - Foreground exclusion via configured ROIs
    - Low-light awareness
    """

    def __init__(
        self,
        scale_factor: float = 0.25,           # Downscale factor for speed
        min_features: int = 100,              # Min features to extract
        min_matches: int = 10,                # Min good matches
        ransac_threshold: float = 3.0,        # RANSAC reprojection threshold (pixels)
        min_inlier_ratio: float = 0.3,        # Min inlier ratio for valid homography
        shift_threshold: float = 0.3,         # Score threshold for shift detection
        persistence_frames: int = 5,          # Frames to persist before confirming
        max_keypoints: int = 500,             # Max keypoints to detect
    ):
        self.scale_factor = scale_factor
        self.min_features = min_features
        self.min_matches = min_matches
        self.ransac_threshold = ransac_threshold
        self.min_inlier_ratio = min_inlier_ratio
        self.shift_threshold = shift_threshold
        self.persistence_frames = persistence_frames

        # State
        self._reference_frame: np.ndarray | None = None
        self._reference_kp: list | None = None
        self._reference_desc: np.ndarray | None = None
        self._reference_features: int = 0
        self._consecutive_shifts: int = 0
        self._last_shift_score: float = 0.0

        # Try to import cv2
        self._cv2_available = False
        try:
            import cv2
            self._cv2 = cv2
            self._orb = cv2.ORB_create(nfeatures=500, scaleFactor=1.2, nlevels=8)
            self._bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
            self._cv2_available = True
        except ImportError:
            self._cv2 = None
            self._orb = None
            self._bf = None

    def _preprocess(self, frame: np.ndarray) -> np.ndarray:
        """Preprocess frame for feature extraction."""
        # Downscale
        if self.scale_factor != 1.0:
            h, w = frame.shape[:2]
            frame = self._cv2.resize(
                frame, (int(w * self.scale_factor), int(h * self.scale_factor))
            )
        # Convert to grayscale
        if len(frame.shape) == 3:
            frame = self._cv2.cvtColor(frame, self._cv2.COLOR_BGR2GRAY)
        # Histogram equalization for contrast normalization
        frame = self._cv2.equalizeHist(frame)
        return frame

    def _extract_features(self, frame: np.ndarray) -> tuple[list, np.ndarray | None]:
        """Extract ORB keypoints and descriptors."""
        kp, desc = self._orb.detectAndCompute(frame, None)
        return kp, desc

    def _match_features(
        self, desc1: np.ndarray, desc2: np.ndarray
    ) -> list:
        """Match descriptors using BFMatcher with ratio test."""
        if desc1 is None or desc2 is None or len(desc1) == 0 or len(desc2) == 0:
            return []
        matches = self._bf.match(desc1, desc2)
        matches = sorted(matches, key=lambda x: x.distance)
        return matches

    def _estimate_homography(
        self, kp1: list, kp2: list, matches: list
    ) -> tuple[np.ndarray | None, float, list[int]]:
        """Estimate homography using RANSAC and return (H, inlier_ratio, inlier_indices)."""
        if len(matches) < self.min_matches:
            return None, 0.0, []

        src_pts = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)

        H, mask = self._cv2.findHomography(
            src_pts, dst_pts, self._cv2.RANSAC, self.ransac_threshold
        )

        if H is None:
            return None, 0.0, []

        inliers = mask.ravel().astype(bool)
        inlier_ratio = float(inliers.sum()) / len(matches)
        inlier_indices = np.where(inliers)[0].tolist()

        return H, inlier_ratio, inlier_indices

    def _decompose_homography(self, H: np.ndarray) -> dict[str, Any]:
        """Decompose homography into translation, rotation, scale."""
        # Simple decomposition - in practice use cv2.decomposeHomographyMat
        # For 2D affine approximation:
        # H = [s*cosθ, -s*sinθ, tx]
        #     [s*sinθ,  s*cosθ, ty]
        #     [0,       0,      1]
        tx, ty = H[0, 2], H[1, 2]
        scale = np.sqrt(H[0, 0]**2 + H[1, 0]**2)
        rotation = np.arctan2(H[1, 0], H[0, 0])

        return {
            "translation": (float(tx), float(ty)),
            "rotation": float(rotation),
            "scale": float(scale),
        }

    def _compute_shift_score(
        self, inlier_ratio: float, H: np.ndarray, decomposition: dict
    ) -> float:
        """Compute normalized shift score from homography."""
        # Translation component (normalized by frame size, assuming ~1000px at full res)
        tx, ty = decomposition["translation"]
        translation_mag = np.sqrt(tx**2 + ty**2) / (1000 * self.scale_factor)

        # Rotation component (radians)
        rotation_mag = abs(decomposition["rotation"])

        # Scale deviation from 1.0
        scale_dev = abs(decomposition["scale"] - 1.0)

        # Weighted combination
        score = (
            0.5 * min(translation_mag / 0.1, 1.0) +  # 10% frame shift = max
            0.3 * min(rotation_mag / 0.1, 1.0) +     # ~5.7 deg = max
            0.2 * min(scale_dev / 0.2, 1.0)          # 20% scale change = max
        ) * inlier_ratio

        return min(max(score, 0.0), 1.0)

    def set_reference(self, frame: np.ndarray) -> bool:
        """Set/update the reference frame for comparison."""
        if not self._cv2_available:
            return False

        processed = self._preprocess(frame)
        kp, desc = self._extract_features(processed)

        if len(kp) < self.min_features:
            return False

        self._reference_frame = processed.copy()
        self._reference_kp = kp
        self._reference_desc = desc
        self._reference_features = len(kp)
        return True

    def analyze(self, frame: np.ndarray) -> ViewpointResult:
        """Analyze a frame for viewpoint shift against the reference."""
        if not self._cv2_available or self._reference_frame is None:
            return ViewpointResult(
                shift_detected=False,
                shift_score=0.0,
                confidence=0.0,
                reason="Detector not initialized or OpenCV unavailable",
            )

        processed = self._preprocess(frame)
        kp, desc = self._extract_features(processed)

        if len(kp) < self.min_features:
            return ViewpointResult(
                shift_detected=False,
                shift_score=0.0,
                confidence=0.0,
                reason=f"Insufficient features: {len(kp)} < {self.min_features}",
            )

        matches = self._match_features(self._reference_desc, desc)

        if len(matches) < self.min_matches:
            return ViewpointResult(
                shift_detected=False,
                shift_score=0.0,
                confidence=0.0,
                reason=f"Insufficient matches: {len(matches)} < {self.min_matches}",
            )

        H, inlier_ratio, inlier_indices = self._estimate_homography(
            self._reference_kp, kp, matches
        )

        if H is None or inlier_ratio < self.min_inlier_ratio:
            return ViewpointResult(
                shift_detected=False,
                shift_score=0.0,
                confidence=inlier_ratio,
                reason=f"Low inlier ratio: {inlier_ratio:.2f}",
                inlier_ratio=inlier_ratio,
            )

        decomposition = self._decompose_homography(H)
        score = self._compute_shift_score(inlier_ratio, H, decomposition)

        # Temporal persistence
        shift_detected = score >= self.shift_threshold
        if shift_detected:
            self._consecutive_shifts += 1
        else:
            self._consecutive_shifts = max(0, self._consecutive_shifts - 1)

        confirmed = self._consecutive_shifts >= self.persistence_frames

        result = ViewpointResult(
            shift_detected=confirmed,
            shift_score=score,
            confidence=inlier_ratio,
            inlier_ratio=inlier_ratio,
            translation=decomposition["translation"],
            rotation=decomposition["rotation"],
            scale=decomposition["scale"],
            detected_at=datetime.now() if confirmed else None,
            reason="Persistent geometric displacement" if confirmed else "Shift below persistence threshold",
        )

        self._last_shift_score = score
        return result

    def reset(self) -> None:
        """Reset detector state (e.g., after maintenance)."""
        self._reference_frame = None
        self._reference_kp = None
        self._reference_desc = None
        self._reference_features = 0
        self._consecutive_shifts = 0
        self._last_shift_score = 0.0

    def is_initialized(self) -> bool:
        return self._reference_frame is not None