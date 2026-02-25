"""1BOX Marketing Dashboard — Streamlit Application.

Main entry point for the Streamlit dashboard. Configures the page
layout, theme, and navigation sidebar.

Run with:
    uv run streamlit run src/dashboard/app.py
"""

import streamlit as st


def main() -> None:
    """Configure and launch the Streamlit dashboard."""
    st.set_page_config(
        page_title="1BOX Marketing Dashboard",
        page_icon="📦",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.title("📦 1BOX Marketing Dashboard")
    st.caption("Real-time Google Ads & GA4 analytics for 1BOX Self-Storage")

    st.info(
        "Dashboard under construction. "
        "Run `uv run python scripts/seed_demo_data.py` to populate demo data, "
        "then check back as pages are implemented in Phase 3."
    )

    # TODO: Phase 3 — Add sidebar filters and page navigation
    # Pages are in src/dashboard/pages/


if __name__ == "__main__":
    main()
