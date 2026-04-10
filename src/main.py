"""1BOX Marketing Dashboard — Minimal FastAPI for Funnel GA4 Data.

Run with:
    uv run uvicorn src.main:app --reload --port 8000
"""

import logging
import os
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Optional

import httpx
from dotenv import load_dotenv
from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware

# Load .env from project root
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from src.fetchers.ga4 import GA4Fetcher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="1BOX Dashboard API", version="0.3.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Funnel event names in order
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


def classify_channel(source: str, medium: str) -> str:
    """Map GA4 source/medium to Organic / Paid / Direct."""
    medium_lower = medium.lower() if medium else ""
    source_lower = source.lower() if source else ""

    if medium_lower == "organic":
        return "organic"
    if medium_lower in ("cpc", "paid", "ppc") or "ads" in source_lower:
        return "paid"
    return "direct"


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/api/ga4/funnel")
async def get_funnel_data(
    start_date: date = Query(default=None, description="Start date YYYY-MM-DD"),
    end_date: date = Query(default=None, description="End date YYYY-MM-DD"),
):
    """Fetch funnel event data from GA4, grouped by event and channel."""
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = date(end_date.year, end_date.month - 3 if end_date.month > 3 else 1, 1)

    try:
        fetcher = GA4Fetcher()
        raw = await fetcher.fetch_conversions(start_date, end_date)
    except Exception as e:
        logger.error(f"GA4 fetch failed: {e}")
        return {"error": str(e), "funnel": []}

    # Group by event_name + channel
    grouped = defaultdict(lambda: {"organic": 0, "paid": 0, "direct": 0})

    for row in raw:
        event = row["event_name"]
        if event not in FUNNEL_EVENT_SET:
            continue
        channel = classify_channel(row["source"], row["medium"])
        grouped[event][channel] += row["event_count"]

    # Build ordered funnel array
    funnel = []
    for i, event in enumerate(FUNNEL_EVENTS):
        counts = grouped.get(event, {"organic": 0, "paid": 0, "direct": 0})
        funnel.append({
            "step": i + 1,
            "event": event,
            "organic": counts["organic"],
            "paid": counts["paid"],
            "direct": counts["direct"],
        })

    return {
        "funnel": funnel,
        "date_range": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
    }


# ---- Location slug → display name mapping ----
LOCATION_SLUGS = {
    "amsterdam-zuidoost": "Amsterdam-Zuidoost",
    "den-haag": "Den Haag",
    "utrecht": "Utrecht",
    "breda": "Breda",
    "rotterdam": "Rotterdam",
    "helmond-kanaaldijk": "Helmond Kanaaldijk",
    "helmond": "Helmond Kanaaldijk",
    "lelystad": "Lelystad",
    "groningen": "Groningen",
    "rijswijk": "Rijswijk",
    "tilburg": "Tilburg",
    "hellevoetsluis": "Hellevoetsluis",
    "eindhoven": "Eindhoven",
    "arnhem": "Arnhem",
    "haarlem": "Haarlem",
    "almere-stad": "Almere Stad",
    "almere": "Almere Stad",
    "leiden": "Leiden",
    "amersfoort": "Amersfoort",
    "delft": "Delft",
    "zoetermeer": "Zoetermeer",
    "dordrecht": "Dordrecht",
    "apeldoorn": "Apeldoorn",
    "enschede": "Enschede",
    "zwolle": "Zwolle",
    "deventer": "Deventer",
    "nijmegen": "Nijmegen",
    "roosendaal": "Roosendaal",
    "den-bosch": "Den Bosch",
    "s-hertogenbosch": "Den Bosch",
    "maastricht": "Maastricht",
    "almere-buiten": "Almere Buiten",
    "leidschendam": "Leidschendam",
}


def extract_location(page_path: str) -> Optional[str]:
    """Extract a 1BOX location slug from a GA4 pagePath.

    Tries to match path segments against known location slugs.
    Example: /amsterdam-zuidoost/opslagruimte/ → 'Amsterdam-Zuidoost'
    """
    path_lower = page_path.lower().strip("/")
    segments = path_lower.split("/")
    for seg in segments:
        if seg in LOCATION_SLUGS:
            return LOCATION_SLUGS[seg]
    return None


# Funnel events grouped by stage
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


@app.get("/api/ga4/funnel/locations")
async def get_funnel_locations(
    start_date: date = Query(default=None, description="Start date YYYY-MM-DD"),
    end_date: date = Query(default=None, description="End date YYYY-MM-DD"),
):
    """Fetch funnel event data from GA4, grouped by location (pagePath)."""
    if end_date is None:
        end_date = date.today()
    if start_date is None:
        start_date = date(
            end_date.year,
            end_date.month - 3 if end_date.month > 3 else 1,
            1,
        )

    try:
        fetcher = GA4Fetcher()
        raw = await fetcher.fetch_conversions_by_location(start_date, end_date)
    except Exception as e:
        logger.error(f"GA4 location fetch failed: {e}")
        return {"error": str(e), "locations": []}

    # Group by location → stage counts
    loc_data: dict[str, dict] = defaultdict(
        lambda: {"started": 0, "booking": 0, "completed": 0}
    )

    for row in raw:
        event = row["event_name"]
        if event not in FUNNEL_EVENT_SET:
            continue
        location = extract_location(row["page_path"])
        if location is None:
            continue
        count = row["event_count"]
        if event in FUNNEL_STARTED:
            loc_data[location]["started"] += count
        elif event in FUNNEL_BOOKING:
            loc_data[location]["booking"] += count
        elif event in FUNNEL_COMPLETED:
            loc_data[location]["completed"] += count

    # Build response
    locations = []
    for name, counts in sorted(loc_data.items(), key=lambda x: x[1]["completed"], reverse=True):
        started = counts["started"]
        completed = counts["completed"]
        completion_rate = round((completed / started) * 100, 1) if started > 0 else 0.0
        # Approximate avg bounce as drop-off from started to completed
        avg_bounce = round(((started - completed) / started) * 100, 1) if started > 0 else 0.0
        locations.append({
            "name": name,
            "started": started,
            "booking": counts["booking"],
            "completed": completed,
            "avgBounce": avg_bounce,
            "completionRate": completion_rate,
        })

    return {
        "locations": locations,
        "date_range": {
            "start": start_date.isoformat(),
            "end": end_date.isoformat(),
        },
    }


@app.post("/api/ai/insights")
async def ai_insights(request: Request):
    """Proxy AI insights request to OpenAI."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key:
        return {"error": "OPENAI_API_KEY not configured"}

    body = await request.json()
    prompt = body.get("prompt", "")
    if not prompt:
        return {"error": "No prompt provided"}

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1500,
                    "temperature": 0.7,
                },
            )
            data = r.json()
            if "error" in data:
                return {"error": data["error"]["message"]}
            return {"insights": data["choices"][0]["message"]["content"]}
    except Exception as e:
        logger.error(f"AI insights failed: {e}")
        return {"error": str(e)}
