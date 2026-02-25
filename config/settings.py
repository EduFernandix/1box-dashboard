"""Application settings loaded from environment variables."""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Project root = parent of config/
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Central configuration for the 1BOX Marketing Dashboard.

    Values are loaded from the .env file at the project root.
    Every field can be overridden via an environment variable of the same name.
    """

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- Application ---
    app_name: str = "1BOX Marketing Dashboard"
    debug: bool = False
    log_level: str = "INFO"

    # --- Database ---
    database_url: str = "sqlite+aiosqlite:///./data/dashboard.db"

    # --- Google Ads API ---
    google_ads_developer_token: str = ""
    google_ads_client_id: str = ""
    google_ads_client_secret: str = ""
    google_ads_refresh_token: str = ""
    google_ads_customer_id: str = ""
    google_ads_login_customer_id: str = ""

    # --- Google Analytics 4 ---
    ga4_property_id: str = ""
    ga4_credentials_path: str = "config/ga4-credentials.json"

    # --- Email Alerts (SMTP) ---
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    alert_email_from: str = "dashboard@1box.nl"
    alert_email_to: str = "marketing@1box.nl"

    # --- Webhook Alerts ---
    webhook_url: str = ""

    # --- API Server ---
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # --- ETL Scheduler ---
    fetch_interval_hours: int = 6

    @property
    def sync_database_url(self) -> str:
        """Return a synchronous database URL (for scripts like seed_demo_data)."""
        return self.database_url.replace("+aiosqlite", "").replace("+asyncpg", "")

    @property
    def db_path(self) -> Path:
        """Extract SQLite file path from the database URL."""
        if "sqlite" in self.database_url:
            path_str = self.database_url.split("///")[-1]
            return PROJECT_ROOT / path_str
        return PROJECT_ROOT / "data" / "dashboard.db"


settings = Settings()
