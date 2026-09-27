# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 7 — ANPR Repositories
# ─────────────────────────────────────────────────────────────────────────────
from .sighting_repository import VehicleSightingRepository
from .plate_read_repository import PlateReadRepository
from .candidate_repository import PlateCandidateRepository
from .config_repository import ANPRConfigRepository

__all__ = [
    "VehicleSightingRepository",
    "PlateReadRepository",
    "PlateCandidateRepository",
    "ANPRConfigRepository",
]