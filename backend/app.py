import json
import os
from collections import defaultdict
import calendar
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from openai import OpenAI

from ga4_client import GA4Client

app = FastAPI(title="1BOX GA4 API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ga4 = GA4Client()

OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")


@app.get("/health")
def health():
    return {"status": "ok"}

# ---- Funnel configuration ----
FUNNEL_EVENTS = [
    "clickto_sizepage_transparent",
    "clickto_detailspage_transparent",
    "select_unit_size_transparent",
    "transparent_booking",
    "bm_transparent_booking_start",
    "bm_transparent_booking_step_1",
    "bm_transparent_booking_step_2",
    "bm_transparent_booking_step_3",
    "bm_transparent_booking_step_4",
    "bm_transparent_booking_complete",
]
FUNNEL_EVENT_SET = set(FUNNEL_EVENTS)

FUNNEL_STARTED = {
    "clickto_sizepage_transparent",
    "clickto_detailspage_transparent",
    "select_unit_size_transparent",
}
FUNNEL_BOOKING = {
    "transparent_booking",
    "bm_transparent_booking_start",
    "bm_transparent_booking_step_1",
    "bm_transparent_booking_step_2",
    "bm_transparent_booking_step_3",
    "bm_transparent_booking_step_4",
}
FUNNEL_COMPLETED = {"bm_transparent_booking_complete"}

# ---- Location slug mapping ----
LOCATION_SLUGS = {
    "utrecht": "Utrecht",
    "amsterdam-schepenbergweg": "Amsterdam Schepenbergweg",
    "rotterdam-centrum": "Rotterdam Centrum",
    "den-haag": "Den Haag",
    "tilburg": "Tilburg",
    "breda": "Breda",
    "helmond-kanaaldijk": "Helmond Kanaaldijk",
    "den-bosch": "Den Bosch",
    "s-hertogenbosch": "Den Bosch",
    "rotterdam-zuid": "Rotterdam Zuid",
    "lelystad": "Lelystad",
    "rijswijk": "Rijswijk",
    "alphen-aan-den-rijn": "Alphen aan den Rijn",
    "schiedam": "Schiedam",
    "sittard": "Sittard",
    "eindhoven-best": "Eindhoven Best",
    "barendrecht": "Barendrecht",
    "alkmaar": "Alkmaar",
    "heerlen": "Heerlen",
    "groningen": "Groningen",
    "nijmegen-wijchen": "Nijmegen Wijchen",
    "almere": "Almere",
    "hellevoetsluis": "Hellevoetsluis",
    "helmond": "Helmond",
    "roermond": "Roermond",
    "boxtel": "Boxtel",
    "venlo": "Venlo",
    "goes": "Goes",
    "bergen-op-zoom": "Bergen op Zoom",
    "heerlen-heerlerbaan": "Heerlen Heerlerbaan",
}


def classify_channel(source: str, medium: str) -> str:
    medium_lower = medium.lower() if medium else ""
    source_lower = source.lower() if source else ""
    if medium_lower == "organic":
        return "organic"
    if medium_lower in ("cpc", "paid", "ppc") or "ads" in source_lower:
        return "paid"
    return "direct"


def extract_location(page_path: str) -> Optional[str]:
    path_lower = page_path.lower().strip("/")
    segments = path_lower.split("/")
    for seg in segments:
        if seg in LOCATION_SLUGS:
            return LOCATION_SLUGS[seg]
    return None


@app.get("/api/ga4/overview")
def ga4_overview(
    start_date: str = Query(default="2026-02-05"),
    end_date: str = Query(default_factory=lambda: date.today().isoformat()),
):
    try:
        data = ga4.get_marketing_overview(start_date, end_date)
        return data
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/ga4/funnel")
def ga4_funnel(
    start_date: str = Query(default="2026-02-05"),
    end_date: str = Query(default_factory=lambda: date.today().isoformat()),
    location: Optional[str] = Query(default=None, description="Filter by facility name"),
):
    """Fetch funnel event data from GA4, grouped by event and channel, with previous period comparison."""
    try:
        raw = ga4.get_funnel_events(start_date, end_date)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e), "funnel": []})

    # Build list of available locations from raw data
    available_locations = sorted(set(
        loc for r in raw
        if (loc := extract_location(r.get("landing_page", ""))) is not None
    ))

    # Calculate previous period of same length
    sd = date.fromisoformat(start_date)
    ed = date.fromisoformat(end_date)
    period_days = (ed - sd).days
    prev_end = sd - timedelta(days=1)
    prev_start = prev_end - timedelta(days=period_days)

    try:
        raw_prev = ga4.get_funnel_events(prev_start.isoformat(), prev_end.isoformat())
    except Exception:
        raw_prev = []

    grouped = defaultdict(lambda: {"organic": 0, "paid": 0, "direct": 0})
    for row in raw:
        event = row["event_name"]
        if event not in FUNNEL_EVENT_SET:
            continue
        if location:
            row_loc = extract_location(row.get("landing_page", ""))
            if row_loc != location:
                continue
        channel = classify_channel(row["source"], row["medium"])
        grouped[event][channel] += row["event_count"]

    grouped_prev = defaultdict(lambda: {"organic": 0, "paid": 0, "direct": 0})
    for row in raw_prev:
        event = row["event_name"]
        if event not in FUNNEL_EVENT_SET:
            continue
        if location:
            row_loc = extract_location(row.get("landing_page", ""))
            if row_loc != location:
                continue
        channel = classify_channel(row["source"], row["medium"])
        grouped_prev[event][channel] += row["event_count"]

    funnel = []
    for i, event in enumerate(FUNNEL_EVENTS):
        counts = grouped.get(event, {"organic": 0, "paid": 0, "direct": 0})
        prev_counts = grouped_prev.get(event, {"organic": 0, "paid": 0, "direct": 0})
        prev_total = prev_counts["organic"] + prev_counts["paid"] + prev_counts["direct"]
        funnel.append({
            "step": i + 1,
            "event": event,
            "organic": counts["organic"],
            "paid": counts["paid"],
            "direct": counts["direct"],
            "prev_total": prev_total,
        })

    return {
        "funnel": funnel,
        "locations": available_locations,
        "date_range": {"start": start_date, "end": end_date},
        "prev_date_range": {"start": prev_start.isoformat(), "end": prev_end.isoformat()},
    }


