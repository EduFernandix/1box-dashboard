"""Webhook notification plugin for n8n, Slack, and generic HTTP endpoints."""

from typing import Any

from src.alerts.notifiers.base import BaseNotifier


class WebhookNotifier(BaseNotifier):
    """Sends alert notifications via HTTP webhook POST.

    Compatible with n8n webhook triggers, Slack incoming webhooks,
    and any HTTP endpoint that accepts JSON POST.
    """

    def __init__(self, url: str | None = None) -> None:
        """Initialize with webhook URL from config or parameter."""
        # TODO: Load from settings.webhook_url if url not provided
        self.url = url

    async def send(
        self,
        alert_id: str,
        severity: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> bool:
        """POST alert data to webhook URL as JSON."""
        # TODO: Implement with httpx
        raise NotImplementedError("Webhook notifier not yet implemented")

    async def test_connection(self) -> bool:
        """Verify webhook URL is reachable."""
        raise NotImplementedError

    @property
    def channel_name(self) -> str:
        return "webhook"
