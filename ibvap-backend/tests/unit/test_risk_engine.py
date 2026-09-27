"""Risk engine scoring rules (exact numbers from the spec)."""
import pytest

from app.core.errors import InvalidConfidenceError, InvalidObjectTypeError
from app.domain.risk.risk_engine import calculate_risk
from app.domain.risk.severity import severity_for_score


def factors_of(result):
    return {f["code"]: f for f in result.factors}


class TestExactScoring:
    def test_human_vehicle_animal_crossing_points(self):
        # Restricted crossing alone (no night, no multi-cam, confidence 0.5 → +10, HIGH rel)
        human = calculate_risk(
            object_type="HUMAN", zone_crossed=True, is_night=False,
            multi_camera_confirmed=False, confidence=0.50, reliability="HIGH",
        )
        vehicle = calculate_risk(
            object_type="VEHICLE", zone_crossed=True, is_night=False,
            multi_camera_confirmed=False, confidence=0.50, reliability="HIGH",
        )
        animal = calculate_risk(
            object_type="ANIMAL", zone_crossed=True, is_night=False,
            multi_camera_confirmed=False, confidence=0.50, reliability="HIGH",
        )
        # 25 (crossing) + 15 (human) + 10 (conf) = 50
        assert human.risk_score == 50
        # 25 (crossing) + 10 (vehicle) + 10 (conf) = 45
        assert vehicle.risk_score == 45
        # 4 (animal crossing) + 0 (object) + 10 (conf) = 14
        assert animal.risk_score == 14
        assert factors_of(human)["RESTRICTED_ZONE_CROSSING"]["points"] == 25
        assert factors_of(animal)["RESTRICTED_ZONE_CROSSING"]["points"] == 4

    def test_night_time_adds_20(self):
        r = calculate_risk(
            object_type="HUMAN", zone_crossed=True, is_night=True,
            multi_camera_confirmed=False, confidence=0.5, reliability="HIGH",
        )
        # 25 + 20 + 15 + 10 = 70
        assert r.risk_score == 70
        assert factors_of(r)["NIGHT_TIME"]["points"] == 20

    def test_multi_camera_adds_15(self):
        r = calculate_risk(
            object_type="HUMAN", zone_crossed=True, is_night=False,
            multi_camera_confirmed=True, confidence=0.5, reliability="HIGH",
        )
        # 25 + 15 + 15 + 10 = 65
        assert r.risk_score == 65
        assert factors_of(r)["MULTI_CAMERA_CONFIRMATION"]["points"] == 15

    def test_confidence_mapping(self):
        for conf, expected in [(0.50, 10), (0.80, 16), (0.92, 18), (0.99, 20)]:
            r = calculate_risk(
                object_type="VEHICLE", zone_crossed=True, is_night=False,
                multi_camera_confirmed=False, confidence=conf, reliability="HIGH",
            )
            assert factors_of(r)["DETECTION_CONFIDENCE"]["points"] == expected

    def test_low_reliability_penalty(self):
        r = calculate_risk(
            object_type="HUMAN", zone_crossed=True, is_night=False,
            multi_camera_confirmed=False, confidence=0.5, reliability="LOW",
        )
        assert factors_of(r)["LOW_RELIABILITY"]["points"] == -15
        # 25 + 15 + 10 - 15 = 35
        assert r.risk_score == 35

    def test_low_reliability_factor_label(self):
        r = calculate_risk(
            object_type="HUMAN", zone_crossed=True, is_night=False,
            multi_camera_confirmed=False, confidence=0.5, reliability="LOW",
        )
        assert factors_of(r)["LOW_RELIABILITY"]["label"] == "Uncertainty penalty"

    def test_medium_reliability_no_penalty(self):
        r = calculate_risk(
            object_type="HUMAN", zone_crossed=True, is_night=False,
            multi_camera_confirmed=False, confidence=0.5, reliability="MEDIUM",
        )
        assert "LOW_RELIABILITY" not in factors_of(r)
        assert r.risk_score == 50