@app.get("/api/ga4/funnel/locations")
def ga4_funnel_locations(
    start_date: str = Query(default="2026-02-05"),
    end_date: str = Query(default_factory=lambda: date.today().isoformat()),
):
    """Fetch funnel event data from GA4, grouped by location via landingPage."""
    try:
        raw = ga4.get_funnel_by_location(start_date, end_date)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e), "locations": []})

    loc_data: dict[str, dict] = defaultdict(lambda: {"started": 0, "booking": 0, "completed": 0})

    for row in raw:
        event = row["event_name"]
        if event not in FUNNEL_EVENT_SET:
            continue

        location = extract_location(row["landing_page"])
        if location is None:
            continue

        count = row["event_count"]
        if event in FUNNEL_STARTED:
            loc_data[location]["started"] += count
        elif event in FUNNEL_BOOKING:
            loc_data[location]["booking"] += count
        elif event in FUNNEL_COMPLETED:
            loc_data[location]["completed"] += count

    locations = []
    for name, counts in sorted(loc_data.items(), key=lambda x: x[1]["started"], reverse=True):
        started = counts["started"]
        booking = counts["booking"]
        completed = counts["completed"]

        completion_rate = round((completed / started) * 100, 1) if started > 0 else 0.0
        avg_bounce = round(((started - completed) / started) * 100, 1) if started > 0 else 0.0

        locations.append({
            "name": name,
            "started": started,
            "booking": booking,
            "completed": completed,
            "avgBounce": avg_bounce,
            "completionRate": completion_rate,
        })

    return {
        "locations": locations,
        "date_range": {"start": start_date, "end": end_date},
    }


