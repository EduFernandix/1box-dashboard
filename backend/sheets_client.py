"""Google Sheets client for reading budget targets."""
import json
import time
from pathlib import Path

import gspread
from google.oauth2.service_account import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

_cache = {"data": None, "ts": 0}
CACHE_TTL = 300  # 5 minutes


def _get_client(credentials_path: str) -> gspread.Client:
    creds = Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    return gspread.authorize(creds)


def get_budget_targets(credentials_path: str, sheet_id: str) -> dict:
    """Read budget targets from Google Sheet. Returns {"leads": {...}, "moveins": {...}}.

    Caches results for 5 minutes.
    """
    now = time.time()
    if _cache["data"] and (now - _cache["ts"]) < CACHE_TTL:
        return _cache["data"]

    client = _get_client(credentials_path)
    sh = client.open_by_key(sheet_id)
    ws = sh.sheet1

    rows = ws.get_all_records()
    leads = {}
    moveins = {}

    for row in rows:
        name = str(row.get("Facility", "")).strip()
        if not name:
            continue
        leads[name] = int(row.get("Leads Target", 0) or 0)
        moveins[name] = int(row.get("Move-ins Target", 0) or 0)

    result = {"leads": leads, "moveins": moveins}
    _cache["data"] = result
    _cache["ts"] = now
    return result
