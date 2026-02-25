"""Tests for Google Ads and GA4 data fetchers.

These tests verify the transformation logic without calling real APIs.
All external clients are mocked.
"""

from datetime import date
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.fetchers.ga4 import GA4Fetcher
from src.fetchers.google_ads import GoogleAdsFetcher


# ---------------------------------------------------------------
# Helpers — fake protobuf-like objects for Google Ads responses
# ---------------------------------------------------------------


def _make_ads_campaign_row(
    campaign_id: int = 123456,
    campaign_name: str = "Brand NL",
    channel_type_name: str = "SEARCH",
    status_name: str = "ENABLED",
    budget_micros: int = 50_000_000,
    cost_micros: int = 25_000_000,
    clicks: int = 100,
    impressions: int = 2000,
    ctr: float = 0.05,  # ratio
    average_cpc: int = 250_000,
    conversions: float = 5.0,
    conversions_value: float = 400.0,
    seg_date: str = "2026-02-01",
    device_name: str = "DESKTOP",
) -> SimpleNamespace:
    """Build a fake Google Ads campaign row mimicking protobuf objects."""
    return SimpleNamespace(
        campaign=SimpleNamespace(
            id=campaign_id,
            name=campaign_name,
            advertising_channel_type=SimpleNamespace(name=channel_type_name),
            status=SimpleNamespace(name=status_name),
        ),
        campaign_budget=SimpleNamespace(amount_micros=budget_micros),
        metrics=SimpleNamespace(
            cost_micros=cost_micros,
            clicks=clicks,
            impressions=impressions,
            ctr=ctr,
            average_cpc=average_cpc,
            conversions=conversions,
            conversions_value=conversions_value,
        ),
        segments=SimpleNamespace(
            date=seg_date,
            device=SimpleNamespace(name=device_name),
        ),
    )


def _make_ads_keyword_row(
    criterion_id: int = 999,
    keyword_text: str = "self storage",
    match_type_name: str = "EXACT",
    ad_group_id: int = 555,
    campaign_id: int = 123456,
    quality_score: int = 7,
    predicted_ctr_name: str = "ABOVE_AVERAGE",
    creative_quality_name: str = "AVERAGE",
    post_click_quality_name: str = "BELOW_AVERAGE",
    ctr: float = 0.06,
    seg_date: str = "2026-02-01",
) -> SimpleNamespace:
    """Build a fake Google Ads keyword row."""
    return SimpleNamespace(
        ad_group_criterion=SimpleNamespace(
            criterion_id=criterion_id,
            keyword=SimpleNamespace(
                text=keyword_text,
                match_type=SimpleNamespace(name=match_type_name),
            ),
            quality_info=SimpleNamespace(
                quality_score=quality_score,
                search_predicted_ctr=SimpleNamespace(name=predicted_ctr_name),
                creative_quality_score=SimpleNamespace(name=creative_quality_name),
                post_click_quality_score=SimpleNamespace(name=post_click_quality_name),
            ),
        ),
        ad_group=SimpleNamespace(id=ad_group_id),
        campaign=SimpleNamespace(id=campaign_id),
        metrics=SimpleNamespace(
            impressions=500,
            clicks=30,
            cost_micros=15_000_000,
            ctr=ctr,
            average_cpc=500_000,
            conversions=2.0,
        ),
        segments=SimpleNamespace(date=seg_date),
    )


# ---------------------------------------------------------------
# Helpers — fake GA4 RunReportResponse
# ---------------------------------------------------------------


def _make_ga4_row(dimension_values: list[str], metric_values: list[str]):
    """Build a fake GA4 report row."""
    return SimpleNamespace(
        dimension_values=[SimpleNamespace(value=v) for v in dimension_values],
        metric_values=[SimpleNamespace(value=v) for v in metric_values],
    )


def _make_ga4_response(rows: list) -> SimpleNamespace:
    """Build a fake RunReportResponse."""
    return SimpleNamespace(rows=rows)


# ---------------------------------------------------------------
# Google Ads tests
# ---------------------------------------------------------------


