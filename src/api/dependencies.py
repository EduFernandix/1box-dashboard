"""Shared FastAPI dependencies for API routers."""

from datetime import date, timedelta
from typing import Annotated, AsyncGenerator

from fastapi import Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.database import async_session


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async database session."""
    async with async_session() as session:
        yield session


# Type alias for dependency injection
DbSession = Annotated[AsyncSession, Depends(get_db_session)]


def date_range_params(
    start_date: date | None = Query(
        default=None, description="Start date (YYYY-MM-DD). Defaults to 30 days ago."
    ),
    end_date: date | None = Query(
        default=None, description="End date (YYYY-MM-DD). Defaults to today."
    ),
) -> tuple[date, date]:
    """Parse and validate date range query parameters."""
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = end_date - timedelta(days=30)
    return start_date, end_date


# Type alias for dependency injection
DateRange = Annotated[tuple[date, date], Depends(date_range_params)]
