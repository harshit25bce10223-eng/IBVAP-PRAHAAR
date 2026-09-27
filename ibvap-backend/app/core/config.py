# ─────────────────────────────────────────────────────────────────────────────
# IBVAP Backend — Core Configuration
# ─────────────────────────────────────────────────────────────────────────────
from pydantic_settings import BaseSettings
from typing import Literal


class Settings(BaseSettings):
    # ── App ───────────────────────────────────────────────────────────────────
    APP_NAME: str = "IBVAP Virtual Fence + Risk Engine"
    APP_VERSION: str = "1.0.0"
    ENV: Literal["development", "production", "test"] = "development"
    DEBUG: bool = True

    # ── Database ──────────────────────────────────────────────────────────────
    DATABASE_URL: str = "sqlite+aiosqlite:///./ibvap.db"
    DATABASE_ECHO: bool = False

    # ── CORS ──────────────────────────────────────────────────────────────────
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]

    # ── Geometry ──────────────────────────────────────────────────────────────
    # Deterministic boundary policy: points ON the polygon edge = INSIDE
    BOUNDARY_POLICY: Literal["INCLUSIVE", "EXCLUSIVE"] = "INCLUSIVE"
    POLYGON_MIN_POINTS: int = 3
    POLYGON_MAX_POINTS: int = 100
    COORD_MIN: float = 0.0
    COORD_MAX: float = 1.0

    # ── Track membership hysteresis ────────────────────────────────────────────
    # Number of consecutive frames before confirming ENTRY / EXIT
    # Set to 1 to disable hysteresis (single-frame confirmation)
    ENTRY_CONFIRMATION_FRAMES: int = 1
    EXIT_CONFIRMATION_FRAMES: int = 1

    # ── Risk Engine ───────────────────────────────────────────────────────────
    # Crossing scores
    RISK_RESTRICTED_NON_ANIMAL: int = 25
    RISK_RESTRICTED_ANIMAL: int = 4
    # Night-time
    RISK_NIGHT: int = 20
    # Multi-camera
    RISK_MULTI_CAMERA: int = 15
    # Object type
    RISK_HUMAN: int = 15
    RISK_VEHICLE: int = 10
    # Confidence multiplier (confidence * RISK_CONFIDENCE_MULTIPLIER, rounded)
    RISK_CONFIDENCE_MULTIPLIER: int = 20
    # Reliability penalty
    RISK_LOW_RELIABILITY_PENALTY: int = -15
    # Bounds
    RISK_SCORE_MIN: int = 0
    RISK_SCORE_MAX: int = 100

    # ── Severity thresholds ───────────────────────────────────────────────────
    # Inclusive lower bounds: LOW 0-39, MEDIUM 40-64, HIGH 65-84, CRITICAL 85-100
    SEVERITY_MEDIUM_THRESHOLD: int = 40
    SEVERITY_HIGH_THRESHOLD: int = 65
    SEVERITY_CRITICAL_THRESHOLD: int = 85

    # ── Camera viewpoint tolerance ────────────────────────────────────────────
    CAMERA_VIEWPOINT_SHIFT_TOLERANCE: float = 0.05  # normalized units

    # ── GPU/Inference ─────────────────────────────────────────────────────────
    USE_GPU: bool = False

    # ── Path history ──────────────────────────────────────────────────────────
    TRACK_PATH_MAX_POSITIONS: int = 100

    # ── Tracking Engine (Component 6) ─────────────────────────────────────────
    # Provider mode: DEMO uses DemoTrackingProvider; REAL requires an external
    # tracker implementation registered at startup.
    TRACKING_PROVIDER_MODE: str = "DEMO"

    # How long (seconds) a track with no new observations waits before
    # being marked STALE by the background maintenance job.
    # Not a hard-coded research threshold — must be calibrated per deployment.
    TRACKING_STALE_AGE_SECONDS: int = 300

    # Provider update timeout (seconds) — caps a single provider.update() call.
    # One camera's provider timeout must not block other cameras.
    TRACKING_PROVIDER_TIMEOUT_SECONDS: float = 30.0

    # Maximum detections per ingestion batch (resource protection)
    TRACKING_MAX_BATCH_SIZE: int = 500

    # Maximum observations returned per track history query (unbounded prevention)
    TRACKING_MAX_OBSERVATION_PAGE_SIZE: int = 500

    # Maximum track results per list query
    TRACKING_MAX_TRACK_PAGE_SIZE: int = 200

    # Maximum trajectory points returned per query
    TRACKING_MAX_TRAJECTORY_POINTS: int = 500

    # Edge sync: number of retries before marking sync as SYNC_FAILED
    TRACKING_EDGE_SYNC_MAX_RETRIES: int = 3

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
