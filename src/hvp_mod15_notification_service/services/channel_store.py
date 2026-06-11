# MOD15-C01 — Channel Store
# Stores notification channel preferences per recipient.
# Channels: SMS, EMAIL, WHATSAPP, IN_APP.
# Each recipient can have multiple channels.

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Default channels per recipient type
DEFAULT_CHANNELS = {
    "HOSPITAL_COORDINATOR": ["EMAIL", "IN_APP"],
    "PATIENT":              ["SMS"],
    "INSURER_ADJUDICATOR":  ["IN_APP", "EMAIL"],
    "INSURER_ADMIN":        ["EMAIL", "IN_APP"],
    "ADMIN":                ["EMAIL", "IN_APP"],
}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ChannelStore:
    def __init__(self) -> None:
        self._configs: dict[str, dict] = {}   # channel_id → config
        self._by_recipient: dict[str, str] = {}  # recipient_id → channel_id

    def upsert(self, data: dict) -> dict:
        """Create or update channel config for a recipient."""
        recipient_id = data["recipient_id"]
        now          = _now()

        if recipient_id in self._by_recipient:
            channel_id = self._by_recipient[recipient_id]
            config     = self._configs[channel_id]
            config.update({
                "channels":   data.get("channels", config["channels"]),
                "email":      data.get("email",    config.get("email")),
                "phone":      data.get("phone",    config.get("phone")),
                "is_active":  data.get("is_active", config["is_active"]),
                "updated_at": now,
            })
            logger.info("Updated channel config for recipient %s", recipient_id)
            return config

        channel_id = f"CHN-{uuid.uuid4().hex[:8].upper()}"
        config = {
            "channel_id":     channel_id,
            "recipient_id":   recipient_id,
            "recipient_type": data.get("recipient_type", "HOSPITAL_COORDINATOR"),
            "channels":       data.get("channels",
                                       DEFAULT_CHANNELS.get(
                                           data.get("recipient_type", "HOSPITAL_COORDINATOR"),
                                           ["IN_APP"]
                                       )),
            "email":          data.get("email"),
            "phone":          data.get("phone"),
            "is_active":      data.get("is_active", True),
            "created_at":     now,
            "updated_at":     now,
        }
        self._configs[channel_id]         = config
        self._by_recipient[recipient_id]  = channel_id
        logger.info("Created channel config %s for recipient %s channels=%s",
                    channel_id, recipient_id, config["channels"])
        return config

    def get_by_recipient(self, recipient_id: str) -> dict | None:
        channel_id = self._by_recipient.get(recipient_id)
        return self._configs.get(channel_id) if channel_id else None

    def get(self, channel_id: str) -> dict | None:
        return self._configs.get(channel_id)

    def list_by_type(self, recipient_type: str) -> list[dict]:
        return [c for c in self._configs.values()
                if c["recipient_type"] == recipient_type and c["is_active"]]

    def deactivate(self, recipient_id: str) -> bool:
        config = self.get_by_recipient(recipient_id)
        if not config:
            return False
        config["is_active"]  = False
        config["updated_at"] = _now()
        return True

    def get_channels_for_recipient(self, recipient_id: str) -> list[str]:
        """Returns list of active channels for a recipient. Uses defaults if none configured."""
        config = self.get_by_recipient(recipient_id)
        if config and config["is_active"]:
            return config["channels"]
        return []

    @property
    def count(self) -> int:
        return len(self._configs)
