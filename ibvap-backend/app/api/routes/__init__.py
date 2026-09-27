# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — API Route Registry
# ─────────────────────────────────────────────────────────────────────────────
from app.api.routes.zones import router as zones_router
from app.api.routes.evaluation import router as evaluation_router
from app.api.routes.incidents import router as incidents_router
from app.api.routes.camera_health import router as camera_health_router, setup_camera_health_provider
from app.api.routes.evidence import router as evidence_router
from app.api.routes.event_correlation import router as event_correlation_router
from app.api.routes.detection import router as detection_router
from app.api.routes.tracking import router as tracking_router
from app.api.routes.anpr import anpr_router

__all__ = [
    "zones_router",
    "evaluation_router",
    "incidents_router",
    "camera_health_router",
    "evidence_router",
    "event_correlation_router",
    "detection_router",
    "tracking_router",
    "anpr_router",
    "setup_camera_health_provider",
]