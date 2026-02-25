"""Campaigns page — interactive table, CPC evolution, cost distribution."""

import streamlit as st

from src.dashboard import data_loader
from src.dashboard.components import charts
from src.dashboard.components.filters import (
    render_campaign_filter,
    render_date_filter,
    render_device_filter,
    render_sidebar_header,
)


def render() -> None:
    """Render the campaigns analysis page."""
    render_sidebar_header()
    start_date, end_date = render_date_filter()
    selected_campaigns = render_campaign_filter()
    device = render_device_filter()

    st.header("Google Ads Campaigns")
    st.markdown('<hr class="brand-divider">', unsafe_allow_html=True)

    # Load data
    df = data_loader.get_campaigns(start_date, end_date, device=device)
    if df.empty:
        st.info("No campaign data for the selected period.")
        return

    # Apply campaign filter
    if selected_campaigns:
        df = df[df["campaign_name"].isin(selected_campaigns)]

    # Campaign summary table
    st.subheader("Campaign Performance")
    summary = (
        df.groupby(["campaign_id", "campaign_name", "status"])
        .agg(
            impressions=("impressions", "sum"),
            clicks=("clicks", "sum"),
            cost=("cost", "sum"),
            conversions=("conversions", "sum"),
            conversion_value=("conversion_value", "sum"),
        )
        .reset_index()
    )
    summary["ctr"] = (summary["clicks"] / summary["impressions"] * 100).round(2)
    summary["cpc"] = (summary["cost"] / summary["clicks"]).round(2)
    summary["roas"] = (summary["conversion_value"] / summary["cost"]).round(2)
    summary["cpc"] = summary["cpc"].fillna(0)
    summary["roas"] = summary["roas"].fillna(0)

    st.dataframe(
        summary[["campaign_name", "status", "impressions", "clicks", "ctr",
                  "cost", "conversions", "conversion_value", "cpc", "roas"]],
        column_config={
            "campaign_name": st.column_config.TextColumn("Campaign"),
            "status": st.column_config.TextColumn("Status"),
            "impressions": st.column_config.NumberColumn("Impressions", format="%d"),
            "clicks": st.column_config.NumberColumn("Clicks", format="%d"),
            "ctr": st.column_config.NumberColumn("CTR (%)", format="%.2f"),
            "cost": st.column_config.NumberColumn("Cost (EUR)", format="%.2f"),
            "conversions": st.column_config.NumberColumn("Conv.", format="%.1f"),
            "conversion_value": st.column_config.NumberColumn("Conv. Value", format="%.2f"),
            "cpc": st.column_config.NumberColumn("CPC (EUR)", format="%.2f"),
            "roas": st.column_config.NumberColumn("ROAS", format="%.2fx"),
        },
        use_container_width=True,
        hide_index=True,
    )

    # Row 2: CPC Evolution + Cost Distribution
    col_left, col_right = st.columns(2)

    with col_left:
        # Daily CPC by campaign
        daily_cpc = (
            df.groupby(["date", "campaign_name"])
            .agg(cost=("cost", "sum"), clicks=("clicks", "sum"))
            .reset_index()
        )
        daily_cpc["cpc"] = (daily_cpc["cost"] / daily_cpc["clicks"]).fillna(0).round(2)

        campaigns = daily_cpc["campaign_name"].unique()
        import plotly.graph_objects as go
        from src.dashboard.theme import COLOR_SEQUENCE, PLOTLY_LAYOUT

        fig = go.Figure()
        for i, name in enumerate(campaigns):
            cdf = daily_cpc[daily_cpc["campaign_name"] == name].sort_values("date")
            fig.add_trace(go.Scatter(
                x=cdf["date"], y=cdf["cpc"],
                name=name, mode="lines+markers",
                line=dict(color=COLOR_SEQUENCE[i % len(COLOR_SEQUENCE)], width=2),
                marker=dict(size=3),
            ))
        fig.update_layout(**PLOTLY_LAYOUT, title=dict(text="CPC Evolution by Campaign", font_size=14))
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        # Daily cost stacked by campaign
        daily_cost = (
            df.groupby(["date", "campaign_name"])["cost"]
            .sum()
            .reset_index()
        )
        fig = charts.stacked_area_chart(
            daily_cost, x="date", y_col="cost", group_col="campaign_name",
            title="Daily Spend by Campaign",
        )
        st.plotly_chart(fig, use_container_width=True)
