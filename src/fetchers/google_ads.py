"""Google Ads API data fetcher.

Uses the google-ads Python client library with GAQL queries to fetch
campaign, ad group, and keyword metrics.
"""

from datetime import date
from typing import Any


class GoogleAdsFetcher:
    """Fetches campaign, ad group, and keyword data from Google Ads API.

    Requires OAuth2 credentials configured in .env and config/google-ads.yaml.
    """

    def __init__(self) -> None:
        """Initialize the Google Ads client."""
        # TODO: Initialize google.ads.googleads.client.GoogleAdsClient
        raise NotImplementedError("Google Ads fetcher not yet implemented")

    async def fetch_campaigns(
        self, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        """Fetch campaign-level metrics for a date range.

        GAQL query selects: campaign.id, campaign.name, metrics.cost_micros,
        metrics.clicks, metrics.impressions, metrics.ctr, metrics.average_cpc,
        metrics.conversions, metrics.conversions_value, segments.date,
        segments.device.
        """
        raise NotImplementedError

    async def fetch_ad_groups(
        self, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        """Fetch ad group-level metrics for a date range."""
        raise NotImplementedError

    async def fetch_keywords(
        self, start_date: date, end_date: date
    ) -> list[dict[str, Any]]:
        """Fetch keyword-level metrics including quality scores."""
        raise NotImplementedError

    async def test_connection(self) -> bool:
        """Verify Google Ads API credentials are working."""
        raise NotImplementedError
