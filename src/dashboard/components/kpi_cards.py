"""KPI card components for the dashboard overview.

Renders metric cards with current value, trend indicator,
and comparison to previous period.
"""

import streamlit as st


def render_kpi_card(
    label: str,
    value: str,
    delta: float | None = None,
    delta_label: str = "vs prev period",
) -> None:
    """Render a single KPI metric card.

    Args:
        label: Metric name (e.g., "Total Spend").
        value: Formatted metric value (e.g., "€12,345").
        delta: Percentage change vs previous period.
        delta_label: Description of the comparison period.
    """
    # TODO: Implement in Phase 3
    st.metric(label=label, value=value, delta=f"{delta:+.1f}%" if delta else None)
