from __future__ import annotations
import logging
from fastapi import APIRouter, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/notifications", tags=["Dispatch"])


class DispatchRequest(BaseModel):
    event_type:    str  = Field(..., min_length=3)
    event_payload: dict = Field(default_factory=dict)


@router.post("/dispatch")
async def dispatch_notification(body: DispatchRequest, request: Request):
    """
    Dispatch notifications for an event.
    Called by MOD-04/05/06 when a claim state changes.
    """
    results = request.app.state.dispatcher.dispatch(
        event_type=body.event_type,
        event_payload=body.event_payload,
        channel_store=request.app.state.channel_store,
        template_engine=request.app.state.template_engine,
        provider_registry=request.app.state.provider_registry,
        delivery_tracker=getattr(request.app.state, "delivery_tracker", None),
    )
    return {
        "event_type":       body.event_type,
        "dispatched_count": len(results),
        "results":          results,
    }
