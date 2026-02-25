#!/usr/bin/env python3
"""Populate the SQLite database with 90 days of realistic demo data.

This script generates fake but realistic Google Ads and GA4 data
for the 1BOX Self-Storage marketing dashboard. Data includes:

- 5 Google Ads campaigns with Dutch self-storage CPC ranges
- Seasonality patterns (summer peak + January peak)
- Weekend dips in traffic and spend
- Correlated GA4 traffic and conversion data
- Keywords with quality scores

Usage:
    uv run python scripts/seed_demo_data.py
"""

import random
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

import numpy as np
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.models.database import (
    AdGroup,
    AlertHistory,
    Base,
    Campaign,
    GA4Conversion,
    GA4Geo,
    GA4Page,
    GA4Traffic,
    Keyword,
    PipelineRun,
)
from config.settings import settings

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SEED = 42
NUM_DAYS = 90

# Campaign definitions: (id, name, type, base_impressions, cpc_range, ctr_base, conv_rate, budget_eur)
CAMPAIGNS = [
    {
        "campaign_id": "C001",
        "name": "1BOX Opslagruimte Huren - Brand",
        "type": "SEARCH",
        "base_impressions": 800,
        "cpc_range": (0.50, 1.00),
        "ctr_base": 0.12,
        "conv_rate": 0.08,
        "budget_eur": 50.0,
        "ad_groups": [
            {"id": "AG001", "name": "Brand - Exact", "keywords": [
                ("1box", "EXACT"), ("1box opslag", "EXACT"), ("1box self storage", "EXACT"),
            ]},
            {"id": "AG002", "name": "Brand - Broad", "keywords": [
                ("1box opslagruimte", "BROAD"), ("1box huren", "BROAD"),
            ]},
        ],
    },
    {
        "campaign_id": "C002",
        "name": "1BOX Self Storage - Generic",
        "type": "SEARCH",
        "base_impressions": 1500,
        "cpc_range": (1.50, 2.50),
        "ctr_base": 0.04,
        "conv_rate": 0.04,
        "budget_eur": 120.0,
        "ad_groups": [
            {"id": "AG003", "name": "Generic - Opslagruimte", "keywords": [
                ("opslagruimte huren", "PHRASE"), ("self storage", "BROAD"),
                ("opslagbox huren", "PHRASE"), ("opslag huren", "BROAD"),
            ]},
            {"id": "AG004", "name": "Generic - Opslag", "keywords": [
                ("goedkope opslag", "BROAD"), ("opslag bij mij in de buurt", "PHRASE"),
            ]},
        ],
    },
    {
        "campaign_id": "C003",
        "name": "1BOX Opslag Amsterdam",
        "type": "SEARCH",
        "base_impressions": 600,
        "cpc_range": (2.00, 3.00),
        "ctr_base": 0.05,
        "conv_rate": 0.05,
        "budget_eur": 80.0,
        "ad_groups": [
            {"id": "AG005", "name": "Amsterdam - Opslag", "keywords": [
                ("opslagruimte amsterdam", "EXACT"), ("self storage amsterdam", "PHRASE"),
                ("opslag amsterdam centrum", "PHRASE"),
            ]},
        ],
    },
    {
        "campaign_id": "C004",
        "name": "1BOX Bedrijfsopslag",
        "type": "SEARCH",
        "base_impressions": 400,
        "cpc_range": (2.50, 3.50),
        "ctr_base": 0.035,
        "conv_rate": 0.03,
        "budget_eur": 70.0,
        "ad_groups": [
            {"id": "AG006", "name": "Bedrijf - Opslag", "keywords": [
                ("bedrijfsopslag", "EXACT"), ("opslag voor bedrijven", "PHRASE"),
                ("magazijnruimte huren", "BROAD"), ("kantooropslag", "BROAD"),
            ]},
        ],
    },
    {
        "campaign_id": "C005",
        "name": "1BOX Verhuisopslag",
        "type": "SEARCH",
        "base_impressions": 500,
        "cpc_range": (1.80, 2.80),
        "ctr_base": 0.045,
        "conv_rate": 0.06,
        "budget_eur": 60.0,
        "ad_groups": [
            {"id": "AG007", "name": "Verhuizing - Opslag", "keywords": [
                ("verhuisopslag", "EXACT"), ("tijdelijke opslag verhuizing", "PHRASE"),
                ("spullen opslaan verhuizing", "BROAD"),
            ]},
        ],
    },
]