class TestGoogleAdsFetcherTransform:
    """Tests for Google Ads data transformation logic."""

    @patch("src.fetchers.google_ads.GoogleAdsClient")
    def _create_fetcher(self, mock_client_class):
        """Create a fetcher with mocked client."""
        mock_client_class.load_from_dict.return_value = MagicMock()
        with patch("src.fetchers.google_ads.settings") as mock_settings:
            mock_settings.google_ads_developer_token = "test"
            mock_settings.google_ads_client_id = "test"
            mock_settings.google_ads_client_secret = "test"
            mock_settings.google_ads_refresh_token = "test"
            mock_settings.google_ads_login_customer_id = ""
            mock_settings.google_ads_customer_id = "123-456-7890"
            fetcher = GoogleAdsFetcher()
        return fetcher

    def test_campaign_id_converted_to_string(self):
        """campaign.id (int) should become str in the output."""
        fetcher = self._create_fetcher()
        row = _make_ads_campaign_row(campaign_id=98765)

        fetcher._query_with_retry = MagicMock(return_value=[row])
        results = fetcher._fetch_campaigns_sync(date(2026, 2, 1), date(2026, 2, 1))

        assert results[0]["campaign_id"] == "98765"
        assert isinstance(results[0]["campaign_id"], str)

    def test_ctr_ratio_to_percentage(self):
        """metrics.ctr (0.05 ratio) should become 5.0 percentage."""
        fetcher = self._create_fetcher()
        row = _make_ads_campaign_row(ctr=0.05)

        fetcher._query_with_retry = MagicMock(return_value=[row])
        results = fetcher._fetch_campaigns_sync(date(2026, 2, 1), date(2026, 2, 1))

        assert results[0]["ctr"] == pytest.approx(5.0)

    def test_date_string_parsed(self):
        """segments.date ('2026-02-01') should become a date object."""
        fetcher = self._create_fetcher()
        row = _make_ads_campaign_row(seg_date="2026-02-15")

        fetcher._query_with_retry = MagicMock(return_value=[row])
        results = fetcher._fetch_campaigns_sync(date(2026, 2, 15), date(2026, 2, 15))

        assert results[0]["date"] == date(2026, 2, 15)

    def test_device_enum_to_name(self):
        """segments.device enum should become a string name."""
        fetcher = self._create_fetcher()
        row = _make_ads_campaign_row(device_name="MOBILE")

        fetcher._query_with_retry = MagicMock(return_value=[row])
        results = fetcher._fetch_campaigns_sync(date(2026, 2, 1), date(2026, 2, 1))

        assert results[0]["device"] == "MOBILE"

    def test_quality_score_zero_becomes_none(self):
        """Quality score of 0 from API means not available → stored as None."""
        fetcher = self._create_fetcher()
        row = _make_ads_keyword_row(quality_score=0)

        fetcher._query_with_retry = MagicMock(return_value=[row])
        results = fetcher._fetch_keywords_sync(date(2026, 2, 1), date(2026, 2, 1))

        assert results[0]["quality_score"] is None

    def test_quality_score_valid(self):
        """Non-zero quality score should be preserved."""
        fetcher = self._create_fetcher()
        row = _make_ads_keyword_row(quality_score=8)

        fetcher._query_with_retry = MagicMock(return_value=[row])
        results = fetcher._fetch_keywords_sync(date(2026, 2, 1), date(2026, 2, 1))

        assert results[0]["quality_score"] == 8

    def test_match_type_as_string(self):
        """match_type enum should become its .name string."""
        fetcher = self._create_fetcher()
        row = _make_ads_keyword_row(match_type_name="PHRASE")

        fetcher._query_with_retry = MagicMock(return_value=[row])
        results = fetcher._fetch_keywords_sync(date(2026, 2, 1), date(2026, 2, 1))

        assert results[0]["match_type"] == "PHRASE"

    def test_quality_subscores_unspecified_becomes_none(self):
        """UNSPECIFIED quality sub-scores should be stored as None."""
        fetcher = self._create_fetcher()
        row = _make_ads_keyword_row(
            predicted_ctr_name="UNSPECIFIED",
            creative_quality_name="UNKNOWN",
            post_click_quality_name="AVERAGE",
        )

        fetcher._query_with_retry = MagicMock(return_value=[row])
        results = fetcher._fetch_keywords_sync(date(2026, 2, 1), date(2026, 2, 1))

        assert results[0]["expected_ctr"] is None
        assert results[0]["ad_relevance"] is None
        assert results[0]["landing_page_experience"] == "AVERAGE"

    def test_budget_micros_preserved(self):
        """budget_micros should pass through unchanged."""
        fetcher = self._create_fetcher()
        row = _make_ads_campaign_row(budget_micros=100_000_000)

        fetcher._query_with_retry = MagicMock(return_value=[row])
        results = fetcher._fetch_campaigns_sync(date(2026, 2, 1), date(2026, 2, 1))

        assert results[0]["budget_micros"] == 100_000_000


# ---------------------------------------------------------------
# GA4 tests
# ---------------------------------------------------------------


