"""Run this once to authenticate with Google via browser.
Saves token.json for the backend to reuse.
"""
import json
import os

from google_auth_oauthlib.flow import InstalledAppFlow

SCOPES = ["https://www.googleapis.com/auth/analytics.readonly"]
TOKEN_FILE = os.path.join(os.path.dirname(__file__), "token.json")

CLIENT_CONFIG = {
    "installed": {
        "client_id": os.environ["GOOGLE_CLIENT_ID"],
        "client_secret": os.environ["GOOGLE_CLIENT_SECRET"],
        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
        "token_uri": "https://oauth2.googleapis.com/token",
        "redirect_uris": ["http://localhost"],
    }
}

if __name__ == "__main__":
    print("Opening browser for Google login...")
    print("Login with your account that has GA4 access.")
    flow = InstalledAppFlow.from_client_config(CLIENT_CONFIG, SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent", access_type="offline")
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())
    print(f"Token saved to {TOKEN_FILE}")
    print("You can now start the backend with: python3 app.py")
