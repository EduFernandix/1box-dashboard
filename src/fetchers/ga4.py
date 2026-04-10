"""GA4 Data API fetcher.

Uses the google-analytics-data (v1beta) Python client to fetch
traffic, conversion, and page-level metrics from Google Analytics 4.
All sync API calls are wrapped with asyncio.to_thread().
"""

import asyncio
import logging
from datetime import date, datetime
from pathlib import Path
from typing import Any

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Metric,
    RunReportRequest,
    RunReportResponse,
)
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account

from config.settings import settings

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
SERVICE_ACCOUNT_PATH = PROJECT_ROOT / "credentials" / "gen-lang-client-0243781846-d4bc18d0f557.json"


class GA4Fetcher:
    """Fetches session, conversion, and page data from GA4 Data API.

    Tries service account first, falls back to OAuth2.
    """

    def __init__(self) -> None:
        """Initialize the GA4 Data API client."""
        creds = None

        # Try service account first
        if SERVICE_ACCOUNT_PATH.exists():
            try:
                creds = service_account.Credentials.from_service_account_file(
                    str(SERVICE_ACCOUNT_PATH),
                    scopes=["https://www.googleapis.com/auth/analytics.readonly"],
                )
                logger.info("Using service account credentials")
            except Exception as e:
                logger.warning(f"Service account failed: {e}")

        # Fallback to OAuth2
        if creds is None and settings.google_ads_refresh_token:
            creds = Credentials(
                token=None,
                refresh_token=settings.google_ads_refresh_token,
                token_uri="https://oauth2.googleapis.com/token",
                client_id=settings.google_ads_client_id,
                client_secret=settings.google_ads_client_secret,
                scopes=["https://www.googleapis.com/auth/analytics.readonly"],
            )
            logger.info("Using OAuth2 credentials")

        if creds is None:
            raise RuntimeError("No GA4 credentials configured")

        self._client = BetaAnalyticsDataClient(credentials=creds)
        self._property = f"properties/{settings.ga4_property_id}"

    def _make_date_range(self, start: date, end: date) -> DateRange:
        """Build a GA4 DateRange from Python date objects."""
        return DateRange(
            start_date=start.strftime("%Y-%m-%d"),
            end_date=end.strftime("%Y-%m-%d"),
        )

    @staticmethod
    def _parse_date(value: str) -> date:
        """Parse GA4 date string (YYYYMMDD) to Python date."""
        return datetime.strptime(value, "%Y%m%d").date()

    @staticmethod
    def _safe_int(value: str) -> int:
        """Parse a metric value to int, defaulting to 0."""
        try:
            return int(value)
        except (ValueError, TypeError):
            return 0

    @staticmethod
    def _safe_float(value: str) -> float:
        """Parse a metric value to float, defaulting to 0.0."""
        try:
            return float(value)
        except (ValueError, TypeError):
            return 0.0

    # ------------------------------------------------------------------
    # Sync internal methods
    # ------------------------------------------------------------------

    def _fetch_traffic_sync(
        self, start: date, end: date
    ) -> list[dict[str, Any]]:
        """Fetch session/traffic data by source, medium, campaign."""
        request = RunReportRequest(
            property=self._property,
            dimensions=[
                Dimension(name="date"),
                Dimension(name="sessionSource"),
                Dimension(name="sessionMedium"),
                Dimension(name="sessionCampaignName"),
            ],
            metrics=[
                Metric(name="sessions"),
                Metric(name="totalUsers"),
                Metric(name="newUsers"),
                Metric(name="bounceRate"),
                Metric(name="averageSessionDuration"),
                Metric(name="screenPageViewsPerSession"),
            ],
            date_ranges=[self._make_date_range(start, end)],
        )
        response = self._client.run_report(request)
        return self._parse_traffic_response(response)

    def _parse_traffic_response(
        self, response: RunReportResponse
    ) -> list[dict[str, Any]]:
        """Parse GA4 traffic report response into dicts."""
        rows = []
        for row in response.rows:
            dims = row.dimension_values
            vals = row.metric_values

            source = dims[1].value or "(direct)"
            medium = dims[2].value or "(none)"
            campaign = dims[3].value or "(not set)"

            # GA4 bounceRate is a ratio (0-1); store as percentage
            bounce_rate = self._safe_float(vals[3].value) * 100

            rows.append(
                {
                    "date": self._parse_date(dims[0].value),
                    "source": source,
                    "medium": medium,
                    "campaign_name": campaign,
                    "sessions": self._safe_int(vals[0].value),
                    "users": self._safe_int(vals[1].value),
                    "new_users": self._safe_int(vals[2].value),
                    "bounce_rate": round(bounce_rate, 1),
                    "avg_session_duration": round(
                        self._safe_float(vals[4].value), 1
                    ),
                    "pages_per_session": round(
                        self._safe_float(vals[5].value), 1
                    ),
                }
            )

        logger.info(f"Fetched {len(rows)} GA4 traffic rows")
        return rows

    def _fetch_conversions_sync(
        self, start: date, end: date
    ) -> list[dict[str, Any]]:
        """Fetch conversion events by source and medium."""
        request = RunReportRequest(
            property=self._property,
            dimensions=[
                Dimension(name="date"),
                Dimension(name="eventName"),
                Dimension(name="sessionSource"),
                Dimension(name="sessionMedium"),
            ],
            metrics=[
                Metric(name="eventCount"),
                Metric(name="eventValue"),
            ],
            date_ranges=[self._make_date_range(start, end)],
        )
        response = self._client.run_report(request)
        return self._parse_conversions_response(response)

    def _parse_conversions_response(
        self, response: RunReportResponse
    ) -> list[dict[str, Any]]:
        """Parse GA4 conversions report response into dicts."""
        rows = []
        for row in response.rows:
            dims = row.dimension_values
            vals = row.metric_values

            rows.append(
                {
                    "date": self._parse_date(dims[0].value),
                    "event_name": dims[1].value,
                    "source": dims[2].value or "(direct)",
                    "medium": dims[3].value or "(none)",
                    "event_count": self._safe_int(vals[0].value),
                    "conversion_value": round(
                        self._safe_float(vals[1].value), 2
                    ),
                }
            )

        logger.info(f"Fetched {len(rows)} GA4 conversion rows")
        return rows

    def _fetch_pages_sync(
        self, start: date, end: date
    ) -> list[dict[str, Any]]:
        """Fetch page-level metrics."""
        request = RunReportRequest(
            property=self._property,
            dimensions=[
                Dimension(name="date"),
                Dimension(name="pagePath"),
                Dimension(name="pageTitle"),
            ],
            metrics=[
                Metric(name="screenPageViews"),
                Metric(name="sessions"),
                Metric(name="userEngagementDuration"),
                Metric(name="bounceRate"),
            ],
            date_ranges=[self._make_date_range(start, end)],
        )
        response = self._client.run_report(request)
        return self._parse_pages_response(response)

    def _parse_pages_response(
        self, response: RunReportResponse
    ) -> list[dict[str, Any]]:
        """Parse GA4 pages report response into dicts."""
        rows = []
        for row in response.rows:
            dims = row.dimension_values
            vals = row.metric_values

            views = self._safe_int(vals[0].value)
            unique_views = self._safe_int(vals[1].value)  # sessions as proxy
            engagement_duration = self._safe_float(vals[2].value)
            bounce_rate = self._safe_float(vals[3].value) * 100

            # avg_time_on_page: total engagement / views (avoid division by 0)
            avg_time = (
                round(engagement_duration / views, 1) if views > 0 else 0.0
            )

            rows.append(
                {
                    "date": self._parse_date(dims[0].value),
                    "page_path": dims[1].value,
                    "page_title": dims[2].value or "",
                    "views": views,
                    "unique_views": unique_views,
                    "avg_time_on_page": avg_time,
                    "bounce_rate": round(bounce_rate, 1),
                    "exit_rate": 0.0,  # GA4 doesn't have a direct exit rate metric
                }
            )

        logger.info(f"Fetched {len(rows)} GA4 page rows")
        return rows

    def _fetch_conversions_by_location_sync(
        self, start: date, end: date
    ) -> list[dict[str, Any]]:
        """Fetch conversion events grouped by eventName and pagePath."""
        request = RunReportRequest(
            property=self._property,
            dimensions=[
                Dimension(name="eventName"),
                Dimension(name="pagePath"),
            ],
            metrics=[
                Metric(name="eventCount"),
            ],
            date_ranges=[self._make_date_range(start, end)],
        )
        response = self._client.run_report(request)
        rows = []
        for row in response.rows:
            dims = row.dimension_values
            vals = row.metric_values
            rows.append({
                "event_name": dims[0].value,
                "page_path": dims[1].value,
                "event_count": self._safe_int(vals[0].value),
            })
        logger.info(f"Fetched {len(rows)} GA4 conversion-by-location rows")
        return rows

    def _test_connection_sync(self) -> bool:
        """Verify GA4 API credentials and property access."""
        request = RunReportRequest(
            property=self._property,
            dimensions=[Dimension(name="date")],
            metrics=[Metric(name="sessions")],
            date_ranges=[
                DateRange(start_date="yesterday", end_date="yesterday")
            ],
        )
        self._client.run_report(request)
        return True

    # ------------------------------------------------------------------
    # Async public API
    # ------------------------------------------------------------------

    async def fetch_traffic(
        self, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        """Fetch session/traffic data by source, medium, and campaign."""
        return await asyncio.to_thread(
            self._fetch_traffic_sync, start_date, end_date
        )

    async def fetch_conversions(
        self, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        """Fetch conversion events by source and medium."""
        return await asyncio.to_thread(
            self._fetch_conversions_sync, start_date, end_date
        )

    async def fetch_pages(
        self, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        """Fetch page-level metrics (views, bounce rate, time on page)."""
        return await asyncio.to_thread(
            self._fetch_pages_sync, start_date, end_date
        )

    async def fetch_conversions_by_location(
        self, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        """Fetch conversion events grouped by eventName and pagePath."""
        return await asyncio.to_thread(
            self._fetch_conversions_by_location_sync, start_date, end_date
        )

    async def test_connection(self) -> bool:
        """Verify GA4 API credentials and property access."""
        try:
            return await asyncio.to_thread(self._test_connection_sync)
        except Exception as e:
            logger.error(f"GA4 connection test failed: {e}")
            return False
