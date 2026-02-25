"""ETL pipeline for fetching and storing marketing data.

Orchestrates the Google Ads and GA4 fetchers, transforms raw API
responses into database records, and handles upserts with conflict
resolution based on unique constraints.
"""

import logging
from datetime import date, datetime, timedelta, timezone
from typing import Any

from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from config.settings import settings
from src.models.database import (
    AdGroup,
    Campaign,
    GA4Conversion,
    GA4Page,
    GA4Traffic,
    Keyword,
    PipelineRun,
    async_session,
)

logger = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Upsert configuration per model
# Maps each model to its conflict columns (UniqueConstraint) and
# the columns to update when a conflict occurs.
# ------------------------------------------------------------------

UPSERT_CONFIG: dict[type, dict[str, list[str]]] = {
    Campaign: {
        "conflict": ["campaign_id", "date"],
        "update": [
            "campaign_name", "campaign_type", "status", "impressions",
            "clicks", "cost_micros", "conversions", "conversion_value",
            "average_cpc_micros", "ctr", "budget_micros", "device",
        ],
    },
    AdGroup: {
        "conflict": ["ad_group_id", "date"],
        "update": [
            "ad_group_name", "campaign_id", "impressions", "clicks",
            "cost_micros", "conversions", "ctr",
        ],
    },
    Keyword: {
        "conflict": ["keyword_id", "date"],
        "update": [
            "keyword_text", "match_type", "ad_group_id", "campaign_id",
            "impressions", "clicks", "cost_micros", "conversions", "ctr",
            "average_cpc_micros", "quality_score", "expected_ctr",
            "ad_relevance", "landing_page_experience",
        ],
    },
    GA4Traffic: {
        "conflict": ["date", "source", "medium", "campaign_name"],
        "update": [
            "sessions", "users", "new_users", "bounce_rate",
            "avg_session_duration", "pages_per_session",
        ],
    },
    GA4Conversion: {
        "conflict": ["date", "event_name", "source", "medium"],
        "update": ["event_count", "conversion_value"],
    },
    GA4Page: {
        "conflict": ["date", "page_path"],
        "update": [
            "page_title", "views", "unique_views",
            "avg_time_on_page", "bounce_rate", "exit_rate",
        ],
    },
}


def _has_google_ads_credentials() -> bool:
    """Check if Google Ads credentials are configured."""
    return bool(
        settings.google_ads_developer_token
        and settings.google_ads_refresh_token
        and settings.google_ads_customer_id
    )


def _has_ga4_credentials() -> bool:
    """Check if GA4 credentials are configured."""
    return bool(settings.ga4_property_id and settings.google_ads_refresh_token)


async def _upsert_rows(
    session: Any, model_class: type, rows: list[dict[str, Any]]
) -> int:
    """Upsert rows using SQLite's ON CONFLICT DO UPDATE.

    Uses the unique constraints defined in UPSERT_CONFIG to handle
    conflicts. When a row with the same key exists, its metric
    columns are updated with the new values.

    Returns the number of rows processed.
    """
    if not rows:
        return 0

    config = UPSERT_CONFIG[model_class]

    stmt = sqlite_insert(model_class).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=config["conflict"],
        set_={col: stmt.excluded[col] for col in config["update"]},
    )
    await session.execute(stmt)
    return len(rows)


async def _fetch_and_store_google_ads(
    start: date, end: date, summary: dict[str, Any]
) -> None:
    """Fetch Google Ads data and upsert into the database."""
    from src.fetchers.google_ads import GoogleAdsFetcher

    try:
        fetcher = GoogleAdsFetcher()
    except Exception as e:
        msg = f"Google Ads init failed: {e}"
        logger.error(msg)
        summary["errors"].append(msg)
        return

    # Campaigns
    try:
        campaigns = await fetcher.fetch_campaigns(start, end)
        summary["records_fetched"] += len(campaigns)
        async with async_session() as session:
            inserted = await _upsert_rows(session, Campaign, campaigns)
            await session.commit()
            summary["records_inserted"] += inserted
            logger.info(f"Upserted {inserted} campaign rows")
    except Exception as e:
        msg = f"Campaign fetch/store failed: {e}"
        logger.error(msg)
        summary["errors"].append(msg)

    # Ad Groups
    try:
        ad_groups = await fetcher.fetch_ad_groups(start, end)
        summary["records_fetched"] += len(ad_groups)
        async with async_session() as session:
            inserted = await _upsert_rows(session, AdGroup, ad_groups)
            await session.commit()
            summary["records_inserted"] += inserted
            logger.info(f"Upserted {inserted} ad group rows")
    except Exception as e:
        msg = f"Ad group fetch/store failed: {e}"
        logger.error(msg)
        summary["errors"].append(msg)

    # Keywords
    try:
        keywords = await fetcher.fetch_keywords(start, end)
        summary["records_fetched"] += len(keywords)
        async with async_session() as session:
            inserted = await _upsert_rows(session, Keyword, keywords)
            await session.commit()
            summary["records_inserted"] += inserted
            logger.info(f"Upserted {inserted} keyword rows")
    except Exception as e:
        msg = f"Keyword fetch/store failed: {e}"
        logger.error(msg)
        summary["errors"].append(msg)


