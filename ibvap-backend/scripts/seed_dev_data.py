import asyncio
import json
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from app.db.database import SessionLocal, Base, engine
from app.models.zone import Zone
from app.models.camera_health import (
    CameraHealthConfig,
    CameraHealthCurrent,
    CameraHealthEvent,
    CameraHealthBaseline,
    IlluminationRegime,
)

ZONES_SEED = [
    {
        "zone_id": "ZONE-A",
        "camera_id": "CAM-07",
        "name": "North Perimeter Buffer Zone",
        "polygon_json": json.dumps([
            {"x": 0.10, "y": 0.20},
            {"x": 0.60, "y": 0.18},
            {"x": 0.65, "y": 0.70},
            {"x": 0.12, "y": 0.72}
        ]),
        "rules_json": json.dumps({
            "allowed_object_types": ["HUMAN", "VEHICLE", "ANIMAL"],
            "active_start": None,
            "active_end": None,
            "dwell_time_seconds": 0
        }),
        "active": True
    },
    {
        "zone_id": "ZONE-B",
        "camera_id": "CAM-07",
        "name": "Zero-Tolerance Restricted Line",
        "polygon_json": json.dumps([
            {"x": 0.55, "y": 0.25},
            {"x": 0.90, "y": 0.22},
            {"x": 0.92, "y": 0.75},
            {"x": 0.58, "y": 0.78}
        ]),
        "rules_json": json.dumps({
            "allowed_object_types": ["HUMAN", "VEHICLE"],
            "active_start": "18:00",
            "active_end": "06:00",
            "dwell_time_seconds": 5
        }),
        "active": True
    },
    {
        "zone_id": "ZONE-C",
        "camera_id": "CAM-08",
        "name": "East Outpost Approach Fence",
        "polygon_json": json.dumps([
            {"x": 0.15, "y": 0.30},
            {"x": 0.75, "y": 0.25},
            {"x": 0.80, "y": 0.85},
            {"x": 0.20, "y": 0.80}
        ]),
        "rules_json": json.dumps({
            "allowed_object_types": ["HUMAN", "VEHICLE"],
            "active_start": None,
            "active_end": None,
            "dwell_time_seconds": 0
        }),
        "active": True
    }
]

CAMERA_HEALTH_CONFIGS_SEED = [
    {
        "camera_id": "CAM-07",
        "expected_fps": 25.0,
        "stale_after_seconds": 30,
        "offline_after_seconds": 120,
        "freeze_window_seconds": 10,
        "health_sampling_interval_seconds": 5,
        "region_profile": "INDO_NEPAL_FOOTHILL_PLAINS",
        "terrain_profile": "FOOTHILL / PLAINS",
        "illumination_mode": "DAY",
        "timezone": "UTC",
        "viewpoint_shift_threshold": 0.3,
        "min_feature_matches": 10,
        "min_ransac_inlier_ratio": 0.5,
        "sharpness_degraded_threshold": 0.5,
        "brightness_low_threshold": 0.15,
        "brightness_high_threshold": 0.85,
        "trend_window_days": 7,
        "trend_persistence_days": 3,
        "baseline_adaptation_rate": 0.1,
        "observation_retention_days": 30,
        "event_retention_days": 90,
        "active": True,
    },
    {
        "camera_id": "CAM-12",
        "expected_fps": 25.0,
        "stale_after_seconds": 30,
        "offline_after_seconds": 120,
        "freeze_window_seconds": 10,
        "health_sampling_interval_seconds": 5,
        "region_profile": "INDO_BHUTAN_HILLY_FOREST",
        "terrain_profile": "HILLY / FOREST",
        "illumination_mode": "DAY",
        "timezone": "UTC",
        "viewpoint_shift_threshold": 0.3,
        "min_feature_matches": 10,
        "min_ransac_inlier_ratio": 0.5,
        "sharpness_degraded_threshold": 0.5,
        "brightness_low_threshold": 0.1,
        "brightness_high_threshold": 0.8,
        "trend_window_days": 7,
        "trend_persistence_days": 3,
        "baseline_adaptation_rate": 0.1,
        "observation_retention_days": 30,
        "event_retention_days": 90,
        "active": True,
    },
    {
        "camera_id": "CAM-19",
        "expected_fps": 30.0,
        "stale_after_seconds": 30,
        "offline_after_seconds": 120,
        "freeze_window_seconds": 10,
        "health_sampling_interval_seconds": 5,
        "region_profile": "INDO_NEPAL_RURAL_FRINGE",
        "terrain_profile": "RURAL / AGRICULTURAL FRINGE",
        "illumination_mode": "DAY",
        "timezone": "UTC",
        "viewpoint_shift_threshold": 0.3,
        "min_feature_matches": 10,
        "min_ransac_inlier_ratio": 0.5,
        "sharpness_degraded_threshold": 0.5,
        "brightness_low_threshold": 0.1,
        "brightness_high_threshold": 0.85,
        "trend_window_days": 7,
        "trend_persistence_days": 3,
        "baseline_adaptation_rate": 0.1,
        "observation_retention_days": 30,
        "event_retention_days": 90,
        "active": True,
    },
    {
        "camera_id": "CAM-03",
        "expected_fps": 30.0,
        "stale_after_seconds": 30,
        "offline_after_seconds": 120,
        "freeze_window_seconds": 10,
        "health_sampling_interval_seconds": 5,
        "region_profile": "INDO_NEPAL_RURAL_FRINGE",
        "terrain_profile": "RURAL / AGRICULTURAL FRINGE",
        "illumination_mode": "DAY",
        "timezone": "UTC",
        "viewpoint_shift_threshold": 0.3,
        "min_feature_matches": 10,
        "min_ransac_inlier_ratio": 0.5,
        "sharpness_degraded_threshold": 0.5,
        "brightness_low_threshold": 0.1,
        "brightness_high_threshold": 0.85,
        "trend_window_days": 7,
        "trend_persistence_days": 3,
        "baseline_adaptation_rate": 0.1,
        "observation_retention_days": 30,
        "event_retention_days": 90,
        "active": True,
    },
]

