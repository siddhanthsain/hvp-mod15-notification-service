from __future__ import annotations
import logging
from fastapi import APIRouter, HTTPException, Query, Request

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/notifications/deliveries", tags=["Deliveries"])


@router.get("")
async def list_deliveries(
    request: Request,
    status: str | None = Query(None),
    channel: str | None = Query(None),
    claim_id: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
):
    return request.app.state.delivery_tracker.list_all(
        status=status,
        channel=channel,
        claim_id=claim_id,
        limit=limit,
    )


@router.get("/stats")
async def delivery_stats(request: Request):
    return request.app.state.delivery_tracker.stats()


@router.get("/{delivery_id}")
async def get_delivery(delivery_id: str, request: Request):
    d = request.app.state.delivery_tracker.get(delivery_id)
    if not d:
        raise HTTPException(404, detail=f"Delivery {delivery_id} not found")
    return d
