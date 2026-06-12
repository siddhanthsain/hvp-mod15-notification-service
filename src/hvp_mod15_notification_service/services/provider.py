# MOD15-C03 — Notification Providers
# Providers send messages via SMS, Email, WhatsApp, In-app.
# MockProvider: records sends without real delivery (dev/test).
# Production: swap MockProvider with TwilioProvider, SESProvider, etc.

from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class MockProvider:
    """
    Dev/test provider — records sends in memory, never delivers.
    Inject into Dispatcher to test without real SMS/email.
    """

    def __init__(self) -> None:
        self._sent: list[dict] = []

    def send(
        self,
        channel:    str,
        recipient:  str,
        subject:    str | None,
        body:       str,
    ) -> dict:
        record = {
            "channel":     channel,
            "recipient":   recipient,
            "subject":     subject,
            "body":        body,
            "sent_at":     _now(),
            "provider":    "MOCK",
            "provider_id": f"MOCK-{len(self._sent):06d}",
        }
        self._sent.append(record)
        logger.info("MOCK SEND [%s] → %s: %s...", channel, recipient, body[:40])
        return {"success": True, "provider_id": record["provider_id"]}

    @property
    def sent_count(self) -> int:
        return len(self._sent)

    def get_sent(self, channel: str | None = None) -> list[dict]:
        if channel:
            return [s for s in self._sent if s["channel"] == channel]
        return list(self._sent)


class ProviderRegistry:
    """Maps channel types to provider instances."""

    def __init__(self, mock: bool = True) -> None:
        self._mock     = MockProvider()
        self._use_mock = mock

    def get_provider(self, channel: str):
        return self._mock   # In production: return real provider per channel

    @property
    def mock_provider(self) -> MockProvider:
        return self._mock
