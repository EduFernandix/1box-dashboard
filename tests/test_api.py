"""API endpoint integration tests.

Uses httpx AsyncClient with ASGI transport to test FastAPI endpoints
against an in-memory SQLite database.
"""

from datetime import date

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.models.database import Base, Campaign, GA4Traffic


@pytest_asyncio.fixture
async def db_engine():
    """Create an in-memory SQLite engine with all tables."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session_factory(db_engine):
    """Create a session factory bound to the test engine."""
    return async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )


@pytest_asyncio.fixture
async def app_client(db_session_factory):
    """Create an httpx test client with database overrides."""
    from src.api.dependencies import get_db_session
    from src.main import app

    async def override_get_db_session():
        async with db_session_factory() as session:
            yield session

    app.dependency_overrides[get_db_session] = override_get_db_session

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client

    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def seeded_client(db_session_factory, app_client):
    """Client with some seed data pre-loaded."""
    async with db_session_factory() as session:
        # Insert test campaigns
        for i in range(3):
            campaign = Campaign(
                campaign_id=f"C00{i+1}",
                campaign_name=f"Campaign {i+1}",
                campaign_type="SEARCH",
                status="ENABLED",
                date=date(2026, 2, 1),
                impressions=1000 * (i + 1),
                clicks=50 * (i + 1),
                cost_micros=50_000_000 * (i + 1),
                conversions=float(i + 1),
                conversion_value=100.0 * (i + 1),
                average_cpc_micros=1_000_000,
                ctr=5.0,
                budget_micros=100_000_000,
                device="DESKTOP",
            )
            session.add(campaign)

        # Insert test traffic
        traffic = GA4Traffic(
            date=date(2026, 2, 1),
            source="google",
            medium="cpc",
            campaign_name="brand",
            sessions=100,
            users=85,
            new_users=70,
            bounce_rate=45.0,
            avg_session_duration=120.5,
            pages_per_session=3.2,
        )
        session.add(traffic)
        await session.commit()

    return app_client


class TestHealthEndpoint:
    """Tests for the /health endpoint."""

    @pytest.mark.asyncio
    async def test_health_returns_200(self, app_client):
        resp = await app_client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert "version" in data


class TestCampaignEndpoints:
    """Tests for /api/v1/campaigns endpoints."""

    @pytest.mark.asyncio
    async def test_list_campaigns_empty(self, app_client):
        """Empty database should return an empty list."""
        resp = await app_client.get("/api/v1/campaigns/")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_list_campaigns_with_data(self, seeded_client):
        """Should return campaign records when data exists."""
        resp = await seeded_client.get(
            "/api/v1/campaigns/",
            params={"start_date": "2026-01-01", "end_date": "2026-03-01"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 3

    @pytest.mark.asyncio
    async def test_list_campaigns_filter_by_id(self, seeded_client):
        """Filtering by campaign_id should return matching records only."""
        resp = await seeded_client.get(
            "/api/v1/campaigns/",
            params={
                "start_date": "2026-01-01",
                "end_date": "2026-03-01",
                "campaign_id": "C001",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["campaign_id"] == "C001"

    @pytest.mark.asyncio
    async def test_campaign_metrics(self, seeded_client):
        """Should return time-series metrics for a specific campaign."""
        resp = await seeded_client.get(
            "/api/v1/campaigns/C001/metrics",
            params={"start_date": "2026-01-01", "end_date": "2026-03-01"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["campaign_id"] == "C001"

    @pytest.mark.asyncio
    async def test_list_keywords_empty(self, app_client):
        """Empty database should return empty keywords list."""
        resp = await app_client.get("/api/v1/campaigns/keywords")
        assert resp.status_code == 200
        assert resp.json() == []


class TestAnalyticsEndpoints:
    """Tests for /api/v1/traffic, /api/v1/conversions, /api/v1/dashboard/summary."""

    @pytest.mark.asyncio
    async def test_traffic_empty(self, app_client):
        resp = await app_client.get("/api/v1/traffic")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_traffic_with_data(self, seeded_client):
        resp = await seeded_client.get(
            "/api/v1/traffic",
            params={"start_date": "2026-01-01", "end_date": "2026-03-01"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["source"] == "google"

    @pytest.mark.asyncio
    async def test_conversions_empty(self, app_client):
        resp = await app_client.get("/api/v1/conversions")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_dashboard_summary_zero_data(self, app_client):
        """Dashboard summary with no data should return zero values."""
        resp = await app_client.get(
            "/api/v1/dashboard/summary",
            params={"start_date": "2026-02-01", "end_date": "2026-02-28"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_spend"] == 0.0
        assert data["total_clicks"] == 0
        assert data["roas"] == 0.0

    @pytest.mark.asyncio
    async def test_dashboard_summary_with_data(self, seeded_client):
        """Dashboard summary should aggregate campaign metrics."""
        resp = await seeded_client.get(
            "/api/v1/dashboard/summary",
            params={"start_date": "2026-02-01", "end_date": "2026-02-28"},
        )
        assert resp.status_code == 200
        data = resp.json()
        # 3 campaigns: total spend = (50+100+150)M micros / 1M = 300 EUR
        assert data["total_spend"] == 300.0
        assert data["total_clicks"] == 300  # 50+100+150


class TestPipelineEndpoints:
    """Tests for /api/v1/pipeline endpoints."""

    @pytest.mark.asyncio
    async def test_pipeline_status_empty(self, app_client):
        """No pipeline runs should return null."""
        resp = await app_client.get("/api/v1/pipeline/status")
        assert resp.status_code == 200
        assert resp.json() is None

    @pytest.mark.asyncio
    async def test_pipeline_history_empty(self, app_client):
        resp = await app_client.get("/api/v1/pipeline/history")
        assert resp.status_code == 200
        assert resp.json() == []

    @pytest.mark.asyncio
    async def test_pipeline_trigger(self, app_client):
        """Trigger endpoint should return 200 with acknowledgment."""
        resp = await app_client.post("/api/v1/pipeline/trigger?source=all")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "triggered"
        assert data["source"] == "all"


class TestAlertEndpoints:
    """Tests for /api/v1/alerts endpoints."""

    @pytest.mark.asyncio
    async def test_alert_history_empty(self, app_client):
        resp = await app_client.get("/api/v1/alerts/history")
        assert resp.status_code == 200
        assert resp.json() == []
