"""Pipeline management API endpoints."""

import asyncio
from datetime import date

from fastapi import APIRouter, Query
from sqlalchemy import select

from src.api.dependencies import DbSession
from src.models.database import PipelineRun
from src.models.schemas import PipelineRunRead

router = APIRouter()


@router.get("/status", response_model=PipelineRunRead | None)
async def pipeline_status(session: DbSession) -> PipelineRunRead | None:
    """Get the most recent pipeline run status."""
    stmt = (
        select(PipelineRun)
        .order_by(PipelineRun.started_at.desc())
        .limit(1)
    )
    result = await session.execute(stmt)
    run = result.scalar_one_or_none()
    return PipelineRunRead.model_validate(run) if run else None


@router.get("/history", response_model=list[PipelineRunRead])
async def pipeline_history(
    session: DbSession,
    limit: int = Query(20, ge=1, le=100, description="Number of runs to return"),
) -> list[PipelineRunRead]:
    """Get pipeline run history."""
    stmt = (
        select(PipelineRun)
        .order_by(PipelineRun.started_at.desc())
        .limit(limit)
    )
    result = await session.execute(stmt)
    return [
        PipelineRunRead.model_validate(r) for r in result.scalars().all()
    ]


@router.post("/trigger")
async def trigger_pipeline(
    source: str = Query(
        "all",
        description="Data source to fetch: 'all', 'google_ads', or 'ga4'",
        pattern="^(all|google_ads|ga4)$",
    ),
    start_date: date | None = Query(
        None, description="Start date (defaults to yesterday)"
    ),
    end_date: date | None = Query(
        None, description="End date (defaults to yesterday)"
    ),
) -> dict:
    """Manually trigger a pipeline run.

    The pipeline runs in the background. Check /status for results.
    """
    from src.pipeline.etl import run_pipeline

    asyncio.create_task(run_pipeline(source, start_date, end_date))
    return {
        "status": "triggered",
        "source": source,
        "message": "Pipeline started in background. Check /status for results.",
    }