class TestBounds:
    def test_clamp_high(self):
        r = calculate_risk(
            object_type="HUMAN", zone_crossed=True, is_night=True,
            multi_camera_confirmed=True, confidence=1.0, reliability="HIGH",
        )
        # raw = 25 + 20 + 15 + 15 + 20 = 95 → still < 100; force higher via reasoning is impossible
        assert 0 <= r.risk_score <= 100

    def test_floor_low(self):
        r = calculate_risk(
            object_type="ANIMAL", zone_crossed=True, is_night=False,
            multi_camera_confirmed=False, confidence=0.0, reliability="LOW",
        )
        # 4 + 0 + 0 - 15 = -11 → clamped to 0
        assert r.risk_score == 0
        assert r.raw_score == -11

    def test_raw_and_final_exposed(self):
        r = calculate_risk(
            object_type="HUMAN", zone_crossed=True, is_night=True,
            multi_camera_confirmed=True, confidence=1.0, reliability="HIGH",
        )
        assert r.raw_score == 95
        assert r.risk_score == 95


class TestValidation:
    def test_reject_negative_confidence(self):
        with pytest.raises(InvalidConfidenceError):
            calculate_risk(
                object_type="HUMAN", zone_crossed=True, is_night=False,
                multi_camera_confirmed=False, confidence=-0.4, reliability="HIGH",
            )

    def test_reject_over_1(self):
        with pytest.raises(InvalidConfidenceError):
            calculate_risk(
                object_type="HUMAN", zone_crossed=True, is_night=False,
                multi_camera_confirmed=False, confidence=1.7, reliability="HIGH",
            )

    def test_reject_nan(self):
        with pytest.raises(InvalidConfidenceError):
            calculate_risk(
                object_type="HUMAN", zone_crossed=True, is_night=False,
                multi_camera_confirmed=False, confidence=float("nan"), reliability="HIGH",
            )

    def test_reject_inf(self):
        with pytest.raises(InvalidConfidenceError):
            calculate_risk(
                object_type="HUMAN", zone_crossed=True, is_night=False,
                multi_camera_confirmed=False, confidence=float("inf"), reliability="HIGH",
            )

    def test_reject_unknown_object_type(self):
        with pytest.raises(InvalidObjectTypeError) as exc:
            calculate_risk(
                object_type="DRONE", zone_crossed=True, is_night=False,
                multi_camera_confirmed=False, confidence=0.5, reliability="HIGH",
            )
        assert "HUMAN" in exc.value.message

    def test_case_insensitive_object_type(self):
        r = calculate_risk(
            object_type="human", zone_crossed=True, is_night=False,
            multi_camera_confirmed=False, confidence=0.5, reliability="HIGH",
        )
        assert r.risk_score == 50


class TestExplainability:
    def test_every_factor_structured(self):
        r = calculate_risk(
            object_type="HUMAN", zone_crossed=True, is_night=True,
            multi_camera_confirmed=True, confidence=0.92, reliability="LOW",
        )
        for f in r.factors:
            assert {"code", "label", "points", "evidence"} <= set(f)
            assert isinstance(f["code"], str)
            assert isinstance(f["label"], str)
            assert isinstance(f["points"], int)
            assert isinstance(f["evidence"], str)

    def test_sum_of_points_equals_raw(self):
        r = calculate_risk(
            object_type="HUMAN", zone_crossed=True, is_night=True,
            multi_camera_confirmed=True, confidence=0.92, reliability="HIGH",
        )
        assert sum(f["points"] for f in r.factors) == r.raw_score


class TestSeverityEngine:
    @pytest.mark.parametrize(
        "score,expected",
        [
            (0, "LOW"),
            (39, "LOW"),
            (40, "MEDIUM"),
            (64, "MEDIUM"),
            (65, "HIGH"),
            (84, "HIGH"),
            (85, "CRITICAL"),
            (100, "CRITICAL"),
        ],
    )
    def test_exact_boundaries(self, score, expected):
        assert severity_for_score(score) == expected