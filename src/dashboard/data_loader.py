"""Synchronous database queries for the Streamlit dashboard.

Uses a sync SQLAlchemy engine (Streamlit is not async) with
@st.cache_data for 5-minute TTL caching. All micros columns
are converted to EUR before returning DataFrames.
"""

from datetime import date, timedelta

import pandas as pd
import streamlit as st
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from config.settings import settings
from src.models.database import (
    AlertHistory,
    Campaign,
    GA4Conversion,
    GA4Geo,
    GA4Page,
    GA4Traffic,
    Keyword,
    PipelineRun,
)

_engine = create_engine(settings.sync_database_url, echo=False)


def _get_session() -> Session:
    return Session(_engine)


# ---------------------------------------------------------------------------
# Campaign data
# ---------------------------------------------------------------------------


@st.cache_data(ttl=300)
def get_campaigns(
    start_date: date,
    end_date: date,
    campaign_id: str | None = None,
    device: str | None = None,
) -> pd.DataFrame:
    """Get campaign data with EUR-converted columns."""
    with _get_session() as session:
        stmt = select(Campaign).where(Campaign.date.between(start_date, end_date))
        if campaign_id:
            stmt = stmt.where(Campaign.campaign_id == campaign_id)
        if device:
            stmt = stmt.where(Campaign.device == device)
        stmt = stmt.order_by(Campaign.date.desc())
        rows = session.execute(stmt).scalars().all()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame([
        {
            "date": r.date,
            "campaign_id": r.campaign_id,
            "campaign_name": r.campaign_name,
            "campaign_type": r.campaign_type,
            "status": r.status,
            "impressions": r.impressions,
            "clicks": r.clicks,
            "cost": r.cost_micros / 1_000_000,
            "conversions": r.conversions,
            "conversion_value": r.conversion_value,
            "cpc": r.average_cpc_micros / 1_000_000,
            "ctr": r.ctr,
            "budget": r.budget_micros / 1_000_000,
            "device": r.device,
        }
        for r in rows
    ])
    return df


@st.cache_data(ttl=300)
def get_campaign_names() -> list[str]:
    """Get distinct campaign names for filter dropdowns."""
    with _get_session() as session:
        rows = session.execute(
            select(Campaign.campaign_name).distinct()
        ).scalars().all()
    return sorted(rows)


@st.cache_data(ttl=300)
def get_daily_metrics(start_date: date, end_date: date) -> pd.DataFrame:
    """Get daily aggregated metrics across all campaigns."""
    with _get_session() as session:
        stmt = (
            select(
                Campaign.date,
                func.sum(Campaign.cost_micros).label("cost_micros"),
                func.sum(Campaign.clicks).label("clicks"),
                func.sum(Campaign.impressions).label("impressions"),
                func.sum(Campaign.conversions).label("conversions"),
                func.sum(Campaign.conversion_value).label("conversion_value"),
            )
            .where(Campaign.date.between(start_date, end_date))
            .group_by(Campaign.date)
            .order_by(Campaign.date)
        )
        rows = session.execute(stmt).all()

    if not rows:
        return pd.DataFrame()

    df = pd.DataFrame(rows, columns=["date", "cost_micros", "clicks", "impressions", "conversions", "conversion_value"])
    df["cost"] = df["cost_micros"] / 1_000_000
    df.drop(columns=["cost_micros"], inplace=True)
    return df


@st.cache_data(ttl=300)
def get_dashboard_summary(start_date: date, end_date: date) -> dict:
    """Aggregate KPIs with period-over-period comparison."""
    period_length = (end_date - start_date).days + 1
    prev_end = start_date - timedelta(days=1)
    prev_start = prev_end - timedelta(days=period_length - 1)

    current = _aggregate_campaigns(start_date, end_date)
    previous = _aggregate_campaigns(prev_start, prev_end)

    def pct_change(cur: float, prev: float) -> float:
        if prev == 0:
            return 0.0
        return round((cur - prev) / prev * 100, 1)

    return {
        **current,
        "spend_change_pct": pct_change(current["total_spend"], previous["total_spend"]),
        "clicks_change_pct": pct_change(current["total_clicks"], previous["total_clicks"]),
        "conversions_change_pct": pct_change(current["total_conversions"], previous["total_conversions"]),
        "cpc_change_pct": pct_change(current["average_cpc"], previous["average_cpc"]),
        "ctr_change_pct": pct_change(current["average_ctr"], previous["average_ctr"]),
        "roas_change_pct": pct_change(current["roas"], previous["roas"]),
    }