class TestGA4FetcherTransform:
    """Tests for GA4 data transformation logic."""

    def test_parse_date_yyyymmdd(self):
        """GA4 date format '20260215' should parse to date(2026, 2, 15)."""
        assert GA4Fetcher._parse_date("20260215") == date(2026, 2, 15)

    def test_safe_int_valid(self):
        assert GA4Fetcher._safe_int("42") == 42

    def test_safe_int_empty(self):
        assert GA4Fetcher._safe_int("") == 0

    def test_safe_int_garbage(self):
        assert GA4Fetcher._safe_int("abc") == 0

    def test_safe_float_valid(self):
        assert GA4Fetcher._safe_float("3.14") == pytest.approx(3.14)

    def test_safe_float_empty(self):
        assert GA4Fetcher._safe_float("") == 0.0

    @patch("src.fetchers.ga4.BetaAnalyticsDataClient")
    @patch("src.fetchers.ga4.Credentials")
    @patch("src.fetchers.ga4.settings")
    def test_traffic_bounce_rate_scaled(
        self, mock_settings, mock_creds_cls, mock_client_cls
    ):
        """bounceRate from GA4 API (0-1 ratio) should be scaled to percentage."""
        mock_settings.google_ads_refresh_token = "token"
        mock_settings.google_ads_client_id = "cid"
        mock_settings.google_ads_client_secret = "csecret"
        mock_settings.ga4_property_id = "12345"

        fetcher = GA4Fetcher()
        response = _make_ga4_response([
            _make_ga4_row(
                ["20260201", "google", "cpc", "brand"],
                ["100", "85", "70", "0.45", "120.5", "3.2"],
            )
        ])

        rows = fetcher._parse_traffic_response(response)
        assert rows[0]["bounce_rate"] == pytest.approx(45.0)

    @patch("src.fetchers.ga4.BetaAnalyticsDataClient")
    @patch("src.fetchers.ga4.Credentials")
    @patch("src.fetchers.ga4.settings")
    def test_traffic_empty_source_defaults(
        self, mock_settings, mock_creds_cls, mock_client_cls
    ):
        """Empty source/medium/campaign should get defaults."""
        mock_settings.google_ads_refresh_token = "token"
        mock_settings.google_ads_client_id = "cid"
        mock_settings.google_ads_client_secret = "csecret"
        mock_settings.ga4_property_id = "12345"

        fetcher = GA4Fetcher()
        response = _make_ga4_response([
            _make_ga4_row(
                ["20260201", "", "", ""],
                ["50", "40", "30", "0.5", "60.0", "2.0"],
            )
        ])

        rows = fetcher._parse_traffic_response(response)
        assert rows[0]["source"] == "(direct)"
        assert rows[0]["medium"] == "(none)"
        assert rows[0]["campaign_name"] == "(not set)"

    @patch("src.fetchers.ga4.BetaAnalyticsDataClient")
    @patch("src.fetchers.ga4.Credentials")
    @patch("src.fetchers.ga4.settings")
    def test_traffic_date_parsed(
        self, mock_settings, mock_creds_cls, mock_client_cls
    ):
        """Date should be parsed from YYYYMMDD to Python date."""
        mock_settings.google_ads_refresh_token = "token"
        mock_settings.google_ads_client_id = "cid"
        mock_settings.google_ads_client_secret = "csecret"
        mock_settings.ga4_property_id = "12345"

        fetcher = GA4Fetcher()
        response = _make_ga4_response([
            _make_ga4_row(
                ["20260215", "google", "organic", "brand"],
                ["50", "40", "30", "0.3", "90.0", "2.5"],
            )
        ])

        rows = fetcher._parse_traffic_response(response)
        assert rows[0]["date"] == date(2026, 2, 15)

    @patch("src.fetchers.ga4.BetaAnalyticsDataClient")
    @patch("src.fetchers.ga4.Credentials")
    @patch("src.fetchers.ga4.settings")
    def test_conversions_parsed(
        self, mock_settings, mock_creds_cls, mock_client_cls
    ):
        """Conversion rows should parse event_count and conversion_value."""
        mock_settings.google_ads_refresh_token = "token"
        mock_settings.google_ads_client_id = "cid"
        mock_settings.google_ads_client_secret = "csecret"
        mock_settings.ga4_property_id = "12345"

        fetcher = GA4Fetcher()
        response = _make_ga4_response([
            _make_ga4_row(
                ["20260201", "purchase", "google", "cpc"],
                ["15", "1200.50"],
            )
        ])

        rows = fetcher._parse_conversions_response(response)
        assert rows[0]["event_name"] == "purchase"
        assert rows[0]["event_count"] == 15
        assert rows[0]["conversion_value"] == pytest.approx(1200.50)

    @patch("src.fetchers.ga4.BetaAnalyticsDataClient")
    @patch("src.fetchers.ga4.Credentials")
    @patch("src.fetchers.ga4.settings")
    def test_pages_bounce_rate_scaled(
        self, mock_settings, mock_creds_cls, mock_client_cls
    ):
        """Page-level bounce rate should also be scaled to percentage."""
        mock_settings.google_ads_refresh_token = "token"
        mock_settings.google_ads_client_id = "cid"
        mock_settings.google_ads_client_secret = "csecret"
        mock_settings.ga4_property_id = "12345"

        fetcher = GA4Fetcher()
        response = _make_ga4_response([
            _make_ga4_row(
                ["20260201", "/", "Home"],
                ["500", "200", "3600.0", "0.35"],
            )
        ])

        rows = fetcher._parse_pages_response(response)
        assert rows[0]["bounce_rate"] == pytest.approx(35.0)
        assert rows[0]["views"] == 500
        assert rows[0]["avg_time_on_page"] == pytest.approx(7.2)  # 3600/500
