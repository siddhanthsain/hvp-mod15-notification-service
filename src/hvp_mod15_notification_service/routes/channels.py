from __future__ import annotations
import logging
from fastapi import APIRouter, HTTPException, Query, Request
from ..schemas.channel import ChannelConfig, ChannelConfigResponse

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/notifications/channels", tags=["Channels"])


@router.post("", response_model=ChannelConfigResponse, status_code=201)
async def upsert_channel(body: ChannelConfig, request: Request):
    return request.app.state.channel_store.upsert(body.model_dump())


@router.get("/{recipient_id}", response_model=ChannelConfigResponse)
async def get_channel(recipient_id: str, request: Request):
    config = request.app.state.channel_store.get_by_recipient(recipient_id)
    if not config:
        raise HTTPException(404, detail=f"No channel config for {recipient_id}")
    return config


@router.get("", response_model=list[ChannelConfigResponse])
async def list_channels(
    request: Request,
    recipient_type: str | None = Query(None),
):
    if recipient_type:
        return request.app.state.channel_store.list_by_type(recipient_type)
    return list(request.app.state.channel_store._configs.values())


@router.delete("/{recipient_id}", status_code=204)
async def deactivate_channel(recipient_id: str, request: Request):
    if not request.app.state.channel_store.deactivate(recipient_id):
        raise HTTPException(404, detail=f"No channel config for {recipient_id}")
