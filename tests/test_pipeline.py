"""Tests for the ETL pipeline.

Tests upsert logic with an in-memory SQLite database and verifies
pipeline orchestration with mocked fetchers.
"""

from datetime import date

import pytest
import pytest_asyncio
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.models.database import Base, Campaign, GA4Traffic, PipelineRun
from src.pipeline.etl import _upsert_rows


@pytest_asyncio.fixture
async def engine():
    """Create an in-memory SQLite engine with all tables."""
    eng = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def session(engine):
    """Provide an async session for testing."""
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with factory() as sess:
        yield sess


class TestUpsert:
    """Tests for the _upsert_rows helper."""

    @pytest.mark.asyncio
    async def test_insert_new_campaign(self, session):
        """New campaign rows should be inserted."""
        rows = [
            {
                "campaign_id": "C001",
                "campaign_name": "Test Campaign",
                "campaign_type": "SEARCH",
                "status": "ENABLED",
                "date": date(2026, 2, 1),
                "impressions": 1000,
                "clicks": 50,
                "cost_micros": 75_000_000,
                "conversions": 3.0,
                "conversion_value": 240.0,
                "average_cpc_micros": 1_500_000,
                "ctr": 5.0,
                "budget_micros": 100_000_000,
                "device": "DESKTOP",
            }
        ]
        count = await _upsert_rows(session, Campaign, rows)
        await session.commit()

        assert count == 1

        result = await session.execute(select(Campaign))
        campaigns = result.scalars().all()
        assert len(campaigns) == 1
        assert campaigns[0].campaign_id == "C001"
        assert campaigns[0].clicks == 50

    @pytest.mark.asyncio
    async def test_upsert_updates_on_conflict(self, session):
        """Existing row with same key should be updated, not duplicated."""
        base_row = {
            "campaign_id": "C001",
            "campaign_name": "Test Campaign",
            "campaign_type": "SEARCH",
            "status": "ENABLED",
            "date": date(2026, 2, 1),
            "impressions": 1000,
            "clicks": 50,
            "cost_micros": 75_000_000,
            "conversions": 3.0,
            "conversion_value": 240.0,
            "average_cpc_micros": 1_500_000,
            "ctr": 5.0,
            "budget_micros": 100_000_000,
            "device": "DESKTOP",
        }

        # Insert first
        await _upsert_rows(session, Campaign, [base_row])
        await session.commit()

        # Upsert with updated clicks
        updated_row = {**base_row, "clicks": 100, "impressions": 2000}
        await _upsert_rows(session, Campaign, [updated_row])
        await session.commit()

        result = await session.execute(select(Campaign))
        campaigns = result.scalars().all()
        assert len(campaigns) == 1  # No duplicate
        assert campaigns[0].clicks == 100
        assert campaigns[0].impressions == 2000

    @pytest.mark.asyncio
    async def test_upsert_empty_rows(self, session):
        """Empty row list should return 0 and not error."""
        count = await _upsert_rows(session, Campaign, [])
        assert count == 0

    @pytest.mark.asyncio
    async def test_insert_ga4_traffic(self, session):
        """GA4 traffic rows should be inserted correctly."""
        rows = [
            {
                "date": date(2026, 2, 1),
                "source": "google",
                "medium": "cpc",
                "campaign_name": "brand",
                "sessions": 100,
                "users": 85,
                "new_users": 70,
                "bounce_rate": 45.0,
                "avg_session_duration": 120.5,
                "pages_per_session": 3.2,
            }
        ]
        count = await _upsert_rows(session, GA4Traffic, rows)
        await session.commit()

        assert count == 1
        result = await session.execute(select(GA4Traffic))
        traffic = result.scalars().all()
        assert len(traffic) == 1
        assert traffic[0].sessions == 100

    @pytest.mark.asyncio
    async def test_upsert_multiple_rows(self, session):
        """Multiple rows with different keys should all be inserted."""
        rows = [
            {
                "campaign_id": "C001",
                "campaign_name": "Campaign A",
                "campaign_type": "SEARCH",
                "status": "ENABLED",
                "date": date(2026, 2, 1),
                "impressions": 1000,
                "clicks": 50,
                "cost_micros": 50_000_000,
                "conversions": 2.0,
                "conversion_value": 150.0,
                "average_cpc_micros": 1_000_000,
                "ctr": 5.0,
                "budget_micros": 80_000_000,
                "device": "DESKTOP",
            },
            {
                "campaign_id": "C002",
                "campaign_name": "Campaign B",
                "campaign_type": "DISPLAY",
                "status": "ENABLED",
                "date": date(2026, 2, 1),
                "impressions": 5000,
                "clicks": 100,
                "cost_micros": 120_000_000,
                "conversions": 5.0,
                "conversion_value": 400.0,
                "average_cpc_micros": 1_200_000,
                "ctr": 2.0,
                "budget_micros": 200_000_000,
                "device": "MOBILE",
            },
        ]
        count = await _upsert_rows(session, Campaign, rows)
        await session.commit()

        assert count == 2
        result = await session.execute(select(Campaign))
        campaigns = result.scalars().all()
        assert len(campaigns) == 2


class TestRunPipeline:
    """Tests for the pipeline orchestration."""

    @pytest.mark.asyncio
    async def test_pipeline_creates_run_record(self, engine):
        """run_pipeline should create a PipelineRun record."""
        from unittest.mock import AsyncMock, patch

        factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        with (
            patch("src.pipeline.etl.async_session", factory),
            patch("src.pipeline.etl._has_google_ads_credentials", return_value=False),
            patch("src.pipeline.etl._has_ga4_credentials", return_value=False),
        ):
            from src.pipeline.etl import run_pipeline

            result = await run_pipeline(source="all")

        assert result["records_fetched"] == 0
        assert result["records_inserted"] == 0

        # Verify PipelineRun was created
        async with factory() as session:
            stmt = select(PipelineRun)
            db_result = await session.execute(stmt)
            runs = db_result.scalars().all()
            assert len(runs) == 1
            assert runs[0].source == "all"
            assert runs[0].status == "success"

    @pytest.mark.asyncio
    async def test_pipeline_no_creds_skips_fetchers(self, engine):
        """Without credentials, pipeline should skip fetchers gracefully."""
        from unittest.mock import patch

        factory = async_sessionmaker(
            engine, class_=AsyncSession, expire_on_commit=False
        )

        with (
            patch("src.pipeline.etl.async_session", factory),
            patch("src.pipeline.etl._has_google_ads_credentials", return_value=False),
            patch("src.pipeline.etl._has_ga4_credentials", return_value=False),
        ):
            from src.pipeline.etl import run_pipeline

            result = await run_pipeline(source="google_ads")

        assert result["records_fetched"] == 0
        assert len(result["errors"]) == 0
