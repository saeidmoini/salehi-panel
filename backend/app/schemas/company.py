from pydantic import BaseModel, Field
from datetime import datetime


class CompanyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=64)
    display_name: str = Field(..., min_length=1, max_length=255)
    is_active: bool = True
    settings: dict = Field(default_factory=dict)


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=64)
    display_name: str | None = None
    is_active: bool | None = None
    settings: dict | None = None


class CompanyDeleteRequest(BaseModel):
    confirm_name: str = Field(..., min_length=1, max_length=64)


class CompanyOut(CompanyBase):
    id: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
