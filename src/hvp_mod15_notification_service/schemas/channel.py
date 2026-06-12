from __future__ import annotations
from pydantic import BaseModel, Field, field_validator
from typing import Literal

ChannelType = Literal["SMS", "EMAIL", "WHATSAPP", "IN_APP"]
RecipientType = Literal[
    "HOSPITAL_COORDINATOR", "PATIENT", "INSURER_ADJUDICATOR", "INSURER_ADMIN", "ADMIN"
]


class ChannelConfig(BaseModel):
    recipient_id: str = Field(..., min_length=1)
    recipient_type: RecipientType
    channels: list[ChannelType] = Field(..., min_length=1)
    email: str | None = Field(None)
    phone: str | None = Field(None)
    is_active: bool = Field(True)

    @field_validator("email")
    @classmethod
    def validate_email(cls, v):
        if v and "@" not in v:
            raise ValueError("Invalid email address")
        return v

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, v):
        if v and not v.replace("+", "").replace(" ", "").isdigit():
            raise ValueError("Phone must be digits with optional + prefix")
        return v


class ChannelConfigResponse(BaseModel):
    channel_id: str
    recipient_id: str
    recipient_type: str
    channels: list[str]
    email: str | None
    phone: str | None
    is_active: bool
    created_at: str
    updated_at: str
