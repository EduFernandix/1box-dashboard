"""Tests for Google Ads and GA4 data fetchers."""

import pytest


class TestGoogleAdsFetcher:
    """Tests for the Google Ads API fetcher."""

    @pytest.mark.skip(reason="Fetcher not yet implemented (Phase 2)")
    def test_fetch_campaigns(self):
        pass

    @pytest.mark.skip(reason="Fetcher not yet implemented (Phase 2)")
    def test_fetch_keywords(self):
        pass

    @pytest.mark.skip(reason="Fetcher not yet implemented (Phase 2)")
    def test_connection_test(self):
        pass


class TestGA4Fetcher:
    """Tests for the GA4 Data API fetcher."""

    @pytest.mark.skip(reason="Fetcher not yet implemented (Phase 2)")
    def test_fetch_traffic(self):
        pass

    @pytest.mark.skip(reason="Fetcher not yet implemented (Phase 2)")
    def test_fetch_conversions(self):
        pass
