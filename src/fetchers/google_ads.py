"""Google Ads API data fetcher.

Uses the google-ads Python client library with GAQL queries to fetch
campaign, ad group, and keyword metrics. All sync gRPC calls are
wrapped with asyncio.to_thread() to avoid blocking the event loop.
"""

import asyncio
import logging
import time
from datetime import date, datetime
from typing import Any

from google.ads.googleads.client import GoogleAdsClient
from google.ads.googleads.errors import GoogleAdsException

from config.settings import settings

logger = logging.getLogger(__name__)

# Maximum retry attempts for transient API errors
MAX_RETRIES = 3
RETRY_BACKOFF_BASE = 2  # seconds


class GoogleAdsFetcher:
    """Fetches campaign, ad group, and keyword data from Google Ads API.

    Requires OAuth2 credentials configured in .env. Initializes the
    GoogleAdsClient from a settings dict (not YAML file).
    """

    def __init__(self) -> None:
        """Initialize the Google Ads client from settings."""
        config = {
            "developer_token": settings.google_ads_developer_token,
            "client_id": settings.google_ads_client_id,
            "client_secret": settings.google_ads_client_secret,
            "refresh_token": settings.google_ads_refresh_token,
            "use_proto_plus": True,
        }
        if settings.google_ads_login_customer_id:
            config["login_customer_id"] = settings.google_ads_login_customer_id

        self._client = GoogleAdsClient.load_from_dict(config)
        self._customer_id = settings.google_ads_customer_id.replace("-", "")

    def _get_service(self):
        """Get the GoogleAdsService for running GAQL queries."""
        return self._client.get_service("GoogleAdsService")

    def _query_with_retry(self, query: str) -> list:
        """Execute a GAQL query with retry for transient errors."""
        ga_service = self._get_service()
        last_error = None

        for attempt in range(MAX_RETRIES):
            try:
                stream = ga_service.search_stream(
                    customer_id=self._customer_id, query=query
                )
                results = []
                for batch in stream:
                    results.extend(batch.results)
                return results
            except GoogleAdsException as e:
                last_error = e
                # Retry on transient errors (INTERNAL, UNAVAILABLE, DEADLINE_EXCEEDED)
                retryable = any(
                    err.error_code.internal_error or err.error_code.quota_error
                    for err in e.failure.errors
                    if hasattr(err.error_code, "internal_error")
                    or hasattr(err.error_code, "quota_error")
                )
                if not retryable or attempt == MAX_RETRIES - 1:
                    raise
                wait = RETRY_BACKOFF_BASE ** (attempt + 1)
                logger.warning(
                    f"Google Ads API transient error (attempt {attempt + 1}), "
                    f"retrying in {wait}s: {e.failure.errors[0].message}"
                )
                time.sleep(wait)

        raise last_error  # type: ignore[misc]

    # ------------------------------------------------------------------
    # Sync internal methods (run in thread via asyncio.to_thread)
    # ------------------------------------------------------------------

    def _fetch_campaigns_sync(
        self, start: date, end: date
    ) -> list[dict[str, Any]]:
        """Fetch campaign-level metrics via GAQL."""
        query = f"""
            SELECT
              campaign.id,
              campaign.name,
              campaign.advertising_channel_type,
              campaign.status,
              campaign_budget.amount_micros,
              metrics.cost_micros,
              metrics.clicks,
              metrics.impressions,
              metrics.ctr,
              metrics.average_cpc,
              metrics.conversions,
              metrics.conversions_value,
              segments.date,
              segments.device
            FROM campaign
            WHERE segments.date BETWEEN '{start.strftime("%Y-%m-%d")}'
              AND '{end.strftime("%Y-%m-%d")}'
              AND campaign.status != 'REMOVED'
            ORDER BY segments.date DESC
        """
        results = self._query_with_retry(query)

        rows = []
        for row in results:
            rows.append(
                {
                    "campaign_id": str(row.campaign.id),
                    "campaign_name": row.campaign.name,
                    "campaign_type": row.campaign.advertising_channel_type.name,
                    "status": row.campaign.status.name,
                    "date": datetime.strptime(
                        row.segments.date, "%Y-%m-%d"
                    ).date(),
                    "impressions": row.metrics.impressions,
                    "clicks": row.metrics.clicks,
                    "cost_micros": row.metrics.cost_micros,
                    "conversions": row.metrics.conversions,
                    "conversion_value": row.metrics.conversions_value,
                    "average_cpc_micros": row.metrics.average_cpc,
                    "ctr": row.metrics.ctr * 100,  # ratio → percentage
                    "budget_micros": row.campaign_budget.amount_micros,
                    "device": row.segments.device.name,
                }
            )

        logger.info(
            f"Fetched {len(rows)} campaign rows ({start} → {end})"
        )
        return rows

    def _fetch_ad_groups_sync(
        self, start: date, end: date
    ) -> list[dict[str, Any]]:
        """Fetch ad group-level metrics via GAQL."""
        query = f"""
            SELECT
              ad_group.id,
              ad_group.name,
              campaign.id,
              metrics.cost_micros,
              metrics.clicks,
              metrics.impressions,
              metrics.ctr,
              metrics.conversions,
              segments.date
            FROM ad_group
            WHERE segments.date BETWEEN '{start.strftime("%Y-%m-%d")}'
              AND '{end.strftime("%Y-%m-%d")}'
              AND ad_group.status != 'REMOVED'
            ORDER BY segments.date DESC
        """
        results = self._query_with_retry(query)

        rows = []
        for row in results:
            rows.append(
                {
                    "ad_group_id": str(row.ad_group.id),
                    "ad_group_name": row.ad_group.name,
                    "campaign_id": str(row.campaign.id),
                    "date": datetime.strptime(
                        row.segments.date, "%Y-%m-%d"
                    ).date(),
                    "impressions": row.metrics.impressions,
                    "clicks": row.metrics.clicks,
                    "cost_micros": row.metrics.cost_micros,
                    "conversions": row.metrics.conversions,
                    "ctr": row.metrics.ctr * 100,
                }
            )

        logger.info(
            f"Fetched {len(rows)} ad group rows ({start} → {end})"
        )
        return rows

    def _fetch_keywords_sync(
        self, start: date, end: date
    ) -> list[dict[str, Any]]:
        """Fetch keyword-level metrics with quality scores via GAQL."""
        query = f"""
            SELECT
              ad_group_criterion.criterion_id,
              ad_group_criterion.keyword.text,
              ad_group_criterion.keyword.match_type,
              ad_group.id,
              campaign.id,
              metrics.impressions,
              metrics.clicks,
              metrics.cost_micros,
              metrics.ctr,
              metrics.average_cpc,
              metrics.conversions,
              ad_group_criterion.quality_info.quality_score,
              ad_group_criterion.quality_info.creative_quality_score,
              ad_group_criterion.quality_info.post_click_quality_score,
              ad_group_criterion.quality_info.search_predicted_ctr,
              segments.date
            FROM keyword_view
            WHERE segments.date BETWEEN '{start.strftime("%Y-%m-%d")}'
              AND '{end.strftime("%Y-%m-%d")}'
            ORDER BY metrics.clicks DESC
        """
        results = self._query_with_retry(query)

        rows = []
        for row in results:
            # Quality score: 0 from API means "not available" → store as None
            qs = row.ad_group_criterion.quality_info.quality_score
            quality_score = qs if qs > 0 else None

            # Quality sub-scores come as enums (BELOW_AVERAGE, AVERAGE, ABOVE_AVERAGE)
            qi = row.ad_group_criterion.quality_info
            expected_ctr = (
                qi.search_predicted_ctr.name
                if qi.search_predicted_ctr
                else None
            )
            ad_relevance = (
                qi.creative_quality_score.name
                if qi.creative_quality_score
                else None
            )
            landing_page = (
                qi.post_click_quality_score.name
                if qi.post_click_quality_score
                else None
            )
            # Filter out UNSPECIFIED / UNKNOWN
            if expected_ctr in ("UNSPECIFIED", "UNKNOWN"):
                expected_ctr = None
            if ad_relevance in ("UNSPECIFIED", "UNKNOWN"):
                ad_relevance = None
            if landing_page in ("UNSPECIFIED", "UNKNOWN"):
                landing_page = None

            rows.append(
                {
                    "keyword_id": str(
                        row.ad_group_criterion.criterion_id
                    ),
                    "keyword_text": row.ad_group_criterion.keyword.text,
                    "match_type": row.ad_group_criterion.keyword.match_type.name,
                    "ad_group_id": str(row.ad_group.id),
                    "campaign_id": str(row.campaign.id),
                    "date": datetime.strptime(
                        row.segments.date, "%Y-%m-%d"
                    ).date(),
                    "impressions": row.metrics.impressions,
                    "clicks": row.metrics.clicks,
                    "cost_micros": row.metrics.cost_micros,
                    "conversions": row.metrics.conversions,
                    "ctr": row.metrics.ctr * 100,
                    "average_cpc_micros": row.metrics.average_cpc,
                    "quality_score": quality_score,
                    "expected_ctr": expected_ctr,
                    "ad_relevance": ad_relevance,
                    "landing_page_experience": landing_page,
                }
            )

        logger.info(
            f"Fetched {len(rows)} keyword rows ({start} → {end})"
        )
        return rows

    def _test_connection_sync(self) -> bool:
        """Verify Google Ads API credentials with a minimal query."""
        ga_service = self._get_service()
        query = "SELECT customer.id FROM customer LIMIT 1"
        response = ga_service.search(
            customer_id=self._customer_id, query=query
        )
        list(response)  # Force execution
        return True

    # ------------------------------------------------------------------
    # Async public API
    # ------------------------------------------------------------------

    async def fetch_campaigns(
        self, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        """Fetch campaign-level metrics for a date range."""
        return await asyncio.to_thread(
            self._fetch_campaigns_sync, start_date, end_date
        )

    async def fetch_ad_groups(
        self, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        """Fetch ad group-level metrics for a date range."""
        return await asyncio.to_thread(
            self._fetch_ad_groups_sync, start_date, end_date
        )

    async def fetch_keywords(
        self, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        """Fetch keyword-level metrics including quality scores."""
        return await asyncio.to_thread(
            self._fetch_keywords_sync, start_date, end_date
        )

    async def test_connection(self) -> bool:
        """Verify Google Ads API credentials are working."""
        try:
            return await asyncio.to_thread(self._test_connection_sync)
        except Exception as e:
            logger.error(f"Google Ads connection test failed: {e}")
            return False
