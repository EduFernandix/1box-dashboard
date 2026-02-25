"""GA4 Traffic page — sessions by channel, Netherlands map, source/medium table."""

import folium
import streamlit as st
from streamlit_folium import st_folium

from src.dashboard import data_loader
from src.dashboard.components import charts
from src.dashboard.components.filters import render_date_filter, render_sidebar_header
from src.dashboard.components.kpi_cards import render_kpi_card
from src.dashboard.theme import GREEN, ORANGE
from src.dashboard.utils import format_number, format_pct

# Netherlands city coordinates
NL_CITY_COORDS = {
    "Amsterdam": (52.3676, 4.9041),
    "Rotterdam": (51.9244, 4.4777),
    "Utrecht": (52.0907, 5.1214),
    "Den Haag": (52.0705, 4.3007),
    "Eindhoven": (51.4416, 5.4697),
    "Groningen": (53.2194, 6.5665),
    "Tilburg": (51.5555, 5.0913),
    "Almere": (52.3508, 5.2647),
    "Breda": (51.5719, 4.7683),
    "Nijmegen": (51.8426, 5.8527),
    "Haarlem": (52.3874, 4.6462),
    "Arnhem": (51.9851, 5.8987),
    "Zaanstad": (52.4550, 4.8167),
    "Amersfoort": (52.1561, 5.3878),
    "Apeldoorn": (52.2112, 5.9699),
}


def _render_netherlands_map(geo_df) -> None:
    """Render the Netherlands map with city session bubbles."""
    m = folium.Map(
        location=[52.1326, 5.2913],
        zoom_start=7,
        tiles="CartoDB dark_matter",
    )

    if geo_df.empty:
        st_folium(m, width=None, height=450, use_container_width=True)
        return

    max_sessions = geo_df["sessions"].max()

    for _, row in geo_df.iterrows():
        coords = NL_CITY_COORDS.get(row["city"])
        if not coords:
            continue

        radius = max(6, (row["sessions"] / max_sessions) * 35)

        folium.CircleMarker(
            location=coords,
            radius=radius,
            color=ORANGE,
            fill=True,
            fill_color=GREEN,
            fill_opacity=0.7,
            weight=2,
            popup=folium.Popup(
                f"<div style='font-family:sans-serif;'>"
                f"<b>{row['city']}</b><br>"
                f"Sessions: {row['sessions']:,}<br>"
                f"Users: {row['users']:,}<br>"
                f"Conversions: {row['conversions']:,}"
                f"</div>",
                max_width=200,
            ),
            tooltip=f"{row['city']}: {row['sessions']:,} sessions",
        ).add_to(m)

    st_folium(m, width=None, height=450, use_container_width=True)


def render() -> None:
    """Render the GA4 traffic analysis page."""
    render_sidebar_header()
    start_date, end_date = render_date_filter()

    st.header("GA4 Traffic Analysis")
    st.markdown('<hr class="brand-divider">', unsafe_allow_html=True)

    # Load traffic data
    traffic = data_loader.get_traffic(start_date, end_date)

    if traffic.empty:
        st.info("No traffic data for the selected period.")
        return

    # KPI row
    total_sessions = int(traffic["sessions"].sum())
    total_users = int(traffic["users"].sum())
    total_new_users = int(traffic["new_users"].sum())
    avg_bounce = traffic["bounce_rate"].mean()
    new_user_pct = (total_new_users / total_users * 100) if total_users > 0 else 0

    cols = st.columns(4)
    with cols[0]:
        render_kpi_card("Total Sessions", format_number(total_sessions))
    with cols[1]:
        render_kpi_card("Total Users", format_number(total_users))
    with cols[2]:
        render_kpi_card("New Users", format_pct(new_user_pct))
    with cols[3]:
        render_kpi_card("Avg. Bounce Rate", format_pct(avg_bounce))

    st.markdown("")

    # Row 2: Traffic by channel + donut
    col_left, col_right = st.columns([2, 1])

    with col_left:
        channel_df = data_loader.get_traffic_by_channel(start_date, end_date)
        if not channel_df.empty:
            fig = charts.stacked_area_chart(
                channel_df, x="date", y_col="sessions", group_col="channel",
                title="Daily Sessions by Channel",
            )
            st.plotly_chart(fig, use_container_width=True)

    with col_right:
        if not channel_df.empty:
            channel_totals = channel_df.groupby("channel")["sessions"].sum().reset_index()
            fig = charts.pie_chart(
                channel_totals, names="channel", values="sessions",
                title="Session Distribution",
            )
            st.plotly_chart(fig, use_container_width=True)

    # Row 3: Netherlands Map
    st.subheader("Sessions by City (Netherlands)")
    geo_df = data_loader.get_geo_data(start_date, end_date)
    _render_netherlands_map(geo_df)

    # Row 4: Source/Medium table
    st.subheader("Source / Medium Performance")
    sm_agg = (
        traffic.groupby(["source", "medium"])
        .agg(
            sessions=("sessions", "sum"),
            users=("users", "sum"),
            new_users=("new_users", "sum"),
            bounce_rate=("bounce_rate", "mean"),
            avg_session_duration=("avg_session_duration", "mean"),
            pages_per_session=("pages_per_session", "mean"),
        )
        .reset_index()
        .sort_values("sessions", ascending=False)
    )
    sm_agg["bounce_rate"] = sm_agg["bounce_rate"].round(1)
    sm_agg["avg_session_duration"] = sm_agg["avg_session_duration"].round(1)
    sm_agg["pages_per_session"] = sm_agg["pages_per_session"].round(1)

    st.dataframe(
        sm_agg,
        column_config={
            "source": st.column_config.TextColumn("Source"),
            "medium": st.column_config.TextColumn("Medium"),
            "sessions": st.column_config.NumberColumn("Sessions", format="%d"),
            "users": st.column_config.NumberColumn("Users", format="%d"),
            "new_users": st.column_config.NumberColumn("New Users", format="%d"),
            "bounce_rate": st.column_config.NumberColumn("Bounce Rate (%)", format="%.1f"),
            "avg_session_duration": st.column_config.NumberColumn("Avg. Duration (s)", format="%.1f"),
            "pages_per_session": st.column_config.NumberColumn("Pages/Session", format="%.1f"),
        },
        use_container_width=True,
        hide_index=True,
    )
