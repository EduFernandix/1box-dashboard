"""1BOX Marketing Dashboard — Streamlit Application.

Main entry point for the Streamlit dashboard. Configures the page
layout, theme, and multipage navigation.

Run with:
    uv run streamlit run src/dashboard/app.py
"""

import streamlit as st

from src.dashboard.theme import inject_custom_css


def main() -> None:
    """Configure and launch the Streamlit dashboard."""
    st.set_page_config(
        page_title="1BOX Marketing Dashboard",
        page_icon="📦",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    inject_custom_css()

    # Import page modules
    from src.dashboard.pages import (
        page_01_overview,
        page_02_campaigns,
        page_03_keywords,
        page_04_traffic,
        page_05_conversions,
        page_06_alerts,
    )

    pages = {
        "Google Ads": [
            st.Page(page_01_overview.render, title="Overview", icon=":material/dashboard:", default=True),
            st.Page(page_02_campaigns.render, title="Campaigns", icon=":material/campaign:"),
            st.Page(page_03_keywords.render, title="Keywords", icon=":material/key:"),
        ],
        "GA4 Analytics": [
            st.Page(page_04_traffic.render, title="Traffic", icon=":material/language:"),
            st.Page(page_05_conversions.render, title="Conversions", icon=":material/target:"),
        ],
        "System": [
            st.Page(page_06_alerts.render, title="Alerts & Log", icon=":material/notifications:"),
        ],
    }

    pg = st.navigation(pages)
    pg.run()


if __name__ == "__main__":
    main()
