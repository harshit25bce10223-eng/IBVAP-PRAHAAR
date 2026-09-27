"""Active-time-window evaluation including midnight-crossing behavior."""
from datetime import datetime, timezone

import pytest

from app.domain.fence.fence_service import is_active_time_window, object_allowed

WINDOW = {"active_start": "18:00", "active_end": "06:00"}


def at(hh: int, mm: int) -> datetime:
    return datetime(2026, 9, 7, hh, mm, tzinfo=timezone.utc)


class TestMidnightWindow:
    # 18:00 -> 06:00 must cover the two intervals 18:00–23:59 and 00:00–06:00.
    @pytest.mark.parametrize(
        ("time_", "expected"),
        [
            (at(17, 59), False),
            (at(18, 0), True),
            (at(23, 59), True),
            (at(0, 0), True),
            (at(6, 0), True),
            (at(6, 1), False),
        ],
    )
    def test_spec_boundaries(self, time_, expected):
        assert is_active_time_window(WINDOW, time_) is expected

    def test_inclusive_endpoints_documented(self):
        assert is_active_time_window({"active_start": "09:00", "active_end": "17:00"}, at(9, 0)) is True
        assert is_active_time_window({"active_start": "09:00", "active_end": "17:00"}, at(17, 0)) is True
        assert is_active_time_window({"active_start": "09:00", "active_end": "17:00"}, at(8, 59)) is False
        assert is_active_time_window({"active_start": "09:00", "active_end": "17:00"}, at(17, 1)) is False

    def test_no_window_always_active(self):
        assert is_active_time_window({}, at(12, 0)) is True
        assert is_active_time_window({"dwell_time_seconds": 10}, at(3, 0)) is True

    def test_malformed_window_inactive(self):
        assert is_active_time_window({"active_start": "oops", "active_end": "06:00"}, at(1, 0)) is False

    def test_deterministic_timezone(self):
        # A fixed UTC instant must produce the same answer regardless of server local time.
        instant = datetime(2026, 9, 7, 22, 30, tzinfo=timezone.utc)
        assert is_active_time_window(WINDOW, instant) is True


class TestObjectAllowed:
    def test_allow_vehicle(self):
        rules = {"allowed_object_types": ["VEHICLE"], **WINDOW}
        assert object_allowed(rules, "VEHICLE", at(22, 0)) is True

    def test_deny_human(self):
        rules = {"allowed_object_types": ["VEHICLE"], **WINDOW}
        assert object_allowed(rules, "HUMAN", at(22, 0)) is False

    def test_deny_when_outside_window(self):
        rules = {"allowed_object_types": ["VEHICLE"], **WINDOW}
        assert object_allowed(rules, "VEHICLE", at(12, 0)) is False

    def test_unrestricted_rules(self):
        assert object_allowed({}, "ANIMAL", at(12, 0)) is True

    def test_case_insensitive(self):
        rules = {"allowed_object_types": ["vehicle"]}
        assert object_allowed(rules, "VEHICLE", at(12, 0)) is True