# GA4 page paths with relative popularity weights
GA4_PAGES = [
    ("/", "Home - 1BOX Self Storage", 1.0),
    ("/opslagruimte-huren", "Opslagruimte Huren", 0.6),
    ("/prijzen", "Prijzen", 0.45),
    ("/locaties", "Alle Locaties", 0.35),
    ("/locaties/amsterdam", "1BOX Amsterdam", 0.25),
    ("/locaties/rotterdam", "1BOX Rotterdam", 0.20),
    ("/locaties/utrecht", "1BOX Utrecht", 0.15),
    ("/locaties/den-haag", "1BOX Den Haag", 0.12),
    ("/contact", "Contact", 0.18),
    ("/over-ons", "Over Ons", 0.08),
    ("/veelgestelde-vragen", "FAQ", 0.10),
    ("/blog/verhuistips", "Verhuistips Blog", 0.06),
]

# Dutch cities for GA4 geo data — with session share weights
DUTCH_CITIES = {
    "Amsterdam": 0.18,
    "Rotterdam": 0.14,
    "Utrecht": 0.10,
    "Den Haag": 0.09,
    "Eindhoven": 0.08,
    "Groningen": 0.06,
    "Tilburg": 0.05,
    "Almere": 0.05,
    "Breda": 0.05,
    "Nijmegen": 0.04,
    "Haarlem": 0.04,
    "Arnhem": 0.04,
    "Zaanstad": 0.03,
    "Amersfoort": 0.03,
    "Apeldoorn": 0.02,
}


# ---------------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------------


def seasonal_multiplier(d: date) -> float:
    """Seasonal demand curve for self-storage in the Netherlands.

    Summer peak (Jun-Aug): people move, students store.
    January peak: New Year moves, decluttering.
    Winter dip (Nov-Dec): fewer moves.
    """
    multipliers = {
        1: 1.25, 2: 0.95, 3: 1.00, 4: 1.05, 5: 1.15,
        6: 1.35, 7: 1.40, 8: 1.30, 9: 1.10, 10: 1.00,
        11: 0.90, 12: 0.85,
    }
    return multipliers[d.month]


def day_of_week_multiplier(d: date) -> float:
    """Weekend dips in search volume."""
    dow = d.weekday()  # 0=Monday
    if dow >= 5:  # Saturday, Sunday
        return 0.55 + random.uniform(-0.05, 0.05)
    if dow == 4:  # Friday — slightly lower
        return 0.90 + random.uniform(-0.05, 0.05)
    return 1.0 + random.uniform(-0.08, 0.08)


def add_noise(value: float, noise_pct: float = 0.15) -> float:
    """Add random noise to a value (±noise_pct)."""
    return value * (1.0 + random.uniform(-noise_pct, noise_pct))


def eur_to_micros(eur: float) -> int:
    """Convert EUR to micros (1 EUR = 1,000,000 micros)."""
    return int(eur * 1_000_000)


# ---------------------------------------------------------------------------
# Data Generators
# ---------------------------------------------------------------------------


