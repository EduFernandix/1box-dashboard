"""Sidebar filter components for the dashboard.

Provides date range picker, campaign selector, and device filter
shared across all dashboard pages.
"""

from datetime import date, timedelta

import streamlit as st


def render_date_filter() -> tuple[date, date]:
    """Render a date range picker in the sidebar.

    Returns:
        (start_date, end_date) tuple.
    """
    # TODO: Implement in Phase 3
    end = date.today()
    start = end - timedelta(days=30)
    return start, end


def render_campaign_filter(campaigns: list[str]) -> list[str]:
    """Render a multi-select campaign filter in the sidebar.

    Args:
        campaigns: List of available campaign names.

    Returns:
        List of selected campaign names.
    """
    # TODO: Implement in Phase 3
    return campaigns


def render_device_filter() -> str | None:
    """Render a device filter (ALL, MOBILE, DESKTOP, TABLET).

    Returns:
        Selected device or None for all.
    """
    # TODO: Implement in Phase 3
    return None
