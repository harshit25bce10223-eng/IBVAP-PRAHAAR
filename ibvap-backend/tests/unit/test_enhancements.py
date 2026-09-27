# ─────────────────────────────────────────────────────────────────────────────
# IBVAP — Research-Backed Enhancement Unit Tests
# ─────────────────────────────────────────────────────────────────────────────
import pytest
from app.domain.geometry.calibration import (
    CalibrationMode,
    CalibrationQuality,
    CameraCalibration,
    apply_homography,
    get_uncalibrated,
    validate_homography_basic,
)
from app.domain.geometry.spatial_uncertainty import (
    GeometryConfidence,
    SpatialZone,
    classify_spatial_zone,
    compute_geometry_confidence,
)
from app.domain.fence.temporal_state import (
    MembershipState,
    TemporalMembership,
    TemporalTransitionResult,
    TrajectoryDirection,
    advance_temporal_state,
    estimate_trajectory,
)

SAMPLE_POLYGON = [
    {"x": 0.20, "y": 0.20},
    {"x": 0.80, "y": 0.20},
    {"x": 0.80, "y": 0.80},
    {"x": 0.20, "y": 0.80},
]


class TestCameraCalibration:
    def test_uncalibrated_returns_image_space(self):
        calib = get_uncalibrated("CAM-07")
        assert calib.calibration_mode == CalibrationMode.IMAGE_SPACE
        assert calib.calibration_quality == CalibrationQuality.INVALID
        assert not calib.enabled

    def test_apply_homography_uncalibrated_passthrough(self):
        calib = get_uncalibrated("CAM-07")
        pt = {"x": 0.5, "y": 0.5}
        transformed, quality = apply_homography(pt, calib)
        assert transformed == pt
        assert quality == CalibrationQuality.INVALID

    def test_apply_homography_identity(self):
        # 3x3 identity homography
        identity = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
        calib = CameraCalibration(
            camera_id="CAM-07",
            calibration_mode=CalibrationMode.GROUND_PLANE,
            homography_matrix=identity,
            calibration_quality=CalibrationQuality.HIGH,
            enabled=True,
        )
        pt = {"x": 0.35, "y": 0.65}
        transformed, quality = apply_homography(pt, calib)
        assert pytest.approx(transformed["x"]) == 0.35
        assert pytest.approx(transformed["y"]) == 0.65
        assert quality == CalibrationQuality.HIGH

    def test_validate_homography_basic_invalid(self):
        assert not validate_homography_basic([])
        assert not validate_homography_basic([1.0] * 8)
        assert not validate_homography_basic([0.0] * 9)  # singular/degenerate


class TestSpatialUncertainty:
    def test_clearly_inside(self):
        pt = {"x": 0.50, "y": 0.50}
        zone = classify_spatial_zone(pt, SAMPLE_POLYGON, uncertainty_margin=0.02)
        assert zone == SpatialZone.DEFINITELY_INSIDE

    def test_clearly_outside(self):
        pt = {"x": 0.05, "y": 0.05}
        zone = classify_spatial_zone(pt, SAMPLE_POLYGON, uncertainty_margin=0.02)
        assert zone == SpatialZone.DEFINITELY_OUTSIDE

    def test_boundary_uncertain_near_edge(self):
        # Point just inside or just outside the edge x=0.20
        pt_near_edge = {"x": 0.205, "y": 0.50}
        zone = classify_spatial_zone(pt_near_edge, SAMPLE_POLYGON, uncertainty_margin=0.02)
        assert zone == SpatialZone.BOUNDARY_UNCERTAIN

    def test_geometry_confidence_viewpoint_shift(self):
        conf = compute_geometry_confidence(
            viewpoint_shift_detected=True,
            calibration_quality=CalibrationQuality.HIGH,
            detection_confidence=0.95,
        )
        assert conf == GeometryConfidence.DEGRADED

    def test_geometry_confidence_stable(self):
        conf = compute_geometry_confidence(
            viewpoint_shift_detected=False,
            calibration_quality=CalibrationQuality.HIGH,
            detection_confidence=0.90,
        )
        assert conf == GeometryConfidence.HIGH


class TestTemporalStateAndTrajectory:
    def test_trajectory_approaching(self):
        # Track moving from x=0.10 toward zone at x=0.20
        path = [
            {"x": 0.05, "y": 0.50, "ts": "2026-09-07T00:00:00Z"},
            {"x": 0.10, "y": 0.50, "ts": "2026-09-07T00:00:01Z"},
        ]
        curr = {"x": 0.15, "y": 0.50}
        traj = estimate_trajectory(path, SAMPLE_POLYGON, curr)
        assert traj == TrajectoryDirection.APPROACHING_ZONE

    def test_trajectory_moving_away(self):
        # Track moving away from zone
        path = [
            {"x": 0.15, "y": 0.50, "ts": "2026-09-07T00:00:00Z"},
            {"x": 0.10, "y": 0.50, "ts": "2026-09-07T00:00:01Z"},
        ]
        curr = {"x": 0.05, "y": 0.50}
        traj = estimate_trajectory(path, SAMPLE_POLYGON, curr)
        assert traj == TrajectoryDirection.MOVING_AWAY

    def test_temporal_confirmation_single_frame_vs_hysteresis(self):
        mem = TemporalMembership(track_id="TRK-01", zone_id="ZONE-A")
        # Step 1: inside candidate 1 with confirmation threshold = 2
        res1 = advance_temporal_state(
            membership=mem,
            is_inside=True,
            spatial_uncertain=False,
            trajectory=TrajectoryDirection.INSIDE_ZONE,
            entry_confirmation_frames=2,
        )
        assert res1.new_state == MembershipState.CROSSING_CANDIDATE
        assert not res1.is_new_confirmed_entry

        # Step 2: inside candidate 2 -> confirmed intrusion!
        res2 = advance_temporal_state(
            membership=mem,
            is_inside=True,
            spatial_uncertain=False,
            trajectory=TrajectoryDirection.INSIDE_ZONE,
            entry_confirmation_frames=2,
        )
        assert res2.new_state == MembershipState.INTRUSION_CONFIRMED
        assert res2.is_new_confirmed_entry

        # Step 3: remaining inside -> DWELLING, no new entry!
        res3 = advance_temporal_state(
            membership=mem,
            is_inside=True,
            spatial_uncertain=False,
            trajectory=TrajectoryDirection.INSIDE_ZONE,
            entry_confirmation_frames=2,
        )
        assert res3.new_state == MembershipState.DWELLING
        assert not res3.is_new_confirmed_entry
