# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR Component 5 — Detection Repositories
# ─────────────────────────────────────────────────────────────────────────────
from .detection_repository import DetectionRepository
from .config_repository import DetectionConfigRepository

__all__ = [
    "DetectionRepository",
    "DetectionConfigRepository",
]