"""Shared test fixtures for the 1BOX Marketing Dashboard."""

import asyncio
from datetime import date, datetime

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from src.models.database import Base


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture
async def db_engine():
    """Create an in-memory SQLite engine with all tables."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine):
    """Provide an async database session for testing."""
    session_factory = async_sessionmaker(
        db_engine, class_=AsyncSession, expire_on_commit=False
    )
    async with session_factory() as session:
        yield session


@pytest_asyncio.fixture
async def client():
    """Create a test client for the FastAPI app."""
    from src.main import app

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


# Sample data factories


def make_campaign_dict(**overrides) -> dict:
    """Create a campaign dict matching the database schema."""
    defaults = {
        "campaign_id": "C001",
        "campaign_name": "Test Campaign",
        "campaign_type": "SEARCH",
        "status": "ENABLED",
        "date": date(2026, 2, 1),
        "impressions": 1000,
        "clicks": 50,
        "cost_micros": 75_000_000,  # €75
        "conversions": 3.0,
        "conversion_value": 240.0,
        "average_cpc_micros": 1_500_000,  # €1.50
        "ctr": 5.0,  # 5%
        "budget_micros": 100_000_000,  # €100
        "device": "DESKTOP",
    }
    defaults.update(overrides)
    return defaults


def make_ga4_traffic_dict(**overrides) -> dict:
    """Create a GA4 traffic dict matching the database schema."""
    defaults = {
        "date": date(2026, 2, 1),
        "source": "google",
        "medium": "cpc",
        "campaign_name": "(ads)",
        "sessions": 100,
        "users": 85,
        "new_users": 70,
        "bounce_rate": 45.0,
        "avg_session_duration": 120.5,
        "pages_per_session": 3.2,
    }
    defaults.update(overrides)
    return defaults
