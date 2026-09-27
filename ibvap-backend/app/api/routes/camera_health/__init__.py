# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — Camera Health Routes
# ─────────────────────────────────────────────────────────────────────────────
from .routes import router, setup_camera_health_provider

__all__ = ["router", "setup_camera_health_provider"]