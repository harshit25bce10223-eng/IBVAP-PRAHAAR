# ─────────────────────────────────────────────────────────────────────────────
# IBVAP — Camera Calibration Abstraction
# ─────────────────────────────────────────────────────────────────────────────
# Research basis:
#   IEEE AVSS 2022: "Robust Camera Calibration with a Single Image by Planar
#   Homography" (DOI: 10.1109/AVSS56176.2022.9959461)
#   IET Smart Cities 2026: "Deep Learning-Driven Intrusion Prediction System
#   Using Ground-Plane Homography in Smart City Dynamic Zones"
#
# DESIGN INTENT:
#   - Calibration is OPTIONAL. Missing calibration → IMAGE_SPACE mode.
#   - Calibration quality is always explicit, never assumed HIGH.
#   - Never fabricate physical metric units without verified calibration.
#   - This abstraction allows future upgrade without changing Risk Engine.
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import math


class CalibrationMode(str, Enum):
    IMAGE_SPACE  = "IMAGE_SPACE"   # raw normalized image coordinates (default)
    GROUND_PLANE = "GROUND_PLANE"  # optional homography-mapped ground coordinates


class CalibrationQuality(str, Enum):
    HIGH    = "HIGH"
    MEDIUM  = "MEDIUM"
    LOW     = "LOW"
    INVALID = "INVALID"


@dataclass
class CameraCalibration:
    """
    Represents an optional camera calibration record.

    If homography_matrix is None or calibration_mode is IMAGE_SPACE,
    all coordinate transformations are identity and results remain in
    normalized image space.

    IMPORTANT: If calibration_quality is LOW or INVALID, do NOT use
    the transform for high-confidence intrusion decisions. Signal degraded
    geometry confidence downstream.
    """
    camera_id: str
    calibration_mode: CalibrationMode = CalibrationMode.IMAGE_SPACE
    # 3x3 homography matrix as flat list [h00, h01, h02, h10, h11, h12, h20, h21, h22]
    # None means no calibration available.
    homography_matrix: list[float] | None = None
    calibration_version: str = "uncalibrated"
    calibration_timestamp: str | None = None
    calibration_quality: CalibrationQuality = CalibrationQuality.INVALID
    reprojection_error: float | None = None  # pixels; lower is better
    enabled: bool = False  # must be explicitly opted in


# Default uncalibrated instance — always IMAGE_SPACE with INVALID quality
_UNCALIBRATED = CameraCalibration(
    camera_id="*",
    calibration_mode=CalibrationMode.IMAGE_SPACE,
    calibration_quality=CalibrationQuality.INVALID,
    enabled=False,
)


def get_uncalibrated(camera_id: str) -> CameraCalibration:
    return CameraCalibration(
        camera_id=camera_id,
        calibration_mode=CalibrationMode.IMAGE_SPACE,
        calibration_quality=CalibrationQuality.INVALID,
        enabled=False,
    )


def apply_homography(
    point: dict[str, float],
    calibration: CameraCalibration,
) -> tuple[dict[str, float], CalibrationQuality]:
    """
    Apply optional homography transform to a normalized image-space point.

    Returns:
        (transformed_point, effective_quality)

    If calibration is disabled, missing, or INVALID quality:
        - Returns the original point unchanged (IMAGE_SPACE passthrough)
        - Returns CalibrationQuality.INVALID to signal no transform occurred

    Never raises — safe for use in hot evaluation path.
    """
    if (
        not calibration.enabled
        or calibration.calibration_mode == CalibrationMode.IMAGE_SPACE
        or calibration.homography_matrix is None
        or calibration.calibration_quality == CalibrationQuality.INVALID
        or len(calibration.homography_matrix) != 9
    ):
        return point, CalibrationQuality.INVALID

    # Apply 3x3 projective homography: p' = H * p (homogeneous coordinates)
    H = calibration.homography_matrix
    x, y = point["x"], point["y"]
    w = H[6]*x + H[7]*y + H[8]
    if abs(w) < 1e-10:
        # Degenerate transform — fall back to image space
        return point, CalibrationQuality.INVALID

    gx = (H[0]*x + H[1]*y + H[2]) / w
    gy = (H[3]*x + H[4]*y + H[5]) / w

    return {"x": gx, "y": gy}, calibration.calibration_quality


def validate_homography_basic(matrix: list[float]) -> bool:
    """Minimal sanity check: matrix must be length-9, finite, and non-degenerate."""
    if not matrix or len(matrix) != 9:
        return False
    if any(not math.isfinite(v) for v in matrix):
        return False
    # Determinant of upper-left 2x2 as a rough degeneracy check
    det = matrix[0]*matrix[4] - matrix[1]*matrix[3]
    return abs(det) > 1e-10
