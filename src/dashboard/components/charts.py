"""Plotly chart components for the dashboard.

Reusable chart functions with consistent 1BOX branding
(blue #003B73, orange #FF6B35).
"""

import pandas as pd
import plotly.graph_objects as go

# 1BOX brand colors
COLOR_PRIMARY = "#003B73"
COLOR_ACCENT = "#FF6B35"
COLOR_BG = "#0E1117"


def line_chart(
    df: pd.DataFrame,
    x: str,
    y: list[str],
    title: str = "",
) -> go.Figure:
    """Create a branded line chart.

    Args:
        df: DataFrame with the data.
        x: Column name for x-axis.
        y: List of column names for y-axis traces.
        title: Chart title.

    Returns:
        Plotly Figure object.
    """
    # TODO: Implement in Phase 3
    raise NotImplementedError


def bar_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str = "",
) -> go.Figure:
    """Create a branded bar chart."""
    # TODO: Implement in Phase 3
    raise NotImplementedError


def heatmap(
    df: pd.DataFrame,
    x: str,
    y: str,
    z: str,
    title: str = "",
) -> go.Figure:
    """Create a branded heatmap (e.g., CPC by day × campaign)."""
    # TODO: Implement in Phase 3
    raise NotImplementedError
