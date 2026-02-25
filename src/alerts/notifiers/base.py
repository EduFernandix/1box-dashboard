"""Abstract base class for alert notification plugins.

All notification channels (email, webhook, WhatsApp, Slack) must
implement this interface to be used by the AlertEngine.
"""

from abc import ABC, abstractmethod
from typing import Any


class BaseNotifier(ABC):
    """Plugin interface for alert notification channels."""

    @abstractmethod
    async def send(
        self,
        alert_id: str,
        severity: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> bool:
        """Send an alert notification.

        Args:
            alert_id: Unique identifier for the alert rule that triggered.
            severity: Alert severity level (low, medium, high, critical).
            message: Human-readable alert message.
            details: Optional dict with metric values, thresholds, etc.

        Returns:
            True if notification was sent successfully.
        """
        ...

    @abstractmethod
    async def test_connection(self) -> bool:
        """Verify the notification channel is configured and reachable."""
        ...

    @property
    @abstractmethod
    def channel_name(self) -> str:
        """Return the name of this notification channel (e.g., 'email')."""
        ...