def _aggregate_campaigns(start: date, end: date) -> dict:
    """Aggregate campaign metrics for a date range."""
    with _get_session() as session:
        stmt = select(
            func.sum(Campaign.cost_micros),
            func.sum(Campaign.clicks),
            func.sum(Campaign.impressions),
            func.sum(Campaign.conversions),
            func.sum(Campaign.conversion_value),
        ).where(Campaign.date.between(start, end))
        row = session.execute(stmt).one()

    cost_micros = row[0] or 0
    clicks = row[1] or 0
    impressions = row[2] or 0
    conversions = row[3] or 0.0
    conv_value = row[4] or 0.0
    spend = cost_micros / 1_000_000

    return {
        "total_spend": round(spend, 2),
        "total_clicks": clicks,
        "total_impressions": impressions,
        "total_conversions": round(conversions, 1),
        "average_cpc": round(spend / clicks, 2) if clicks > 0 else 0.0,
        "average_ctr": round(clicks / impressions * 100, 2) if impressions > 0 else 0.0,
        "roas": round(conv_value / spend, 2) if spend > 0 else 0.0,
    }


# ---------------------------------------------------------------------------
# Keywords
# ---------------------------------------------------------------------------


@st.cache_data(ttl=300)
def get_keywords(
    start_date: date,
    end_date: date,
    campaign_id: str | None = None,
    min_quality_score: int | None = None,
) -> pd.DataFrame:
    """Get keyword data with quality scores."""
    with _get_session() as session:
        stmt = select(Keyword).where(Keyword.date.between(start_date, end_date))
        if campaign_id:
            stmt = stmt.where(Keyword.campaign_id == campaign_id)
        if min_quality_score:
            stmt = stmt.where(Keyword.quality_score >= min_quality_score)
        stmt = stmt.order_by(Keyword.clicks.desc())
        rows = session.execute(stmt).scalars().all()

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame([
        {
            "date": r.date,
            "keyword_id": r.keyword_id,
            "keyword_text": r.keyword_text,
            "match_type": r.match_type,
            "campaign_id": r.campaign_id,
            "ad_group_id": r.ad_group_id,
            "impressions": r.impressions,
            "clicks": r.clicks,
            "cost": r.cost_micros / 1_000_000,
            "conversions": r.conversions,
            "ctr": r.ctr,
            "cpc": r.average_cpc_micros / 1_000_000,
            "quality_score": r.quality_score,
            "expected_ctr": r.expected_ctr,
            "ad_relevance": r.ad_relevance,
            "landing_page_experience": r.landing_page_experience,
        }
        for r in rows
    ])


# ---------------------------------------------------------------------------
# GA4 Traffic
# ---------------------------------------------------------------------------


@st.cache_data(ttl=300)
def get_traffic(
    start_date: date,
    end_date: date,
    source: str | None = None,
    medium: str | None = None,
) -> pd.DataFrame:
    """Get GA4 traffic data."""
    with _get_session() as session:
        stmt = select(GA4Traffic).where(GA4Traffic.date.between(start_date, end_date))
        if source:
            stmt = stmt.where(GA4Traffic.source == source)
        if medium:
            stmt = stmt.where(GA4Traffic.medium == medium)
        stmt = stmt.order_by(GA4Traffic.date.desc())
        rows = session.execute(stmt).scalars().all()

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame([
        {
            "date": r.date,
            "source": r.source,
            "medium": r.medium,
            "campaign_name": r.campaign_name,
            "sessions": r.sessions,
            "users": r.users,
            "new_users": r.new_users,
            "bounce_rate": r.bounce_rate,
            "avg_session_duration": r.avg_session_duration,
            "pages_per_session": r.pages_per_session,
        }
        for r in rows
    ])


@st.cache_data(ttl=300)
def get_traffic_by_channel(start_date: date, end_date: date) -> pd.DataFrame:
    """Aggregate daily traffic by channel."""
    df = get_traffic(start_date, end_date)
    if df.empty:
        return df

    from src.dashboard.utils import channel_label

    df["channel"] = df.apply(lambda r: channel_label(r["source"], r["medium"]), axis=1)
    grouped = df.groupby(["date", "channel"]).agg(
        sessions=("sessions", "sum"),
        users=("users", "sum"),
    ).reset_index()
    return grouped.sort_values("date")


# ---------------------------------------------------------------------------
# GA4 Geo
# ---------------------------------------------------------------------------


