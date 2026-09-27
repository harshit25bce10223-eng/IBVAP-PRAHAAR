"""Ray-casting geometry: point-in-polygon, representative points, validation."""
import pytest

from app.core.errors import ZoneGeometryError
from app.domain.fence.membership import polygon_area, validate_polygon
from app.domain.geometry.bbox import get_bbox_center, get_representative_point, is_bbox_inside_zone
from app.domain.geometry.point_in_polygon import check_point_in_polygon

# Square polygon (normalized)
SQUARE = [
    {"x": 0.2, "y": 0.2},
    {"x": 0.8, "y": 0.2},
    {"x": 0.8, "y": 0.8},
    {"x": 0.2, "y": 0.8},
]


class TestPointInPolygon:
    def test_center_inside(self):
        assert check_point_in_polygon({"x": 0.5, "y": 0.5}, SQUARE) is True

    def test_outside_left(self):
        assert check_point_in_polygon({"x": 0.1, "y": 0.5}, SQUARE) is False

    def test_outside_above(self):
        assert check_point_in_polygon({"x": 0.5, "y": 0.1}, SQUARE) is False

    def test_outside_far(self):
        assert check_point_in_polygon({"x": 0.5, "y": 0.99}, SQUARE) is False

    def test_boundary_inclusive(self):
        # Boundary contact is INSIDE under the documented BOUNDARY_POLICY.
        assert check_point_in_polygon({"x": 0.2, "y": 0.5}, SQUARE) is True
        assert check_point_in_polygon({"x": 0.5, "y": 0.2}, SQUARE) is True
        assert check_point_in_polygon({"x": 0.8, "y": 0.5}, SQUARE) is True
        assert check_point_in_polygon({"x": 0.5, "y": 0.8}, SQUARE) is True

    def test_vertex_inclusive(self):
        assert check_point_in_polygon({"x": 0.2, "y": 0.2}, SQUARE) is True
        assert check_point_in_polygon({"x": 0.8, "y": 0.8}, SQUARE) is True

    def test_concave_polygon(self):
        concave = [
            {"x": 0.1, "y": 0.1},
            {"x": 0.9, "y": 0.1},
            {"x": 0.9, "y": 0.9},
            {"x": 0.5, "y": 0.4},
            {"x": 0.1, "y": 0.9},
        ]
        # Notch region (0.5, 0.9) is outside the concave shape.
        assert check_point_in_polygon({"x": 0.5, "y": 0.9}, concave) is False
        # Inside lobe (0.5, 0.2).
        assert check_point_in_polygon({"x": 0.5, "y": 0.2}, concave) is True

    def test_triangle(self):
        tri = [{"x": 0.0, "y": 0.0}, {"x": 1.0, "y": 0.0}, {"x": 0.0, "y": 1.0}]
        assert check_point_in_polygon({"x": 0.1, "y": 0.1}, tri) is True
        assert check_point_in_polygon({"x": 0.6, "y": 0.6}, tri) is False

    def test_polygon_not_closed_explicitly(self):
        # Even-odd parity assumes the ring is implicitly closed by the last point.
        pts = [{"x": 0.0, "y": 0.0}, {"x": 1.0, "y": 0.0}, {"x": 1.0, "y": 1.0}, {"x": 0.0, "y": 1.0}]
        assert check_point_in_polygon({"x": 0.3, "y": 0.7}, pts) is True


