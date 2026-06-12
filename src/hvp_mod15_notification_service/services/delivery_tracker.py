# MOD15-C04 — Delivery Tracker
# Tracks every notification send — PENDING → DELIVERED / FAILED / DEAD.
# Append-only for compliance. Retries recorded.

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Literal

logger = logging.getLogger(__name__)

DeliveryStatus = Literal["PENDING", "DELIVERED", "FAILED", "DEAD"]
MAX_RETRIES    = 3


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class DeliveryTracker:
    def __init__(self) -> None:
        self._deliveries: dict[str, dict] = {}

    def record(self, dispatch_record: dict) -> dict:
        """Record a dispatch attempt."""
        delivery_id = f"DLV-{uuid.uuid4().hex[:8].upper()}"
        claim_id    = dispatch_record.get("event_payload", {}).get("claim_id") \
                      or dispatch_record.get("claim_id", "")
        delivery    = {
            "delivery_id":  delivery_id,
            "event_type":   dispatch_record.get("event_type", ""),
            "recipient_id": dispatch_record.get("recipient_id", ""),
            "channel":      dispatch_record.get("channel", ""),
            "contact":      dispatch_record.get("contact", ""),
            "claim_id":     claim_id,
            "status":       "DELIVERED" if dispatch_record.get("success") else "FAILED",
            "retry_count":  0,
            "provider_id":  dispatch_record.get("provider_id"),
            "recorded_at":  _now(),
            "updated_at":   _now(),
        }
        self._deliveries[delivery_id] = delivery
        logger.info("Delivery %s status=%s recipient=%s channel=%s",
                    delivery_id, delivery["status"],
                    delivery["recipient_id"], delivery["channel"])
        return delivery

    def mark_failed(self, delivery_id: str, error: str = "") -> dict | None:
        d = self._deliveries.get(delivery_id)
        if not d:
            return None
        d["retry_count"] += 1
        d["status"]       = "DEAD" if d["retry_count"] >= MAX_RETRIES else "FAILED"
        d["last_error"]   = error
        d["updated_at"]   = _now()
        return d

    def mark_delivered(self, delivery_id: str) -> dict | None:
        d = self._deliveries.get(delivery_id)
        if not d:
            return None
        d["status"]     = "DELIVERED"
        d["updated_at"] = _now()
        return d

    def get(self, delivery_id: str) -> dict | None:
        return self._deliveries.get(delivery_id)

    def list_all(
        self,
        status:    str | None = None,
        channel:   str | None = None,
        claim_id:  str | None = None,
        limit:     int        = 100,
    ) -> list[dict]:
        entries = list(self._deliveries.values())
        if status:
            entries = [e for e in entries if e["status"] == status]
        if channel:
            entries = [e for e in entries if e["channel"] == channel]
        if claim_id:
            entries = [e for e in entries if e["claim_id"] == claim_id]
        return entries[-limit:]

    def stats(self) -> dict:
        entries   = list(self._deliveries.values())
        total     = len(entries)
        by_status = {}
        by_channel = {}
        for e in entries:
            by_status[e["status"]]    = by_status.get(e["status"], 0) + 1
            by_channel[e["channel"]]  = by_channel.get(e["channel"], 0) + 1
        return {
            "total":      total,
            "delivered":  by_status.get("DELIVERED", 0),
            "failed":     by_status.get("FAILED", 0),
            "dead":       by_status.get("DEAD", 0),
            "pending":    by_status.get("PENDING", 0),
            "by_channel": by_channel,
        }

    @property
    def total(self) -> int:
        return len(self._deliveries)
