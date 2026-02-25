"""KPI card components for the dashboard."""

import streamlit as st

from src.dashboard.utils import format_eur, format_number, format_pct


def render_kpi_card(
    label: str,
    value: str,
    delta: float | None = None,
    inverse: bool = False,
) -> None:
    """Render a single KPI metric card.

    Args:
        label: Metric name.
        value: Formatted metric value.
        delta: Percentage change vs previous period.
        inverse: If True, negative delta is good (e.g., CPC decrease).
    """
    st.metric(
        label=label,
        value=value,
        delta=f"{delta:+.1f}%" if delta is not None else None,
        delta_color="inverse" if inverse else "normal",
    )


def render_kpi_row(summary: dict) -> None:
    """Render a full row of 6 KPI cards from dashboard summary data."""
    cols = st.columns(6)

    with cols[0]:
        render_kpi_card(
            "Total Spend",
            format_eur(summary["total_spend"]),
            summary.get("spend_change_pct"),
            inverse=True,
        )
    with cols[1]:
        render_kpi_card(
            "Total Clicks",
            format_number(summary["total_clicks"]),
            summary.get("clicks_change_pct"),
        )
    with cols[2]:
        render_kpi_card(
            "Conversions",
            format_number(summary["total_conversions"]),
            summary.get("conversions_change_pct"),
        )
    with cols[3]:
        render_kpi_card(
            "Avg. CPC",
            format_eur(summary["average_cpc"]),
            summary.get("cpc_change_pct"),
            inverse=True,
        )
    with cols[4]:
        render_kpi_card(
            "CTR",
            format_pct(summary["average_ctr"]),
            summary.get("ctr_change_pct"),
        )
    with cols[5]:
        render_kpi_card(
            "ROAS",
            f"{summary['roas']:.2f}x",
            summary.get("roas_change_pct"),
        )
