"""Email notification plugin using SMTP (aiosmtplib).

Sends alert emails using Jinja2 HTML templates.
"""

from typing import Any

from src.alerts.notifiers.base import BaseNotifier


class EmailNotifier(BaseNotifier):
    """Sends alert notifications via SMTP email.

    Uses aiosmtplib for async email delivery and Jinja2 templates
    for HTML formatting.
    """

    def __init__(self) -> None:
        """Initialize with SMTP settings from config."""
        # TODO: Load SMTP config from settings
        pass

    async def send(
        self,
        alert_id: str,
        severity: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> bool:
        """Send an alert email."""
        # TODO: Implement with aiosmtplib + Jinja2 templates
        raise NotImplementedError("Email notifier not yet implemented")

    async def test_connection(self) -> bool:
        """Test SMTP connection."""
        raise NotImplementedError

    @property
    def channel_name(self) -> str:
        return "email"
