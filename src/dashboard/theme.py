"""1BOX brand theme — colors, Plotly layout, and custom CSS."""

import streamlit as st

# 1BOX Brand Colors (from logo and website)
GREEN = "#4CAF50"
GREEN_LIGHT = "#66BB6A"
GREEN_DARK = "#388E3C"
ORANGE = "#FF6B00"
ORANGE_LIGHT = "#FF8F00"
BG_DARK = "#0E1117"
BG_CARD = "#1A1F2B"
TEXT_PRIMARY = "#FAFAFA"
TEXT_SECONDARY = "#B0B0B0"
RED = "#EF5350"
YELLOW = "#FFC107"

# Chart color sequence for multi-trace plots
COLOR_SEQUENCE = [GREEN, ORANGE, "#42A5F5", "#AB47BC", "#26C6DA", GREEN_LIGHT]

# Plotly layout defaults
PLOTLY_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    font=dict(color=TEXT_PRIMARY, family="Inter, sans-serif", size=12),
    xaxis=dict(gridcolor="#333", zerolinecolor="#555"),
    yaxis=dict(gridcolor="#333", zerolinecolor="#555"),
    margin=dict(l=40, r=20, t=40, b=40),
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
)


def inject_custom_css() -> None:
    """Inject 1BOX-branded CSS overrides."""
    st.markdown(
        """
        <style>
        /* KPI metric cards */
        [data-testid="stMetric"] {
            background-color: #1A1F2B;
            border: 1px solid #333;
            border-radius: 8px;
            padding: 12px 16px;
            border-left: 4px solid #4CAF50;
        }
        [data-testid="stMetricValue"] {
            font-size: 1.6rem;
            font-weight: 700;
        }
        [data-testid="stMetricDelta"] > div {
            font-size: 0.85rem;
        }

        /* Sidebar branding */
        [data-testid="stSidebar"] [data-testid="stMarkdown"] h1 {
            color: #4CAF50;
            font-size: 1.4rem;
        }

        /* Data tables */
        .stDataFrame {
            border-radius: 8px;
        }

        /* Tabs */
        .stTabs [data-baseweb="tab"] {
            font-weight: 600;
        }
        .stTabs [aria-selected="true"] {
            border-bottom-color: #4CAF50;
        }

        /* Header divider */
        .brand-divider {
            height: 3px;
            background: linear-gradient(90deg, #4CAF50 0%, #FF6B00 100%);
            border: none;
            margin: 0 0 1.5rem 0;
            border-radius: 2px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
