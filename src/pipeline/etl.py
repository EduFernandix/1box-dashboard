"""ETL pipeline for fetching and storing marketing data.

Orchestrates the Google Ads and GA4 fetchers, transforms raw API
responses into database records, and handles upserts.
"""

from datetime import date, datetime
from typing import Any

from src.models.database import PipelineRun, async_session


async def run_pipeline(
    source: str = "all",
    start_date: date | None = None,
    end_date: date | None = None,
) -> dict[str, Any]:
    """Execute the ETL pipeline for the specified source(s).

    Args:
        source: Which data to fetch — "google_ads", "ga4", or "all".
        start_date: Start of the fetch window (defaults to yesterday).
        end_date: End of the fetch window (defaults to yesterday).

    Returns:
        Summary dict with records_fetched, records_inserted, errors.
    """
    # TODO: Implement in Phase 2
    # 1. Create PipelineRun record (status=running)
    # 2. Call fetchers based on source
    # 3. Transform and upsert into database
    # 4. Update PipelineRun (status=success/failed)
    raise NotImplementedError("ETL pipeline not yet implemented")