def generate_campaign_data(
    campaign: dict, day: date, rng: random.Random
) -> tuple[dict, list[dict], list[dict]]:
    """Generate a single day's data for a campaign, its ad groups, and keywords.

    Returns (campaign_row, adgroup_rows, keyword_rows).
    """
    season = seasonal_multiplier(day)
    dow = day_of_week_multiplier(day)
    noise = 1.0 + rng.uniform(-0.12, 0.12)

    multiplier = season * dow * noise

    # Campaign-level metrics
    impressions = max(10, int(campaign["base_impressions"] * multiplier))
    ctr = max(0.005, campaign["ctr_base"] * (1.0 + rng.uniform(-0.2, 0.2)))
    clicks = max(1, int(impressions * ctr))

    cpc_min, cpc_max = campaign["cpc_range"]
    cpc = cpc_min + (cpc_max - cpc_min) * rng.random()
    cpc *= (1.0 + rng.uniform(-0.1, 0.1))  # CPC noise
    cpc = max(0.10, cpc)

    cost = clicks * cpc
    budget = campaign["budget_eur"]

    # Cap cost at budget
    if cost > budget * 1.1:
        cost = budget * (0.85 + rng.uniform(0, 0.15))
        clicks = max(1, int(cost / cpc))

    conv_rate = campaign["conv_rate"] * (1.0 + rng.uniform(-0.3, 0.3))
    conversions = max(0, round(clicks * conv_rate, 1))
    conversion_value = conversions * rng.uniform(40, 120)  # EUR per conversion

    campaign_row = {
        "campaign_id": campaign["campaign_id"],
        "campaign_name": campaign["name"],
        "campaign_type": campaign["type"],
        "status": "ENABLED",
        "date": day,
        "impressions": impressions,
        "clicks": clicks,
        "cost_micros": eur_to_micros(cost),
        "conversions": conversions,
        "conversion_value": round(conversion_value, 2),
        "average_cpc_micros": eur_to_micros(cpc),
        "ctr": round(ctr * 100, 2),  # Store as percentage
        "budget_micros": eur_to_micros(budget),
        "device": rng.choice(["MOBILE", "DESKTOP", "TABLET"]),
    }

    # Ad group-level metrics (distribute campaign totals)
    adgroup_rows = []
    keyword_rows = []
    num_ags = len(campaign["ad_groups"])

    for i, ag in enumerate(campaign["ad_groups"]):
        # Distribute clicks/impressions unevenly across ad groups
        ag_share = (0.6 if i == 0 else 0.4 / max(1, num_ags - 1))
        ag_impressions = max(1, int(impressions * ag_share * (1 + rng.uniform(-0.1, 0.1))))
        ag_clicks = max(0, int(clicks * ag_share * (1 + rng.uniform(-0.1, 0.1))))
        ag_cost = ag_clicks * cpc * (1 + rng.uniform(-0.05, 0.05))
        ag_conversions = round(ag_clicks * conv_rate, 1)
        ag_ctr = (ag_clicks / ag_impressions * 100) if ag_impressions > 0 else 0

        adgroup_rows.append({
            "ad_group_id": ag["id"],
            "ad_group_name": ag["name"],
            "campaign_id": campaign["campaign_id"],
            "date": day,
            "impressions": ag_impressions,
            "clicks": ag_clicks,
            "cost_micros": eur_to_micros(ag_cost),
            "conversions": ag_conversions,
            "ctr": round(ag_ctr, 2),
        })

        # Keyword-level metrics
        num_kws = len(ag["keywords"])
        for j, (kw_text, match_type) in enumerate(ag["keywords"]):
            kw_share = 1.0 / num_kws * (1 + rng.uniform(-0.2, 0.2))
            kw_impressions = max(0, int(ag_impressions * kw_share))
            kw_clicks = max(0, int(ag_clicks * kw_share))
            kw_cpc = cpc * (1 + rng.uniform(-0.15, 0.15))
            kw_cost = kw_clicks * kw_cpc
            kw_conversions = round(kw_clicks * conv_rate * (1 + rng.uniform(-0.2, 0.2)), 1)
            kw_ctr = (kw_clicks / kw_impressions * 100) if kw_impressions > 0 else 0

            # Quality score: weighted distribution (mostly 6-8, some outliers)
            qs_weights = [0.02, 0.03, 0.05, 0.08, 0.15, 0.25, 0.22, 0.12, 0.05, 0.03]
            quality_score = rng.choices(range(1, 11), weights=qs_weights, k=1)[0]

            qs_labels = ["BELOW_AVERAGE", "AVERAGE", "ABOVE_AVERAGE"]
            qs_weights_label = [0.2, 0.5, 0.3] if quality_score >= 6 else [0.5, 0.35, 0.15]

            keyword_rows.append({
                "keyword_id": f"KW{ag['id'][2:]}{j+1:02d}",
                "keyword_text": kw_text,
                "match_type": match_type,
                "ad_group_id": ag["id"],
                "campaign_id": campaign["campaign_id"],
                "date": day,
                "impressions": kw_impressions,
                "clicks": kw_clicks,
                "cost_micros": eur_to_micros(kw_cost),
                "conversions": max(0, kw_conversions),
                "ctr": round(kw_ctr, 2),
                "average_cpc_micros": eur_to_micros(kw_cpc),
                "quality_score": quality_score,
                "expected_ctr": rng.choices(qs_labels, weights=qs_weights_label, k=1)[0],
                "ad_relevance": rng.choices(qs_labels, weights=qs_weights_label, k=1)[0],
                "landing_page_experience": rng.choices(qs_labels, weights=qs_weights_label, k=1)[0],
            })

    return campaign_row, adgroup_rows, keyword_rows


