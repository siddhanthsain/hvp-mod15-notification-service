# MOD15-C05 — Primary Notification API
# This is the single endpoint other modules call.
# POST /notify → dispatches + tracks everything automatically.

from __future__ import annotations
import logging
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/notifications", tags=["Notify"])


class NotifyRequest(BaseModel):
    event_type:    str  = Field(..., min_length=3,
                                description="e.g. claim.approved, adjudicator.assigned")
    event_payload: dict = Field(default_factory=dict,
                                description="Variables for template + recipient IDs")
    source_module: str  = Field("", max_length=20)


class NotifyResponse(BaseModel):
    event_type:       str
    source_module:    str
    dispatched_count: int
    delivered:        int
    failed:           int
    notification_ids: list[str]


@router.post("/notify", response_model=NotifyResponse)
async def notify(body: NotifyRequest, request: Request):
    """
    Primary notification endpoint.
    Called by MOD-04/05/06 on claim events.
    Dispatches to all configured recipients and channels.
    Tracks delivery automatically.
    """
    results = request.app.state.dispatcher.dispatch(
        event_type=body.event_type,
        event_payload=body.event_payload,
        channel_store=request.app.state.channel_store,
        template_engine=request.app.state.template_engine,
        provider_registry=request.app.state.provider_registry,
        delivery_tracker=request.app.state.delivery_tracker,
    )

    # Record all results in delivery tracker
    notification_ids = []
    delivered = 0
    failed    = 0
    for r in results:
        d = request.app.state.delivery_tracker.record({
            **r,
            "claim_id": body.event_payload.get("claim_id", ""),
        })
        notification_ids.append(d["delivery_id"])
        if d["status"] == "DELIVERED":
            delivered += 1
        else:
            failed += 1

    logger.info("Notify event=%s source=%s dispatched=%s delivered=%s failed=%s",
                body.event_type, body.source_module, len(results), delivered, failed)

    return NotifyResponse(
        event_type=body.event_type,
        source_module=body.source_module,
        dispatched_count=len(results),
        delivered=delivered,
        failed=failed,
        notification_ids=notification_ids,
    )


@router.get("/claim/{claim_id}")
async def get_notifications_for_claim(claim_id: str, request: Request):
    """All notifications sent for a specific claim."""
    return request.app.state.delivery_tracker.list_all(claim_id=claim_id)


@router.get("/stats")
async def notification_stats(request: Request):
    """Delivery stats dashboard."""
    tracker_stats = request.app.state.delivery_tracker.stats()
    return {
        **tracker_stats,
        "total_channels_configured": request.app.state.channel_store.count,
        "total_templates":           request.app.state.template_engine.total_templates,
    }
