"""Plotly chart components with 1BOX green/orange branding."""

import pandas as pd
import plotly.graph_objects as go

from src.dashboard.theme import (
    COLOR_SEQUENCE,
    GREEN,
    GREEN_DARK,
    GREEN_LIGHT,
    ORANGE,
    PLOTLY_LAYOUT,
    RED,
    TEXT_SECONDARY,
)


def _apply_layout(fig: go.Figure, title: str = "") -> go.Figure:
    """Apply 1BOX branded layout to a figure."""
    fig.update_layout(**PLOTLY_LAYOUT, title=dict(text=title, font_size=14) if title else {})
    return fig


def line_chart(
    df: pd.DataFrame,
    x: str,
    y: list[str],
    title: str = "",
    colors: list[str] | None = None,
) -> go.Figure:
    """Branded line chart with one or more traces."""
    colors = colors or COLOR_SEQUENCE
    fig = go.Figure()
    for i, col in enumerate(y):
        fig.add_trace(go.Scatter(
            x=df[x],
            y=df[col],
            name=col.replace("_", " ").title(),
            mode="lines+markers",
            line=dict(color=colors[i % len(colors)], width=2),
            marker=dict(size=4),
        ))
    return _apply_layout(fig, title)


def dual_axis_chart(
    df: pd.DataFrame,
    x: str,
    y1: str,
    y2: str,
    y1_name: str = "",
    y2_name: str = "",
    title: str = "",
) -> go.Figure:
    """Dual-axis line chart (left + right y-axis)."""
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df[x], y=df[y1],
        name=y1_name or y1.replace("_", " ").title(),
        mode="lines+markers",
        line=dict(color=GREEN, width=2),
        marker=dict(size=4),
    ))
    fig.add_trace(go.Scatter(
        x=df[x], y=df[y2],
        name=y2_name or y2.replace("_", " ").title(),
        mode="lines+markers",
        line=dict(color=ORANGE, width=2),
        marker=dict(size=4),
        yaxis="y2",
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text=title, font_size=14) if title else {},
        yaxis=dict(gridcolor="#333", title=y1_name or y1, titlefont_color=GREEN),
        yaxis2=dict(
            title=y2_name or y2,
            titlefont_color=ORANGE,
            overlaying="y",
            side="right",
            gridcolor="rgba(0,0,0,0)",
        ),
    )
    return fig


def bar_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    title: str = "",
    color: str | None = None,
    horizontal: bool = False,
) -> go.Figure:
    """Branded bar chart."""
    fig = go.Figure()
    if horizontal:
        fig.add_trace(go.Bar(
            y=df[x], x=df[y],
            orientation="h",
            marker_color=color or GREEN,
        ))
    else:
        fig.add_trace(go.Bar(
            x=df[x], y=df[y],
            marker_color=color or GREEN,
        ))
    return _apply_layout(fig, title)


def stacked_area_chart(
    df: pd.DataFrame,
    x: str,
    y_col: str,
    group_col: str,
    title: str = "",
) -> go.Figure:
    """Stacked area chart for channel breakdown over time."""
    fig = go.Figure()
    groups = df[group_col].unique()
    colors = COLOR_SEQUENCE
    for i, group in enumerate(groups):
        gdf = df[df[group_col] == group].sort_values(x)
        fig.add_trace(go.Scatter(
            x=gdf[x], y=gdf[y_col],
            name=str(group),
            mode="lines",
            stackgroup="one",
            line=dict(width=0.5, color=colors[i % len(colors)]),
            fillcolor=colors[i % len(colors)],
        ))
    return _apply_layout(fig, title)


def pie_chart(
    df: pd.DataFrame,
    names: str,
    values: str,
    title: str = "",
) -> go.Figure:
    """Donut chart for distribution."""
    fig = go.Figure(go.Pie(
        labels=df[names],
        values=df[values],
        hole=0.45,
        marker=dict(colors=COLOR_SEQUENCE),
        textinfo="label+percent",
        textposition="outside",
        textfont=dict(size=11),
    ))
    return _apply_layout(fig, title)


def scatter_chart(
    df: pd.DataFrame,
    x: str,
    y: str,
    size: str | None = None,
    color: str | None = None,
    title: str = "",
    labels: str | None = None,
) -> go.Figure:
    """Scatter plot with optional bubble sizing and color mapping."""
    marker_kwargs: dict = {"color": GREEN, "opacity": 0.7}
    if size and size in df.columns:
        marker_kwargs["size"] = df[size]
        marker_kwargs["sizemode"] = "area"
        marker_kwargs["sizeref"] = 2.0 * df[size].max() / (30**2) if df[size].max() > 0 else 1
    if color and color in df.columns:
        marker_kwargs["color"] = df[color]
        marker_kwargs["colorscale"] = [[0, RED], [0.5, ORANGE], [1, GREEN]]
        marker_kwargs["showscale"] = True
        marker_kwargs["colorbar"] = dict(title=color.replace("_", " ").title())

    fig = go.Figure(go.Scatter(
        x=df[x], y=df[y],
        mode="markers",
        marker=marker_kwargs,
        text=df[labels] if labels and labels in df.columns else None,
        hovertemplate=(
            f"<b>%{{text}}</b><br>{x}: %{{x}}<br>{y}: %{{y}}<extra></extra>"
            if labels else None
        ),
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text=title, font_size=14) if title else {},
        xaxis_title=x.replace("_", " ").title(),
        yaxis_title=y.replace("_", " ").title(),
    )
    return fig


def funnel_chart(
    stages: list[str],
    values: list[int | float],
    title: str = "",
) -> go.Figure:
    """Conversion funnel visualization."""
    fig = go.Figure(go.Funnel(
        y=stages,
        x=values,
        textinfo="value+percent initial",
        marker=dict(
            color=[GREEN, GREEN_LIGHT, ORANGE, GREEN_DARK, RED][: len(stages)]
        ),
        connector=dict(line=dict(color=TEXT_SECONDARY, width=1)),
    ))
    return _apply_layout(fig, title)


def quality_score_bar(df: pd.DataFrame, title: str = "") -> go.Figure:
    """Quality score distribution bar chart with colored bins."""
    if "quality_score" not in df.columns or df.empty:
        return go.Figure()

    qs = df["quality_score"].dropna()
    bins = list(range(1, 11))
    counts = [int((qs == b).sum()) for b in bins]
    colors_map = [RED] * 4 + [ORANGE] * 3 + [GREEN] * 3

    fig = go.Figure(go.Bar(
        x=bins,
        y=counts,
        marker_color=colors_map,
        text=counts,
        textposition="auto",
    ))
    fig.update_layout(
        **PLOTLY_LAYOUT,
        title=dict(text=title, font_size=14) if title else {},
        xaxis=dict(title="Quality Score", dtick=1, gridcolor="#333"),
        yaxis=dict(title="Keywords", gridcolor="#333"),
    )
    return fig
