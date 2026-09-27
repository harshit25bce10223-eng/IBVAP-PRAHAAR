# ─────────────────────────────────────────────────────────────────────────────
# PRHAAR — FastAPI Application Entry
# ─────────────────────────────────────────────────────────────────────────────
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import evaluation, incidents, zones, camera_health_router, evidence_router, event_correlation_router, detection_router, tracking_router, anpr_router, setup_camera_health_provider
from app.core.config import settings
from app.core.errors import IBVAPError
from app.core.logging import configure_logging, get_logger

configure_logging()
logger = get_logger("prhaar.main")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="PRHAAR — Virtual Fence + Explainable Risk Engine + Camera Health Monitor + AI Detection Engine + ANPR",
)


@app.exception_handler(IBVAPError)
async def ibvap_error_handler(request: Request, exc: IBVAPError) -> JSONResponse:
    """Return structured domain errors as {"error": {...}} (spec §6)."""
    return JSONResponse(status_code=exc.status_code, content=exc.to_dict())

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health")
async def health() -> dict:
    return {"status": "ok", "service": "prhaar", "version": settings.APP_VERSION}


app.include_router(zones.router, prefix="/api/v1")
app.include_router(evaluation.router, prefix="/api/v1")
app.include_router(incidents.router, prefix="/api/v1")
app.include_router(camera_health_router, prefix="/api/v1")
app.include_router(evidence_router, prefix="/api/v1")
app.include_router(event_correlation_router, prefix="/api/v1")
app.include_router(detection_router, prefix="/api/v1")
app.include_router(tracking_router, prefix="/api/v1")
app.include_router(anpr_router, prefix="/api/v1")


@app.on_event("startup")
async def startup() -> None:
    logger.info("PRHAAR starting (env=%s)", settings.ENV)
    # Setup Camera Health Provider for Component 1 integration
    setup_camera_health_provider()
    # Setup Tracking Provider (Component 6)
    from app.domain.tracking.provider import set_tracking_provider
    from app.domain.tracking.demo_provider import DemoTrackingProvider
    tracking_provider = DemoTrackingProvider()
    await tracking_provider.initialize()
    set_tracking_provider(tracking_provider)
    logger.info("TrackingProvider registered: %s", type(tracking_provider).__name__)
    # Setup ANPR Provider (Component 7)
    from app.domain.anpr.provider import set_anpr_provider
    from app.domain.anpr.demo_provider import DemoANPRProvider
    anpr_provider = DemoANPRProvider()
    await anpr_provider.initialize()
    set_anpr_provider(anpr_provider)
    logger.info("ANPRProvider registered: %s", type(anpr_provider).__name__)