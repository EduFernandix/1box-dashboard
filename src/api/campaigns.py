"""Campaign and keyword API endpoints."""

from fastapi import APIRouter, Query
from sqlalchemy import select

from src.api.dependencies import DateRange, DbSession
from src.models.database import Campaign, Keyword
from src.models.schemas import CampaignRead, KeywordRead

router = APIRouter()


@router.get("/", response_model=list[CampaignRead])
async def list_campaigns(
    session: DbSession,
    dates: DateRange,
    campaign_id: str | None = Query(None, description="Filter by campaign ID"),
    device: str | None = Query(None, description="Filter by device (MOBILE, DESKTOP, TABLET)"),
) -> list[CampaignRead]:
    """List campaign metrics for a date range.

    Returns daily campaign rows, ordered by date descending.
    """
    start_date, end_date = dates

    stmt = select(Campaign).where(
        Campaign.date.between(start_date, end_date)
    )
    if campaign_id:
        stmt = stmt.where(Campaign.campaign_id == campaign_id)
    if device:
        stmt = stmt.where(Campaign.device == device.upper())

    stmt = stmt.order_by(Campaign.date.desc(), Campaign.campaign_name)
    result = await session.execute(stmt)
    return [CampaignRead.model_validate(r) for r in result.scalars().all()]


@router.get("/{campaign_id}/metrics", response_model=list[CampaignRead])
async def campaign_metrics(
    campaign_id: str,
    session: DbSession,
    dates: DateRange,
) -> list[CampaignRead]:
    """Get daily time-series metrics for a specific campaign."""
    start_date, end_date = dates

    stmt = (
        select(Campaign)
        .where(
            Campaign.campaign_id == campaign_id,
            Campaign.date.between(start_date, end_date),
        )
        .order_by(Campaign.date.asc())
    )
    result = await session.execute(stmt)
    return [CampaignRead.model_validate(r) for r in result.scalars().all()]


@router.get("/keywords", response_model=list[KeywordRead])
async def list_keywords(
    session: DbSession,
    dates: DateRange,
    campaign_id: str | None = Query(None, description="Filter by campaign ID"),
    min_quality_score: int | None = Query(None, ge=1, le=10, description="Minimum quality score"),
) -> list[KeywordRead]:
    """List keyword metrics with quality scores.

    Returns daily keyword rows, ordered by clicks descending.
    """
    start_date, end_date = dates

    stmt = select(Keyword).where(
        Keyword.date.between(start_date, end_date)
    )
    if campaign_id:
        stmt = stmt.where(Keyword.campaign_id == campaign_id)
    if min_quality_score:
        stmt = stmt.where(Keyword.quality_score >= min_quality_score)

    stmt = stmt.order_by(Keyword.clicks.desc())
    result = await session.execute(stmt)
    return [KeywordRead.model_validate(r) for r in result.scalars().all()]
