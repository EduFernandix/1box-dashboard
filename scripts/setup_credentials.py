#!/usr/bin/env python3
"""Interactive credential setup for the 1BOX Marketing Dashboard.

Guides the user step-by-step through configuring Google Ads API,
GA4 Data API, and SMTP credentials. Generates the OAuth2 refresh
token automatically.

Usage:
    uv run python scripts/setup_credentials.py
"""

import getpass
import json
import re
import sys
import webbrowser
from pathlib import Path

# Project root
ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = ROOT / ".env"
GOOGLE_ADS_YAML = ROOT / "config" / "google-ads.yaml"

SCOPES = [
    "https://www.googleapis.com/auth/adwords",
    "https://www.googleapis.com/auth/analytics.readonly",
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def banner(text: str) -> None:
    """Print a section banner."""
    width = 60
    print(f"\n{'═' * width}")
    print(f"  {text}")
    print(f"{'═' * width}\n")


def step_header(step: int, total: int, title: str) -> None:
    """Print a step header."""
    print(f"\n── Step {step}/{total}: {title} {'─' * (40 - len(title))}\n")


def ask(prompt: str, required: bool = True, secret: bool = False) -> str:
    """Ask for user input with optional validation."""
    while True:
        if secret:
            value = getpass.getpass(f"  {prompt}: ").strip()
        else:
            value = input(f"  {prompt}: ").strip()
        if value or not required:
            return value
        print("  ⚠  This field is required. Please enter a value.\n")


def ask_optional(prompt: str) -> str:
    """Ask for optional user input."""
    return ask(prompt, required=False)


def validate_customer_id(cid: str) -> str | None:
    """Validate Google Ads Customer ID format (XXX-XXX-XXXX)."""
    pattern = r"^\d{3}-\d{3}-\d{4}$"
    if re.match(pattern, cid):
        return cid.replace("-", "")
    # Try without dashes
    if re.match(r"^\d{10}$", cid):
        return cid
    return None


def update_env(key: str, value: str) -> None:
    """Update a key in the .env file."""
    env_content = ENV_FILE.read_text() if ENV_FILE.exists() else ""
    pattern = rf"^{key}=.*$"
    replacement = f"{key}={value}"

    if re.search(pattern, env_content, re.MULTILINE):
        env_content = re.sub(pattern, replacement, env_content, flags=re.MULTILINE)
    else:
        env_content += f"\n{replacement}\n"

    ENV_FILE.write_text(env_content)


def write_google_ads_yaml(
    developer_token: str,
    client_id: str,
    client_secret: str,
    refresh_token: str,
    login_customer_id: str,
) -> None:
    """Generate config/google-ads.yaml."""
    content = f"""developer_token: "{developer_token}"
client_id: "{client_id}"
client_secret: "{client_secret}"
refresh_token: "{refresh_token}"
login_customer_id: "{login_customer_id}"
use_proto_plus: true
"""
    GOOGLE_ADS_YAML.write_text(content)


# ---------------------------------------------------------------------------
# OAuth2 Flow
# ---------------------------------------------------------------------------


def run_oauth_flow(client_id: str, client_secret: str) -> str | None:
    """Run the OAuth2 installed app flow to obtain a refresh token."""
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("  ⚠  google-auth-oauthlib not installed. Run:")
        print("     uv add google-auth-oauthlib")
        return None

    client_config = {
        "installed": {
            "client_id": client_id,
            "client_secret": client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }

    flow = InstalledAppFlow.from_client_config(client_config, scopes=SCOPES)

    print("  Opening browser for Google authorization...")
    print("  (If the browser doesn't open, copy the URL shown below)\n")

    try:
        credentials = flow.run_local_server(port=8090, open_browser=True)
        return credentials.refresh_token
    except Exception as e:
        print(f"  ⚠  OAuth flow failed: {e}")
        print("  You can try again or enter a refresh token manually.")
        return None


# ---------------------------------------------------------------------------
# API Connection Tests
# ---------------------------------------------------------------------------


def test_google_ads(
    developer_token: str,
    client_id: str,
    client_secret: str,
    refresh_token: str,
    customer_id: str,
    login_customer_id: str,
) -> bool:
    """Test Google Ads API connection."""
    try:
        from google.ads.googleads.client import GoogleAdsClient
    except ImportError:
        print("  ⚠  google-ads package not installed. Skipping test.")
        print("     Install with: uv add google-ads")
        return False

    try:
        config = {
            "developer_token": developer_token,
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "login_customer_id": login_customer_id,
            "use_proto_plus": True,
        }
        client = GoogleAdsClient.load_from_dict(config)
        ga_service = client.get_service("GoogleAdsService")
        query = "SELECT customer.id FROM customer LIMIT 1"
        response = ga_service.search(customer_id=customer_id, query=query)
        list(response)  # Force execution
        return True
    except Exception as e:
        print(f"  ⚠  Google Ads API error: {e}")
        return False


def test_ga4(property_id: str) -> bool:
    """Test GA4 Data API connection."""
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import (
            DateRange,
            Dimension,
            Metric,
            RunReportRequest,
        )
    except ImportError:
        print("  ⚠  google-analytics-data not installed. Skipping test.")
        return False

    try:
        client = BetaAnalyticsDataClient()
        request = RunReportRequest(
            property=f"properties/{property_id}",
            dimensions=[Dimension(name="date")],
            metrics=[Metric(name="sessions")],
            date_ranges=[DateRange(start_date="yesterday", end_date="yesterday")],
        )
        client.run_report(request)
        return True
    except Exception as e:
        print(f"  ⚠  GA4 API error: {e}")
        return False


# ---------------------------------------------------------------------------
# Main Script
# ---------------------------------------------------------------------------


def main() -> None:
    """Run the interactive credential setup."""
    banner("1BOX Marketing Dashboard — Credential Setup")

    print("  This script will guide you through setting up:")
    print("  1. Google Cloud Project & OAuth credentials")
    print("  2. Google Ads API credentials")
    print("  3. OAuth2 authorization (automatic)")
    print("  4. GA4 Property configuration")
    print("  5. Email notification settings (optional)")
    print()
    input("  Press Enter to begin...")

    total_steps = 5

    # ── Step 1: Google Cloud Project ──────────────────────────────────────

    step_header(1, total_steps, "Google Cloud Project")
    print("  First, you need a Google Cloud Project with APIs enabled.")
    print()
    print("  1. Go to: https://console.cloud.google.com/")
    print("  2. Create a new project (or select existing)")
    print("  3. Enable these APIs:")
    print("     • Google Ads API")
    print("       https://console.cloud.google.com/apis/library/googleads.googleapis.com")
    print("     • Google Analytics Data API")
    print("       https://console.cloud.google.com/apis/library/analyticsdata.googleapis.com")
    print("  4. Go to Credentials → Create Credentials → OAuth 2.0 Client ID")
    print("     • Application type: Desktop app")
    print("     • Download the JSON or copy Client ID + Secret")
    print()

    client_id = ask("OAuth Client ID (ending in .apps.googleusercontent.com)")
    client_secret = ask("OAuth Client Secret", secret=True)

    update_env("GOOGLE_ADS_CLIENT_ID", client_id)
    update_env("GOOGLE_ADS_CLIENT_SECRET", client_secret)
    print("\n  ✓ OAuth credentials saved to .env")

    # ── Step 2: Google Ads ────────────────────────────────────────────────

    step_header(2, total_steps, "Google Ads API")
    print("  Get your Developer Token from:")
    print("  https://ads.google.com/aw/apicenter")
    print()

    developer_token = ask("Developer Token", secret=True)
    update_env("GOOGLE_ADS_DEVELOPER_TOKEN", developer_token)

    while True:
        customer_id_raw = ask("Customer ID (format: XXX-XXX-XXXX)")
        customer_id = validate_customer_id(customer_id_raw)
        if customer_id:
            break
        print("  ⚠  Invalid format. Use XXX-XXX-XXXX (e.g., 123-456-7890)\n")

    update_env("GOOGLE_ADS_CUSTOMER_ID", customer_id)

    login_customer_id_raw = ask_optional(
        "Manager Account (MCC) ID (leave blank if none)"
    )
    login_customer_id = ""
    if login_customer_id_raw:
        validated = validate_customer_id(login_customer_id_raw)
        if validated:
            login_customer_id = validated
        else:
            print("  ⚠  Invalid format, skipping MCC ID.")

    update_env("GOOGLE_ADS_LOGIN_CUSTOMER_ID", login_customer_id)
    print("\n  ✓ Google Ads credentials saved to .env")

    # ── Step 3: OAuth2 Authorization ──────────────────────────────────────

    step_header(3, total_steps, "OAuth2 Authorization")
    print("  We'll now open your browser to authorize API access.")
    print("  Sign in with the Google account that manages your Ads & GA4.\n")

    refresh_token = run_oauth_flow(client_id, client_secret)

    if not refresh_token:
        print("\n  ⚠  Automatic OAuth flow failed.")
        refresh_token = ask("Enter refresh token manually (or leave blank)", required=False)

    if refresh_token:
        update_env("GOOGLE_ADS_REFRESH_TOKEN", refresh_token)
        write_google_ads_yaml(
            developer_token, client_id, client_secret,
            refresh_token, login_customer_id,
        )
        print("\n  ✓ Refresh token saved to .env and config/google-ads.yaml")
    else:
        print("\n  ⚠  No refresh token obtained. You'll need to set this up later.")

    # ── Step 4: GA4 Property ──────────────────────────────────────────────

    step_header(4, total_steps, "Google Analytics 4")
    print("  Find your GA4 Property ID:")
    print("  GA4 Admin → Property → Property Details → Property ID (number)")
    print()

    ga4_property_id = ask("GA4 Property ID (e.g., 123456789)")
    update_env("GA4_PROPERTY_ID", ga4_property_id)
    print("\n  ✓ GA4 Property ID saved to .env")

    # ── Step 5: Email Notifications ───────────────────────────────────────

    step_header(5, total_steps, "Email Notifications (optional)")
    print("  Configure SMTP for alert emails (press Enter to skip each).\n")

    smtp_host = ask_optional("SMTP Host (e.g., smtp.gmail.com)")
    if smtp_host:
        update_env("SMTP_HOST", smtp_host)
        smtp_port = ask_optional("SMTP Port (default: 587)") or "587"
        update_env("SMTP_PORT", smtp_port)
        smtp_user = ask_optional("SMTP Username")
        update_env("SMTP_USER", smtp_user)
        smtp_password = ask_optional("SMTP Password")
        if smtp_password:
            update_env("SMTP_PASSWORD", smtp_password)
        alert_email = ask_optional("Alert recipient email") or "marketing@1box.nl"
        update_env("ALERT_EMAIL_TO", alert_email)
        print("\n  ✓ SMTP settings saved to .env")
    else:
        print("\n  ⏭  Skipped email configuration.")

    # ── Connection Tests ──────────────────────────────────────────────────

    banner("Testing API Connections")

    print("  Testing Google Ads API...", end=" ", flush=True)
    if refresh_token and test_google_ads(
        developer_token, client_id, client_secret,
        refresh_token, customer_id, login_customer_id,
    ):
        print("✓ Connected!")
    else:
        print("✗ Failed (you can fix credentials in .env and retry)")

    print("  Testing GA4 Data API...", end=" ", flush=True)
    if test_ga4(ga4_property_id):
        print("✓ Connected!")
    else:
        print("✗ Failed (check credentials and property ID)")

    # ── Done ──────────────────────────────────────────────────────────────

    banner("Setup Complete!")
    print("  Files updated:")
    print(f"    • {ENV_FILE}")
    if GOOGLE_ADS_YAML.exists():
        print(f"    • {GOOGLE_ADS_YAML}")
    print()
    print("  Next steps:")
    print("    1. Run the seed script:  uv run python scripts/seed_demo_data.py")
    print("    2. Start the API:        uv run uvicorn src.main:app --reload")
    print("    3. Start the dashboard:  uv run streamlit run src/dashboard/app.py")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n  Setup cancelled. Your progress has been saved to .env.\n")
        sys.exit(0)
