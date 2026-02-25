"""1BOX Marketing Dashboard — FastAPI Application.

Entry point for the REST API. Provides endpoints for:
- Health checks
- Campaign, keyword, and traffic data (Phase 2)
- Alert management (Phase 4)

Run with:
    uv run uvicorn src.main:app --reload --port 8000
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config.settings import settings
from src.models.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize database on startup."""
    await init_db()
    yield


app = FastAPI(
    title=settings.app_name,
    description="Marketing analytics dashboard for 1BOX Self-Storage",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """Verify the API is running."""
    return {"status": "healthy", "version": "0.1.0", "app": settings.app_name}


# ── Phase 2+ Router Stubs ──────────────────────────────────────────────────
# from src.api.campaigns import router as campaigns_router
# from src.api.analytics import router as analytics_router
# from src.api.alerts import router as alerts_router
#
# app.include_router(campaigns_router, prefix="/api/v1/campaigns", tags=["campaigns"])
# app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["analytics"])
# app.include_router(alerts_router, prefix="/api/v1/alerts", tags=["alerts"])
