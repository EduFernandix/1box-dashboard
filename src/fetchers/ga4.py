"""GA4 Data API fetcher.

Uses the google-analytics-data (v1beta) Python client to fetch
traffic, conversion, and page-level metrics from Google Analytics 4.
"""

from datetime import date
from typing import Any


class GA4Fetcher:
    """Fetches session, conversion, and page data from GA4 Data API.

    Requires GA4 Property ID and OAuth2/service account credentials.
    """

    def __init__(self) -> None:
        """Initialize the GA4 Data API client."""
        # TODO: Initialize google.analytics.data_v1beta.BetaAnalyticsDataClient
        raise NotImplementedError("GA4 fetcher not yet implemented")

    async def fetch_traffic(
        self, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        """Fetch session/traffic data by source, medium, and campaign.

        Dimensions: date, sessionSource, sessionMedium, sessionCampaignName.
        Metrics: sessions, totalUsers, newUsers, bounceRate,
                 averageSessionDuration, screenPageViewsPerSession.
        """
        raise NotImplementedError

    async def fetch_conversions(
        self, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        """Fetch conversion events by source and medium."""
        raise NotImplementedError

    async def fetch_pages(
        self, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        """Fetch page-level metrics (views, bounce rate, time on page)."""
        raise NotImplementedError

    async def test_connection(self) -> bool:
        """Verify GA4 API credentials and property access."""
        raise NotImplementedError
