"""Overview page — KPI cards, spend vs conversions chart, top campaigns."""

import streamlit as st

from src.dashboard import data_loader
from src.dashboard.components import charts, kpi_cards
from src.dashboard.components.filters import render_date_filter, render_sidebar_header


def render() -> None:
    """Render the overview dashboard page."""
    render_sidebar_header()
    start_date, end_date = render_date_filter()

    st.header("1BOX Marketing Overview")
    st.markdown('<hr class="brand-divider">', unsafe_allow_html=True)

    # KPI row
    summary = data_loader.get_dashboard_summary(start_date, end_date)
    kpi_cards.render_kpi_row(summary)

    st.markdown("")  # spacer

    # Row 2: Spend vs Conversions + Top Campaigns
    col_left, col_right = st.columns([2, 1])

    with col_left:
        daily = data_loader.get_daily_metrics(start_date, end_date)
        if not daily.empty:
            fig = charts.dual_axis_chart(
                daily, x="date", y1="cost", y2="conversions",
                y1_name="Spend (EUR)", y2_name="Conversions",
                title="Daily Spend vs Conversions",
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No campaign data for the selected period.")

    with col_right:
        campaigns = data_loader.get_campaigns(start_date, end_date)
        if not campaigns.empty:
            top5 = (
                campaigns.groupby("campaign_name")["cost"]
                .sum()
                .nlargest(5)
                .reset_index()
            )
            fig = charts.bar_chart(
                top5, x="campaign_name", y="cost",
                title="Top 5 Campaigns by Spend",
                horizontal=True,
            )
            st.plotly_chart(fig, use_container_width=True)

    # Row 3: Clicks/Impressions trend + Device breakdown
    col_left2, col_right2 = st.columns([2, 1])

    with col_left2:
        if not daily.empty:
            fig = charts.line_chart(
                daily, x="date", y=["clicks", "impressions"],
                title="Clicks & Impressions Trend",
            )
            st.plotly_chart(fig, use_container_width=True)

    with col_right2:
        if not campaigns.empty:
            device_df = (
                campaigns.groupby("device")["clicks"]
                .sum()
                .reset_index()
            )
            fig = charts.pie_chart(
                device_df, names="device", values="clicks",
                title="Clicks by Device",
            )
            st.plotly_chart(fig, use_container_width=True)
