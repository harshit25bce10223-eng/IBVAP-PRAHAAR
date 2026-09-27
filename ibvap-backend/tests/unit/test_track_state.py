"""Track membership state machine: transitions and dedup-key generation."""
import pytest

from app.domain.tracking.track_state import (
    append_position,
    dedup_key,
    membership_transition,
    parse_membership,
    parse_path,
)


class TestTransitions:
    @pytest.mark.parametrize(
        ("prev", "cur", "expected"),
        [
            (None, True, "FIRST"),
            (None, False, "FIRST"),
            (False, True, "ENTRY"),
            (True, False, "EXIT"),
            (True, True, "STABLE_INSIDE"),
            (False, False, "STABLE_OUTSIDE"),
        ],
    )
    def test_all_transitions(self, prev, cur, expected):
        assert membership_transition(prev, cur) == expected


class TestDedupKey:
    def test_entry_key_shape(self):
        key = dedup_key("CAM-07", "TRK-1042", "ZONE-B", "ENTRY", generation=0)
        assert key == "CAM-07|TRK-1042|ZONE-B|ENTRY|0"

    def test_generation_increments(self):
        k0 = dedup_key("CAM-07", "TRK-1042", "ZONE-B", "ENTRY", generation=0)
        k1 = dedup_key("CAM-07", "TRK-1042", "ZONE-B", "ENTRY", generation=1)
        assert k0 != k1  # re-entry must produce a distinct incident

    def test_exit_key(self):
        key = dedup_key("CAM-07", "TRK-1042", "ZONE-B", "EXIT", generation=0)
        assert key == "CAM-07|TRK-1042|ZONE-B|EXIT|0"


class TestPath:
    def test_append_bounded(self):
        from app.core.config import settings

        path = []
        for i in range(settings.TRACK_PATH_MAX_POSITIONS + 25):
            path = append_position(path, {"x": 0.1, "y": 0.2, "ts": str(i)})
        assert len(path) == settings.TRACK_PATH_MAX_POSITIONS
        assert path[0]["ts"] == "25"  # oldest dropped

    def test_append_none(self):
        assert append_position(None, {"x": 0.1, "y": 0.2, "ts": "t0"}) == [
            {"x": 0.1, "y": 0.2, "ts": "t0"}
        ]

    def test_append_copies(self):
        original = [{"x": 0.1, "y": 0.2, "ts": "t0"}]
        mutated = append_position(original, {"x": 0.3, "y": 0.4, "ts": "t1"})
        original.append({"x": 0.9, "y": 0.9, "ts": "t99"})
        assert len(mutated) == 2
        assert mutated[-1]["ts"] == "t1"


class TestSerialization:
    def test_parse_membership(self):
        assert parse_membership('{"ZONE-B": true}') == {"ZONE-B": True}
        assert parse_membership("") == {}
        assert parse_membership("not-json") == {}
        assert parse_membership(None) == {}

    def test_parse_path(self):
        p = parse_path('[{"x": 0.1, "y": 0.2, "ts": "t0"}, {"bad": 1}]')
        assert len(p) == 1
        assert p[0]["x"] == 0.1