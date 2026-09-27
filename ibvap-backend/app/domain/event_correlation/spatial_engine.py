# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 4 — Spatial Relation Engine
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.core.config import settings


@dataclass
class SpatialEvent:
    event_id: str
    camera_id: str | None
    zone_id: str | None
    sector_id: str | None
    camera_location: tuple[float, float] | None = None  # (lat, lon)
    zone_polygon: list[tuple[float, float]] | None = None  # normalized [0,1] coords
    sector_polygon: list[tuple[float, float]] | None = None


@dataclass
class SpatialRelation:
    from_event_id: str
    to_event_id: str
    relation_type: str  # SAME_ZONE, SAME_SECTOR, ADJACENT_CAMERA, SAME_CAMERA, NEARBY
    confidence: int
    distance_meters: float | None = None
    evidence: dict | None = None


class SpatialRelationEngine:
    """
    Determines spatial relationships between events.
    
    Supports:
    - Same camera
    - Same zone
    - Same sector
    - Adjacent cameras (via topology)
    - Geographic distance (when GPS available)
    - Zone polygon containment
    """

    def __init__(
        self,
        default_spatial_window_meters: int = 100,
        camera_adjacency: dict[str, list[str]] | None = None,
        zone_polygons: dict[str, list[tuple[float, float]]] | None = None,
        sector_polygons: dict[str, list[tuple[float, float]]] | None = None,
    ):
        self.default_spatial_window = default_spatial_window_meters
        self.camera_adjacency = camera_adjacency or {}
        self.zone_polygons = zone_polygons or {}
        self.sector_polygons = sector_polygons or {}

    def _haversine_distance(self, lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Calculate distance in meters between two GPS coordinates."""
        from math import radians, sin, cos, sqrt, atan2
        R = 6371000  # Earth radius in meters
        
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlat/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        return R * c

    def _point_in_polygon(self, point: tuple[float, float], polygon: list[tuple[float, float]]) -> bool:
        """Ray casting algorithm for point in polygon test."""
        x, y = point
        inside = False
        n = len(polygon)
        j = n - 1
        for i in range(n):
            xi, yi = polygon[i]
            xj, yj = polygon[j]
            if ((yi > y) != (yj > y)) and (x < (xj - xi) * (y - yi) / (yj - yi) + xi):
                inside = not inside
            j = i
        return inside

    def _get_camera_location(self, camera_id: str) -> tuple[float, float] | None:
        """Get camera GPS coordinates if available."""
        # This would typically come from a camera registry
        # For now, return None - would be populated from camera registry
        return None

    def _get_zone_polygon(self, zone_id: str) -> list[tuple[float, float]] | None:
        """Get zone polygon if available."""
        return self.zone_polygons.get(zone_id)

    def _get_sector_polygon(self, sector_id: str) -> list[tuple[float, float]] | None:
        """Get sector polygon if available."""
        return self.sector_polygons.get(sector_id)

    def classify_relation(self, event_a: dict, event_b: dict) -> dict | None:
        """
        Classify the spatial relationship between two events.
        """
        # Same camera - strongest spatial relationship
        cam_a = event_a.get("camera_id")
        cam_b = event_b.get("camera_id")
        
        if cam_a and cam_b and cam_a == cam_b:
            return {
                "type": "SPATIAL",
                "subtype": "SAME_CAMERA",
                "confidence": 100,
                "evidence": {"camera_id": cam_a},
            }

        # Same zone
        zone_a = event_a.get("zone_id")
        zone_b = event_b.get("zone_id")
        
        if zone_a and zone_b and zone_a == zone_b:
            # Check if both events are actually inside the zone polygon
            if self._both_in_zone(event_a, event_b, zone_a):
                return {
                    "type": "SPATIAL",
                    "subtype": "SAME_ZONE",
                    "confidence": 90,
                    "evidence": {"zone_id": zone_a},
                }
            return {
                "type": "SPATIAL",
                "subtype": "SAME_ZONE",
                "confidence": 70,
                "evidence": {"zone_id": zone_a},
            }

        # Same sector
        sector_a = event_a.get("sector_id")
        sector_b = event_b.get("sector_id")
        
        if sector_a and sector_b and sector_a == sector_b:
            return {
                "type": "SPATIAL",
                "subtype": "SAME_SECTOR",
                "confidence": 60,
                "evidence": {"sector_id": sector_a},
            }

        # Adjacent cameras
        cam_a = event_a.get("camera_id")
        cam_b = event_b.get("camera_id")
        
        if cam_a and cam_b:
            adjacent = self.camera_adjacency.get(cam_a, [])
            if cam_b in adjacent:
                return {
                    "type": "SPATIAL",
                    "subtype": "ADJACENT_CAMERA",
                    "confidence": 60,
                    "evidence": {"camera_a": cam_a, "camera_b": cam_b},
                }
            
            adjacent = self.camera_adjacency.get(cam_b, [])
            if cam_a in adjacent:
                return {
                    "type": "SPATIAL",
                    "subtype": "ADJACENT_CAMERA",
                    "confidence": 60,
                    "evidence": {"camera_a": cam_a, "camera_b": cam_b},
                }

        # GPS distance if both have coordinates
        loc_a = event_a.get("location")
        loc_b = event_b.get("location")
        
        if loc_a and loc_b:
            lat1, lon1 = loc_a.get("lat"), loc_a.get("lon")
            lat2, lon2 = loc_b.get("lat"), loc_b.get("lon")
            
            if all(v is not None for v in [lat1, lon1, lat2, lon2]):
                from math import radians, sin, cos, sqrt, atan2
                
                lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
                dlat = lat2 - lat1
                dlon = lon2 - lon1
                
                a = sin((lat2 - lat1) / 2)**2 + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2)**2
                c = 2 * atan2(sqrt(a), sqrt(1 - a))
                distance = 6371000 * c  # meters
                
                if distance <= 50:  # 50 meters
                    return {
                        "type": "SPATIAL",
                        "subtype": "NEARBY",
                        "distance_meters": distance,
                        "confidence": max(0, 100 - int(distance / 50 * 100)),
                        "evidence": {"distance_meters": distance},
                    }
        
        return None

    def _both_in_zone(self, event_a: dict, event_b: dict, zone_id: str) -> bool:
        """Check if both events' locations fall within the zone polygon."""
        polygon = self._get_zone_polygon(zone_id)
        if not polygon:
            return True  # Assume true if no polygon defined
        
        loc_a = event_a.get("location")
        loc_b = event_b.get("location")
        
        if not loc_a or not loc_b:
            return True  # Can't verify, assume true
        
        point_a = (loc_a.get("lat"), loc_a.get("lon"))
        point_b = (loc_b.get("lat"), loc_b.get("lon"))
        
        if not all(v is not None for v in point_a + point_b):
            return True
        
        return self._point_in_polygon(point_a, polygon) and self._point_in_polygon(point_b, polygon)

    def find_candidates(
        self,
        target_event: dict,
        candidate_events: list[dict],
        max_distance_meters: int | None = None,
    ) -> list[dict]:
        """Find spatially related candidate events."""
        max_dist = max_distance_meters or self.default_spatial_window
        candidates = []
        
        for event in candidate_events:
            relation = self.classify_relation(target_event, event)
            if relation and relation.get("confidence", 0) > 0:
                relation["to_event_id"] = event.get("event_id")
                relation["from_event_id"] = target_event.get("event_id")
                candidates.append(relation)
        
        return sorted(candidates, key=lambda x: -x.get("confidence", 0))

    def get_camera_adjacency(self, camera_id: str) -> list[str]:
        """Get adjacent cameras for a given camera."""
        return self.camera_adjacency.get(camera_id, [])

    def set_camera_adjacency(self, camera_id: str, adjacent: list[str]) -> None:
        """Set camera adjacency manually."""
        self.camera_adjacency[camera_id] = adjacent

    def set_zone_polygon(self, zone_id: str, polygon: list[tuple[float, float]]) -> None:
        """Set zone polygon for spatial checks."""
        self.zone_polygons[zone_id] = polygon

    def set_sector_polygon(self, sector_id: str, polygon: list[tuple[float, float]]) -> None:
        """Set sector polygon for spatial checks."""
        self.sector_polygons[sector_id] = polygon


# Global instance
spatial_engine = SpatialRelationEngine()