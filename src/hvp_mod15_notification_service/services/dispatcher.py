# MOD15-C03 — Notification Dispatcher
# Receives an event, finds recipients, renders messages, dispatches via providers.
# Every dispatch is logged to DeliveryTracker (C04).

from __future__ import annotations

import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

# Maps event_type → list of recipient_id fields in the payload
EVENT_RECIPIENT_MAP: dict[str, list[str]] = {
    "claim.submitted":     ["hospital_coordinator_id", "patient_abha"],
    "claim.approved":      ["hospital_coordinator_id", "patient_abha"],
    "claim.rejected":      ["hospital_coordinator_id", "patient_abha"],
    "claim.queried":       ["hospital_coordinator_id"],
    "adjudicator.assigned": ["adjudicator_id"],
    "auth.login_success":  ["actor_id"],
}


class Dispatcher:
    """
    Routes events to the correct recipients and channels.
    Uses ChannelStore for preferences, TemplateEngine for messages,
    ProviderRegistry for delivery.
    """

    def dispatch(
        self,
        event_type:      str,
        event_payload:   dict,
        channel_store,
        template_engine,
        provider_registry,
        delivery_tracker=None,
    ) -> list[dict]:
        """
        Dispatch a notification for an event.
        Returns list of dispatch records (one per recipient per channel).
        """
        recipient_fields = EVENT_RECIPIENT_MAP.get(event_type, [])
        results          = []

        # Collect all recipient IDs from the payload
        recipient_ids = []
        for field in recipient_fields:
            rid = event_payload.get(field)
            if rid:
                recipient_ids.append(rid)

        if not recipient_ids:
            logger.warning("No recipients found for event_type=%s payload_keys=%s",
                           event_type, list(event_payload.keys()))

        for recipient_id in recipient_ids:
            channels = channel_store.get_channels_for_recipient(recipient_id)
            if not channels:
                logger.warning("No channels configured for recipient %s", recipient_id)
                continue

            for channel in channels:
                rendered = template_engine.render(event_type, channel, event_payload)
                if not rendered:
                    logger.warning("No template for event=%s channel=%s", event_type, channel)
                    continue

                # Get recipient contact info
                config   = channel_store.get_by_recipient(recipient_id)
                contact  = self._get_contact(channel, config)

                provider = provider_registry.get_provider(channel)
                result   = provider.send(
                    channel=channel,
                    recipient=contact or recipient_id,
                    subject=rendered.get("subject"),
                    body=rendered["body"],
                )

                dispatch_record = {
                    "event_type":    event_type,
                    "recipient_id":  recipient_id,
                    "channel":       channel,
                    "template_id":   rendered["template_id"],
                    "contact":       contact or recipient_id,
                    "success":       result.get("success", False),
                    "provider_id":   result.get("provider_id"),
                    "dispatched_at": datetime.now(timezone.utc).isoformat(),
                }
                results.append(dispatch_record)

                if delivery_tracker:
                    delivery_tracker.record(dispatch_record)

        return results

    @staticmethod
    def _get_contact(channel: str, config: dict | None) -> str | None:
        if not config:
            return None
        if channel == "SMS" and config.get("phone"):
            return config["phone"]
        if channel in ("EMAIL",) and config.get("email"):
            return config["email"]
        return None
