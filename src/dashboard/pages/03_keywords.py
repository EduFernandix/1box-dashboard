"""Keywords page — quality score table, CPC vs conversions scatter."""

import streamlit as st

from src.dashboard import data_loader
from src.dashboard.components import charts
from src.dashboard.components.filters import (
    render_campaign_filter,
    render_date_filter,
    render_sidebar_header,
)


def render() -> None:
    """Render the keywords analysis page."""
    render_sidebar_header()
    start_date, end_date = render_date_filter()
    selected_campaigns = render_campaign_filter()

    # Quality score filter
    qs_range = st.sidebar.slider("Min Quality Score", 1, 10, 1)

    st.header("Google Ads Keywords")
    st.markdown('<hr class="brand-divider">', unsafe_allow_html=True)

    # Load data
    df = data_loader.get_keywords(
        start_date, end_date,
        min_quality_score=qs_range if qs_range > 1 else None,
    )
    if df.empty:
        st.info("No keyword data for the selected period.")
        return

    # Apply campaign filter
    if selected_campaigns:
        campaign_ids = data_loader.get_campaigns(start_date, end_date)
        if not campaign_ids.empty:
            ids = campaign_ids[campaign_ids["campaign_name"].isin(selected_campaigns)]["campaign_id"].unique()
            df = df[df["campaign_id"].isin(ids)]

    # Row 1: QS Distribution + Keyword Table
    col_left, col_right = st.columns([1, 2])

    with col_left:
        # Aggregate unique keywords for QS distribution
        kw_qs = df.groupby("keyword_id").agg(quality_score=("quality_score", "first")).reset_index()
        fig = charts.quality_score_bar(kw_qs, title="Quality Score Distribution")
        st.plotly_chart(fig, use_container_width=True)

    with col_right:
        st.subheader("Keyword Performance")
        # Aggregate keywords across dates
        kw_agg = (
            df.groupby(["keyword_id", "keyword_text", "match_type", "campaign_id"])
            .agg(
                impressions=("impressions", "sum"),
                clicks=("clicks", "sum"),
                cost=("cost", "sum"),
                conversions=("conversions", "sum"),
                quality_score=("quality_score", "first"),
                expected_ctr=("expected_ctr", "first"),
                ad_relevance=("ad_relevance", "first"),
                landing_page_experience=("landing_page_experience", "first"),
            )
            .reset_index()
        )
        kw_agg["ctr"] = (kw_agg["clicks"] / kw_agg["impressions"] * 100).fillna(0).round(2)
        kw_agg["cpc"] = (kw_agg["cost"] / kw_agg["clicks"]).fillna(0).round(2)

        st.dataframe(
            kw_agg[["keyword_text", "match_type", "clicks", "impressions", "ctr",
                     "cost", "conversions", "cpc", "quality_score",
                     "expected_ctr", "ad_relevance", "landing_page_experience"]],
            column_config={
                "keyword_text": st.column_config.TextColumn("Keyword"),
                "match_type": st.column_config.TextColumn("Match"),
                "clicks": st.column_config.NumberColumn("Clicks", format="%d"),
                "impressions": st.column_config.NumberColumn("Impr.", format="%d"),
                "ctr": st.column_config.NumberColumn("CTR (%)", format="%.2f"),
                "cost": st.column_config.NumberColumn("Cost", format="%.2f"),
                "conversions": st.column_config.NumberColumn("Conv.", format="%.1f"),
                "cpc": st.column_config.NumberColumn("CPC", format="%.2f"),
                "quality_score": st.column_config.NumberColumn("QS", format="%d"),
                "expected_ctr": st.column_config.TextColumn("Exp. CTR"),
                "ad_relevance": st.column_config.TextColumn("Ad Rel."),
                "landing_page_experience": st.column_config.TextColumn("LP Exp."),
            },
            use_container_width=True,
            hide_index=True,
        )

    # Row 2: Scatter + Opportunities
    col_left2, col_right2 = st.columns(2)

    with col_left2:
        if not kw_agg.empty and kw_agg["clicks"].sum() > 0:
            fig = charts.scatter_chart(
                kw_agg, x="cpc", y="conversions",
                size="impressions", color="quality_score",
                title="CPC vs Conversions (bubble = impressions, color = QS)",
                labels="keyword_text",
            )
            st.plotly_chart(fig, use_container_width=True)

    with col_right2:
        st.subheader("Keyword Opportunities")

        # High spend, low QS (potential waste)
        waste = kw_agg[
            (kw_agg["quality_score"].notna()) &
            (kw_agg["quality_score"] < 5) &
            (kw_agg["cost"] > kw_agg["cost"].median())
        ].sort_values("cost", ascending=False).head(5)

        if not waste.empty:
            st.markdown("**High spend, low QS (reduce waste):**")
            st.dataframe(
                waste[["keyword_text", "quality_score", "cost", "conversions"]],
                hide_index=True, use_container_width=True,
            )

        # High QS, low spend (scale opportunity)
        scale = kw_agg[
            (kw_agg["quality_score"].notna()) &
            (kw_agg["quality_score"] >= 8) &
            (kw_agg["cost"] < kw_agg["cost"].median())
        ].sort_values("quality_score", ascending=False).head(5)

        if not scale.empty:
            st.markdown("**High QS, low spend (scale up):**")
            st.dataframe(
                scale[["keyword_text", "quality_score", "cost", "conversions"]],
                hide_index=True, use_container_width=True,
            )
