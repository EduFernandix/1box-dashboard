# 1BOX Marketing Dashboard

Marketing analytics dashboard for **1BOX Self-Storage** (29 locations, Netherlands). Pulls data from Google Ads and GA4, displays real-time metrics, and sends alerts when KPIs cross thresholds.

## Architecture

```
┌──────────────┐     ┌──────────────┐
│  Google Ads  │     │   GA4 API    │
│     API      │     │  (v1beta)    │
└──────┬───────┘     └──────┬───────┘
       │                    │
       ▼                    ▼
┌──────────────────────────────────┐
│         ETL Pipeline             │
│  (APScheduler · every 6h)        │
└──────────────┬───────────────────┘
               │
               ▼
┌──────────────────────────────────┐
│         SQLite / PostgreSQL      │
│  campaigns · keywords · ga4_*   │
│  alerts_history · pipeline_runs │
└──────┬───────────────┬──────────┘
       │               │
       ▼               ▼
┌──────────┐   ┌───────────────┐
│ FastAPI  │   │   Streamlit   │
│ REST API │   │   Dashboard   │
│ :8000    │   │   :8501       │
└──────────┘   └───────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3.12, FastAPI, SQLAlchemy 2.0 |
| Dashboard | Streamlit, Plotly |
| Database | SQLite (dev) / PostgreSQL (prod) |
| APIs | google-ads, google-analytics-data |
| Alerts | Rule engine + Email (SMTP) / Webhook |
| Scheduling | APScheduler |
| Package Manager | uv |

## Quick Start

### 1. Clone & install

```bash
cd ~/Desktop/1box-dashboard
uv sync
```

### 2. Seed demo data (no API credentials needed)

```bash
uv run python scripts/seed_demo_data.py
```

This creates `data/dashboard.db` with 90 days of realistic data:
- 5 Google Ads campaigns with Dutch self-storage metrics
- Correlated GA4 traffic and conversion data
- Sample alert history

### 3. Start the API

```bash
uv run uvicorn src.main:app --reload --port 8000
```

Visit http://localhost:8000/health to verify.

### 4. Start the dashboard

```bash
uv run streamlit run src/dashboard/app.py
```

### 5. Set up real API credentials (when ready)

```bash
uv run python scripts/setup_credentials.py
```

Interactive script that guides you through Google Cloud, Google Ads, GA4, and SMTP setup.

## Project Structure

```
1box-dashboard/
├── config/
│   ├── settings.py             # Pydantic Settings (loads .env)
│   ├── alerts.yaml             # 5 default alert rules
│   └── google-ads.yaml.example # Credential template
├── src/
│   ├── main.py                 # FastAPI application
│   ├── fetchers/               # Google Ads + GA4 API clients
│   ├── models/
│   │   ├── database.py         # SQLAlchemy 2.0 models (8 tables)
│   │   └── schemas.py          # Pydantic v2 schemas
│   ├── pipeline/               # ETL orchestration + scheduler
│   ├── alerts/                 # Rule engine + notifier plugins
│   ├── analytics/              # Anomaly detection, forecasting, scoring
│   └── dashboard/              # Streamlit app + pages
├── templates/email/            # Jinja2 email templates
├── scripts/
│   ├── setup_credentials.py    # Interactive credential setup
│   └── seed_demo_data.py       # Demo data generator
└── tests/                      # pytest test suite
```

## Database Tables

| Table | Description |
|-------|------------|
| `campaigns` | Google Ads campaign metrics (daily) |
| `ad_groups` | Ad group metrics (daily) |
| `keywords` | Keyword metrics + quality scores |
| `ga4_traffic` | GA4 sessions by source/medium |
| `ga4_conversions` | GA4 conversion events |
| `ga4_pages` | Page-level metrics |
| `alerts_history` | Triggered alert log |
| `pipeline_runs` | ETL execution log |

## Running Tests

```bash
uv run pytest tests/ -v
```

## Environment Variables

Copy `.env.example` to `.env` and fill in your values. See the file for documentation on each variable.

## License

Private — 1BOX Self-Storage.
