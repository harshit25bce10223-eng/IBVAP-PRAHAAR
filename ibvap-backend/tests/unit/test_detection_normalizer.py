# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 5 — Detection Normalizer Tests
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

import pytest
from datetime import datetime, timezone

from app.domain.detection.normalizer import DetectionNormalizer, BBoxFormat


class TestDetectionNormalizer:
    """Tests for detection normalizer."""

    @pytest.fixture
    def normalizer(self):
        return DetectionNormalizer(
            taxonomy_version="1.0",
            schema_version="1.0",
            default_confidence_threshold=0.3,
            clip_bbox=True,
        )

    # ─── BBox Conversion ────────────────────────────────────────────────────

    def test_xyxy_pixels_to_normalized(self, normalizer):
        """Pixel xyxy → normalized xywh."""
        frame_w, frame_h = 1920, 1080
        bbox = [100.0, 200.0, 500.0, 600.0]  # xyxy pixels
        x, y, w, h = normalizer.normalize_bbox(bbox, BBoxFormat.XYXY, frame_w, frame_h)
        
        assert x == pytest.approx(100.0 / 1920.0)
        assert y == pytest.approx(200.0 / 1080.0)
        assert w == pytest.approx(400.0 / 1920.0)
        assert h == pytest.approx(400.0 / 1080.0)

    def test_xywh_pixels_to_normalized(self, normalizer):
        """Pixel xywh → normalized xywh."""
        frame_w, frame_h = 1280, 720
        bbox = [100.0, 150.0, 200.0, 300.0]  # xywh pixels
        x, y, w, h = normalizer.normalize_bbox(bbox, BBoxFormat.XYWH, frame_w, frame_h)
        
        assert x == pytest.approx(100.0 / 1280.0)
        assert y == pytest.approx(150.0 / 720.0)
        assert w == pytest.approx(200.0 / 1280.0)
        assert h == pytest.approx(300.0 / 720.0)

    def test_xyxy_norm_to_normalized(self, normalizer):
        """Normalized xyxy → normalized xywh."""
        bbox = [0.1, 0.2, 0.5, 0.6]  # normalized xyxy
        x, y, w, h = normalizer.normalize_bbox(bbox, BBoxFormat.XYXY_NORM)
        
        assert x == pytest.approx(0.1)
        assert y == pytest.approx(0.2)
        assert w == pytest.approx(0.4)
        assert h == pytest.approx(0.4)

    def test_xywh_norm_to_normalized(self, normalizer):
        """Normalized xywh → normalized xywh (passthrough)."""
        bbox = [0.1, 0.2, 0.3, 0.4]  # normalized xywh
        x, y, w, h = normalizer.normalize_bbox(bbox, BBoxFormat.XYWH_NORM)
        
        assert x == pytest.approx(0.1)
        assert y == pytest.approx(0.2)
        assert w == pytest.approx(0.3)
        assert h == pytest.approx(0.4)

    def test_different_resolutions(self, normalizer):
        """Different source resolutions produce correct normalized results."""
        # 1920x1080
        x1, y1, w1, h1 = normalizer.normalize_bbox(
            [100, 100, 200, 200], BBoxFormat.XYXY, 1920, 1080
        )
        # 1280x720 - same relative position
        x2, y2, w2, h2 = normalizer.normalize_bbox(
            [66.67, 66.67, 133.33, 133.33], BBoxFormat.XYXY, 1280, 720
        )
        assert x1 == pytest.approx(x2, rel=0.01)
        assert y1 == pytest.approx(y2, rel=0.01)

    def test_deterministic_conversion(self, normalizer):
        """Same input always produces same normalized output."""
        frame_w, frame_h = 1920, 1080
        bbox = [100.0, 200.0, 500.0, 600.0]
        
        for _ in range(10):
            x, y, w, h = normalizer.normalize_bbox(bbox, BBoxFormat.XYXY, frame_w, frame_h)
            assert x == pytest.approx(100.0 / 1920.0)
            assert y == pytest.approx(200.0 / 1080.0)
            assert w == pytest.approx(400.0 / 1920.0)
            assert h == pytest.approx(400.0 / 1080.0)

    # ─── BBox Validation ──────────────────────────────────────────────────

    def test_negative_x_rejected(self, normalizer):
        """Negative x is clipped or rejected."""
        with pytest.raises(ValueError):
            normalizer.normalize_bbox([-10.0, 100.0, 200.0, 200.0], BBoxFormat.XYXY, 1920, 1080)

    def test_negative_y_rejected(self, normalizer):
        """Negative y is clipped or rejected."""
        with pytest.raises(ValueError):
            normalizer.normalize_bbox([100.0, -50.0, 200.0, 200.0], BBoxFormat.XYXY, 1920, 1080)

    def test_width_exceeds_frame_rejected(self, normalizer):
        """Width > frame width is rejected."""
        with pytest.raises(ValueError):
            normalizer.normalize_bbox([100.0, 100.0, 2000.0, 200.0], BBoxFormat.XYXY, 1920, 1080)

    def test_height_exceeds_frame_rejected(self, normalizer):
        """Height > frame height is rejected."""
        with pytest.raises(ValueError):
            normalizer.normalize_bbox([100.0, 100.0, 200.0, 1200.0], BBoxFormat.XYXY, 1920, 1080)

    def test_nan_rejected(self, normalizer):
        """NaN values are rejected."""
        import math
        with pytest.raises(ValueError):
            normalizer.normalize_bbox([float('nan'), 100.0, 200.0, 200.0], BBoxFormat.XYXY, 1920, 1080)

    def test_infinity_rejected(self, normalizer):
        """Infinity values are rejected."""
        with pytest.raises(ValueError):
            normalizer.normalize_bbox([float('inf'), 100.0, 200.0, 200.0], BBoxFormat.XYXY, 1920, 1080)

    def test_negative_infinity_rejected(self, normalizer):
        """Negative infinity is rejected."""
        with pytest.raises(ValueError):
            normalizer.normalize_bbox([float('-inf'), 100.0, 200.0, 200.0], BBoxFormat.XYXY, 1920, 1080)

    # ─── Taxonomy Normalization ───────────────────────────────────────────

    def test_person_normalization(self, normalizer):
        """Various person labels map to PERSON."""
        for label in ["person", "human", "pedestrian", "people"]:
            canonical, provider = normalizer.normalize_class(label)
            assert canonical == "PERSON"
            assert provider == label

    def test_vehicle_normalization(self, normalizer):
        """Various vehicle labels map to VEHICLE."""
        for label in ["car", "truck", "bus", "motorcycle", "bicycle", "vehicle", "auto"]:
            canonical, provider = normalizer.normalize_class(label)
            assert canonical == "VEHICLE"
            assert provider == label

    def test_animal_normalization(self, normalizer):
        """Various animal labels map to ANIMAL."""
        for label in ["dog", "cat", "bird", "cow", "horse", "animal", "wildlife"]:
            canonical, provider = normalizer.normalize_class(label)
            assert canonical == "ANIMAL"
            assert provider == label

    def test_object_normalization(self, normalizer):
        """Various object labels map to OBJECT."""
        for label in ["package", "bag", "box", "object", "item"]:
            canonical, provider = normalizer.normalize_class(label)
            assert canonical == "OBJECT"
            assert provider == label

    def test_unknown_normalization(self, normalizer):
        """Unknown/unsupported labels map to UNKNOWN."""
        for label in ["unknown", "other", "unclassified", "foo", "bar"]:
            canonical, provider = normalizer.normalize_class(label)
            assert canonical == "UNKNOWN"
            assert provider == label

    def test_case_insensitive_normalization(self, normalizer):
        """Taxonomy normalization is case-insensitive."""
        canonical, _ = normalizer.normalize_class("PERSON")
        assert canonical == "PERSON"
        canonical, _ = normalizer.normalize_class("Person")
        assert canonical == "PERSON"
        canonical, _ = normalizer.normalize_class("person")
        assert canonical == "PERSON"

    def test_taxonomy_versioning(self, normalizer):
        """Taxonomy version is preserved."""
        assert normalizer.taxonomy_version == "1.0"

    # ─── Confidence Validation ────────────────────────────────────────────

    def test_confidence_zero_preserved(self, normalizer):
        """Confidence 0 is preserved."""
        assert normalizer.normalize_confidence(0.0) == 0.0

    def test_confidence_low_preserved(self, normalizer):
        """Low confidence is preserved."""
        assert normalizer.normalize_confidence(0.42) == 0.42

    def test_confidence_high_preserved(self, normalizer):
        """High confidence is preserved."""
        assert normalizer.normalize_confidence(0.94) == pytest.approx(0.94)

    def test_confidence_one_preserved(self, normalizer):
        """Confidence 1.0 is preserved."""
        assert normalizer.normalize_confidence(1.0) == 1.0

    def test_null_confidence_preserved(self, normalizer):
        """Null confidence remains null."""
        assert normalizer.normalize_confidence(None) is None

    def test_negative_confidence_rejected(self, normalizer):
        """Negative confidence is rejected."""
        with pytest.raises(ValueError):
            normalizer.normalize_confidence(-0.1)

    def test_over_one_confidence_rejected(self, normalizer):
        """Confidence > 1 is rejected."""
        with pytest.raises(ValueError):
            normalizer.normalize_confidence(1.1)

    def test_nan_confidence_rejected(self, normalizer):
        """NaN confidence is rejected."""
        import math
        with pytest.raises(ValueError):
            normalizer.normalize_confidence(float('nan'))

    def test_infinity_confidence_rejected(self, normalizer):
        """Infinity confidence is rejected."""
        with pytest.raises(ValueError):
            normalizer.normalize_confidence(float('inf'))

    # ─── Quality Normalization ────────────────────────────────────────────

    def test_good_quality_mappings(self, normalizer):
        """GOOD quality mappings."""
        for q in ["GOOD", "HIGH", "EXCELLENT", "CLEAR"]:
            assert normalizer.normalize_quality(q) == "GOOD"

    def test_limited_quality_mappings(self, normalizer):
        """LIMITED quality mappings."""
        for q in ["LIMITED", "MEDIUM", "FAIR", "PARTIAL"]:
            assert normalizer.normalize_quality(q) == "LIMITED"

    def test_poor_quality_mappings(self, normalizer):
        """POOR quality mappings."""
        for q in ["POOR", "LOW", "BAD", "UNCLEAR"]:
            assert normalizer.normalize_quality(q) == "POOR"

    def test_unknown_quality(self, normalizer):
        """Unknown quality defaults to UNKNOWN."""
        assert normalizer.normalize_quality("UNKNOWN") == "UNKNOWN"
        assert normalizer.normalize_quality(None) == "UNKNOWN"
        assert normalizer.normalize_quality("FOO") == "UNKNOWN"

    # ─── Occlusion Normalization ──────────────────────────────────────────

    def test_low_occlusion_mappings(self, normalizer):
        """Low occlusion mappings."""
        for o in ["LOW", "NONE", "MINIMAL", 0.0, 0.1]:
            assert normalizer.normalize_occlusion(o) == "LOW"

    def test_medium_occlusion_mappings(self, normalizer):
        """Medium occlusion mappings."""
        for o in ["MEDIUM", "MODERATE", "PARTIAL", 0.3, 0.5]:
            assert normalizer.normalize_occlusion(o) == "MEDIUM"

    def test_high_occlusion_mappings(self, normalizer):
        """High occlusion mappings."""
        for o in ["HIGH", "SEVERE", "HEAVY", 0.7, 0.9]:
            assert normalizer.normalize_occlusion(o) == "HIGH"

    def test_unknown_occlusion(self, normalizer):
        """Unknown occlusion defaults to UNKNOWN."""
        assert normalizer.normalize_occlusion(None) == "UNKNOWN"
        assert normalizer.normalize_occlusion("FOO") == "UNKNOWN"

    # ─── Detection State Normalization ────────────────────────────────────

    def test_detected_state(self, normalizer):
        """High confidence, good quality → DETECTED."""
        state = normalizer.normalize_state(
            confidence=0.9,
            quality="GOOD",
            occlusion="LOW",
        )
        assert state == "DETECTED"

    def test_low_confidence_state(self, normalizer):
        """Low confidence → LOW_CONFIDENCE."""
        state = normalizer.normalize_state(
            confidence=0.2,
            quality="GOOD",
            occlusion="LOW",
        )
        assert state == "LOW_CONFIDENCE"

    def test_null_confidence_state(self, normalizer):
        """Null confidence → UNKNOWN."""
        state = normalizer.normalize_state(
            confidence=None,
            quality="GOOD",
            occlusion="LOW",
        )
        assert state == "UNKNOWN"

    def test_poor_quality_state(self, normalizer):
        """Poor quality → LOW_CONFIDENCE."""
        state = normalizer.normalize_state(
            confidence=0.9,
            quality="POOR",
            occlusion="LOW",
        )
        assert state == "LOW_CONFIDENCE"

    def test_limited_quality_state(self, normalizer):
        """Limited quality → LOW_CONFIDENCE."""
        state = normalizer.normalize_state(
            confidence=0.9,
            quality="LIMITED",
            occlusion="LOW",
        )
        assert state == "LOW_CONFIDENCE"

    def test_high_occlusion_state(self, normalizer):
        """High occlusion → OCCLUDED."""
        state = normalizer.normalize_state(
            confidence=0.9,
            quality="GOOD",
            occlusion="HIGH",
        )
        assert state == "OCCLUDED"

    def test_medium_occlusion_state(self, normalizer):
        """Medium occlusion → OCCLUDED."""
        state = normalizer.normalize_state(
            confidence=0.9,
            quality="GOOD",
            occlusion="MEDIUM",
        )
        assert state == "OCCLUDED"

    # ─── Timestamp Normalization ──────────────────────────────────────────

    def test_iso_timestamp_preserved(self, normalizer):
        """ISO timestamps with Z are preserved."""
        ts = "2026-01-15T10:30:00Z"
        normalized = normalizer.normalize_timestamp(ts)
        assert normalized == "2026-01-15T10:30:00+00:00"

    def test_iso_timestamp_with_offset_preserved(self, normalizer):
        """ISO timestamps with offset are preserved."""
        ts = "2026-01-15T10:30:00+05:30"
        normalized = normalizer.normalize_timestamp(ts)
        assert normalized == "2026-01-15T10:30:00+05:30"

    def test_naive_timestamp_made_utc(self, normalizer):
        """Naive timestamps get UTC timezone."""
        ts = "2026-01-15T10:30:00"
        normalized = normalizer.normalize_timestamp(ts)
        assert normalized.endswith("+00:00")

    def test_none_timestamp_returns_now(self, normalizer):
        """None timestamp returns current UTC time."""
        before = datetime.now(timezone.utc)
        normalized = normalizer.normalize_timestamp(None)
        after = datetime.now(timezone.utc)
        parsed = datetime.fromisoformat(normalized.replace("Z", "+00:00"))
        assert before <= parsed <= after