async def seed():
    async with SessionLocal() as session:
        # Seed zones
        for z in ZONES_SEED:
            stmt = select(Zone).where(Zone.zone_id == z["zone_id"])
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if not existing:
                now = datetime.now(timezone.utc)
                model = Zone(
                    zone_id=z["zone_id"],
                    camera_id=z["camera_id"],
                    name=z["name"],
                    polygon_json=z["polygon_json"],
                    rules_json=z["rules_json"],
                    active=z["active"],
                    created_at=now,
                    updated_at=now,
                )
                session.add(model)
                print(f"Seeded zone: {z['zone_id']} ({z['name']})")
            else:
                print(f"Zone already exists: {z['zone_id']}")

        # Seed camera health configs
        for cfg in CAMERA_HEALTH_CONFIGS_SEED:
            stmt = select(CameraHealthConfig).where(CameraHealthConfig.camera_id == cfg["camera_id"])
            existing = (await session.execute(stmt)).scalar_one_or_none()
            if not existing:
                now = datetime.now(timezone.utc)
                model = CameraHealthConfig(
                    camera_id=cfg["camera_id"],
                    expected_fps=cfg["expected_fps"],
                    stale_after_seconds=cfg["stale_after_seconds"],
                    offline_after_seconds=cfg["offline_after_seconds"],
                    freeze_window_seconds=cfg["freeze_window_seconds"],
                    health_sampling_interval_seconds=cfg["health_sampling_interval_seconds"],
                    region_profile=cfg["region_profile"],
                    terrain_profile=cfg["terrain_profile"],
                    illumination_mode=cfg["illumination_mode"],
                    timezone=cfg["timezone"],
                    viewpoint_shift_threshold=cfg["viewpoint_shift_threshold"],
                    min_feature_matches=cfg["min_feature_matches"],
                    min_ransac_inlier_ratio=cfg["min_ransac_inlier_ratio"],
                    sharpness_degraded_threshold=cfg["sharpness_degraded_threshold"],
                    brightness_low_threshold=cfg["brightness_low_threshold"],
                    brightness_high_threshold=cfg["brightness_high_threshold"],
                    trend_window_days=cfg["trend_window_days"],
                    trend_persistence_days=cfg["trend_persistence_days"],
                    baseline_adaptation_rate=cfg["baseline_adaptation_rate"],
                    observation_retention_days=cfg["observation_retention_days"],
                    event_retention_days=cfg["event_retention_days"],
                    active=cfg["active"],
                    created_at=now,
                    updated_at=now,
                )
                session.add(model)
                print(f"Seeded camera health config: {cfg['camera_id']}")
            else:
                print(f"Camera health config already exists: {cfg['camera_id']}")

        await session.commit()
    print("Seed complete.")

if __name__ == "__main__":
    asyncio.run(seed())
