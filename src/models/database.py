"""SQLAlchemy 2.0 database models for the 1BOX Marketing Dashboard.

All monetary values are stored in micros (1 EUR = 1,000,000 micros)
to avoid floating-point precision issues.
"""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from config.settings import settings


class Base(DeclarativeBase):
    """Base class for all database models."""

    pass


# ---------------------------------------------------------------------------
# Google Ads Tables
# ---------------------------------------------------------------------------


class Campaign(Base):
    """Daily campaign-level metrics from Google Ads."""

    __tablename__ = "campaigns"
    __table_args__ = (
        UniqueConstraint("campaign_id", "date", name="uq_campaign_date"),
        Index("ix_campaigns_date", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    campaign_id: Mapped[str] = mapped_column(String(64), nullable=False)
    campaign_name: Mapped[str] = mapped_column(String(255), nullable=False)
    campaign_type: Mapped[str] = mapped_column(String(32), default="SEARCH")
    status: Mapped[str] = mapped_column(String(16), default="ENABLED")
    date: Mapped[date] = mapped_column(Date, nullable=False)

    impressions: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    cost_micros: Mapped[int] = mapped_column(BigInteger, default=0)
    conversions: Mapped[float] = mapped_column(Float, default=0.0)
    conversion_value: Mapped[float] = mapped_column(Float, default=0.0)
    average_cpc_micros: Mapped[int] = mapped_column(BigInteger, default=0)
    ctr: Mapped[float] = mapped_column(Float, default=0.0)
    budget_micros: Mapped[int] = mapped_column(BigInteger, default=0)
    device: Mapped[str] = mapped_column(String(16), default="ALL")

    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class AdGroup(Base):
    """Daily ad group-level metrics from Google Ads."""

    __tablename__ = "ad_groups"
    __table_args__ = (
        UniqueConstraint("ad_group_id", "date", name="uq_adgroup_date"),
        Index("ix_adgroups_date", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    ad_group_id: Mapped[str] = mapped_column(String(64), nullable=False)
    ad_group_name: Mapped[str] = mapped_column(String(255), nullable=False)
    campaign_id: Mapped[str] = mapped_column(String(64), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)

    impressions: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    cost_micros: Mapped[int] = mapped_column(BigInteger, default=0)
    conversions: Mapped[float] = mapped_column(Float, default=0.0)
    ctr: Mapped[float] = mapped_column(Float, default=0.0)

    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class Keyword(Base):
    """Daily keyword-level metrics from Google Ads."""

    __tablename__ = "keywords"
    __table_args__ = (
        UniqueConstraint("keyword_id", "date", name="uq_keyword_date"),
        Index("ix_keywords_date", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    keyword_id: Mapped[str] = mapped_column(String(64), nullable=False)
    keyword_text: Mapped[str] = mapped_column(String(512), nullable=False)
    match_type: Mapped[str] = mapped_column(String(16), default="BROAD")
    ad_group_id: Mapped[str] = mapped_column(String(64), nullable=False)
    campaign_id: Mapped[str] = mapped_column(String(64), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)

    impressions: Mapped[int] = mapped_column(Integer, default=0)
    clicks: Mapped[int] = mapped_column(Integer, default=0)
    cost_micros: Mapped[int] = mapped_column(BigInteger, default=0)
    conversions: Mapped[float] = mapped_column(Float, default=0.0)
    ctr: Mapped[float] = mapped_column(Float, default=0.0)
    average_cpc_micros: Mapped[int] = mapped_column(BigInteger, default=0)

    quality_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    expected_ctr: Mapped[str | None] = mapped_column(String(32), nullable=True)
    ad_relevance: Mapped[str | None] = mapped_column(String(32), nullable=True)
    landing_page_experience: Mapped[str | None] = mapped_column(
        String(32), nullable=True
    )

    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


# ---------------------------------------------------------------------------
# GA4 Tables
# ---------------------------------------------------------------------------


class GA4Traffic(Base):
    """GA4 session/traffic data aggregated by date, source, medium, campaign."""

    __tablename__ = "ga4_traffic"
    __table_args__ = (
        UniqueConstraint(
            "date", "source", "medium", "campaign_name", name="uq_ga4traffic_key"
        ),
        Index("ix_ga4traffic_date", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    medium: Mapped[str] = mapped_column(String(64), nullable=False)
    campaign_name: Mapped[str] = mapped_column(String(255), default="(not set)")

    sessions: Mapped[int] = mapped_column(Integer, default=0)
    users: Mapped[int] = mapped_column(Integer, default=0)
    new_users: Mapped[int] = mapped_column(Integer, default=0)
    bounce_rate: Mapped[float] = mapped_column(Float, default=0.0)
    avg_session_duration: Mapped[float] = mapped_column(Float, default=0.0)
    pages_per_session: Mapped[float] = mapped_column(Float, default=0.0)

    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class GA4Conversion(Base):
    """GA4 conversion events aggregated by date, event name, source, medium."""

    __tablename__ = "ga4_conversions"
    __table_args__ = (
        UniqueConstraint(
            "date", "event_name", "source", "medium", name="uq_ga4conv_key"
        ),
        Index("ix_ga4conv_date", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    event_name: Mapped[str] = mapped_column(String(128), nullable=False)
    source: Mapped[str] = mapped_column(String(128), nullable=False)
    medium: Mapped[str] = mapped_column(String(64), nullable=False)

    event_count: Mapped[int] = mapped_column(Integer, default=0)
    conversion_value: Mapped[float] = mapped_column(Float, default=0.0)

    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class GA4Page(Base):
    """GA4 page-level metrics aggregated by date and page path."""

    __tablename__ = "ga4_pages"
    __table_args__ = (
        UniqueConstraint("date", "page_path", name="uq_ga4page_key"),
        Index("ix_ga4pages_date", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    page_path: Mapped[str] = mapped_column(String(512), nullable=False)
    page_title: Mapped[str] = mapped_column(String(255), default="")

    views: Mapped[int] = mapped_column(Integer, default=0)
    unique_views: Mapped[int] = mapped_column(Integer, default=0)
    avg_time_on_page: Mapped[float] = mapped_column(Float, default=0.0)
    bounce_rate: Mapped[float] = mapped_column(Float, default=0.0)
    exit_rate: Mapped[float] = mapped_column(Float, default=0.0)

    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


class GA4Geo(Base):
    """GA4 geographic data aggregated by date and city."""

    __tablename__ = "ga4_geo"
    __table_args__ = (
        UniqueConstraint("date", "city", name="uq_ga4geo_key"),
        Index("ix_ga4geo_date", "date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    city: Mapped[str] = mapped_column(String(128), nullable=False)
    country: Mapped[str] = mapped_column(String(64), default="Netherlands")
    sessions: Mapped[int] = mapped_column(Integer, default=0)
    users: Mapped[int] = mapped_column(Integer, default=0)
    conversions: Mapped[int] = mapped_column(Integer, default=0)

    fetched_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )


# ---------------------------------------------------------------------------
# System Tables
# ---------------------------------------------------------------------------


class AlertHistory(Base):
    """Log of triggered alert events."""

    __tablename__ = "alerts_history"
    __table_args__ = (Index("ix_alerts_triggered_at", "triggered_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    alert_rule_id: Mapped[str] = mapped_column(String(64), nullable=False)
    alert_name: Mapped[str] = mapped_column(String(128), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metric_value: Mapped[float] = mapped_column(Float, nullable=False)
    threshold_value: Mapped[float] = mapped_column(Float, nullable=False)
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    notified: Mapped[bool] = mapped_column(Boolean, default=False)
    notification_type: Mapped[str] = mapped_column(String(32), default="email")
    acknowledged: Mapped[bool] = mapped_column(Boolean, default=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class PipelineRun(Base):
    """ETL pipeline execution log."""

    __tablename__ = "pipeline_runs"
    __table_args__ = (Index("ix_pipeline_started_at", "started_at"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now(), nullable=False
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="running")
    source: Mapped[str] = mapped_column(String(32), nullable=False)
    records_fetched: Mapped[int] = mapped_column(Integer, default=0)
    records_inserted: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


# ---------------------------------------------------------------------------
# Database Engine & Session
# ---------------------------------------------------------------------------

engine = create_async_engine(settings.database_url, echo=settings.debug)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def init_db() -> None:
    """Create all tables if they don't exist."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
