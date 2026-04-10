"""Create a Google Sheet with budget targets pre-populated from config/budget-targets.json.

Uses OAuth2 user flow (opens browser) to create the sheet under your personal Google account,
then shares it with the service account for backend reading.
"""
import json
import os
import sys
from pathlib import Path

import gspread
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

ROOT = Path(__file__).resolve().parent.parent
BUDGET_FILE = ROOT / "config" / "budget-targets.json"
TOKEN_FILE = ROOT / "scripts" / "sheets_token.json"

CLIENT_CONFIG = {
    "installed": {
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost"],
    }
}

SERVICE_ACCOUNT_EMAIL = "ga4-analytics@gen-lang-client-0243781846.iam.gserviceaccount.com"


def get_user_creds():
    """Get OAuth2 user credentials (opens browser if needed)."""
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        if creds and creds.valid:
            return creds

    flow = InstalledAppFlow.from_client_config(CLIENT_CONFIG, SCOPES)
    creds = flow.run_local_server(port=0)

    TOKEN_FILE.write_text(creds.to_json())
    return creds


def main():
    # Load current budget data
    with open(BUDGET_FILE) as f:
        targets = json.load(f)

    leads = targets["leads"]
    moveins = targets["moveins"]
    all_facilities = sorted(set(list(leads.keys()) + list(moveins.keys())))

    # Authenticate as user
    print("🔐 Authenticating with Google (browser will open)...")
    creds = get_user_creds()
    client = gspread.authorize(creds)

    # Create spreadsheet
    print("📊 Creating spreadsheet...")
    sh = client.create("1BOX Budget Targets")
    ws = sh.sheet1
    ws.update_title("Budget Targets")

    # Header row
    ws.update("A1:C1", [["Facility", "Leads Target", "Move-ins Target"]])

    # Data rows
    rows = []
    for name in all_facilities:
        rows.append([name, leads.get(name, 0), moveins.get(name, 0)])

    if rows:
        ws.update(f"A2:C{len(rows) + 1}", rows)

    # Format header
    ws.format("A1:C1", {
        "textFormat": {"bold": True},
        "backgroundColor": {"red": 0.9, "green": 0.95, "blue": 0.9},
    })

    # Auto-resize columns
    ws.columns_auto_resize(0, 3)

    # Share with service account so backend can read it
    sh.share(SERVICE_ACCOUNT_EMAIL, perm_type="user", role="writer")

    sheet_id = sh.id
    sheet_url = sh.url

    print(f"\n✅ Google Sheet created successfully!")
    print(f"   Sheet ID: {sheet_id}")
    print(f"   URL: {sheet_url}")
    print(f"\n   Add this to your .env file:")
    print(f"   BUDGET_SHEET_ID={sheet_id}")
    print(f"\n   {len(rows)} facilities pre-populated.")
    print(f"   Shared with service account: {SERVICE_ACCOUNT_EMAIL}")


if __name__ == "__main__":
    main()
