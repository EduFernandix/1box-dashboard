import json
import os
from pathlib import Path

from google.analytics.data_v1beta import BetaAnalyticsDataClient
from google.analytics.data_v1beta.types import (
    DateRange,
    Dimension,
    Filter,
    FilterExpression,
    Metric,
    OrderBy,
    RunReportRequest,
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROPERTY_ID = os.environ.get("GA4_PROPERTY_ID", "308309603")
TOKEN_FILE = Path(__file__).resolve().parent / "token.json"
SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]


def _get_credentials():
    """Load OAuth2 credentials from token.json (auto-refreshes if expired)."""
    if not TOKEN_FILE.exists():
        raise RuntimeError(
            "token.json not found. Run: cd backend && python3 auth_login.py"
        )

    from google.oauth2.credentials import Credentials
    from google.auth.transport.requests import Request

    with open(TOKEN_FILE) as f:
        info = json.load(f)

    creds = Credentials.from_authorized_user_info(info, SCOPES)

    if not creds.valid or creds.expired:
        creds.refresh(Request())
        with open(TOKEN_FILE, "w") as f:
            f.write(creds.to_json())

    return creds


def _safe_int(val, default=0):
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def _safe_float(val, default=0.0):
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


class GA4Client:
    def __init__(self, property_id=None):
        self.property_id = property_id or PROPERTY_ID
        creds = _get_credentials()
        self.client = BetaAnalyticsDataClient(credentials=creds)
        self.property = f"properties/{self.property_id}"

    def _run(self, request):
        return self.client.run_report(request)

    def _event_filter(self, event_name):
        return FilterExpression(
            filter=Filter(
                field_name="eventName",
                string_filter=Filter.StringFilter(value=event_name),
            )
        )

    def _transparent_filter(self):
        """Filter for all events containing 'transparent' in the name."""
        return FilterExpression(
            filter=Filter(
                field_name="eventName",
                string_filter=Filter.StringFilter(
                    value="transparent",
                    match_type=Filter.StringFilter.MatchType.CONTAINS,
                ),
            )
        )

    def _date_range(self, start_date, end_date):
        return [DateRange(start_date=start_date, end_date=end_date)]

    def get_marketing_overview(self, start_date: str, end_date: str) -> dict:
        dr = self._date_range(start_date, end_date)

        # 1. Rent count (bm_transparent_booking_complete)
        rent_resp = self._run(RunReportRequest(
            property=self.property,
            date_ranges=dr,
            metrics=[Metric(name="eventCount")],
            dimension_filter=self._event_filter("bm_transparent_booking_complete"),
        ))
        rent_count = _safe_int(rent_resp.rows[0].metric_values[0].value) if rent_resp.rows else 0

        # 2. Reservations count (transparent_booking)
        res_resp = self._run(RunReportRequest(
            property=self.property,
            date_ranges=dr,
            metrics=[Metric(name="eventCount")],
            dimension_filter=self._event_filter("transparent_booking"),
        ))
        reservations_count = _safe_int(res_resp.rows[0].metric_values[0].value) if res_resp.rows else 0

        # 3. Visits by device
        device_resp = self._run(RunReportRequest(
            property=self.property,
            date_ranges=dr,
            dimensions=[Dimension(name="deviceCategory")],
            metrics=[Metric(name="activeUsers")],
        ))
        visits_by_device = {}
        for row in device_resp.rows:
            visits_by_device[row.dimension_values[0].value] = _safe_int(row.metric_values[0].value)

        # 3b. Conversions by device (bm_transparent_booking_complete by device)
        conv_device_resp = self._run(RunReportRequest(
            property=self.property,
            date_ranges=dr,
            dimensions=[Dimension(name="deviceCategory")],
            metrics=[Metric(name="eventCount")],
            dimension_filter=self._event_filter("bm_transparent_booking_complete"),
        ))
        conversions_by_device = {}
        for row in conv_device_resp.rows:
            conversions_by_device[row.dimension_values[0].value] = _safe_int(row.metric_values[0].value)

        # 4. Users by source channel
        source_resp = self._run(RunReportRequest(
            property=self.property,
            date_ranges=dr,
            dimensions=[Dimension(name="sessionDefaultChannelGrouping")],
            metrics=[Metric(name="activeUsers")],
        ))
        conversions_by_source = []
        for row in source_resp.rows:
            conversions_by_source.append({
                "source": row.dimension_values[0].value,
                "users": _safe_int(row.metric_values[0].value),
            })

        # 4b. Demographics — Gender
        gender_resp = self._run(RunReportRequest(
            property=self.property,
            date_ranges=dr,
            dimensions=[Dimension(name="userGender")],
            metrics=[Metric(name="activeUsers")],
        ))
        demographics_gender = {}
        for row in gender_resp.rows:
            demographics_gender[row.dimension_values[0].value] = _safe_int(row.metric_values[0].value)

        # 4c. Demographics — Age
        age_resp = self._run(RunReportRequest(
            property=self.property,
            date_ranges=dr,
            dimensions=[Dimension(name="userAgeBracket")],
            metrics=[Metric(name="activeUsers")],
        ))
        demographics_age = {}
        for row in age_resp.rows:
            demographics_age[row.dimension_values[0].value] = _safe_int(row.metric_values[0].value)

        # 5. Engagement table (monthly)
        engagement_resp = self._run(RunReportRequest(
            property=self.property,
            date_ranges=dr,
            dimensions=[Dimension(name="year"), Dimension(name="month")],
            metrics=[
                Metric(name="activeUsers"),
                Metric(name="engagedSessions"),
                Metric(name="userEngagementDuration"),
            ],
            order_bys=[
                OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name="year")),
                OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name="month")),
            ],
        ))
        engagement = {}
        for row in engagement_resp.rows:
            key = f"{row.dimension_values[0].value}-{row.dimension_values[1].value}"
            users = _safe_int(row.metric_values[0].value)
            engaged = _safe_int(row.metric_values[1].value)
            duration = _safe_float(row.metric_values[2].value)
            avg_time = round(duration / users, 2) if users > 0 else 0
            engagement[key] = {
                "year": row.dimension_values[0].value,
                "month": row.dimension_values[1].value,
                "users": users,
                "engaged_sessions": engaged,
                "avg_engagement_time": avg_time,
                "rentals": 0,
                "reservations": 0,
            }

        # 6. Rentals monthly
        rentals_resp = self._run(RunReportRequest(
            property=self.property,
            date_ranges=dr,
            dimensions=[Dimension(name="year"), Dimension(name="month")],
            metrics=[Metric(name="eventCount")],
            dimension_filter=self._event_filter("bm_transparent_booking_complete"),
            order_bys=[
                OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name="year")),
                OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name="month")),
            ],
        ))
        for row in rentals_resp.rows:
            key = f"{row.dimension_values[0].value}-{row.dimension_values[1].value}"
            if key in engagement:
                engagement[key]["rentals"] = _safe_int(row.metric_values[0].value)

        # 7. Reservations monthly
        reserv_resp = self._run(RunReportRequest(
            property=self.property,
            date_ranges=dr,
            dimensions=[Dimension(name="year"), Dimension(name="month")],
            metrics=[Metric(name="eventCount")],
            dimension_filter=self._event_filter("transparent_booking"),
            order_bys=[
                OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name="year")),
                OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name="month")),
            ],
        ))
        for row in reserv_resp.rows:
            key = f"{row.dimension_values[0].value}-{row.dimension_values[1].value}"
            if key in engagement:
                engagement[key]["reservations"] = _safe_int(row.metric_values[0].value)

        engagement_table = list(engagement.values())
        trend = [
            {"year": r["year"], "month": r["month"], "rentals": r["rentals"], "reservations": r["reservations"]}
            for r in engagement_table
        ]

        # 8. Top Cities
        city_resp = self._run(RunReportRequest(
            property=self.property,
            date_ranges=dr,
            dimensions=[Dimension(name="city")],
            metrics=[Metric(name="activeUsers"), Metric(name="sessions")],
            order_bys=[
                OrderBy(metric=OrderBy.MetricOrderBy(metric_name="activeUsers"), desc=True),
            ],
            limit=10,
        ))
        top_cities = []
        for row in city_resp.rows:
            city_name = row.dimension_values[0].value
            if city_name and city_name != "(not set)":
                top_cities.append({
                    "city": city_name,
                    "users": _safe_int(row.metric_values[0].value),
                    "sessions": _safe_int(row.metric_values[1].value),
                })

        # 9. Sessions by day of week
        dow_resp = self._run(RunReportRequest(
            property=self.property,
            date_ranges=dr,
            dimensions=[Dimension(name="dayOfWeekName")],
            metrics=[Metric(name="activeUsers"), Metric(name="sessions")],
        ))
        sessions_by_dow = {}
        for row in dow_resp.rows:
            sessions_by_dow[row.dimension_values[0].value] = {
                "users": _safe_int(row.metric_values[0].value),
                "sessions": _safe_int(row.metric_values[1].value),
            }

        # 10. Sessions by hour
        hour_resp = self._run(RunReportRequest(
            property=self.property,
            date_ranges=dr,
            dimensions=[Dimension(name="hour")],
            metrics=[Metric(name="activeUsers"), Metric(name="sessions")],
            order_bys=[
                OrderBy(dimension=OrderBy.DimensionOrderBy(dimension_name="hour")),
            ],
        ))
        sessions_by_hour = {}
        for row in hour_resp.rows:
            sessions_by_hour[row.dimension_values[0].value] = {
                "users": _safe_int(row.metric_values[0].value),
                "sessions": _safe_int(row.metric_values[1].value),
            }

        return {
            "scorecards": {
                "rent": rent_count,
                "reservations": reservations_count,
                "total_cost": None,
            },
            "visits_by_device": visits_by_device,
            "conversions_by_device": conversions_by_device,
            "conversions_by_source": conversions_by_source,
            "demographics_gender": demographics_gender,
            "demographics_age": demographics_age,
            "engagement_table": engagement_table,
            "trend": trend,
            "top_cities": top_cities,
            "sessions_by_dow": sessions_by_dow,
            "sessions_by_hour": sessions_by_hour,
        }

    def get_funnel_events(self, start_date: str, end_date: str) -> list:
        """Fetch all 'transparent' events grouped by eventName, source, medium, landingPage."""
        dr = self._date_range(start_date, end_date)
        resp = self._run(RunReportRequest(
            property=self.property,
            date_ranges=dr,
            dimensions=[
                Dimension(name="eventName"),
                Dimension(name="sessionSource"),
                Dimension(name="sessionMedium"),
                Dimension(name="landingPage"),
            ],
            metrics=[Metric(name="eventCount")],
            dimension_filter=self._transparent_filter(),
        ))

        rows = []
        for row in resp.rows:
            rows.append({
                "event_name": row.dimension_values[0].value,
                "source": row.dimension_values[1].value or "(direct)",
                "medium": row.dimension_values[2].value or "(none)",
                "landing_page": row.dimension_values[3].value or "",
                "event_count": _safe_int(row.metric_values[0].value),
            })
        return rows

    def get_monthly_report(
        self,
        period_start: str,
        period_end: str,
        prev_start: str,
        prev_end: str,
    ) -> dict:
        """Fetch all data needed for the monthly report.

        Returns total users, leads (transparent_booking), customers
        (bm_transparent_booking_complete) for current and previous months,
        plus a per-location breakdown for the current month.
        """
        dr_current = self._date_range(period_start, period_end)
        dr_prev = self._date_range(prev_start, prev_end)

        # 1. Total active users — current week
        users_cur = self._run(RunReportRequest(
            property=self.property,
            date_ranges=dr_current,
            metrics=[Metric(name="activeUsers")],
        ))
        total_users = _safe_int(users_cur.rows[0].metric_values[0].value) if users_cur.rows else 0

        # 2. Total active users — previous week
        users_prev = self._run(RunReportRequest(
            property=self.property,
            date_ranges=dr_prev,
            metrics=[Metric(name="activeUsers")],
        ))
        prev_users = _safe_int(users_prev.rows[0].metric_values[0].value) if users_prev.rows else 0

        # 3. Leads (transparent_booking) — current week
        leads_cur = self._run(RunReportRequest(
            property=self.property,
            date_ranges=dr_current,
            metrics=[Metric(name="eventCount")],
            dimension_filter=self._event_filter("transparent_booking"),
        ))
        total_leads = _safe_int(leads_cur.rows[0].metric_values[0].value) if leads_cur.rows else 0

        # 4. Leads — previous week
        leads_prev = self._run(RunReportRequest(
            property=self.property,
            date_ranges=dr_prev,
            metrics=[Metric(name="eventCount")],
            dimension_filter=self._event_filter("transparent_booking"),
        ))
        prev_leads = _safe_int(leads_prev.rows[0].metric_values[0].value) if leads_prev.rows else 0

        # 5. Customers / Move-ins (bm_transparent_booking_complete) — current week
        cust_cur = self._run(RunReportRequest(
            property=self.property,
            date_ranges=dr_current,
            metrics=[Metric(name="eventCount")],
            dimension_filter=self._event_filter("bm_transparent_booking_complete"),
        ))
        total_customers = _safe_int(cust_cur.rows[0].metric_values[0].value) if cust_cur.rows else 0

        # 6. Customers — previous week
        cust_prev = self._run(RunReportRequest(
            property=self.property,
            date_ranges=dr_prev,
            metrics=[Metric(name="eventCount")],
            dimension_filter=self._event_filter("bm_transparent_booking_complete"),
        ))
        prev_customers = _safe_int(cust_prev.rows[0].metric_values[0].value) if cust_prev.rows else 0

        # 7. By-location breakdown for current week (leads + completed)
        loc_resp = self._run(RunReportRequest(
            property=self.property,
            date_ranges=dr_current,
            dimensions=[
                Dimension(name="eventName"),
                Dimension(name="landingPage"),
            ],
            metrics=[Metric(name="eventCount")],
            dimension_filter=self._transparent_filter(),
        ))

        # Return raw landing page data — caller does location mapping
        raw_locations = []
        for row in loc_resp.rows:
            raw_locations.append({
                "event_name": row.dimension_values[0].value,
                "landing_page": row.dimension_values[1].value,
                "event_count": _safe_int(row.metric_values[0].value),
            })

        # 8. Website engagement metrics — current month
        web_cur = self._run(RunReportRequest(
            property=self.property,
            date_ranges=dr_current,
            metrics=[
                Metric(name="totalUsers"),
                Metric(name="bounceRate"),
                Metric(name="averageSessionDuration"),
                Metric(name="screenPageViewsPerSession"),
                Metric(name="engagedSessions"),
                Metric(name="sessions"),
            ],
        ))
        wc = web_cur.rows[0].metric_values if web_cur.rows else []
        cur_unique = _safe_int(wc[0].value) if wc else 0
        cur_bounce = _safe_float(wc[1].value) if wc else 0.0
        cur_avg_dur = _safe_float(wc[2].value) if wc else 0.0
        cur_pps = _safe_float(wc[3].value) if wc else 0.0
        cur_engaged = _safe_int(wc[4].value) if wc else 0
        cur_sessions = _safe_int(wc[5].value) if wc else 0

        # 9. Website engagement metrics — previous month
        web_prev = self._run(RunReportRequest(
            property=self.property,
            date_ranges=dr_prev,
            metrics=[
                Metric(name="totalUsers"),
                Metric(name="bounceRate"),
                Metric(name="averageSessionDuration"),
                Metric(name="screenPageViewsPerSession"),
                Metric(name="engagedSessions"),
                Metric(name="sessions"),
            ],
        ))
        wp = web_prev.rows[0].metric_values if web_prev.rows else []
        prev_unique = _safe_int(wp[0].value) if wp else 0
        prev_bounce = _safe_float(wp[1].value) if wp else 0.0
        prev_avg_dur = _safe_float(wp[2].value) if wp else 0.0
        prev_pps = _safe_float(wp[3].value) if wp else 0.0
        prev_engaged = _safe_int(wp[4].value) if wp else 0
        prev_sessions = _safe_int(wp[5].value) if wp else 0

        cur_eng_rate = round((cur_engaged / cur_sessions) * 100, 1) if cur_sessions > 0 else 0.0
        prev_eng_rate = round((prev_engaged / prev_sessions) * 100, 1) if prev_sessions > 0 else 0.0

        # Compute rates
        user_to_lead = round((total_leads / total_users) * 100, 1) if total_users > 0 else 0.0
        lead_to_customer = round((total_customers / total_leads) * 100, 1) if total_leads > 0 else 0.0
        prev_user_to_lead = round((prev_leads / prev_users) * 100, 1) if prev_users > 0 else 0.0
        prev_lead_to_customer = round((prev_customers / prev_leads) * 100, 1) if prev_leads > 0 else 0.0

        return {
            "conversion": {
                "total_users": total_users,
                "total_leads": total_leads,
                "total_customers": total_customers,
                "user_to_lead_rate": user_to_lead,
                "lead_to_customer_rate": lead_to_customer,
                "prev_total_users": prev_users,
                "prev_total_leads": prev_leads,
                "prev_total_customers": prev_customers,
                "prev_user_to_lead_rate": prev_user_to_lead,
                "prev_lead_to_customer_rate": prev_lead_to_customer,
            },
            "raw_locations": raw_locations,
            "website_data": {
                "unique_visitors": cur_unique,
                "bounce_rate": round(cur_bounce * 100, 1),
                "avg_session_duration": round(cur_avg_dur, 1),
                "pages_per_session": round(cur_pps, 1),
                "engagement_rate": cur_eng_rate,
                "prev_unique_visitors": prev_unique,
                "prev_bounce_rate": round(prev_bounce * 100, 1),
                "prev_avg_session_duration": round(prev_avg_dur, 1),
                "prev_pages_per_session": round(prev_pps, 1),
                "prev_engagement_rate": prev_eng_rate,
            },
        }

    def get_funnel_by_location(self, start_date: str, end_date: str) -> list:
        """Fetch all 'transparent' events grouped by eventName and landingPage."""
        dr = self._date_range(start_date, end_date)
        resp = self._run(RunReportRequest(
            property=self.property,
            date_ranges=dr,
            dimensions=[
                Dimension(name="eventName"),
                Dimension(name="landingPage"),
            ],
            metrics=[Metric(name="eventCount")],
            dimension_filter=self._transparent_filter(),
        ))

        rows = []
        for row in resp.rows:
            rows.append({
                "event_name": row.dimension_values[0].value,
                "landing_page": row.dimension_values[1].value,
                "event_count": _safe_int(row.metric_values[0].value),
            })
        return rows