async def _fetch_and_store_ga4(
    start: date, end: date, summary: dict[str, Any]
) -> None:
    """Fetch GA4 data and upsert into the database."""
    from src.fetchers.ga4 import GA4Fetcher

    try:
        fetcher = GA4Fetcher()
    except Exception as e:
        msg = f"GA4 init failed: {e}"
        logger.error(msg)
        summary["errors"].append(msg)
        return

    # Traffic
    try:
        traffic = await fetcher.fetch_traffic(start, end)
        summary["records_fetched"] += len(traffic)
        async with async_session() as session:
            inserted = await _upsert_rows(session, GA4Traffic, traffic)
            await session.commit()
            summary["records_inserted"] += inserted
            logger.info(f"Upserted {inserted} GA4 traffic rows")
    except Exception as e:
        msg = f"GA4 traffic fetch/store failed: {e}"
        logger.error(msg)
        summary["errors"].append(msg)

    # Conversions
    try:
        conversions = await fetcher.fetch_conversions(start, end)
        summary["records_fetched"] += len(conversions)
        async with async_session() as session:
            inserted = await _upsert_rows(session, GA4Conversion, conversions)
            await session.commit()
            summary["records_inserted"] += inserted
            logger.info(f"Upserted {inserted} GA4 conversion rows")
    except Exception as e:
        msg = f"GA4 conversions fetch/store failed: {e}"
        logger.error(msg)
        summary["errors"].append(msg)

    # Pages
    try:
        pages = await fetcher.fetch_pages(start, end)
        summary["records_fetched"] += len(pages)
        async with async_session() as session:
            inserted = await _upsert_rows(session, GA4Page, pages)
            await session.commit()
            summary["records_inserted"] += inserted
            logger.info(f"Upserted {inserted} GA4 page rows")
    except Exception as e:
        msg = f"GA4 pages fetch/store failed: {e}"
        logger.error(msg)
        summary["errors"].append(msg)


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
    if start_date is None:
        start_date = date.today() - timedelta(days=1)
    if end_date is None:
        end_date = date.today() - timedelta(days=1)

    logger.info(
        f"Pipeline starting: source={source}, "
        f"dates={start_date} → {end_date}"
    )

    summary: dict[str, Any] = {
        "source": source,
        "start_date": str(start_date),
        "end_date": str(end_date),
        "records_fetched": 0,
        "records_inserted": 0,
        "errors": [],
    }

    # 1. Create PipelineRun record
    async with async_session() as session:
        pipeline_run = PipelineRun(source=source, status="running")
        session.add(pipeline_run)
        await session.commit()
        await session.refresh(pipeline_run)
        run_id = pipeline_run.id

    try:
        # 2. Fetch and store data
        if source in ("all", "google_ads") and _has_google_ads_credentials():
            await _fetch_and_store_google_ads(start_date, end_date, summary)
        elif source in ("all", "google_ads"):
            logger.warning("Google Ads credentials not configured, skipping")

        if source in ("all", "ga4") and _has_ga4_credentials():
            await _fetch_and_store_ga4(start_date, end_date, summary)
        elif source in ("all", "ga4"):
            logger.warning("GA4 credentials not configured, skipping")

        # 3. Update PipelineRun
        status = "success" if not summary["errors"] else "failed"
        async with async_session() as session:
            run = await session.get(PipelineRun, run_id)
            if run:
                run.status = status
                run.completed_at = datetime.now(tz=timezone.utc)
                run.records_fetched = summary["records_fetched"]
                run.records_inserted = summary["records_inserted"]
                run.error_message = (
                    "; ".join(summary["errors"])
                    if summary["errors"]
                    else None
                )
                await session.commit()

    except Exception as e:
        logger.exception("Pipeline failed with unhandled exception")
        async with async_session() as session:
            run = await session.get(PipelineRun, run_id)
            if run:
                run.status = "failed"
                run.completed_at = datetime.now(tz=timezone.utc)
                run.error_message = str(e)
                await session.commit()
        summary["errors"].append(str(e))

    logger.info(
        f"Pipeline finished: fetched={summary['records_fetched']}, "
        f"inserted={summary['records_inserted']}, "
        f"errors={len(summary['errors'])}"
    )
    return summary