def generate_ga4_traffic(
    day: date, total_ads_clicks: int, rng: random.Random
) -> list[dict]:
    """Generate GA4 traffic data correlated with Google Ads clicks."""
    season = seasonal_multiplier(day)
    dow = day_of_week_multiplier(day)
    rows = []

    # google / cpc — directly from ads
    cpc_sessions = max(1, int(total_ads_clicks * (1 + rng.uniform(-0.05, 0.05))))
    rows.append({
        "date": day,
        "source": "google",
        "medium": "cpc",
        "campaign_name": "(ads)",
        "sessions": cpc_sessions,
        "users": int(cpc_sessions * 0.85),
        "new_users": int(cpc_sessions * 0.70),
        "bounce_rate": round(rng.uniform(35, 55), 1),
        "avg_session_duration": round(rng.uniform(60, 180), 1),
        "pages_per_session": round(rng.uniform(2.0, 4.5), 1),
    })

    # google / organic — roughly 1.2x of ads traffic
    organic_sessions = max(5, int(total_ads_clicks * 1.2 * season * dow * (1 + rng.uniform(-0.15, 0.15))))
    rows.append({
        "date": day,
        "source": "google",
        "medium": "organic",
        "campaign_name": "(not set)",
        "sessions": organic_sessions,
        "users": int(organic_sessions * 0.80),
        "new_users": int(organic_sessions * 0.65),
        "bounce_rate": round(rng.uniform(40, 60), 1),
        "avg_session_duration": round(rng.uniform(80, 220), 1),
        "pages_per_session": round(rng.uniform(2.5, 5.0), 1),
    })

    # (direct) / (none)
    direct_sessions = max(3, int(total_ads_clicks * 0.4 * season * (1 + rng.uniform(-0.2, 0.2))))
    rows.append({
        "date": day,
        "source": "(direct)",
        "medium": "(none)",
        "campaign_name": "(not set)",
        "sessions": direct_sessions,
        "users": int(direct_sessions * 0.75),
        "new_users": int(direct_sessions * 0.40),
        "bounce_rate": round(rng.uniform(30, 50), 1),
        "avg_session_duration": round(rng.uniform(90, 240), 1),
        "pages_per_session": round(rng.uniform(3.0, 6.0), 1),
    })

    # Referral traffic (smaller)
    ref_sessions = max(1, int(total_ads_clicks * 0.1 * (1 + rng.uniform(-0.3, 0.3))))
    rows.append({
        "date": day,
        "source": "opslagvergelijker.nl",
        "medium": "referral",
        "campaign_name": "(not set)",
        "sessions": ref_sessions,
        "users": int(ref_sessions * 0.90),
        "new_users": int(ref_sessions * 0.85),
        "bounce_rate": round(rng.uniform(45, 65), 1),
        "avg_session_duration": round(rng.uniform(50, 150), 1),
        "pages_per_session": round(rng.uniform(1.5, 3.5), 1),
    })

    return rows


