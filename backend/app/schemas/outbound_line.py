from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime


class OutboundLineBase(BaseModel):
    phone_number: str = Field(..., min_length=1, max_length=32)
    display_name: str = Field(..., min_length=1, max_length=255)
    is_active: bool = True


class OutboundLineCreate(OutboundLineBase):
    company_id: int


class OutboundLineUpdate(BaseModel):
    display_name: str | None = None
    is_active: bool | None = None


class OutboundLineOut(OutboundLineBase):
    id: int
    company_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class RegisterOutboundLineItem(BaseModel):
    """Minimal outbound line shape accepted from dialer startup registration."""
    model_config = ConfigDict(extra="forbid")
    phone_number: str = Field(..., min_length=1, max_length=32)
    display_name: str | None = Field(default=None, min_length=1, max_length=255)


class RegisterOutboundLinesRequest(BaseModel):
    """Request from dialer app to register available outbound lines."""
    company: str
    outbound_lines: list[RegisterOutboundLineItem]
