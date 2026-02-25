"""Analytics API endpoints — traffic, conversions, dashboard summary."""

from datetime import timedelta

from fastapi import APIRouter, Query
from sqlalchemy import func, select

from src.api.dependencies import DateRange, DbSession
from src.models.database import Campaign, GA4Conversion, GA4Traffic
from src.models.schemas import (
    DashboardSummary,
    GA4ConversionRead,
    GA4TrafficRead,
)

router = APIRouter()


@router.get("/traffic", response_model=list[GA4TrafficRead])
async def get_traffic(
    session: DbSession,
    dates: DateRange,
    source: str | None = Query(None, description="Filter by source"),
    medium: str | None = Query(None, description="Filter by medium"),
) -> list[GA4TrafficRead]:
    """Get GA4 traffic data by source/medium/campaign."""
    start_date, end_date = dates

    stmt = select(GA4Traffic).where(
        GA4Traffic.date.between(start_date, end_date)
    )
    if source:
        stmt = stmt.where(GA4Traffic.source == source)
    if medium:
        stmt = stmt.where(GA4Traffic.medium == medium)

    stmt = stmt.order_by(GA4Traffic.date.desc())
    result = await session.execute(stmt)
    return [GA4TrafficRead.model_validate(r) for r in result.scalars().all()]


@router.get("/conversions", response_model=list[GA4ConversionRead])
async def get_conversions(
    session: DbSession,
    dates: DateRange,
    event_name: str | None = Query(None, description="Filter by event name"),
) -> list[GA4ConversionRead]:
    """Get GA4 conversion events."""
    start_date, end_date = dates

    stmt = select(GA4Conversion).where(
        GA4Conversion.date.between(start_date, end_date)
    )
    if event_name:
        stmt = stmt.where(GA4Conversion.event_name == event_name)

    stmt = stmt.order_by(GA4Conversion.date.desc())
    result = await session.execute(stmt)
    return [
        GA4ConversionRead.model_validate(r) for r in result.scalars().all()
    ]


async def _aggregate_campaigns(
    session: DbSession, start: "date", end: "date"
) -> dict:
    """Aggregate campaign metrics for a date range."""
    from datetime import date as date_type

    stmt = select(
        func.sum(Campaign.cost_micros).label("total_cost_micros"),
        func.sum(Campaign.clicks).label("total_clicks"),
        func.sum(Campaign.impressions).label("total_impressions"),
        func.sum(Campaign.conversions).label("total_conversions"),
        func.sum(Campaign.conversion_value).label("total_conversion_value"),
    ).where(Campaign.date.between(start, end))

    result = await session.execute(stmt)
    row = result.one()

    total_cost_micros = row.total_cost_micros or 0
    total_clicks = row.total_clicks or 0
    total_impressions = row.total_impressions or 0
    total_conversions = row.total_conversions or 0.0
    total_conversion_value = row.total_conversion_value or 0.0
    total_spend = total_cost_micros / 1_000_000

    return {
        "total_spend": round(total_spend, 2),
        "total_clicks": total_clicks,
        "total_impressions": total_impressions,
        "total_conversions": round(total_conversions, 1),
        "average_cpc": (
            round(total_spend / total_clicks, 2) if total_clicks > 0 else 0.0
        ),
        "average_ctr": (
            round(total_clicks / total_impressions * 100, 2)
            if total_impressions > 0
            else 0.0
        ),
        "roas": (
            round(total_conversion_value / total_spend, 2)
            if total_spend > 0
            else 0.0
        ),
    }


def _pct_change(current: float, previous: float) -> float:
    """Calculate percentage change from previous to current."""
    if previous == 0:
        return 0.0
    return round((current - previous) / previous * 100, 1)


@router.get("/dashboard/summary", response_model=DashboardSummary)
async def dashboard_summary(
    session: DbSession,
    dates: DateRange,
) -> DashboardSummary:
    """Get aggregated KPIs with period-over-period comparison.

    Compares the requested date range with the previous period
    of equal length to compute percentage changes.
    """
    start_date, end_date = dates
    period_length = (end_date - start_date).days + 1

    # Previous period of equal length
    prev_end = start_date - timedelta(days=1)
    prev_start = prev_end - timedelta(days=period_length - 1)

    current = await _aggregate_campaigns(session, start_date, end_date)
    previous = await _aggregate_campaigns(session, prev_start, prev_end)

    return DashboardSummary(
        total_spend=current["total_spend"],
        total_clicks=current["total_clicks"],
        total_impressions=current["total_impressions"],
        total_conversions=current["total_conversions"],
        average_cpc=current["average_cpc"],
        average_ctr=current["average_ctr"],
        roas=current["roas"],
        spend_change_pct=_pct_change(
            current["total_spend"], previous["total_spend"]
        ),
        clicks_change_pct=_pct_change(
            current["total_clicks"], previous["total_clicks"]
        ),
        conversions_change_pct=_pct_change(
            current["total_conversions"], previous["total_conversions"]
        ),
        cpc_change_pct=_pct_change(
            current["average_cpc"], previous["average_cpc"]
        ),
        ctr_change_pct=_pct_change(
            current["average_ctr"], previous["average_ctr"]
        ),
        roas_change_pct=_pct_change(current["roas"], previous["roas"]),
    )