class TestNormalizedDetectionDataclass:
    """Tests for NormalizedDetection dataclass."""

    def test_required_fields_only(self):
        """Required fields only."""
        from app.domain.detection.normalizer import NormalizedDetection
        
        det = NormalizedDetection(
            detection_id="DET-TEST",
            camera_id="CAM-01",
            class_name="PERSON",
            bbox_x=0.1,
            bbox_y=0.2,
            bbox_width=0.3,
            bbox_height=0.4,
            quality_state="GOOD",
            occlusion_state="LOW",
            detection_state="DETECTED",
            source="EDGE",
        )
        assert det.detection_id == "DET-TEST"
        assert det.camera_id == "CAM-01"
        assert det.class_name == "PERSON"
        assert det.confidence is None
        assert det.frame_id is None
        assert det.event_id is None

    def test_all_fields_populated(self):
        """All optional fields can be populated."""
        from app.domain.detection.normalizer import NormalizedDetection
        from datetime import datetime, timezone
        
        det = NormalizedDetection(
            detection_id="DET-TEST",
            camera_id="CAM-01",
            class_name="PERSON",
            bbox_x=0.1,
            bbox_y=0.2,
            bbox_width=0.3,
            bbox_height=0.4,
            quality_state="GOOD",
            occlusion_state="LOW",
            detection_state="DETECTED",
            frame_id="FRM-001",
            event_id="EVT-001",
            track_id="TRK-001",
            incident_id="INC-001",
            evidence_id="EVD-001",
            class_id=0,
            taxonomy_version="1.0",
            provider_class="person",
            confidence=0.95,
            frame_width=1920,
            frame_height=1080,
            provider="local_cpu",
            model_name="yolo-v8",
            model_version="1.0",
            runtime_version="onnx-1.15",
            device="cuda:0",
            inference_mode="single",
            postprocess_version="1.0",
            schema_version="1.0",
            region_profile="INDO_NEPAL_FOOTHILL_PLAINS",
            sector_id="SEC-01",
            camera_health_state="HEALTHY",
            camera_health_reliability="HIGH",
            camera_viewpoint_shift=False,
            camera_health_captured_at=datetime.now(timezone.utc).isoformat(),
            sync_state="LOCAL_ONLY",
            sync_payload_hash="abc123",
            edge_device_id="edge-01",
            source_event_id="SRC-EVT-001",
            source_sequence=1,
            observed_at="2026-01-15T10:30:00+00:00",
            received_at=datetime.now(timezone.utc).isoformat(),
            processed_at=datetime.now(timezone.utc).isoformat(),
            inference_latency_ms=45,
            queue_latency_ms=5,
            payload_json='{"demo": true}',
        )
        assert det.detection_id == "DET-TEST"
        assert det.track_id == "TRK-001"
        assert det.inference_latency_ms == 45


