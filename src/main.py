"""1BOX Marketing Dashboard — FastAPI Application.

Entry point for the REST API. Provides endpoints for:
- Health checks
- Campaign and keyword data
- GA4 traffic and conversions
- Dashboard summary with period-over-period comparison
- Pipeline management (status, trigger)
- Alert history

Run with:
    uv run uvicorn src.main:app --reload --port 8000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from src.api.alerts import router as alerts_router
from src.api.analytics import router as analytics_router
from src.api.campaigns import router as campaigns_router
from src.api.pipeline import router as pipeline_router
from src.models.database import init_db
from src.pipeline.scheduler import start_scheduler, stop_scheduler

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize database and scheduler on startup."""
    await init_db()
    logger.info("Database initialized")

    scheduler = start_scheduler()
    yield

    if scheduler:
        stop_scheduler()


app = FastAPI(
    title=settings.app_name,
    description="Marketing analytics dashboard for 1BOX Self-Storage",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(
    campaigns_router, prefix="/api/v1/campaigns", tags=["campaigns"]
)
app.include_router(
    analytics_router, prefix="/api/v1", tags=["analytics"]
)
app.include_router(
    pipeline_router, prefix="/api/v1/pipeline", tags=["pipeline"]
)
app.include_router(
    alerts_router, prefix="/api/v1/alerts", tags=["alerts"]
)


@app.get("/health")
async def health_check():
    """Verify the API is running."""
    return {"status": "healthy", "version": "0.2.0", "app": settings.app_name}