def generate_ga4_conversions(
    day: date, traffic_rows: list[dict], rng: random.Random
) -> list[dict]:
    """Generate GA4 conversion events based on traffic."""
    rows = []
    events = [
        ("generate_lead", 0.03, 0),     # 3% of sessions, no monetary value
        ("phone_call", 0.015, 0),        # 1.5% of sessions
        ("submit_form", 0.02, 0),        # 2% of sessions
    ]

    for traffic in traffic_rows:
        for event_name, rate, value in events:
            event_count = max(0, int(traffic["sessions"] * rate * (1 + rng.uniform(-0.3, 0.3))))
            if event_count > 0:
                rows.append({
                    "date": day,
                    "event_name": event_name,
                    "source": traffic["source"],
                    "medium": traffic["medium"],
                    "event_count": event_count,
                    "conversion_value": round(event_count * rng.uniform(30, 100), 2) if value == 0 else value,
                })

    return rows


def generate_ga4_pages(
    day: date, total_sessions: int, rng: random.Random
) -> list[dict]:
    """Generate GA4 page-level metrics."""
    rows = []

    for page_path, page_title, weight in GA4_PAGES:
        views = max(1, int(total_sessions * weight * (1 + rng.uniform(-0.15, 0.15))))
        unique_views = max(1, int(views * rng.uniform(0.65, 0.85)))

        rows.append({
            "date": day,
            "page_path": page_path,
            "page_title": page_title,
            "views": views,
            "unique_views": unique_views,
            "avg_time_on_page": round(rng.uniform(20, 180), 1),
            "bounce_rate": round(rng.uniform(25, 70), 1),
            "exit_rate": round(rng.uniform(15, 60), 1),
        })

    return rows


def generate_ga4_geo(
    day: date, total_sessions: int, rng: random.Random
) -> list[dict]:
    """Generate GA4 city-level geographic data for the Netherlands map."""
    rows = []
    for city, share in DUTCH_CITIES.items():
        city_sessions = max(1, int(total_sessions * share * (1 + rng.uniform(-0.25, 0.25))))
        city_users = max(1, int(city_sessions * rng.uniform(0.70, 0.90)))
        city_conversions = max(0, int(city_sessions * rng.uniform(0.02, 0.06)))
        rows.append({
            "date": day,
            "city": city,
            "country": "Netherlands",
            "sessions": city_sessions,
            "users": city_users,
            "conversions": city_conversions,
        })
    return rows


# ---------------------------------------------------------------------------
# Main Seeder
# ---------------------------------------------------------------------------


