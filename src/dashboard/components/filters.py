"""Sidebar filter components for the dashboard."""

from datetime import date, timedelta

import streamlit as st

from src.dashboard import data_loader


def render_sidebar_header() -> None:
    """Render the sidebar branding and data refresh info."""
    st.sidebar.markdown("# 1BOX Marketing")
    st.sidebar.markdown('<hr class="brand-divider">', unsafe_allow_html=True)

    last_refresh = data_loader.get_last_refresh()
    if last_refresh:
        st.sidebar.caption(f"Last data refresh: {last_refresh}")

    if st.sidebar.button("Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()


def render_date_filter() -> tuple[date, date]:
    """Render a date range picker with preset buttons."""
    st.sidebar.subheader("Date Range")

    preset = st.sidebar.radio(
        "Quick select",
        ["Last 7 days", "Last 30 days", "Last 90 days", "Custom"],
        index=1,
        horizontal=True,
        label_visibility="collapsed",
    )

    today = date.today()
    if preset == "Last 7 days":
        start = today - timedelta(days=7)
        end = today - timedelta(days=1)
    elif preset == "Last 30 days":
        start = today - timedelta(days=30)
        end = today - timedelta(days=1)
    elif preset == "Last 90 days":
        start = today - timedelta(days=90)
        end = today - timedelta(days=1)
    else:
        col1, col2 = st.sidebar.columns(2)
        start = col1.date_input("From", today - timedelta(days=30))
        end = col2.date_input("To", today - timedelta(days=1))

    return start, end


def render_campaign_filter() -> list[str] | None:
    """Render a multi-select campaign filter. Returns None for 'all'."""
    campaigns = data_loader.get_campaign_names()
    if not campaigns:
        return None

    selected = st.sidebar.multiselect(
        "Campaigns",
        options=campaigns,
        default=None,
        placeholder="All campaigns",
    )
    return selected if selected else None


def render_device_filter() -> str | None:
    """Render a device filter."""
    device = st.sidebar.radio(
        "Device",
        ["All", "DESKTOP", "MOBILE", "TABLET"],
        horizontal=True,
    )
    return None if device == "All" else device
