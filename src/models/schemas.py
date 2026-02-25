"""Pydantic v2 schemas for API validation and data transfer."""

from datetime import date, datetime
from enum import Enum

from pydantic import BaseModel, Field, computed_field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class PipelineStatus(str, Enum):
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"


class AlertSeverity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertCondition(str, Enum):
    PERCENT_INCREASE = "percent_increase"
    PERCENT_DECREASE = "percent_decrease"
    GREATER_THAN = "greater_than"
    LESS_THAN = "less_than"
    EQUALS = "equals"


# ---------------------------------------------------------------------------
# Google Ads Schemas
# ---------------------------------------------------------------------------


class CampaignBase(BaseModel):
    """Shared campaign fields."""

    campaign_id: str
    campaign_name: str
    campaign_type: str = "SEARCH"
    status: str = "ENABLED"
    date: date
    impressions: int = 0
    clicks: int = 0
    cost_micros: int = 0
    conversions: float = 0.0
    conversion_value: float = 0.0
    average_cpc_micros: int = 0
    ctr: float = 0.0
    budget_micros: int = 0
    device: str = "ALL"


class CampaignCreate(CampaignBase):
    """Schema for creating a campaign record."""

    pass


class CampaignRead(CampaignBase):
    """Schema for reading a campaign record (includes computed fields)."""

    id: int
    fetched_at: datetime

    @computed_field
    @property
    def cost(self) -> float:
        """Cost in EUR (converted from micros)."""
        return self.cost_micros / 1_000_000

    @computed_field
    @property
    def average_cpc(self) -> float:
        """Average CPC in EUR (converted from micros)."""
        return self.average_cpc_micros / 1_000_000

    @computed_field
    @property
    def budget(self) -> float:
        """Daily budget in EUR (converted from micros)."""
        return self.budget_micros / 1_000_000

    model_config = {"from_attributes": True}


class AdGroupBase(BaseModel):
    """Shared ad group fields."""

    ad_group_id: str
    ad_group_name: str
    campaign_id: str
    date: date
    impressions: int = 0
    clicks: int = 0
    cost_micros: int = 0
    conversions: float = 0.0
    ctr: float = 0.0


class AdGroupRead(AdGroupBase):
    id: int
    fetched_at: datetime

    @computed_field
    @property
    def cost(self) -> float:
        return self.cost_micros / 1_000_000

    model_config = {"from_attributes": True}


class KeywordBase(BaseModel):
    """Shared keyword fields."""

    keyword_id: str
    keyword_text: str
    match_type: str = "BROAD"
    ad_group_id: str
    campaign_id: str
    date: date
    impressions: int = 0
    clicks: int = 0
    cost_micros: int = 0
    conversions: float = 0.0
    ctr: float = 0.0
    average_cpc_micros: int = 0
    quality_score: int | None = None


class KeywordRead(KeywordBase):
    id: int
    fetched_at: datetime
    expected_ctr: str | None = None
    ad_relevance: str | None = None
    landing_page_experience: str | None = None

    @computed_field
    @property
    def average_cpc(self) -> float:
        return self.average_cpc_micros / 1_000_000

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# GA4 Schemas
# ---------------------------------------------------------------------------


class GA4TrafficRead(BaseModel):
    """GA4 traffic data."""

    id: int
    date: date
    source: str
    medium: str
    campaign_name: str = "(not set)"
    sessions: int = 0
    users: int = 0
    new_users: int = 0
    bounce_rate: float = 0.0
    avg_session_duration: float = 0.0
    pages_per_session: float = 0.0
    fetched_at: datetime

    model_config = {"from_attributes": True}


class GA4ConversionRead(BaseModel):
    """GA4 conversion event data."""

    id: int
    date: date
    event_name: str
    source: str
    medium: str
    event_count: int = 0
    conversion_value: float = 0.0
    fetched_at: datetime

    model_config = {"from_attributes": True}


class GA4PageRead(BaseModel):
    """GA4 page-level data."""

    id: int
    date: date
    page_path: str
    page_title: str = ""
    views: int = 0
    unique_views: int = 0
    avg_time_on_page: float = 0.0
    bounce_rate: float = 0.0
    exit_rate: float = 0.0
    fetched_at: datetime

    model_config = {"from_attributes": True}


class GA4GeoRead(BaseModel):
    """GA4 geographic data."""

    id: int
    date: date
    city: str
    country: str = "Netherlands"
    sessions: int = 0
    users: int = 0
    conversions: int = 0
    fetched_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Alert Schemas
# ---------------------------------------------------------------------------


class AlertRuleConfig(BaseModel):
    """An alert rule parsed from config/alerts.yaml."""

    id: str
    name: str
    description: str
    metric: str
    level: str = "campaign"
    condition: AlertCondition
    threshold: float
    compare_period: str | None = None
    only_weekdays: bool = False
    time_check: str | None = None
    severity: AlertSeverity = AlertSeverity.MEDIUM
    enabled: bool = True
    notify: list[dict] = Field(default_factory=list)
    cooldown_hours: int = 4


class AlertHistoryRead(BaseModel):
    """An alert event from the database."""

    id: int
    alert_rule_id: str
    alert_name: str
    severity: str
    message: str
    metric_value: float
    threshold_value: float
    triggered_at: datetime
    notified: bool = False
    notification_type: str = "email"
    acknowledged: bool = False
    acknowledged_at: datetime | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Pipeline Schemas
# ---------------------------------------------------------------------------


class PipelineRunRead(BaseModel):
    """ETL pipeline run record."""

    id: int
    started_at: datetime
    completed_at: datetime | None = None
    status: PipelineStatus = PipelineStatus.RUNNING
    source: str
    records_fetched: int = 0
    records_inserted: int = 0
    error_message: str | None = None

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Dashboard / API Schemas
# ---------------------------------------------------------------------------


class DateRangeFilter(BaseModel):
    """Date range filter for API queries."""

    start_date: date
    end_date: date
    campaign_id: str | None = None
    device: str | None = None


class DashboardSummary(BaseModel):
    """Aggregated KPIs for the overview page."""

    total_spend: float = 0.0
    total_clicks: int = 0
    total_impressions: int = 0
    total_conversions: float = 0.0
    average_cpc: float = 0.0
    average_ctr: float = 0.0
    roas: float = 0.0

    spend_change_pct: float = 0.0
    clicks_change_pct: float = 0.0
    conversions_change_pct: float = 0.0
    cpc_change_pct: float = 0.0
    ctr_change_pct: float = 0.0
    roas_change_pct: float = 0.0
