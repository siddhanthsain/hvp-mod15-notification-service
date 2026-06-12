from __future__ import annotations
import logging
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v1/notifications/templates", tags=["Templates"])


class AddTemplateRequest(BaseModel):
    event_type: str = Field(..., min_length=3)
    channel: str = Field(..., pattern="^(SMS|EMAIL|WHATSAPP|IN_APP)$")
    subject: str | None = None
    body: str = Field(..., min_length=5)


class RenderRequest(BaseModel):
    event_type: str = Field(..., min_length=3)
    channel: str = Field(..., pattern="^(SMS|EMAIL|WHATSAPP|IN_APP)$")
    variables: dict = Field(default_factory=dict)


@router.get("")
async def list_templates(request: Request):
    return list(request.app.state.template_engine._templates.values())


@router.get("/{event_type}")
async def get_templates_for_event(event_type: str, request: Request):
    return request.app.state.template_engine.list_by_event_type(event_type)


@router.post("", status_code=201)
async def add_template(body: AddTemplateRequest, request: Request):
    try:
        return request.app.state.template_engine.add_template(body.model_dump())
    except ValueError as exc:
        raise HTTPException(409, detail=str(exc))


@router.post("/render")
async def render_template(body: RenderRequest, request: Request):
    result = request.app.state.template_engine.render(
        event_type=body.event_type,
        channel=body.channel,
        variables=body.variables,
    )
    if not result:
        raise HTTPException(
            404, detail=f"No template for event_type={body.event_type} channel={body.channel}"
        )
    return result