class TestNormalizerEdgeCases:
    """Edge cases for normalizer."""

    @pytest.fixture
    def normalizer(self):
        return DetectionNormalizer()

    def test_empty_class_name(self, normalizer):
        """Empty class name becomes UNKNOWN."""
        canonical, provider = normalizer.normalize_class("")
        assert canonical == "UNKNOWN"

    def test_whitespace_class(self, normalizer):
        """Whitespace-only class becomes UNKNOWN."""
        canonical, provider = normalizer.normalize_class("   ")
        assert canonical == "UNKNOWN"

    def test_special_chars_class(self, normalizer):
        """Special characters in class become UNKNOWN."""
        canonical, provider = normalizer.normalize_class("person@#$")
        assert canonical == "UNKNOWN"

    def test_confidence_rounding(self, normalizer):
        """Confidence is rounded to 4 decimal places."""
        assert normalizer.normalize_confidence(0.123456789) == 0.1235
        assert normalizer.normalize_confidence(0.123444444) == 0.1234

    def test_clip_bbox_disabled(self):
        """clip_bbox=False preserves out-of-bounds values."""
        normalizer = DetectionNormalizer(clip_bbox=False)
        # This would fail with clip_bbox=True
        x, y, w, h = normalizer.normalize_bbox(
            [-0.1, -0.1, 1.2, 1.2], BBoxFormat.XYXY_NORM
        )
        assert x == -0.1
        assert y == -0.1
        assert w == 1.3  # 1.2 - (-0.1) = 1.3
        assert h == 1.3  # 1.2 - (-0.1) = 1.3


# ─── Helper for running tests ────────────────────────────────────────────
if __name__ == "__main__":
    pytest.main([__file__, "-v"])