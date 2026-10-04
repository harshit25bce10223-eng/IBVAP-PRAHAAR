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
    
    Uses ORB features + Lowe ratio test + RANSAC similarity estimation.
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
        scale_factor: float = 1.0,            # Downscale factor for speed
        min_features: int = 30,               # Min features to extract
        min_matches: int = 10,                # Min good matches
        ransac_threshold: float = 3.0,        # RANSAC reprojection threshold (pixels)
        min_inlier_ratio: float = 0.3,        # Min inlier ratio for valid transform
        shift_threshold: float = 0.3,         # Score threshold for shift detection
        persistence_frames: int = 5,          # Frames to persist before confirming
        max_keypoints: int = 500,             # Max keypoints to detect
        ratio_test: float = 0.75,             # Lowe ratio test threshold
    ):
        # F5 calibration (measured on the reopen corpus, see
        # C2_CAMERA_HEALTH_REPAIR_REPORT.md): scale_factor=1.0 + ratio test +
        # similarity RANSAC gives 100% reference init, 13/15 VIEWPOINT_CHANGED
        # detections and 0/24 ONLINE false shifts at p95 ~25 ms. The previous
        # defaults (0.25 / 100) starved ORB at 320x180 (0% reference init).
        self.scale_factor = scale_factor
        self.min_features = min_features
        self.min_matches = min_matches
        self.ransac_threshold = ransac_threshold
        self.min_inlier_ratio = min_inlier_ratio
        self.shift_threshold = shift_threshold
        self.persistence_frames = persistence_frames
        self.ratio_test = ratio_test
        self._last_frame_width: int | None = None

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
            # crossCheck must be False for knnMatch (Lowe ratio test below)
            self._bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)
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
        # Record analyzed frame width for resolution-independent scoring
        self._last_frame_width = frame.shape[1]
        return frame

    def _extract_features(self, frame: np.ndarray) -> tuple[list, np.ndarray | None]:
        """Extract ORB keypoints and descriptors."""
        kp, desc = self._orb.detectAndCompute(frame, None)
        return kp, desc

    def _match_features(
        self, desc1: np.ndarray, desc2: np.ndarray
    ) -> list:
        """Match descriptors using BFMatcher + Lowe ratio test.

        The ratio test (k=2 KNN, keep when d1 < ratio * d2) is required on
        repetitive texture (fence posts, poles): crossCheck alone admits
        ambiguous matches that RANSAC then fits with wrong geometry. Measured
        effect on the reopen corpus: VIEWPOINT_CHANGED detections 4/15 -> 13/15
        with ONLINE false shifts unchanged at 0/24.
        """
        if desc1 is None or desc2 is None or len(desc1) < 2 or len(desc2) < 2:
            return []
        good = []
        for pair in self._bf.knnMatch(desc1, desc2, k=2):
            if len(pair) == 2:
                m, n = pair
                if m.distance < self.ratio_test * n.distance:
                    good.append(m)
        good = sorted(good, key=lambda x: x.distance)
        return good

    def _estimate_homography(
        self, kp1: list, kp2: list, matches: list
    ) -> tuple[np.ndarray | None, float, list[int]]:
        """Estimate the camera displacement with RANSAC.

        Fits a 4-DOF similarity (rotation, uniform scale, translation) via
        cv2.estimateAffinePartial2D. This is the model _decompose_homography
        actually reads back (tx, ty, angle, scale); the previous 8-DOF
        findHomography estimation was inconsistent with that decomposition
        and over-fitted noise on low-texture feeds.

        Returns (3x3 transform, inlier_ratio, inlier_indices).
        """
        if len(matches) < self.min_matches:
            return None, 0.0, []

        src_pts = np.float32([kp1[m.queryIdx].pt for m in matches]).reshape(-1, 1, 2)
        dst_pts = np.float32([kp2[m.trainIdx].pt for m in matches]).reshape(-1, 1, 2)

        M, mask = self._cv2.estimateAffinePartial2D(
            src_pts,
            dst_pts,
            method=self._cv2.RANSAC,
            ransacReprojThreshold=self.ransac_threshold,
            maxIters=2000,
            confidence=0.99,
        )

        if M is None or mask is None:
            return None, 0.0, []

        H = np.vstack([M, [0.0, 0.0, 1.0]])
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
        """Compute normalized shift score from the estimated transform.

        Translation is normalized by the ANALYZED FRAME WIDTH (previously a
        hardcoded "1000 px full res" constant, which deflated real shifts on
        small frames: a 50%-of-width shift scored as 0.16 of the translation
        term). The score is now resolution-independent by construction:
        the same physical displacement yields the same score at any frame
        size or downscale factor.
        """
        # Translation magnitude as a fraction of frame width
        tx, ty = decomposition["translation"]
        frame_w = self._last_frame_width or 1
        translation_mag = np.sqrt(tx**2 + ty**2) / float(frame_w)

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
        self._last_frame_width = None

    @property
    def reference_feature_count(self) -> int:
        """Feature count of the active reference frame (0 when uninitialized).

        Exposed for the F5 reference lifecycle: the analyzer records how many
        features the accepted reference carried, so provisioning quality is
        observable downstream.
        """
        return self._reference_features

    def is_initialized(self) -> bool:
        return self._reference_frame is not None