@st.cache_data(ttl=300)
def get_geo_data(start_date: date, end_date: date) -> pd.DataFrame:
    """Get city-level session data for the Netherlands map."""
    with _get_session() as session:
        stmt = (
            select(
                GA4Geo.city,
                func.sum(GA4Geo.sessions).label("sessions"),
                func.sum(GA4Geo.users).label("users"),
                func.sum(GA4Geo.conversions).label("conversions"),
            )
            .where(GA4Geo.date.between(start_date, end_date))
            .group_by(GA4Geo.city)
            .order_by(func.sum(GA4Geo.sessions).desc())
        )
        rows = session.execute(stmt).all()

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(rows, columns=["city", "sessions", "users", "conversions"])


# ---------------------------------------------------------------------------
# GA4 Conversions & Pages
# ---------------------------------------------------------------------------


@st.cache_data(ttl=300)
def get_conversions(
    start_date: date,
    end_date: date,
    event_name: str | None = None,
) -> pd.DataFrame:
    """Get GA4 conversion data."""
    with _get_session() as session:
        stmt = select(GA4Conversion).where(
            GA4Conversion.date.between(start_date, end_date)
        )
        if event_name:
            stmt = stmt.where(GA4Conversion.event_name == event_name)
        stmt = stmt.order_by(GA4Conversion.date.desc())
        rows = session.execute(stmt).scalars().all()

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame([
        {
            "date": r.date,
            "event_name": r.event_name,
            "source": r.source,
            "medium": r.medium,
            "event_count": r.event_count,
            "conversion_value": r.conversion_value,
        }
        for r in rows
    ])


@st.cache_data(ttl=300)
def get_pages(start_date: date, end_date: date) -> pd.DataFrame:
    """Get GA4 page performance data."""
    with _get_session() as session:
        stmt = (
            select(
                GA4Page.page_path,
                GA4Page.page_title,
                func.sum(GA4Page.views).label("views"),
                func.sum(GA4Page.unique_views).label("unique_views"),
                func.avg(GA4Page.avg_time_on_page).label("avg_time_on_page"),
                func.avg(GA4Page.bounce_rate).label("bounce_rate"),
                func.avg(GA4Page.exit_rate).label("exit_rate"),
            )
            .where(GA4Page.date.between(start_date, end_date))
            .group_by(GA4Page.page_path, GA4Page.page_title)
            .order_by(func.sum(GA4Page.views).desc())
        )
        rows = session.execute(stmt).all()

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame(
        rows,
        columns=["page_path", "page_title", "views", "unique_views",
                 "avg_time_on_page", "bounce_rate", "exit_rate"],
    )


# ---------------------------------------------------------------------------
# Alerts & Pipeline
# ---------------------------------------------------------------------------


@st.cache_data(ttl=300)
def get_alerts(limit: int = 50, severity: str | None = None) -> pd.DataFrame:
    """Get alert history."""
    with _get_session() as session:
        stmt = select(AlertHistory).order_by(AlertHistory.triggered_at.desc())
        if severity:
            stmt = stmt.where(AlertHistory.severity == severity)
        stmt = stmt.limit(limit)
        rows = session.execute(stmt).scalars().all()

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame([
        {
            "id": r.id,
            "alert_name": r.alert_name,
            "severity": r.severity,
            "message": r.message,
            "metric_value": r.metric_value,
            "threshold_value": r.threshold_value,
            "triggered_at": r.triggered_at,
            "notified": r.notified,
            "acknowledged": r.acknowledged,
        }
        for r in rows
    ])


@st.cache_data(ttl=300)
def get_pipeline_runs(limit: int = 20) -> pd.DataFrame:
    """Get pipeline execution history."""
    with _get_session() as session:
        stmt = (
            select(PipelineRun)
            .order_by(PipelineRun.started_at.desc())
            .limit(limit)
        )
        rows = session.execute(stmt).scalars().all()

    if not rows:
        return pd.DataFrame()

    return pd.DataFrame([
        {
            "id": r.id,
            "started_at": r.started_at,
            "completed_at": r.completed_at,
            "status": r.status,
            "source": r.source,
            "records_fetched": r.records_fetched,
            "records_inserted": r.records_inserted,
            "error_message": r.error_message,
        }
        for r in rows
    ])


@st.cache_data(ttl=300)
def get_last_refresh() -> str | None:
    """Get the timestamp of the most recent pipeline run."""
    with _get_session() as session:
        stmt = (
            select(PipelineRun.completed_at)
            .order_by(PipelineRun.started_at.desc())
            .limit(1)
        )
        row = session.execute(stmt).scalar_one_or_none()
    if row:
        return row.strftime("%Y-%m-%d %H:%M")
    return None