@app.get("/api/ga4/monthly-report")
def ga4_monthly_report(
    month: str = Query(default=None, description="Target month as YYYY-MM (e.g. 2026-03)"),
):
    """Fetch monthly report data: conversion rates, leads by facility, MoM comparison."""
    try:
        if month:
            year, mon = int(month[:4]), int(month[5:7])
        else:
            today = date.today()
            year, mon = today.year, today.month

        month_start = date(year, mon, 1)
        last_day = calendar.monthrange(year, mon)[1]
        month_end = date(year, mon, last_day)

        # Previous month
        if mon == 1:
            prev_year, prev_mon = year - 1, 12
        else:
            prev_year, prev_mon = year, mon - 1
        prev_start = date(prev_year, prev_mon, 1)
        prev_last_day = calendar.monthrange(prev_year, prev_mon)[1]
        prev_end = date(prev_year, prev_mon, prev_last_day)

        month_names = ['January','February','March','April','May','June',
                       'July','August','September','October','November','December']

        raw = ga4.get_monthly_report(
            month_start.isoformat(), month_end.isoformat(),
            prev_start.isoformat(), prev_end.isoformat(),
        )

        # Map raw locations to facility names
        loc_data = defaultdict(lambda: {"leads": 0, "completed": 0})
        for row in raw.get("raw_locations", []):
            event = row["event_name"]
            landing = row["landing_page"]
            count = row["event_count"]
            location = extract_location(landing)
            if location is None:
                continue
            if event == "transparent_booking":
                loc_data[location]["leads"] += count
            elif event == "bm_transparent_booking_complete":
                loc_data[location]["completed"] += count

        facilities = [
            {"name": name, "leads": d["leads"], "completed": d["completed"]}
            for name, d in sorted(loc_data.items(), key=lambda x: x[1]["leads"], reverse=True)
        ]

        return {
            "month_name": month_names[mon - 1],
            "month_number": mon,
            "year": year,
            "date_range": {"start": month_start.isoformat(), "end": month_end.isoformat()},
            "conversion": raw["conversion"],
            "leads_by_facility": facilities,
            "website_data": raw["website_data"],
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


BUDGET_FILE = Path(__file__).resolve().parent.parent / "config" / "budget-targets.json"
BUDGET_SHEET_ID = os.getenv("BUDGET_SHEET_ID", "")
SA_CREDS = os.getenv("GA4_CREDENTIALS_JSON", "")
if SA_CREDS and not os.path.isabs(SA_CREDS):
    SA_CREDS = str(Path(__file__).resolve().parent.parent / SA_CREDS)


def _load_budget_targets() -> dict:
    """Load budget targets from Google Sheets (preferred) or fallback to JSON."""
    if BUDGET_SHEET_ID:
        try:
            from sheets_client import get_budget_targets
            return get_budget_targets(SA_CREDS, BUDGET_SHEET_ID)
        except Exception as e:
            print(f"Sheets fallback to JSON: {e}")
    with open(BUDGET_FILE) as f:
        return json.load(f)


@app.get("/api/budget/pace")
def budget_pace():
    """Return budget targets + actual GA4 leads/move-ins for current month."""
    try:
        targets = _load_budget_targets()

        today = date.today()
        year, mon = today.year, today.month
        month_start = date(year, mon, 1)
        last_day = calendar.monthrange(year, mon)[1]
        month_end = date(year, mon, last_day)

        # Fetch current month location data from GA4
        raw = ga4.get_monthly_report(
            month_start.isoformat(), month_end.isoformat(),
            month_start.isoformat(), month_end.isoformat(),  # prev not needed
        )

        loc_data = defaultdict(lambda: {"leads": 0, "completed": 0})
        for row in raw.get("raw_locations", []):
            event = row["event_name"]
            landing = row["landing_page"]
            count = row["event_count"]
            location = extract_location(landing)
            if location is None:
                continue
            if event == "transparent_booking":
                loc_data[location]["leads"] += count
            elif event == "bm_transparent_booking_complete":
                loc_data[location]["completed"] += count

        month_names = ['January', 'February', 'March', 'April', 'May', 'June',
                       'July', 'August', 'September', 'October', 'November', 'December']

        facilities = []
        all_names = set(list(targets.get("leads", {}).keys()) + list(loc_data.keys()))
        for name in sorted(all_names):
            facilities.append({
                "name": name,
                "leads_actual": loc_data[name]["leads"],
                "leads_budget": targets.get("leads", {}).get(name, 0),
                "moveins_actual": loc_data[name]["completed"],
                "moveins_budget": targets.get("moveins", {}).get(name, 0),
            })

        return {
            "current_day": today.day,
            "days_in_month": last_day,
            "month_name": month_names[mon - 1],
            "facilities": facilities,
        }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.get("/api/ga4/conversion-trend")
def ga4_conversion_trend(months: int = Query(default=6)):
    """Return monthly conversion rates (user→lead and lead→customer) for the last N months."""
    try:
        today = date.today()
        results = []

        for i in range(months):
            # Go back i months from current
            if i == 0:
                y, m = today.year, today.month
            else:
                m = today.month - i
                y = today.year
                while m <= 0:
                    m += 12
                    y -= 1

            m_start = date(y, m, 1)
            m_last = calendar.monthrange(y, m)[1]
            m_end = date(y, m, m_last)

            # Fetch users, leads, customers for this month
            raw = ga4.get_monthly_report(
                m_start.isoformat(), m_end.isoformat(),
                m_start.isoformat(), m_end.isoformat(),  # prev not needed here
            )
            c = raw["conversion"]

            month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun',
                           'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

            results.append({
                "month": month_names[m - 1],
                "year": y,
                "user_to_lead": c["user_to_lead_rate"],
                "lead_to_customer": c["lead_to_customer_rate"],
            })

        results.reverse()  # oldest first
        return {"trend": results}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/api/ai/insights")
async def ai_insights(request: Request):
    try:
        body = await request.json()
        client = OpenAI(api_key=OPENAI_API_KEY)
        prompt = f"""You are a digital marketing analyst for 1BOX Self-Storage in the Netherlands.
Analyze the following Google Analytics 4 data and provide 3-5 key actionable insights.
Be concise, use bullet points. Focus on:
- Device performance (visits vs conversions by device)
- Traffic source effectiveness
- Rental and reservation trends
- Demographics patterns
- Any notable anomalies or opportunities

Data:
{json.dumps(body, indent=2)}

Respond in English with bullet points. Keep each insight to 1-2 sentences max."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=2000,
            temperature=0.7,
        )
        return {"insights": response.choices[0].message.content}
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