class TestBBox:
    def test_center(self):
        c = get_bbox_center({"x": 0.2, "y": 0.2, "width": 0.4, "height": 0.2})
        assert c == {"x": 0.4, "y": 0.3}

    def test_representative_bottom_center_default(self):
        r = get_representative_point({"x": 0.4, "y": 0.35, "width": 0.08, "height": 0.25})
        assert r == {
            "x": 0.44,
            "y": 0.60,
        }  # bottom-center: x + w/2, y + h

    def test_representative_center(self):
        r = get_representative_point(
            {"x": 0.4, "y": 0.35, "width": 0.08, "height": 0.25}, strategy="center"
        )
        assert r["x"] == 0.44 and r["y"] == 0.475

    def test_representative_bottom_left(self):
        r = get_representative_point(
            {"x": 0.4, "y": 0.35, "width": 0.08, "height": 0.25}, strategy="bottom_left"
        )
        assert r == {"x": 0.4, "y": 0.60}

    def test_representative_bottom_right(self):
        r = get_representative_point(
            {"x": 0.4, "y": 0.35, "width": 0.08, "height": 0.25}, strategy="bottom_right"
        )
        assert r == {"x": 0.48, "y": 0.60}

    def test_bbox_inside_zone(self):
        # bottom bar of bbox is (0.44, 0.60) — inside the square polygon.
        assert is_bbox_inside_zone({"x": 0.4, "y": 0.35, "width": 0.08, "height": 0.25}, SQUARE)

    def test_bbox_outside_zone_via_ground(self):
        # bottom-center lands on y=0.9 → outside.
        assert not is_bbox_inside_zone({"x": 0.4, "y": 0.65, "width": 0.08, "height": 0.25}, SQUARE)


class TestPolygonValidation:
    def test_valid(self):
        validate_polygon(SQUARE)
        assert polygon_area(SQUARE) == pytest.approx(0.36)

    def test_min_points(self):
        with pytest.raises(ZoneGeometryError) as exc:
            validate_polygon([{"x": 0.1, "y": 0.1}, {"x": 0.9, "y": 0.9}])
        assert "at least 3" in exc.value.message

    def test_max_points(self):
        big = [{"x": 0.001 * i, "y": 0.001 * i} for i in range(101)]
        with pytest.raises(ZoneGeometryError):
            validate_polygon(big)

    def test_non_numeric(self):
        with pytest.raises(ZoneGeometryError):
            validate_polygon([{"x": "a", "y": 0.1}, {"x": 0.5, "y": 0.5}, {"x": 0.9, "y": 0.1}])

    def test_missing_key(self):
        with pytest.raises(ZoneGeometryError):
            validate_polygon([{"x": 0.1}, {"x": 0.5, "y": 0.5}, {"x": 0.9, "y": 0.1}])

    def test_range_x(self):
        with pytest.raises(ZoneGeometryError) as exc:
            validate_polygon([{"x": 1.5, "y": 0.1}, {"x": 0.5, "y": 0.5}, {"x": 0.9, "y": 0.1}])
        assert "range" in exc.value.message

    def test_range_y_negative(self):
        with pytest.raises(ZoneGeometryError):
            validate_polygon([{"x": 0.1, "y": -0.2}, {"x": 0.5, "y": 0.5}, {"x": 0.9, "y": 0.1}])

    def test_degenerate_zero_area(self):
        # All points collinear on y=0.4
        with pytest.raises(ZoneGeometryError) as exc:
            validate_polygon(
                [
                    {"x": 0.1, "y": 0.4},
                    {"x": 0.5, "y": 0.4},
                    {"x": 0.9, "y": 0.4},
                ]
            )
        assert "degenerate" in exc.value.message

    def test_self_intersecting(self):
        # Asymmetric bowtie: non-zero shoelace area so the self-intersection
        # guard (not the zero-area guard) must reject it.
        bowtie = [
            {"x": 0.2, "y": 0.2},
            {"x": 0.8, "y": 0.6},
            {"x": 0.8, "y": 0.2},
            {"x": 0.2, "y": 0.8},
        ]
        assert polygon_area(bowtie) > 0
        with pytest.raises(ZoneGeometryError) as exc:
            validate_polygon(bowtie)
        assert "self-intersecting" in exc.value.message

    def test_repeated_vertex_zero_area(self):
        twice = [{"x": 0.1, "y": 0.1}, {"x": 0.1, "y": 0.1}, {"x": 0.9, "y": 0.9}]
        with pytest.raises(ZoneGeometryError):
            validate_polygon(twice)


class TestBoundaryPolicy:
    def test_policy_is_inclusive(self):
        from app.domain.geometry.point_in_polygon import BOUNDARY_POLICY

        assert BOUNDARY_POLICY == "INCLUSIVE"