def seed_database() -> None:
    """Generate and insert 90 days of demo data."""
    random.seed(SEED)
    np.random.seed(SEED)
    rng = random.Random(SEED)

    # Ensure data directory exists
    db_path = settings.db_path
    db_path.parent.mkdir(parents=True, exist_ok=True)

    # Delete existing DB file to start fresh
    if db_path.exists():
        db_path.unlink()
        print(f"  Deleted existing database: {db_path}")

    # Create sync engine for seeding
    sync_url = settings.sync_database_url
    engine = create_engine(sync_url, echo=False)
    Base.metadata.create_all(engine)
    print(f"  Created database: {db_path}")

    today = date.today()
    start_date = today - timedelta(days=NUM_DAYS)

    # Counters
    total_campaigns = 0
    total_adgroups = 0
    total_keywords = 0
    total_traffic = 0
    total_conversions = 0
    total_pages = 0
    total_geo = 0

    with Session(engine) as session:
        for day_offset in range(NUM_DAYS):
            day = start_date + timedelta(days=day_offset)
            daily_ads_clicks = 0

            for campaign in CAMPAIGNS:
                campaign_row, adgroup_rows, keyword_rows = generate_campaign_data(
                    campaign, day, rng
                )

                session.add(Campaign(**campaign_row))
                total_campaigns += 1
                daily_ads_clicks += campaign_row["clicks"]

                for ag_row in adgroup_rows:
                    session.add(AdGroup(**ag_row))
                    total_adgroups += 1

                for kw_row in keyword_rows:
                    session.add(Keyword(**kw_row))
                    total_keywords += 1

            # GA4 traffic (correlated with ads)
            traffic_rows = generate_ga4_traffic(day, daily_ads_clicks, rng)
            for tr_row in traffic_rows:
                session.add(GA4Traffic(**tr_row))
                total_traffic += 1

            # GA4 conversions
            conv_rows = generate_ga4_conversions(day, traffic_rows, rng)
            for cv_row in conv_rows:
                session.add(GA4Conversion(**cv_row))
                total_conversions += 1

            # GA4 pages
            total_sessions = sum(t["sessions"] for t in traffic_rows)
            page_rows = generate_ga4_pages(day, total_sessions, rng)
            for pg_row in page_rows:
                session.add(GA4Page(**pg_row))
                total_pages += 1

            # GA4 geo (city-level)
            geo_rows = generate_ga4_geo(day, total_sessions, rng)
            for geo_row in geo_rows:
                session.add(GA4Geo(**geo_row))
                total_geo += 1

        # Add a couple of sample alert history entries
        session.add(AlertHistory(
            alert_rule_id="cpc_spike",
            alert_name="CPC Spike",
            severity="high",
            message="Campaign 'Generic' CPC increased 35% vs 7-day average (€2.85 → €3.85)",
            metric_value=3.85,
            threshold_value=30.0,
            notified=True,
            notification_type="email",
        ))
        session.add(AlertHistory(
            alert_rule_id="zero_conversions",
            alert_name="Zero Conversions",
            severity="critical",
            message="No conversions recorded on Tuesday (weekday)",
            metric_value=0.0,
            threshold_value=0.0,
            notified=True,
            notification_type="email",
        ))

        # Add a sample pipeline run
        session.add(PipelineRun(
            status="success",
            source="demo_seed",
            records_fetched=total_campaigns + total_traffic,
            records_inserted=total_campaigns + total_traffic,
            completed_at=datetime.now(tz=None),
        ))

        session.commit()

    print(f"\n  Seed complete!")
    print(f"  ─────────────────────────────────────")
    print(f"  Period:       {start_date} → {today - timedelta(days=1)}")
    print(f"  Campaigns:    {total_campaigns:,} rows")
    print(f"  Ad Groups:    {total_adgroups:,} rows")
    print(f"  Keywords:     {total_keywords:,} rows")
    print(f"  GA4 Traffic:  {total_traffic:,} rows")
    print(f"  GA4 Converts: {total_conversions:,} rows")
    print(f"  GA4 Pages:    {total_pages:,} rows")
    print(f"  GA4 Geo:      {total_geo:,} rows")
    print(f"  Alerts:       2 sample entries")
    print(f"  Pipeline:     1 run logged")
    print(f"  ─────────────────────────────────────")
    print(f"  Database:     {db_path}")


if __name__ == "__main__":
    print("\n🗄️  1BOX Dashboard — Seeding Demo Data\n")
    seed_database()
    print("\n✅ Done! You can now start the dashboard.\n")
