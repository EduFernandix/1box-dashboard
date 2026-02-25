"""Alerts & Pipeline Log page."""

import streamlit as st
import yaml

from src.dashboard import data_loader
from src.dashboard.components.filters import render_sidebar_header
from src.dashboard.components.kpi_cards import render_kpi_card
from src.dashboard.theme import GREEN, ORANGE, RED, YELLOW
from src.dashboard.utils import format_number


def render() -> None:
    """Render the alerts and pipeline log page."""
    render_sidebar_header()

    st.header("Alerts & Pipeline Log")
    st.markdown('<hr class="brand-divider">', unsafe_allow_html=True)

    tab_alerts, tab_pipeline, tab_rules = st.tabs(
        ["Alert History", "Pipeline Log", "Alert Rules"]
    )

    # ---- Tab 1: Alert History ----
    with tab_alerts:
        severity_filter = st.selectbox(
            "Filter by severity",
            ["All", "low", "medium", "high", "critical"],
        )
        sev = None if severity_filter == "All" else severity_filter

        alerts = data_loader.get_alerts(limit=100, severity=sev)

        if alerts.empty:
            st.info("No alerts recorded yet.")
        else:
            # Summary cards
            cols = st.columns(4)
            with cols[0]:
                render_kpi_card("Total Alerts", format_number(len(alerts)))
            with cols[1]:
                critical = int((alerts["severity"] == "critical").sum())
                render_kpi_card("Critical", format_number(critical))
            with cols[2]:
                unack = int((~alerts["acknowledged"]).sum())
                render_kpi_card("Unacknowledged", format_number(unack))
            with cols[3]:
                notified = int(alerts["notified"].sum())
                render_kpi_card("Notified", format_number(notified))

            st.markdown("")

            # Color-code severity
            def _severity_badge(sev: str) -> str:
                colors = {"critical": RED, "high": ORANGE, "medium": YELLOW, "low": GREEN}
                color = colors.get(sev, "#999")
                return f'<span style="color:{color};font-weight:600">{sev.upper()}</span>'

            st.subheader("Alert History")
            st.dataframe(
                alerts[["triggered_at", "alert_name", "severity", "message",
                         "metric_value", "threshold_value", "notified", "acknowledged"]],
                column_config={
                    "triggered_at": st.column_config.DatetimeColumn("Time", format="YYYY-MM-DD HH:mm"),
                    "alert_name": st.column_config.TextColumn("Alert"),
                    "severity": st.column_config.TextColumn("Severity"),
                    "message": st.column_config.TextColumn("Message", width="large"),
                    "metric_value": st.column_config.NumberColumn("Value", format="%.2f"),
                    "threshold_value": st.column_config.NumberColumn("Threshold", format="%.2f"),
                    "notified": st.column_config.CheckboxColumn("Notified"),
                    "acknowledged": st.column_config.CheckboxColumn("Acked"),
                },
                use_container_width=True,
                hide_index=True,
            )

    # ---- Tab 2: Pipeline Log ----
    with tab_pipeline:
        runs = data_loader.get_pipeline_runs(limit=20)

        if runs.empty:
            st.info("No pipeline runs recorded yet.")
        else:
            latest = runs.iloc[0]
            cols = st.columns(4)
            with cols[0]:
                render_kpi_card("Last Status", latest["status"].upper())
            with cols[1]:
                render_kpi_card("Records Fetched", format_number(latest["records_fetched"]))
            with cols[2]:
                render_kpi_card("Records Inserted", format_number(latest["records_inserted"]))
            with cols[3]:
                last_time = latest["started_at"]
                render_kpi_card("Last Run", str(last_time)[:16] if last_time else "N/A")

            st.markdown("")
            st.subheader("Pipeline Run History")
            st.dataframe(
                runs[["started_at", "completed_at", "status", "source",
                       "records_fetched", "records_inserted", "error_message"]],
                column_config={
                    "started_at": st.column_config.DatetimeColumn("Started", format="YYYY-MM-DD HH:mm"),
                    "completed_at": st.column_config.DatetimeColumn("Completed", format="YYYY-MM-DD HH:mm"),
                    "status": st.column_config.TextColumn("Status"),
                    "source": st.column_config.TextColumn("Source"),
                    "records_fetched": st.column_config.NumberColumn("Fetched", format="%d"),
                    "records_inserted": st.column_config.NumberColumn("Inserted", format="%d"),
                    "error_message": st.column_config.TextColumn("Error", width="large"),
                },
                use_container_width=True,
                hide_index=True,
            )

    # ---- Tab 3: Alert Rules ----
    with tab_rules:
        st.subheader("Configured Alert Rules")
        try:
            from config.settings import PROJECT_ROOT
            rules_path = PROJECT_ROOT / "config" / "alerts.yaml"
            with open(rules_path) as f:
                rules_config = yaml.safe_load(f)

            rules = rules_config.get("rules", [])
            if rules:
                for rule in rules:
                    enabled = rule.get("enabled", True)
                    icon = "+" if enabled else "-"
                    sev = rule.get("severity", "medium")
                    colors = {"critical": RED, "high": ORANGE, "medium": YELLOW, "low": GREEN}
                    color = colors.get(sev, "#999")

                    with st.expander(
                        f"{'[ON]' if enabled else '[OFF]'} {rule.get('name', 'Unnamed')} "
                        f"({sev.upper()})",
                        expanded=False,
                    ):
                        st.markdown(f"**Description:** {rule.get('description', 'N/A')}")
                        st.markdown(f"**Metric:** `{rule.get('metric', 'N/A')}`")
                        st.markdown(f"**Condition:** {rule.get('condition', 'N/A')} (threshold: {rule.get('threshold', 'N/A')})")
                        st.markdown(f"**Level:** {rule.get('level', 'campaign')}")
                        st.markdown(f"**Cooldown:** {rule.get('cooldown_hours', 4)}h")
            else:
                st.info("No alert rules configured.")
        except Exception as e:
            st.warning(f"Could not load alert rules: {e}")
