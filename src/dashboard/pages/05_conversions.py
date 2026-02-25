"""Conversions page — funnel, conversions by channel, landing page performance."""

import streamlit as st

from src.dashboard import data_loader
from src.dashboard.components import charts
from src.dashboard.components.filters import render_date_filter, render_sidebar_header
from src.dashboard.components.kpi_cards import render_kpi_card
from src.dashboard.utils import channel_label, format_eur, format_number


def render() -> None:
    """Render the conversions analysis page."""
    render_sidebar_header()
    start_date, end_date = render_date_filter()

    st.header("GA4 Conversions")
    st.markdown('<hr class="brand-divider">', unsafe_allow_html=True)

    # Load data
    conversions = data_loader.get_conversions(start_date, end_date)
    traffic = data_loader.get_traffic(start_date, end_date)

    if conversions.empty:
        st.info("No conversion data for the selected period.")
        return

    # KPI row
    total_events = int(conversions["event_count"].sum())
    total_value = conversions["conversion_value"].sum()
    total_sessions = int(traffic["sessions"].sum()) if not traffic.empty else 0
    conv_rate = (total_events / total_sessions * 100) if total_sessions > 0 else 0

    cols = st.columns(3)
    with cols[0]:
        render_kpi_card("Total Conversions", format_number(total_events))
    with cols[1]:
        render_kpi_card("Conversion Rate", f"{conv_rate:.2f}%")
    with cols[2]:
        render_kpi_card("Total Conv. Value", format_eur(total_value))

    st.markdown("")

    # Row 2: Funnel
    st.subheader("Conversion Funnel")
    # Build funnel from traffic sessions -> event counts
    leads = int(conversions[conversions["event_name"] == "generate_lead"]["event_count"].sum())
    forms = int(conversions[conversions["event_name"] == "submit_form"]["event_count"].sum())
    calls = int(conversions[conversions["event_name"] == "phone_call"]["event_count"].sum())

    stages = ["Sessions", "Form Submissions", "Lead Generation", "Phone Calls"]
    values = [total_sessions, forms, leads, calls]

    fig = charts.funnel_chart(stages, values, title="Conversion Funnel")
    st.plotly_chart(fig, use_container_width=True)

    # Row 3: Conversions by channel + Event breakdown
    col_left, col_right = st.columns(2)

    with col_left:
        # Daily conversions by channel
        conv_channel = conversions.copy()
        conv_channel["channel"] = conv_channel.apply(
            lambda r: channel_label(r["source"], r["medium"]), axis=1
        )
        daily_conv = (
            conv_channel.groupby(["date", "channel"])["event_count"]
            .sum()
            .reset_index()
        )
        if not daily_conv.empty:
            fig = charts.stacked_area_chart(
                daily_conv, x="date", y_col="event_count", group_col="channel",
                title="Daily Conversions by Channel",
            )
            st.plotly_chart(fig, use_container_width=True)

    with col_right:
        # Event type breakdown
        event_totals = (
            conversions.groupby("event_name")["event_count"]
            .sum()
            .reset_index()
        )
        fig = charts.pie_chart(
            event_totals, names="event_name", values="event_count",
            title="Conversion Events Breakdown",
        )
        st.plotly_chart(fig, use_container_width=True)

    # Row 4: Landing Page Performance
    st.subheader("Landing Page Performance")
    pages = data_loader.get_pages(start_date, end_date)
    if not pages.empty:
        pages["avg_time_on_page"] = pages["avg_time_on_page"].round(1)
        pages["bounce_rate"] = pages["bounce_rate"].round(1)
        pages["exit_rate"] = pages["exit_rate"].round(1)

        st.dataframe(
            pages,
            column_config={
                "page_path": st.column_config.TextColumn("Page Path"),
                "page_title": st.column_config.TextColumn("Title"),
                "views": st.column_config.NumberColumn("Views", format="%d"),
                "unique_views": st.column_config.NumberColumn("Unique Views", format="%d"),
                "avg_time_on_page": st.column_config.NumberColumn("Avg. Time (s)", format="%.1f"),
                "bounce_rate": st.column_config.NumberColumn("Bounce Rate (%)", format="%.1f"),
                "exit_rate": st.column_config.NumberColumn("Exit Rate (%)", format="%.1f"),
            },
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.info("No page data available.")
